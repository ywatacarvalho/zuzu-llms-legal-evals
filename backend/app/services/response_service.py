import asyncio
import time
import uuid

from app.db.session import AsyncSessionLocal
from app.models.evaluation import Evaluation, StatusEnum
from app.models.response import ModelResponse
from app.services import cancel_store, log_stream

_RESPONSES_PER_MODEL = 40
_CONCURRENCY_LIMIT = 25

_SYSTEM_PROMPT = (
    "You are an expert legal analyst. Answer the question below based on legal reasoning, "
    "relevant doctrine, and sound argumentation. Be thorough but focused."
)


async def _generate_single_response(
    evaluation_id: uuid.UUID,
    question: str,
    model_name: str,
    run_index: int,
    semaphore: asyncio.Semaphore,
    question_version: str = "base",
) -> tuple[str, str, int, str | None, str]:
    """Return (model_name, eid_str, run_index, response_text_or_None, question_version)."""
    from app.services.github_copilot_client import chat_completion  # noqa: PLC0415

    async with semaphore:
        try:
            text = await chat_completion(
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
                model=model_name,
                temperature=0.7,
                stream_id=str(evaluation_id),
            )
            return model_name, str(evaluation_id), run_index, text, question_version
        except Exception:  # noqa: BLE001
            return model_name, str(evaluation_id), run_index, None, question_version


async def _generate_comparison_responses(
    evaluation_id: uuid.UUID,
    question: str,
    model_names: list[str],
    variation_question: str | None = None,
) -> None:
    """
    Generate comparison responses (40 per selected model) and persist them.
    When variation_question is provided, a second batch tagged "variation" is also generated.
    Sets evaluation status to running, then done (or failed).
    """
    eid = str(evaluation_id)

    if cancel_store.is_cancelled(eid):
        return

    async with AsyncSessionLocal() as db:
        eval_row = await db.get(Evaluation, evaluation_id)
        if eval_row:
            eval_row.status = StatusEnum.running
            await db.commit()

    n_total = len(model_names) * _RESPONSES_PER_MODEL
    log_stream.log(
        eid,
        f"[Stage 3] Generating {n_total} comparison responses"
        f" ({len(model_names)} models x {_RESPONSES_PER_MODEL})...",
    )

    # Inter-stage cooldown to let rate limits reset
    log_stream.log(eid, "  Cooling down 20s before comparison responses...")
    await asyncio.sleep(10)

    from app.services.github_copilot_client import (  # noqa: PLC0415
        ledger_report,
        reset_call_budget,
        set_call_budget,
    )

    semaphore = asyncio.Semaphore(_CONCURRENCY_LIMIT)

    # --- Base pass ---
    set_call_budget(0, n_total)
    base_tasks = [
        _generate_single_response(evaluation_id, question, model_name, run_idx, semaphore)
        for run_idx in range(_RESPONSES_PER_MODEL)
        for model_name in model_names
    ]
    t_start = time.time()
    base_raw = await asyncio.gather(*base_tasks, return_exceptions=True)
    elapsed = time.time() - t_start
    base_results = list(base_raw)
    reset_call_budget()

    model_counts: dict[str, int] = {}
    for r in base_results:
        if not isinstance(r, Exception) and r[3] is not None:
            model_counts[r[0]] = model_counts.get(r[0], 0) + 1
    for model_name in model_names:
        count = model_counts.get(model_name, 0)
        log_stream.log(eid, f"  {model_name}: {count}/{_RESPONSES_PER_MODEL} responses done")

    successes = sum(1 for r in base_results if not isinstance(r, Exception) and r[3] is not None)
    log_stream.log(
        eid,
        f"  Total: {successes}/{n_total} responses in {elapsed:.0f}s. Persisting...",
    )
    for line in ledger_report("stage 3").split("\n"):
        log_stream.log(eid, line)

    # --- Variation pass (only when dual_rubric_mode is active) ---
    var_results: list = []
    if variation_question:
        log_stream.log(
            eid,
            f"[Stage 3b] Generating {n_total} variation responses"
            f" ({len(model_names)} models x {_RESPONSES_PER_MODEL})...",
        )
        set_call_budget(0, n_total)
        var_tasks = [
            _generate_single_response(
                evaluation_id,
                variation_question,
                model_name,
                run_idx,
                semaphore,
                question_version="variation",
            )
            for run_idx in range(_RESPONSES_PER_MODEL)
            for model_name in model_names
        ]
        t_start = time.time()
        var_raw = await asyncio.gather(*var_tasks, return_exceptions=True)
        elapsed = time.time() - t_start
        var_results = list(var_raw)
        reset_call_budget()

        var_counts: dict[str, int] = {}
        for r in var_results:
            if not isinstance(r, Exception) and r[3] is not None:
                var_counts[r[0]] = var_counts.get(r[0], 0) + 1
        for model_name in model_names:
            count = var_counts.get(model_name, 0)
            log_stream.log(eid, f"  {model_name}: {count}/{_RESPONSES_PER_MODEL} variation done")
        var_successes = sum(
            1 for r in var_results if not isinstance(r, Exception) and r[3] is not None
        )
        log_stream.log(eid, f"  Variation total: {var_successes}/{n_total} in {elapsed:.0f}s.")
        for line in ledger_report("stage 3b").split("\n"):
            log_stream.log(eid, line)

    # --- Persist base + variation responses together ---
    all_results = base_results + var_results
    async with AsyncSessionLocal() as db:
        try:
            for result in all_results:
                if isinstance(result, Exception):
                    continue
                model_name, _, run_index, text, question_version = result
                db.add(
                    ModelResponse(
                        evaluation_id=evaluation_id,
                        model_name=model_name,
                        response_text=text,
                        run_index=run_index,
                        question_version=question_version,
                    )
                )
            eval_row = await db.get(Evaluation, evaluation_id)
            if eval_row and not cancel_store.is_cancelled(eid):
                eval_row.status = StatusEnum.done
            await db.commit()
            if not cancel_store.is_cancelled(eid):
                log_stream.log(eid, "Evaluation pipeline complete.")
        except Exception:  # noqa: BLE001
            await db.rollback()
            async with AsyncSessionLocal() as db2:
                eval_row = await db2.get(Evaluation, evaluation_id)
                if eval_row:
                    eval_row.status = StatusEnum.failed
                    await db2.commit()
            log_stream.log(eid, "[ERROR] Failed to persist responses.")


# Kept as a public alias for backward compatibility with existing tests.
generate_responses_background = _generate_comparison_responses


async def run_evaluation_pipeline(
    evaluation_id: uuid.UUID,
    question: str,
    model_names: list[str],
    variation_question: str | None = None,
) -> None:
    """
    Comparison-only pipeline: generate comparison responses.
    The rubric must already be frozen before calling this.
    When variation_question is set, a second batch of variation responses is generated.
    Sets evaluation status: running -> done / failed.
    """
    await _generate_comparison_responses(evaluation_id, question, model_names, variation_question)
