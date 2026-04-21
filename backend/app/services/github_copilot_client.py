import asyncio
import itertools
import random
import time
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.services.available_models import CONTROL_MODEL


class CallBudgetExceeded(RuntimeError):
    """Raised when the hard call ceiling is reached."""


_BASE_URL = "https://api.together.xyz/v1"
_TIMEOUT = 120.0

# ---------------------------------------------------------------------------
# Retry / rotation / adaptive pacing state (mirrors run_benchmark.py)
# ---------------------------------------------------------------------------

_MAX_RETRIES = 8
_BASE_DELAY = 10.0  # seconds base for 5xx backoff
_PACING_MIN = 0.1
_PACING_MAX = 20.0
_PACING_STEP_UP = 3.0  # increase on 429
_PACING_STEP_DOWN = 0.5  # decrease on success

_call_counter: int = 0
_call_total: int = 0

_model_pace: dict[str, float] = {}
_rotation_pool: list[str] = []
_pool_cycle: itertools.cycle | None = None


def _get_pace(model: str) -> float:
    return _model_pace.get(model, _PACING_MIN)


def _bump_pace(model: str) -> None:
    current = _model_pace.get(model, _PACING_MIN)
    _model_pace[model] = min(current + _PACING_STEP_UP, _PACING_MAX)


def _decay_pace(model: str) -> None:
    current = _model_pace.get(model, _PACING_MIN)
    if current > _PACING_MIN:
        _model_pace[model] = max(current - _PACING_STEP_DOWN, _PACING_MIN)


def _next_pool_model(requested: str) -> str:
    if _pool_cycle is None or not _rotation_pool:
        return requested
    candidate = next(_pool_cycle)
    if candidate == requested and len(_rotation_pool) > 1:
        candidate = next(_pool_cycle)
    return candidate


def init_rotation_pool(models: list[str]) -> None:
    """Build the model rotation pool. Called once at pipeline start."""
    global _rotation_pool, _pool_cycle  # noqa: PLW0603
    _rotation_pool = list(dict.fromkeys(models))  # dedupe, preserve order
    _pool_cycle = itertools.cycle(_rotation_pool)
    _model_pace.clear()


def set_call_budget(counter: int, total: int) -> None:
    """Set the progress counter for [N/M] tags in log lines."""
    global _call_counter, _call_total  # noqa: PLW0603
    _call_counter = counter
    _call_total = total


def reset_call_budget() -> None:
    global _call_counter, _call_total  # noqa: PLW0603
    _call_counter = 0
    _call_total = 0


# Models that do not accept a temperature parameter (reasoning models).
_NO_TEMPERATURE_MODELS = {
    "deepseek-ai/DeepSeek-R1",
}

# Together AI pricing (USD per million tokens, input/output).
_COST_PER_M: dict[str, tuple[float, float]] = {
    # Setup / control / reference models
    "deepseek-ai/DeepSeek-V3": (1.25, 1.25),
    "deepseek-ai/DeepSeek-R1": (3.00, 7.00),
    "Qwen/Qwen2.5-7B-Instruct-Turbo": (0.30, 0.30),
    "meta-llama/Llama-3.3-70B-Instruct-Turbo": (0.88, 0.88),
    # Comparison pool
    "LiquidAI/LFM2-24B-A2B": (0.03, 0.03),
    "openai/gpt-oss-20b": (0.05, 0.05),
    "google/gemma-3n-E4B-it": (0.06, 0.06),
    "arize-ai/qwen-2-1.5b-instruct": (0.10, 0.10),
    "meta-llama/Meta-Llama-3-8B-Instruct-Lite": (0.10, 0.10),
    "essentialai/rnj-1-instruct": (0.15, 0.15),
    "openai/gpt-oss-120b": (0.15, 0.15),
    "Qwen/Qwen3-235B-A22B-Instruct-2507-tput": (0.20, 0.20),
    "MiniMaxAI/MiniMax-M2.5": (0.30, 0.30),
    "MiniMaxAI/MiniMax-M2.7": (0.30, 0.30),
    "deepseek-ai/DeepSeek-V3.1": (0.60, 0.60),
    "Qwen/Qwen3.5-397B-A17B": (0.60, 0.60),
    "zai-org/GLM-5": (1.00, 1.00),
    "deepcogito/cogito-v2-1-671b": (1.25, 1.25),
    "zai-org/GLM-5.1": (1.40, 1.40),
}


# ---------------------------------------------------------------------------
# Token ledger
# ---------------------------------------------------------------------------


@dataclass
class _ModelUsage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


_ledger: dict[str, _ModelUsage] = {}


def ledger_reset() -> None:
    """Clear accumulated token counts (call at the start of each benchmark case)."""
    _ledger.clear()


def ledger_summary() -> dict[str, dict]:
    """Return per-model token counts and costs, plus a grand total."""
    rows: dict[str, dict] = {}
    total_cost = 0.0
    total_prompt = 0
    total_completion = 0
    total_calls = 0

    for model, usage in sorted(_ledger.items()):
        in_price, out_price = _COST_PER_M.get(model, (0.0, 0.0))
        cost = (usage.prompt_tokens * in_price + usage.completion_tokens * out_price) / 1_000_000
        rows[model] = {
            "calls": usage.calls,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "cost_usd": round(cost, 6),
        }
        total_cost += cost
        total_prompt += usage.prompt_tokens
        total_completion += usage.completion_tokens
        total_calls += usage.calls

    rows["__total__"] = {
        "calls": total_calls,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "cost_usd": round(total_cost, 6),
    }
    return rows


def ledger_report(label: str = "") -> str:
    """Return a formatted cost table string suitable for printing."""
    summary = ledger_summary()
    total = summary.pop("__total__", {})
    lines: list[str] = []
    header = f"  Cost ledger{f' [{label}]' if label else ''}"
    lines.append(header)
    lines.append(f"  {'Model':<46} {'Calls':>5}  {'Prompt':>8}  {'Compl':>8}  {'Cost':>9}")
    lines.append(f"  {'-' * 46} {'-' * 5}  {'-' * 8}  {'-' * 8}  {'-' * 9}")
    for model, row in summary.items():
        lines.append(
            f"  {model:<46} {row['calls']:>5}  {row['prompt_tokens']:>8,}"
            f"  {row['completion_tokens']:>8,}  ${row['cost_usd']:>8.4f}"
        )
    if total:
        lines.append(
            f"  {'TOTAL':<46} {total['calls']:>5}  {total['prompt_tokens']:>8,}"
            f"  {total['completion_tokens']:>8,}  ${total['cost_usd']:>8.4f}"
        )
    return "\n".join(lines)


def _update_ledger(model: str, usage: dict) -> None:
    if model not in _ledger:
        _ledger[model] = _ModelUsage()
    entry = _ledger[model]
    entry.calls += 1
    entry.prompt_tokens += usage.get("prompt_tokens", 0)
    entry.completion_tokens += usage.get("completion_tokens", 0)


# ---------------------------------------------------------------------------
# Chat completion with retry, rotation, and per-call logging
# ---------------------------------------------------------------------------


async def chat_completion(
    messages: list[dict],
    model: str = CONTROL_MODEL,
    response_format: dict | None = None,
    temperature: float = 0.2,
    stream_id: str | None = None,
) -> str:
    """Send a chat completion request to Together AI with retry/rotation.

    When ``stream_id`` is provided, detailed per-call logs are written to
    ``log_stream`` so they appear in the frontend pipeline console.
    """
    from app.services import log_stream  # local import to avoid circular deps

    global _call_counter  # noqa: PLW0603

    # Enforce hard call ceiling when a budget is active
    if _call_total > 0 and _call_counter >= _call_total:
        raise CallBudgetExceeded(f"Call budget exhausted: {_call_counter}/{_call_total} calls used")

    payload_chars = sum(len(m.get("content", "")) for m in messages)
    last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    prompt_preview = last_user[:80].replace("\n", " ")
    counter_tag = (
        f"{_call_counter + 1}/{_call_total}" if _call_total > 0 else f"#{_call_counter + 1}"
    )

    def _log(msg: str) -> None:
        if stream_id:
            log_stream.log(stream_id, msg)

    _log(
        f"  >> [{counter_tag}] {model} | {payload_chars} chars"
        f" | temp={temperature} | prompt: {prompt_preview!r}..."
    )

    if not settings.TOGETHER_API_KEY:
        raise RuntimeError(
            "TOGETHER_API_KEY is not set. "
            "Set it via `dokku config:set <app> TOGETHER_API_KEY=<key>` in production "
            "or add it to your .env file for local development."
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
    }

    current_model = model
    hard_attempt = 0
    tried_in_cycle: set[str] = set()

    while True:
        call_payload: dict = {
            "model": current_model,
            "messages": messages,
        }
        if current_model not in _NO_TEMPERATURE_MODELS:
            call_payload["temperature"] = temperature
        if response_format:
            call_payload["response_format"] = response_format

        t_start = time.time()
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(
                    f"{_BASE_URL}/chat/completions",
                    json=call_payload,
                    headers=headers,
                )
                response.raise_for_status()

            data = response.json()
            _update_ledger(current_model, data.get("usage", {}))
            result = data["choices"][0]["message"]["content"]

            elapsed = time.time() - t_start
            _call_counter += 1
            preview = result[:100].replace("\n", " ")
            suffix = f" [rotated from {model}]" if current_model != model else ""
            pace = _get_pace(current_model)
            _log(
                f"  OK [{counter_tag}] {current_model}{suffix}"
                f" done in {elapsed:.1f}s | response: {preview!r}..."
            )
            _decay_pace(current_model)
            if pace > _PACING_MIN:
                _log(f"    [pace-] {current_model}: pacing {pace:.1f}s")
            await asyncio.sleep(pace)
            return result

        except Exception as exc:
            elapsed = time.time() - t_start
            exc_str = str(exc)
            is_rate_limit = "429" in exc_str
            is_payload = "413" in exc_str
            is_server_error = any(code in exc_str for code in ("500", "502", "503", "504"))
            is_timeout = (
                any(t in type(exc).__name__ for t in ("Timeout", "TimeoutError", "ReadTimeout"))
                or "ReadTimeout" in exc_str
                or "ConnectTimeout" in exc_str
            )

            if is_payload:
                _log(
                    f"  ERR [{counter_tag}] [FATAL] 413 - payload too large"
                    f" ({payload_chars} chars)."
                )
                raise

            if is_rate_limit:
                _log(f"  ERR [{counter_tag}] 429 | {current_model} | {exc_str[:80]}")
                _bump_pace(current_model)
                _log(f"    [pace+] {current_model}: pacing -> {_get_pace(current_model):.1f}s")
                tried_in_cycle.add(current_model)
                if _rotation_pool and len(tried_in_cycle) >= len(_rotation_pool):
                    wait = 30.0 + random.uniform(0, 10)
                    _log(
                        f"    [cooldown] all {len(_rotation_pool)} models rate-limited,"
                        f" waiting {wait:.0f}s ..."
                    )
                    await asyncio.sleep(wait)
                    tried_in_cycle.clear()
                    current_model = model
                elif _rotation_pool:
                    next_model = _next_pool_model(current_model)
                    _log(f"    [rotate] 429 on {current_model} -> {next_model}")
                    current_model = next_model
                else:
                    # No rotation pool — simple backoff
                    wait = _BASE_DELAY + random.uniform(0, 5)
                    _log(f"    [backoff] 429, waiting {wait:.0f}s ...")
                    await asyncio.sleep(wait)
                continue

            # Hard failure (5xx, timeout)
            hard_attempt += 1
            _log(
                f"  ERR [{counter_tag}] hard attempt {hard_attempt}/{_MAX_RETRIES}"
                f" | {current_model} | {type(exc).__name__}: {exc_str[:100]}"
            )
            if (is_server_error or is_timeout) and hard_attempt < _MAX_RETRIES:
                delay = _BASE_DELAY * (2 ** (hard_attempt - 1)) + random.uniform(0, 2)
                reason = "timeout" if is_timeout else "5xx"
                _log(
                    f"    [retry {hard_attempt}/{_MAX_RETRIES}] {reason}, waiting {delay:.0f}s ..."
                )
                await asyncio.sleep(delay)
                continue
            raise
