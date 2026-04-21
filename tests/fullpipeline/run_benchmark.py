"""
LexEval Full-Pipeline Benchmark Runner

Runs the complete RRD-compliant pipeline for each benchmark legal case:
  Stage 1  PDF text extraction
  Stage 2  Rubric construction (setup responses, clustering, recursive refinement)
  Stage 3  Comparison response generation (5 models x 40 each)
  Stage 4  Analysis (embed, cluster, score, rank under 3 weighting modes)
  Stage 5  Write JSON artifacts to tests/fullpipeline/results/

Usage:
    cd <repo-root>
    python -m tests.fullpipeline.run_benchmark                 # all 3 cases
    python -m tests.fullpipeline.run_benchmark --case anglemire # single case
    python -m tests.fullpipeline.run_benchmark --dry-run        # validate config only

Requires:
    - TOGETHER_API_KEY set in .env or environment
    - sentence-transformers model available (downloads on first run)
"""

import argparse
import asyncio
import importlib.util as _ilu
import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

# Ensure the backend package and repo root are importable
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "backend"))
sys.path.insert(0, str(_REPO_ROOT))

_conftest_path = Path(__file__).resolve().parent / "conftest.py"
_spec = _ilu.spec_from_file_location("conftest", _conftest_path)
_conftest = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_conftest)  # type: ignore[union-attr]

BENCHMARK_CASES = _conftest.BENCHMARK_CASES
COMPARISON_MODELS = _conftest.COMPARISON_MODELS
DOCUMENTS_DIR = _conftest.DOCUMENTS_DIR
RESPONSES_PER_MODEL = _conftest.RESPONSES_PER_MODEL
RESULTS_DIR = _conftest.RESULTS_DIR
BenchmarkCase = _conftest.BenchmarkCase

# ---------------------------------------------------------------------------
# Monkey-patch chat_completion with retry + backoff for rate limits
# ---------------------------------------------------------------------------

_MAX_RETRIES = 8
_BASE_DELAY = 10.0  # seconds base for 5xx backoff
_PACING_MIN = 0.1  # minimum pacing per model
_PACING_MAX = 20.0  # maximum pacing per model
_PACING_STEP_UP = 3.0  # increase on 429
_PACING_STEP_DOWN = 0.5  # decrease on success
_call_counter = 0
_call_total = 0

# Adaptive per-model pacing state
_model_pace: dict[str, float] = {}


def _get_pace(model: str) -> float:
    return _model_pace.get(model, _PACING_MIN)


def _bump_pace(model: str) -> None:
    """Increase pacing for a model after a 429."""
    current = _model_pace.get(model, _PACING_MIN)
    _model_pace[model] = min(current + _PACING_STEP_UP, _PACING_MAX)
    print(f"    [pace+] {model}: {current:.1f}s -> {_model_pace[model]:.1f}s")


def _decay_pace(model: str) -> None:
    """Decrease pacing for a model after a successful call."""
    current = _model_pace.get(model, _PACING_MIN)
    if current > _PACING_MIN:
        _model_pace[model] = max(current - _PACING_STEP_DOWN, _PACING_MIN)
        print(f"    [pace-] {model}: {current:.1f}s -> {_model_pace[model]:.1f}s")


# ---------------------------------------------------------------------------
# Model rotation pools — on 429 we rotate to next model instead of waiting
# ---------------------------------------------------------------------------
import itertools as _itertools  # noqa: E402

from app.services.available_models import CONTROL_MODEL  # noqa: E402

# Populated after rubric_service is imported (see below)
_SETUP_MODEL_POOL: list[str] = []
_setup_pool_cycle: "_itertools.cycle[str] | None" = None  # type: ignore[type-arg]


def _next_pool_model(requested: str) -> str:
    """Return next model in the rotation pool (skips requested to avoid immediate retry)."""
    if _setup_pool_cycle is None or not _SETUP_MODEL_POOL:
        return requested
    candidate = next(_setup_pool_cycle)
    if candidate == requested and len(_SETUP_MODEL_POOL) > 1:
        candidate = next(_setup_pool_cycle)
    return candidate


def _install_retry_wrapper() -> None:
    """Wrap the GitHub Copilot client: rotate model on 429, backoff on 5xx."""
    import app.services.github_copilot_client as client_mod

    _original = client_mod.chat_completion

    async def _chat_completion_with_retry(
        messages: list[dict],
        model: str = CONTROL_MODEL,
        response_format: dict | None = None,
        temperature: float = 0.2,
    ) -> str:
        global _call_counter  # noqa: PLW0603

        payload_chars = sum(len(m.get("content", "")) for m in messages)
        last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        prompt_preview = last_user[:80].replace("\n", " ")
        counter_tag = (
            f"{_call_counter + 1}/{_call_total}" if _call_total > 0 else f"#{_call_counter + 1}"
        )

        current_model = model
        print(
            f"  >> [{counter_tag}] {current_model} | {payload_chars} chars"
            f" | temp={temperature} | prompt: {prompt_preview!r}..."
        )

        # 429s use unlimited rotation+cooldown loop; hard failures use attempt counter
        hard_attempt = 0
        tried_in_cycle: set[str] = set()
        while True:
            t_start = time.time()
            try:
                result = await _original(
                    messages=messages,
                    model=current_model,
                    response_format=response_format,
                    temperature=temperature,
                )
                elapsed = time.time() - t_start
                _call_counter += 1
                preview = result[:100].replace("\n", " ")
                suffix = f" [rotated from {model}]" if current_model != model else ""
                pace = _get_pace(current_model)
                print(
                    f"  OK [{counter_tag}] {current_model}{suffix}"
                    f" done in {elapsed:.1f}s | response: {preview!r}..."
                )
                _decay_pace(current_model)
                print(f"    pacing {pace:.1f}s ...")
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
                    print(
                        f"  ERR [{counter_tag}] [FATAL] 413 - payload too large"
                        f" ({payload_chars} chars)."
                    )
                    raise
                if is_rate_limit:
                    # 429: rotate models, cooldown if all exhausted — does NOT consume hard_attempt
                    print(f"  ERR [{counter_tag}] 429 | {current_model} | {exc_str[:80]}")
                    _bump_pace(current_model)
                    tried_in_cycle.add(current_model)
                    if len(tried_in_cycle) >= len(_SETUP_MODEL_POOL):
                        wait = 30.0 + random.uniform(0, 10)
                        print(
                            f"    [cooldown] all {len(_SETUP_MODEL_POOL)} models rate-limited,"
                            f" waiting {wait:.0f}s ..."
                        )
                        await asyncio.sleep(wait)
                        tried_in_cycle.clear()
                        current_model = model
                    else:
                        next_model = _next_pool_model(current_model)
                        print(f"    [rotate] 429 on {current_model} -> {next_model}")
                        current_model = next_model
                    continue
                # Hard failure (5xx, timeout): consume attempt counter
                hard_attempt += 1
                print(
                    f"  ERR [{counter_tag}] hard attempt {hard_attempt}/{_MAX_RETRIES}"
                    f" | {current_model} | {type(exc).__name__}: {exc_str[:100]}"
                )
                if (is_server_error or is_timeout) and hard_attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2 ** (hard_attempt - 1)) + random.uniform(0, 2)
                    reason = "timeout" if is_timeout else "5xx"
                    print(
                        f"    [retry {hard_attempt}/{_MAX_RETRIES}] {reason},"
                        f" waiting {delay:.0f}s ..."
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

    client_mod.chat_completion = _chat_completion_with_retry


_install_retry_wrapper()

# ---------------------------------------------------------------------------
# Cost ledger helpers (imported after client is set up)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Patch rubric_service: reduce concurrency + make asyncio.gather sequential
# ---------------------------------------------------------------------------
import app.services.rubric_service as _rs  # noqa: E402
from app.services.available_models import SETUP_MODELS as _SETUP_MODELS_LIST  # noqa: E402
from app.services.github_copilot_client import ledger_report, ledger_reset  # noqa: E402

_rs._SETUP_RESPONSES_PER_MODEL = 25  # 100 total across 4 models
_rs._MAX_REJECTED_PROPOSALS = 5  # stop sooner to reduce total call count

# Build the rotation pool: all setup models + control model
# Used by the retry wrapper to rotate on 429 instead of waiting
_SETUP_MODEL_POOL = [m.id for m in _SETUP_MODELS_LIST] + [_rs._CONTROL_MODEL]
_SETUP_MODEL_POOL = list(dict.fromkeys(_SETUP_MODEL_POOL))  # dedupe, preserve order
_setup_pool_cycle = _itertools.cycle(_SETUP_MODEL_POOL)
print(f"  [init] Rotation pool ({len(_SETUP_MODEL_POOL)} models): {_SETUP_MODEL_POOL}")

# Patch generate_setup_responses to run calls in parallel (one slot per model).
# Uses _original_gather (real asyncio.gather) to bypass the sequential patch
# that is only needed for the refinement loop's rapid binary eval calls.
_original_generate_setup = _rs.generate_setup_responses

_SETUP_CONCURRENCY = 4  # one concurrent slot per setup model


async def _interleaved_setup_responses(question: str) -> list[str]:
    from app.services.available_models import SETUP_MODELS

    n = _rs._SETUP_RESPONSES_PER_MODEL
    semaphore = asyncio.Semaphore(_SETUP_CONCURRENCY)
    tasks = [
        _rs._call_single(model.id, question, semaphore) for i in range(n) for model in SETUP_MODELS
    ]
    results = await _original_gather(*tasks)
    return [r for r in results if r is not None]


_rs.generate_setup_responses = _interleaved_setup_responses

# Patch asyncio.gather used inside rubric_service so that concurrent breadth
# checks (8 binary eval calls fired at once) run sequentially instead.
# This is the primary cause of 429s during the refinement loop.
_original_gather = asyncio.gather


async def _sequential_gather(*coros_or_futures, return_exceptions=False):  # noqa: ANN002
    """Drop-in replacement for asyncio.gather that runs tasks one by one."""
    results = []
    for coro in coros_or_futures:
        try:
            results.append(await coro)
        except Exception as exc:  # noqa: BLE001
            if return_exceptions:
                results.append(exc)
            else:
                raise
    return results


# Patch only inside the rubric_service module so the rest of the codebase
# still uses real asyncio.gather.
import app.services.rubric_service as _rs_mod  # noqa: E402

_rs_mod.asyncio.gather = _sequential_gather  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Checkpoint helpers (resume from last completed stage)
# ---------------------------------------------------------------------------
# One JSON file per case: RESULTS_DIR/{case_name}.checkpoint.json
# Keys present = that stage is complete. Missing key = needs to run.


def _checkpoint_path(case_name: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR / f"{case_name}.checkpoint.json"


def _load_checkpoint(case_name: str) -> dict:
    path = _checkpoint_path(case_name)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        stages = [k for k in data if k.startswith("stage")]
        print(f"  [cache] Checkpoint loaded - completed stages: {stages}")
        return data
    return {}


def _save_checkpoint(case_name: str, checkpoint: dict) -> None:
    path = _checkpoint_path(case_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Stage 1: PDF ingestion (no FastAPI UploadFile dependency)
# ---------------------------------------------------------------------------


def extract_text_from_pdf_path(pdf_path: Path) -> str:
    """Extract text from a PDF file on disk."""
    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                pages.append(text.strip())
    return "\n\n".join(pages)


# ---------------------------------------------------------------------------
# Stage 3: Comparison response generation (standalone, no DB)
# ---------------------------------------------------------------------------


@dataclass
class FakeResponse:
    """Lightweight stand-in for ModelResponse used by run_analysis()."""

    model_name: str
    response_text: str


async def generate_comparison_responses(
    question: str,
    models: list[str],
    responses_per_model: int,
) -> list[FakeResponse]:
    """Generate comparison responses without database persistence."""
    from app.services.github_copilot_client import chat_completion

    concurrency = 8  # 2 models × 4 parallel slots each
    semaphore = asyncio.Semaphore(concurrency)
    system_prompt = (
        "You are an expert legal analyst. Answer the question below based on "
        "legal reasoning, relevant doctrine, and sound argumentation. "
        "Be thorough but focused."
    )

    async def _call(model: str, idx: int) -> FakeResponse | None:
        async with semaphore:
            try:
                text = await chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question},
                    ],
                    model=model,
                    temperature=0.7,
                )
                return FakeResponse(model_name=model, response_text=text)
            except Exception as exc:
                print(f"  [WARN] {model} run {idx}: {exc}")
                return None

    # Round-robin across models so load is spread evenly from the start
    tasks = [_call(model, idx) for idx in range(responses_per_model) for model in models]
    results = await _original_gather(*tasks)
    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Run one benchmark case
# ---------------------------------------------------------------------------


async def run_single_case(case: BenchmarkCase) -> dict:
    """Execute the full pipeline for a single benchmark case. Returns the result dict."""
    from app.services.analysis_service import run_analysis
    from app.services.rubric_service import (
        generate_reference_pair,
        generate_setup_responses,
        propose_initial_rubric,
        run_refinement_loop,
    )

    pdf_path = DOCUMENTS_DIR / case.pdf_filename
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"\n{'=' * 70}")
    print(f"CASE: {case.name}")
    print(f"Focus: {case.testing_focus}")
    print(f"{'=' * 70}")

    t0 = time.time()
    ledger_reset()
    checkpoint = _load_checkpoint(case.name)

    # Stage 1: PDF ingestion (always fast, no checkpoint needed)
    print("\n[Stage 1] Extracting text from PDF ...")
    case_text = extract_text_from_pdf_path(pdf_path)
    print(f"  Extracted {len(case_text):,} characters from {pdf_path.name}")

    # ------------------------------------------------------------------
    # Stage 2: Rubric construction
    # ------------------------------------------------------------------
    print("\n[Stage 2] Building RRD-compliant rubric ...")

    global _call_counter, _call_total  # noqa: PLW0603

    # 2a: Setup responses + reference pair
    if "stage2a" in checkpoint:
        print("  [cache] Stage 2a: loading setup responses + reference pair from checkpoint ...")
        setup_responses = checkpoint["stage2a"]["setup_responses"]
        strong_text = checkpoint["stage2a"]["strong_text"]
        weak_text = checkpoint["stage2a"]["weak_text"]
        print(f"  Got {len(setup_responses)} setup responses (cached)")
    else:
        n_setup = _rs._SETUP_RESPONSES_PER_MODEL * 4
        per_model = _rs._SETUP_RESPONSES_PER_MODEL
        print(
            f"  [2a] Generating {n_setup} setup responses"
            f" (4 models x {per_model}) + reference pair ..."
        )
        _call_counter = 0
        _call_total = n_setup
        t_setup = time.time()
        setup_responses, (strong_text, weak_text) = await _original_gather(
            generate_setup_responses(case.question),
            generate_reference_pair(case.question),
        )
        print(f"  Got {len(setup_responses)} setup responses in {time.time() - t_setup:.0f}s")
        print(
            f"  Reference pair: strong={'ok' if strong_text else 'missing'},"
            f" weak={'ok' if weak_text else 'missing'}"
        )
        checkpoint["stage2a"] = {
            "setup_responses": setup_responses,
            "strong_text": strong_text,
            "weak_text": weak_text,
        }
        _save_checkpoint(case.name, checkpoint)
        print(ledger_report("stage 2a"))

    # 2b: Clustering
    if "stage2b" in checkpoint:
        print("  [cache] Stage 2b: loading centroid texts from checkpoint ...")
        centroid_texts = checkpoint["stage2b"]["centroid_texts"]
        print(f"  Got {len(centroid_texts)} centroids (cached)")
    else:
        print("  Cooling down 10s before clustering ...")
        await asyncio.sleep(10)
        print("  [2b] Clustering to 8 centroids ...")
        from app.services.clustering import embed_and_cluster as _eac  # noqa: PLC0415

        loop = asyncio.get_event_loop()
        cluster_data = await loop.run_in_executor(None, _eac, setup_responses, 8)
        clusters_map = cluster_data["clusters_map"]
        centroid_indices = cluster_data["centroid_indices"]
        centroid_texts = [
            setup_responses[centroid_indices[cid]] for cid in sorted(clusters_map.keys())
        ]
        print(f"  Clusters: {len(clusters_map)}  (k=8 fixed)")
        for cid in sorted(clusters_map.keys()):
            size = len(clusters_map[cid])
            preview = setup_responses[centroid_indices[cid]][:120].replace("\n", " ")
            label = "response" if size == 1 else "responses"
            print(f"    Cluster {cid}  ({size} {label})  centroid: {preview!r}...")
        checkpoint["stage2b"] = {"centroid_texts": centroid_texts}
        _save_checkpoint(case.name, checkpoint)

    # 2c: Initial rubric proposal
    if "stage2c" in checkpoint:
        print("  [cache] Stage 2c: loading initial rubric from checkpoint ...")
        initial_criteria = checkpoint["stage2c"]["initial_criteria"]
        print(f"  Got {len(initial_criteria)} initial criteria (cached)")
    else:
        print("  Cooling down 15s before rubric proposal ...")
        await asyncio.sleep(15)
        print("  [2c] Proposing initial rubric ...")
        initial_criteria = await propose_initial_rubric(case.question, centroid_texts)
        print(f"  Initial rubric: {len(initial_criteria)} criteria")
        checkpoint["stage2c"] = {"initial_criteria": initial_criteria}
        _save_checkpoint(case.name, checkpoint)
        print(ledger_report("stage 2c cumulative"))

    # 2d: Refinement loop
    if "stage2d" in checkpoint:
        print("  [cache] Stage 2d: loading rubric payload from checkpoint ...")
        rubric_payload = checkpoint["stage2d"]["rubric_payload"]
        print(
            f"  Got {len(rubric_payload['criteria'])} final criteria (cached),"
            f" stop: {rubric_payload['stopping_metadata']['reason']}"
        )
    else:
        print("  Cooling down 15s before refinement loop ...")
        await asyncio.sleep(15)
        import app.services.rubric_service as _rs2  # noqa: PLC0415, E402

        print(f"  Control model (all rubric calls): {_rs2._CONTROL_MODEL}")
        print("  [2d] Running refinement loop ...")
        t_refine = time.time()
        rubric_payload = await run_refinement_loop(
            initial_criteria, centroid_texts, strong_text, weak_text
        )
        elapsed_refine = time.time() - t_refine
        stop_meta = rubric_payload["stopping_metadata"]
        print(f"  Refinement done in {elapsed_refine:.0f}s")
        print(f"  Final rubric: {len(rubric_payload['criteria'])} criteria")
        print(f"  Stopping reason: {stop_meta['reason']}")
        print(f"  Passes: {stop_meta['passes_completed']}, rejected: {stop_meta['total_rejected']}")
        checkpoint["stage2d"] = {"rubric_payload": rubric_payload}
        _save_checkpoint(case.name, checkpoint)
        print(ledger_report("stage 2d cumulative"))

    criteria = rubric_payload["criteria"]
    stop_meta = rubric_payload["stopping_metadata"]

    # ------------------------------------------------------------------
    # Stage 3: Comparison responses
    # ------------------------------------------------------------------
    if "stage3" in checkpoint:
        print("\n[Stage 3] Loading comparison responses from checkpoint ...")
        responses = [
            FakeResponse(model_name=r["model_name"], response_text=r["response_text"])
            for r in checkpoint["stage3"]["responses"]
        ]
        print(f"  Got {len(responses)} responses (cached)")
    else:
        n_models = len(COMPARISON_MODELS)
        n_total_resp = n_models * RESPONSES_PER_MODEL
        print(
            f"\n[Stage 3] Generating comparison responses"
            f" ({n_models} models x {RESPONSES_PER_MODEL} = {n_total_resp}) ..."
        )
        print("  Cooling down 20s before comparison response generation ...")
        await asyncio.sleep(20)
        _call_counter = 0
        _call_total = n_total_resp
        t_resp = time.time()
        responses = await generate_comparison_responses(
            case.question,
            COMPARISON_MODELS,
            RESPONSES_PER_MODEL,
        )
        print(f"  Got {len(responses)} responses in {time.time() - t_resp:.0f}s")
        checkpoint["stage3"] = {
            "responses": [
                {"model_name": r.model_name, "response_text": r.response_text} for r in responses
            ]
        }
        _save_checkpoint(case.name, checkpoint)
        print(ledger_report("stage 3 cumulative"))

    if len(responses) < 10:
        print("  [ERROR] Too few responses to analyze. Skipping analysis.")
        return {
            "case_name": case.name,
            "error": "too_few_responses",
            "response_count": len(responses),
        }

    # ------------------------------------------------------------------
    # Stage 4: Analysis
    # ------------------------------------------------------------------
    if "stage4" in checkpoint:
        print("\n[Stage 4] Loading analysis result from checkpoint ...")
        analysis_result = checkpoint["stage4"]["analysis_result"]
        print(f"  Clusters: {analysis_result['k']} (cached)")
    else:
        print("  Cooling down 20s before analysis ...")
        await asyncio.sleep(20)
        print("\n[Stage 4] Running analysis (embed, cluster, score, rank) ...")
        t_analysis = time.time()
        analysis_result = await run_analysis(case.question, responses, criteria)
        elapsed_analysis = time.time() - t_analysis
        print(f"  Analysis done in {elapsed_analysis:.0f}s")
        print(f"  Clusters: {analysis_result['k']}")
        print(f"  Winning cluster: {analysis_result['winning_cluster']}")
        print(f"  Model shares (heuristic): {analysis_result['model_shares']}")
        wc = analysis_result.get("weighting_comparison", {})
        for mode_name, mode_data in wc.items():
            print(
                f"  [{mode_name}] winner: cluster {mode_data['winning_cluster']},"
                f" shares: {mode_data['model_shares']}"
            )
        checkpoint["stage4"] = {"analysis_result": analysis_result}
        _save_checkpoint(case.name, checkpoint)
        print(ledger_report("stage 4 cumulative"))

    total_elapsed = time.time() - t0
    print(f"\n  Total time for {case.name}: {total_elapsed:.0f}s")
    print(ledger_report(f"{case.name} total"))

    return {
        "case_name": case.name,
        "question": case.question,
        "testing_focus": case.testing_focus,
        "pdf_filename": case.pdf_filename,
        "case_text_length": len(case_text),
        "rubric": {
            "criteria": criteria,
            "decomposition_tree": rubric_payload.get("decomposition_tree", {}),
            "refinement_passes": rubric_payload.get("refinement_passes", []),
            "stopping_metadata": stop_meta,
            "conditioning_sample_count": len(centroid_texts),
        },
        "response_generation": {
            "models": COMPARISON_MODELS,
            "responses_per_model": RESPONSES_PER_MODEL,
            "total_generated": len(responses),
        },
        "analysis": analysis_result,
        "timing": {
            "total_seconds": round(total_elapsed, 1),
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _write_result(case_name: str, result: dict) -> Path:
    """Write a result dict as JSON and return the path."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{case_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    return out_path


def _print_summary(results: list[dict]) -> None:
    """Print a compact summary table."""
    print(f"\n{'=' * 70}")
    print("BENCHMARK SUMMARY")
    print(f"{'=' * 70}")
    header = (
        f"{'Case':<12} {'Criteria':>8} {'Stop Reason':<28}"
        f" {'Responses':>9} {'Clusters':>8} {'Time':>7}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        if "error" in r:
            print(f"{r['case_name']:<12} ERROR: {r['error']}")
            continue
        rubric = r.get("rubric", {})
        analysis = r.get("analysis", {})
        timing = r.get("timing", {})
        print(
            f"{r['case_name']:<12} "
            f"{len(rubric.get('criteria', [])):>8} "
            f"{rubric.get('stopping_metadata', {}).get('reason', '?'):<28} "
            f"{r.get('response_generation', {}).get('total_generated', 0):>9} "
            f"{analysis.get('k', '?'):>8} "
            f"{timing.get('total_seconds', 0):>6.0f}s"
        )

    # Weighting stability check for Westside
    for r in results:
        if r.get("case_name") == "westside" and "error" not in r:
            wc = r.get("analysis", {}).get("weighting_comparison", {})
            if wc:
                print("\nWeighting stability check (Westside):")
                for mode_name, mode_data in wc.items():
                    shares = mode_data.get("model_shares", {})
                    top_model = max(shares, key=shares.get) if shares else "?"
                    pct = f"{shares.get(top_model, 0):.2%}"
                    print(f"  {mode_name:<20} top model: {top_model} ({pct})")


async def _async_main(case_filter: str | None, dry_run: bool, clear_cache: bool) -> None:
    cases = BENCHMARK_CASES
    if case_filter:
        cases = [c for c in cases if c.name == case_filter]
        if not cases:
            valid = ", ".join(c.name for c in BENCHMARK_CASES)
            print(f"Unknown case '{case_filter}'. Valid: {valid}")
            sys.exit(1)

    # Validate PDFs exist
    for case in cases:
        pdf_path = DOCUMENTS_DIR / case.pdf_filename
        if not pdf_path.exists():
            print(f"Missing PDF: {pdf_path}")
            sys.exit(1)
        print(f"[OK] {case.name}: {pdf_path.name}")

    if clear_cache:
        for case in cases:
            p = _checkpoint_path(case.name)
            if p.exists():
                p.unlink()
                print(f"[cache] Cleared checkpoint for {case.name}")

    if dry_run:
        print("\nDry run complete. All PDFs found, config valid.")
        print(f"Models: {COMPARISON_MODELS}")
        print(f"Cases: {[c.name for c in cases]}")
        return

    results: list[dict] = []
    session_cost = 0.0
    for case in cases:
        result = await run_single_case(case)
        out_path = _write_result(case.name, result)
        print(f"\n  Result written to {out_path}")
        results.append(result)
        from app.services.github_copilot_client import ledger_summary as _ls

        case_total = _ls().get("__total__", {}).get("cost_usd", 0.0)
        session_cost += case_total

    _print_summary(results)
    print(f"\n  Session total cost: ${session_cost:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LexEval full-pipeline benchmark runner")
    parser.add_argument(
        "--case",
        choices=[c.name for c in BENCHMARK_CASES],
        default=None,
        help="Run a single benchmark case instead of all three",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and PDF paths without running the pipeline",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Delete checkpoints for selected cases before running (forces a clean run)",
    )
    args = parser.parse_args()
    asyncio.run(_async_main(args.case, args.dry_run, args.clear_cache))


if __name__ == "__main__":
    main()
