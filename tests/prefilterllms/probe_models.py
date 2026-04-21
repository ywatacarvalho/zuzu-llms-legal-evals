"""
LLM Speed & Availability Probe -- Together AI

Fetches the full Together AI model catalog, filters for cheap chat models
(input price <= MAX_INPUT_PRICE_PER_M), then probes each one with a short
legal reasoning prompt, measuring latency and availability.
Results are written to tests/prefilterllms/results.json.

Usage:
    python tests/prefilterllms/probe_models.py
    python tests/prefilterllms/probe_models.py --concurrency 4
    python tests/prefilterllms/probe_models.py --timeout 30
    python tests/prefilterllms/probe_models.py --max-price 2.0
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "backend"))
sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(str(_REPO_ROOT / ".env"))

from app.core.config import settings  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Maximum input price per million tokens in USD (filters out expensive models)
_DEFAULT_MAX_PRICE = 2.0

_TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
_TOGETHER_MODELS_URL = "https://api.together.xyz/v1/models"

# Short legal prompt -- representative of actual LexEval usage
_PROBE_PROMPT = (
    "In one paragraph, explain whether an oral promise made in consideration of marriage "
    "is enforceable under a typical statute of frauds."
)

# Models that don't accept a temperature parameter (reasoning/chain-of-thought models)
_NO_TEMPERATURE_MODELS: set[str] = {
    "deepseek-ai/DeepSeek-R1",
    "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
}

RESULTS_DIR = Path(__file__).resolve().parent
RESULTS_FILE = RESULTS_DIR / "results.json"


# ---------------------------------------------------------------------------
# Fetch catalog
# ---------------------------------------------------------------------------


async def _fetch_cheap_chat_models(max_price: float) -> list[dict]:
    """
    Pull the Together AI model catalog and return chat models whose
    input price is at or below max_price (USD per million tokens).
    """
    import httpx

    headers = {
        "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(_TOGETHER_MODELS_URL, headers=headers)
        r.raise_for_status()
        catalog = r.json()

    cheap_chat = []
    for m in catalog:
        # Keep only language/chat models
        model_type = m.get("type", "").lower()
        if model_type not in ("chat", "language"):
            continue
        # Filter by input price
        pricing = m.get("pricing", {})
        input_price = pricing.get("input")  # USD per million tokens
        if input_price is None:
            continue
        try:
            if float(input_price) > max_price:
                continue
        except (TypeError, ValueError):
            continue
        cheap_chat.append(
            {
                "id": m["id"],
                "display_name": m.get("display_name", m["id"]),
                "input_price": float(input_price),
                "output_price": float(pricing.get("output", 0)),
            }
        )

    return sorted(cheap_chat, key=lambda x: x["input_price"])


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ProbeResult:
    model: str
    status: str  # ok | error | timeout
    latency_s: float | None = None
    response_preview: str = ""
    error: str = ""
    tokens_per_sec: float | None = None
    input_price: float | None = None


# ---------------------------------------------------------------------------
# Probe a single model
# ---------------------------------------------------------------------------


def _parse_error(r) -> str:  # type: ignore[no-untyped-def]
    if not r.text:
        return f"HTTP {r.status_code}: (empty body)"
    try:
        return r.json().get("error", {}).get("message", r.text[:120])
    except Exception:
        return r.text[:120]


async def probe_model(
    model: str,
    input_price: float | None,
    timeout: float,
    semaphore: asyncio.Semaphore,
) -> ProbeResult:
    import httpx

    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise legal expert."},
            {"role": "user", "content": _PROBE_PROMPT},
        ],
    }
    if model not in _NO_TEMPERATURE_MODELS:
        payload["temperature"] = 0.2

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
    }

    _max_retries = 3
    _retry_delay = 5.0

    async with semaphore:
        t0 = time.time()
        for attempt in range(1, _max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    r = await client.post(_TOGETHER_API_URL, json=payload, headers=headers)
                elapsed = time.time() - t0

                if r.status_code == 429 or (r.status_code != 200 and not r.text):
                    if attempt < _max_retries:
                        await asyncio.sleep(_retry_delay * attempt)
                        continue
                    return ProbeResult(
                        model=model,
                        status="error",
                        latency_s=round(elapsed, 2),
                        error=f"HTTP {r.status_code}: rate limited",
                        input_price=input_price,
                    )

                if r.status_code != 200:
                    return ProbeResult(
                        model=model,
                        status="error",
                        latency_s=round(elapsed, 2),
                        error=f"HTTP {r.status_code}: {_parse_error(r)}",
                        input_price=input_price,
                    )

                data = r.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                completion_tokens = usage.get("completion_tokens", 0)
                tps = completion_tokens / elapsed if elapsed > 0 and completion_tokens > 0 else None

                return ProbeResult(
                    model=model,
                    status="ok",
                    latency_s=round(elapsed, 2),
                    response_preview=content[:120].replace("\n", " "),
                    tokens_per_sec=round(tps, 1) if tps else None,
                    input_price=input_price,
                )

            except TimeoutError:
                return ProbeResult(
                    model=model,
                    status="timeout",
                    latency_s=timeout,
                    error=f"Timed out after {timeout}s",
                    input_price=input_price,
                )
            except Exception as exc:
                elapsed = time.time() - t0
                return ProbeResult(
                    model=model,
                    status="error",
                    latency_s=round(elapsed, 2),
                    error=str(exc)[:200],
                    input_price=input_price,
                )

        elapsed = time.time() - t0
        return ProbeResult(
            model=model,
            status="error",
            latency_s=round(elapsed, 2),
            error="all retries exhausted",
            input_price=input_price,
        )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _status_icon(status: str) -> str:
    return {"ok": "OK", "error": "ERR", "timeout": "TMO"}.get(status, "?")


def _print_results(results: list[ProbeResult], max_price: float) -> None:
    ok = [r for r in results if r.status == "ok"]
    errors = [r for r in results if r.status == "error"]
    timeouts = [r for r in results if r.status == "timeout"]

    print(f"\n{'=' * 80}")
    print(f"RESULTS  | {len(ok)} ok, {len(errors)} errors, {len(timeouts)} timeouts")
    print(f"{'=' * 80}")

    print("\nFAST MODELS (ok, sorted by latency):")
    print(f"  {'Model':<55} {'$/M in':>7}  {'Latency':>8}  {'Tok/s':>6}")
    print(f"  {'-' * 55} {'-' * 7}  {'-' * 8}  {'-' * 6}")
    for r in sorted(ok, key=lambda x: x.latency_s or 9999):
        price = f"${r.input_price:.3f}" if r.input_price is not None else "   n/a"
        tps = f"{r.tokens_per_sec:.0f}" if r.tokens_per_sec else "  n/a"
        print(f"  {r.model:<55} {price:>7}  {r.latency_s:>7.1f}s  {tps:>6}")

    if timeouts:
        print("\nTIMED OUT:")
        for r in timeouts:
            print(f"  TMO  {r.model}")

    if errors:
        print("\nERRORS:")
        for r in errors:
            print(f"  ERR  {r.model}: {r.error[:80]}")

    print(f"\n{'=' * 80}")
    fast = [r for r in ok if (r.latency_s or 999) < 30]
    print(f"RECOMMENDATION | ok, latency < 30s, price <= ${max_price}/M:")
    for r in sorted(fast, key=lambda x: x.latency_s or 9999):
        print(f'  "{r.model}",  # ${r.input_price:.3f}/M  {r.latency_s:.1f}s')


async def _async_main(timeout: float, concurrency: int, max_price: float) -> None:
    import httpx

    print(f"Fetching Together AI model catalog (max input price: ${max_price}/M tokens)...")
    try:
        catalog = await _fetch_cheap_chat_models(max_price)
    except httpx.HTTPError as exc:
        print(f"Failed to fetch catalog: {exc}")
        sys.exit(1)

    print(f"Found {len(catalog)} eligible models. Probing...")
    print(f"Timeout={timeout}s  |  Concurrency={concurrency}\n")

    semaphore = asyncio.Semaphore(concurrency)
    tasks = [probe_model(m["id"], m["input_price"], timeout, semaphore) for m in catalog]
    results: list[ProbeResult] = []

    for coro in asyncio.as_completed(tasks):
        r = await coro
        icon = _status_icon(r.status)
        lat = f"{r.latency_s:.1f}s" if r.latency_s is not None else "  n/a"
        price = f"${r.input_price:.3f}/M" if r.input_price is not None else "       "
        print(f"  {icon}  {r.model:<55} {price}  {lat}")
        results.append(r)

    _print_results(results, max_price)

    output = [
        {
            "model": r.model,
            "status": r.status,
            "latency_s": r.latency_s,
            "tokens_per_sec": r.tokens_per_sec,
            "input_price_per_m": r.input_price,
            "response_preview": r.response_preview,
            "error": r.error,
        }
        for r in sorted(results, key=lambda x: x.latency_s or 9999)
    ]
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nFull results written to {RESULTS_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe Together AI cheap chat models for speed and availability"
    )
    parser.add_argument(
        "--timeout", type=float, default=45.0, help="Per-model timeout in seconds (default: 45)"
    )
    parser.add_argument("--concurrency", type=int, default=6, help="Parallel probes (default: 6)")
    parser.add_argument(
        "--max-price",
        type=float,
        default=_DEFAULT_MAX_PRICE,
        help=f"Max input price in USD per million tokens (default: {_DEFAULT_MAX_PRICE})",
    )
    args = parser.parse_args()
    asyncio.run(_async_main(args.timeout, args.concurrency, args.max_price))


if __name__ == "__main__":
    main()
