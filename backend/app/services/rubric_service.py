"""RRD-compliant rubric construction pipeline (steps 2a-2f of the LexEval workflow).

build_rubric() is the top-level orchestrator:
  1. Generate 100 setup responses (4 models x 25 each)
  2. Cluster to 8 centroids (fixed k=8)
  3. Propose initial rubric conditioned on 8 centroids
  4. Run recursive decompose-filter loop until saturation
  5. Persist frozen rubric payload on the Rubric row
"""

import asyncio
import json
import time

import numpy as np

from app.services import frank_instructions, log_stream
from app.services.available_models import (
    CONTROL_MODEL,
    SETUP_MODELS,
    STRONG_REF_MODEL,
    WEAK_REF_MODEL,
)
from app.services.clustering import embed_and_cluster
from app.services.frank_service import (
    enrich_criteria_with_row_cards,
    extract_source,
    generate_controller_card,
    generate_gold_answer,
    generate_gold_packet_mapping,
    generate_variation_rubric,
    predict_failure_modes,
    route_to_doctrine_pack,
    run_overlap_audit,
    run_self_audit,
    screen_source_intake,
)
from app.services.github_copilot_client import (
    CallBudgetExceeded,
    chat_completion,
    init_rotation_pool,
    ledger_report,
    ledger_reset,
    reset_call_budget,
    set_call_budget,
)
from app.services.rubric_prompts import (
    build_binary_eval_messages,
    build_decompose_messages,
    build_draft_comparison_messages,
    build_filter_redundancy_messages,
    build_initial_proposal_messages,
    build_question_generation_messages,
    build_question_validation_messages,
    build_setup_system_prompt,
)

_CONTROL_MODEL = CONTROL_MODEL
_STRONG_REF_MODEL = STRONG_REF_MODEL
_WEAK_REF_MODEL = WEAK_REF_MODEL


_SETUP_RESPONSES_PER_MODEL = 25
_FIXED_K = 8
_BREADTH_THRESHOLD = 2  # criterion is "broad" if it passes >2 of 8 centroids (paper's n=2)
_MAX_REJECTED_PROPOSALS = 5
_MAX_DECOMPOSITION_DEPTH = 1  # children are never further decomposed (one level only)
_CONCURRENCY_LIMIT = 4  # one slot per setup model (matches benchmark)
_REFINEMENT_CALL_CEILING = 500  # hard cap on API calls during stages 2d-2f
_LEGACY_PACK_FALLBACKS = {
    "pack_marriage": "pack_10",
    "pack_suretyship": "pack_10",
    "pack_one_year": "pack_10",
    "pack_land": "pack_20",
    "pack_ucc_2201": "pack_40",
    "pack_executor": "pack_30",
}
_CONTROLLER_CARD_VERSION = "step_2a_v1"

# Module default weights (decimal) used as Bayesian prior in WU blending (Phase 6)
_MODULE_DEFAULT_WEIGHTS: dict[int, float] = {1: 0.28, 2: 0.40, 3: 0.19, 4: 0.13}


def _get_pack_content(pack_id: str | None) -> dict:
    if not pack_id:
        return {}
    try:
        return frank_instructions.get_doctrine_pack(pack_id)
    except Exception:  # noqa: BLE001
        legacy_id = _LEGACY_PACK_FALLBACKS.get(pack_id)
        if not legacy_id:
            raise
        return frank_instructions.get_doctrine_pack(legacy_id)


# ---------------------------------------------------------------------------
# Setup response generation
# ---------------------------------------------------------------------------


async def _call_single(
    model_id: str,
    question: str,
    semaphore: asyncio.Semaphore,
    stream_id: str | None = None,
    source_extraction: dict | None = None,
    doctrine_pack: str | None = None,
) -> str | None:
    async with semaphore:
        try:
            return await chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": build_setup_system_prompt(
                            source_extraction=source_extraction,
                            doctrine_pack=doctrine_pack,
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                model=model_id,
                temperature=0.7,
                stream_id=stream_id,
            )
        except Exception:  # noqa: BLE001
            return None


async def generate_setup_responses(
    question: str,
    stream_id: str | None = None,
    source_extraction: dict | None = None,
    doctrine_pack: str | None = None,
) -> list[dict]:
    """Generate diverse responses from all setup models (round-robin interleaved).

    Returns list of {"model": str, "text": str} dicts so callers can
    persist provenance. Nones (failed calls) are dropped.
    """
    semaphore = asyncio.Semaphore(_CONCURRENCY_LIMIT)
    n = _SETUP_RESPONSES_PER_MODEL
    n_expected = len(SETUP_MODELS) * n
    if stream_id:
        log_stream.log(
            stream_id,
            f"[Stage 2a] Generating {n_expected} setup responses"
            f" ({len(SETUP_MODELS)} models x {n})...",
        )
        set_call_budget(0, n_expected)

    # Round-robin interleaved: model0, model1, ..., model0, model1, ...
    tasks = [
        _call_single(
            model.id,
            question,
            semaphore,
            stream_id,
            source_extraction=source_extraction,
            doctrine_pack=doctrine_pack,
        )
        for _ in range(n)
        for model in SETUP_MODELS
    ]
    t_start = time.time()
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - t_start

    # Collect results preserving model provenance
    responses: list[dict] = []
    model_counts: dict[str, int] = {}
    idx = 0
    for _ in range(n):
        for model in SETUP_MODELS:
            text = results[idx]
            idx += 1
            if text is not None:
                responses.append({"model": model.id, "text": text})
                model_counts[model.id] = model_counts.get(model.id, 0) + 1

    if stream_id:
        for model_id, count in model_counts.items():
            log_stream.log(stream_id, f"  {model_id}: {count}/{n} responses ok")
        log_stream.log(
            stream_id,
            f"  Total: {len(responses)}/{n_expected} setup responses in {elapsed:.0f}s",
        )
        reset_call_budget()
    return responses


async def generate_reference_pair(
    question: str, stream_id: str | None = None
) -> tuple[str | None, str | None]:
    """Generate one response each from the strong and weak reference models."""
    if stream_id:
        log_stream.log(stream_id, "[Stage 2a] Generating reference pair (strong + weak)...")
    semaphore = asyncio.Semaphore(2)
    strong, weak = await asyncio.gather(
        _call_single(_STRONG_REF_MODEL, question, semaphore, stream_id),
        _call_single(_WEAK_REF_MODEL, question, semaphore, stream_id),
    )
    if stream_id:
        log_stream.log(
            stream_id,
            f"  Reference pair: strong={'ok' if strong else 'missing'},"
            f" weak={'ok' if weak else 'missing'}",
        )
    return strong, weak


async def generate_weak_reference(question: str, stream_id: str | None = None) -> str | None:
    """Generate a single response from the weak reference model only.

    Used in the FI path where the strong reference is replaced by the gold answer.
    """
    if stream_id:
        log_stream.log(stream_id, "[Stage 2a] Generating weak reference response...")
    semaphore = asyncio.Semaphore(1)
    weak = await _call_single(_WEAK_REF_MODEL, question, semaphore, stream_id)
    if stream_id:
        log_stream.log(
            stream_id,
            f"  Weak reference: {'ok' if weak else 'missing'}",
        )
    return weak


# ---------------------------------------------------------------------------
# Centroid extraction (fixed k=8)
# ---------------------------------------------------------------------------


async def cluster_to_centroids(
    responses: list[dict] | list[str], stream_id: str | None = None
) -> list[str]:
    """Cluster setup responses with fixed k=8. Returns 8 centroid response texts.

    Accepts either list[str] or list[{"model": str, "text": str}] for backward
    compatibility with the benchmark's patched generate_setup_responses.
    """
    if stream_id:
        log_stream.log(
            stream_id,
            f"[Stage 2b] Clustering {len(responses)} responses to {_FIXED_K} centroids...",
        )
    texts = [r["text"] if isinstance(r, dict) else r for r in responses]
    t_start = time.time()
    loop = asyncio.get_event_loop()
    cluster_data = await loop.run_in_executor(None, embed_and_cluster, texts, _FIXED_K)
    elapsed = time.time() - t_start
    clusters_map: dict[int, list[int]] = cluster_data["clusters_map"]
    centroid_indices: dict[int, int] = cluster_data["centroid_indices"]
    centroids = [texts[centroid_indices[cid]] for cid in sorted(clusters_map.keys())]
    if stream_id:
        log_stream.log(
            stream_id,
            f"  Clusters: {len(clusters_map)} (k={_FIXED_K} fixed) in {elapsed:.0f}s",
        )
        for cid in sorted(clusters_map.keys()):
            size = len(clusters_map[cid])
            preview = texts[centroid_indices[cid]][:120].replace("\n", " ")
            label = "response" if size == 1 else "responses"
            log_stream.log(
                stream_id,
                f"    Cluster {cid} ({size} {label}) centroid: {preview!r}...",
            )
    return centroids


# ---------------------------------------------------------------------------
# Rubric proposal
# ---------------------------------------------------------------------------


def _renormalize_weights(criteria: list[dict]) -> list[dict]:
    """Simple proportional renormalization to fix LLM rounding errors."""
    if not criteria:
        return []
    total = sum(float(c.get("weight", 0)) for c in criteria)
    if total <= 0:
        w = round(1.0 / len(criteria), 4)
        return [{**c, "weight": w} for c in criteria]
    return [{**c, "weight": round(float(c.get("weight", 0)) / total, 4)} for c in criteria]


async def propose_initial_rubric(
    question: str,
    centroid_texts: list[str],
    stream_id: str | None = None,
    doctrine_pack: str | None = None,
) -> list[dict]:
    """Ask GPT-4.1 for an initial rubric conditioned on the question and 8 centroids."""
    t_start = time.time()
    if stream_id:
        log_stream.log(stream_id, "[Stage 2c] Proposing initial rubric...")
    messages = build_initial_proposal_messages(
        question, centroid_texts, doctrine_pack=doctrine_pack
    )
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.2,
        stream_id=stream_id,
    )
    try:
        criteria: list[dict] = json.loads(raw)["criteria"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise ValueError(f"GPT returned invalid rubric JSON: {exc}") from exc
    criteria = _renormalize_weights(criteria)
    _validate_criteria(criteria)
    elapsed = time.time() - t_start
    if stream_id:
        log_stream.log(
            stream_id,
            f"  Proposed {len(criteria)} initial criteria in {elapsed:.0f}s:",
        )
        for c in criteria:
            log_stream.log(stream_id, f"    [{c['id']}] {c['name']} (w={c['weight']:.3f})")
        for line in ledger_report("stage 2c").split("\n"):
            log_stream.log(stream_id, line)
    return criteria


# ---------------------------------------------------------------------------
# Breadth check and decomposition
# ---------------------------------------------------------------------------


async def _binary_eval_centroid(
    criterion: dict, centroid_text: str, stream_id: str | None = None
) -> bool:
    messages = build_binary_eval_messages(criterion, centroid_text)
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        temperature=0.0,
        response_format={"type": "json_object"},
        stream_id=stream_id,
    )
    try:
        return bool(json.loads(raw).get("passes", False))
    except Exception:  # noqa: BLE001
        return False


async def _check_criterion_breadth(
    criterion: dict, centroid_texts: list[str], stream_id: str | None = None
) -> bool:
    """Return True if the criterion matches more than _BREADTH_THRESHOLD centroids (too broad).

    Runs evaluations sequentially to avoid 429 storms (matches benchmark behavior).
    """
    flags: list[bool] = []
    for text in centroid_texts:
        flags.append(await _binary_eval_centroid(criterion, text, stream_id))
    return sum(flags) > _BREADTH_THRESHOLD


async def _decompose_criterion(
    criterion: dict, centroid_texts: list[str], stream_id: str | None = None
) -> list[dict]:
    """Decompose a broad criterion into 2-3 narrower children using the next judge model."""
    messages = build_decompose_messages(criterion, centroid_texts)
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.2,
        stream_id=stream_id,
    )
    try:
        children: list[dict] = json.loads(raw).get("children", [])
        return [c for c in children if isinstance(c, dict) and "id" in c]
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


async def _filter_misalignment(
    criterion: dict,
    strong_text: str | None,
    weak_text: str | None,
    stream_id: str | None = None,
) -> bool:
    """Return True if the criterion should be kept (positive-edge semantics).

    A criterion is misaligned — and should be discarded — only when it passes
    the weak reference response but fails the strong one, indicating an inverted
    preference direction (negative edge proxy, per RRD paper §2.3).
    All other outcomes are kept conservatively.
    """
    if strong_text is None or weak_text is None:
        return True  # no reference pair available; keep conservatively
    passes_strong = await _binary_eval_centroid(criterion, strong_text, stream_id)
    passes_weak = await _binary_eval_centroid(criterion, weak_text, stream_id)
    return not (passes_weak and not passes_strong)


async def _filter_redundancy(
    criterion: dict, accepted: list[dict], stream_id: str | None = None
) -> bool:
    """Return True if the criterion is NOT redundant (should be kept)."""
    if not accepted:
        return True
    messages = build_filter_redundancy_messages(criterion, accepted)
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        temperature=0.0,
        response_format={"type": "json_object"},
        stream_id=stream_id,
    )
    try:
        return not bool(json.loads(raw).get("redundant", False))
    except Exception:  # noqa: BLE001
        return True  # conservative: keep on parse failure


def _order_accepted_for_redundancy(child: dict, accepted: list[dict]) -> list[dict]:
    """Return `accepted` with same-module criteria first.

    Within-module redundancy is more likely and is checked before cross-module
    so that rejections happen at the strictest boundary first.
    """
    child_module = child.get("module_id")
    if child_module is None:
        return accepted
    same = [c for c in accepted if c.get("module_id") == child_module]
    other = [c for c in accepted if c.get("module_id") != child_module]
    return same + other


# ---------------------------------------------------------------------------
# Refinement loop
# ---------------------------------------------------------------------------


async def _compute_wu_weights(
    criteria: list[dict], centroid_texts: list[str], stream_id: str | None = None
) -> list[dict]:
    """Assign whitened-uniform (WU) weights via Σ^(-1/2) (RRD paper §2.3).

    Scores all centroids against all criteria to build a binary matrix, estimates
    the rubric covariance Σ with Tikhonov regularization, then projects a uniform
    vector through Σ^(-1/2). Falls back to equal weights on numerical failure.

    When criteria carry ``module_id``, blends WU weights with a Bayesian module
    prior (0.3 * prior + 0.7 * WU) where the prior is each module's default
    percentage weight distributed evenly across that module's criteria.
    """
    if not criteria:
        return []
    m = len(criteria)
    if m == 1:
        return [{**criteria[0], "weight": 1.0}]

    if stream_id:
        log_stream.log(
            stream_id,
            f"[Stage 2f] Scoring {len(centroid_texts)} centroids x {m} criteria for WU weights...",
        )
    t_start = time.time()
    # Sequential row-by-row to avoid 429 storms (matches benchmark behavior)
    score_rows: list[list[bool]] = []
    for text in centroid_texts:
        row: list[bool] = []
        for c in criteria:
            row.append(await _binary_eval_centroid(c, text, stream_id))
        score_rows.append(row)
    M = np.array([[float(v) for v in row] for row in score_rows])  # (n_centroids, m)

    try:
        cov = np.cov(M, rowvar=False)  # (m, m)
        if cov.ndim == 0:
            cov = np.array([[float(cov)]])
        cov += 1e-6 * np.eye(m)  # regularize

        eigvals, eigvecs = np.linalg.eigh(cov)
        eigvals = np.maximum(eigvals, 1e-10)
        sigma_inv_half = eigvecs @ np.diag(eigvals**-0.5) @ eigvecs.T

        uniform = np.ones(m) / m
        wu = sigma_inv_half @ uniform
        wu = np.abs(wu)  # ensure non-negative
        total = wu.sum()
        if total <= 0:
            raise ValueError("zero weight sum")
        wu = wu / total
    except Exception:  # noqa: BLE001
        wu = np.full(m, 1.0 / m)

    # Bayesian module prior blend when module_id is available on criteria
    module_ids = [c.get("module_id") for c in criteria]
    if any(mid is not None for mid in module_ids):
        from collections import Counter

        module_counts = Counter(mid for mid in module_ids if mid is not None)
        prior = np.array(
            [
                _MODULE_DEFAULT_WEIGHTS.get(mid, 0.0) / module_counts[mid]
                if mid is not None and mid in _MODULE_DEFAULT_WEIGHTS
                else 1.0 / m
                for mid in module_ids
            ]
        )
        prior_total = prior.sum()
        if prior_total > 0:
            prior = prior / prior_total
        wu = 0.3 * prior + 0.7 * wu
        wu = wu / wu.sum()

    result = [{**c, "weight": round(float(wu[i]), 6)} for i, c in enumerate(criteria)]
    elapsed = time.time() - t_start
    if stream_id:
        log_stream.log(
            stream_id,
            f"[Stage 2f] WU weights assigned to {len(result)} criteria in {elapsed:.0f}s.",
        )
    return result


async def run_refinement_loop(
    initial_criteria: list[dict],
    centroid_texts: list[str],
    strong_text: str | None = None,
    weak_text: str | None = None,
    stream_id: str | None = None,
) -> dict:
    """
    Iterative decompose-filter loop.

    Terminates when accumulated rejected proposals >= _MAX_REJECTED_PROPOSALS
    or when no broad criteria remain (convergence).

    Returns a dict with: criteria, decomposition_tree, refinement_passes,
    stopping_metadata, conditioning_sample.
    """
    if stream_id:
        log_stream.log(
            stream_id,
            f"[Stage 2d] Starting refinement loop ({len(initial_criteria)} initial criteria)...",
        )
    t_refine = time.time()
    current_criteria = list(initial_criteria)
    # Track depth: 0 = initial proposal, 1 = decomposed child (never re-decomposed)
    criterion_depth: dict[str, int] = {c["id"]: 0 for c in initial_criteria}
    decomposition_tree: dict[str, list[str]] = {}
    refinement_passes: list[dict] = []
    total_rejected = 0
    stopping_reason = "convergence"

    for pass_num in range(1, 21):  # hard cap at 20 passes
        if total_rejected >= _MAX_REJECTED_PROPOSALS:
            stopping_reason = "rejection_threshold_reached"
            break

        depth0 = [c for c in current_criteria if criterion_depth.get(c["id"], 0) == 0]
        depth1 = [c for c in current_criteria if criterion_depth.get(c["id"], 0) >= 1]

        if stream_id:
            log_stream.log(
                stream_id,
                f"  Pass {pass_num}: {len(depth0)} depth-0 criteria, "
                f"{len(depth1)} children accepted so far",
            )

        if not depth0:
            # All remaining criteria are already children — converged
            stopping_reason = "convergence"
            refinement_passes.append(
                {"pass": pass_num, "actions": [], "total_rejected": total_rejected}
            )
            break

        # Sequential breadth checks to avoid 429 storms (matches benchmark)
        breadth_flags: list[bool] = []
        for c in depth0:
            breadth_flags.append(await _check_criterion_breadth(c, centroid_texts, stream_id))
        broad = [c for c, flag in zip(depth0, breadth_flags) if flag]
        narrow = [c for c, flag in zip(depth0, breadth_flags) if not flag]
        accepted = narrow + depth1

        if stream_id:
            log_stream.log(
                stream_id,
                f"    Breadth check: {len(broad)} broad, {len(narrow)} narrow"
                + (f" — narrow kept: {', '.join(c['name'] for c in narrow)}" if narrow else ""),
            )

        if not broad:
            stopping_reason = "convergence"
            refinement_passes.append(
                {"pass": pass_num, "actions": [], "total_rejected": total_rejected}
            )
            break

        pass_actions: list[dict] = []

        for parent in broad:
            if total_rejected >= _MAX_REJECTED_PROPOSALS:
                accepted.append(parent)
                break

            children = await _decompose_criterion(parent, centroid_texts, stream_id)
            if not children:
                total_rejected += 1
                pass_actions.append({"criterion_id": parent["id"], "action": "decomposition_empty"})
                accepted.append(parent)
                if stream_id:
                    log_stream.log(
                        stream_id,
                        f"    '{parent['name']}': decomposition returned empty — kept as-is",
                    )
                continue

            decomposition_tree[parent["id"]] = [c["id"] for c in children]
            pass_actions.append(
                {
                    "criterion_id": parent["id"],
                    "action": "decomposed",
                    "children": [c["id"] for c in children],
                }
            )
            if stream_id:
                child_names = ", ".join(f"'{c['name']}'" for c in children)
                log_stream.log(
                    stream_id,
                    f"    Decomposed '{parent['name']}' -> [{child_names}]",
                )

            for child in children:
                # Mark as depth 1 — will never be re-evaluated for breadth
                criterion_depth[child["id"]] = 1
                if total_rejected >= _MAX_REJECTED_PROPOSALS:
                    break
                keep = await _filter_misalignment(child, strong_text, weak_text, stream_id)
                if not keep:
                    total_rejected += 1
                    pass_actions.append(
                        {"criterion_id": child["id"], "action": "rejected_misalignment"}
                    )
                    if stream_id:
                        log_stream.log(
                            stream_id,
                            f"      '{child['name']}': rejected (misalignment)",
                        )
                    continue
                not_redundant = await _filter_redundancy(
                    child,
                    _order_accepted_for_redundancy(child, accepted),
                    stream_id,
                )
                if not not_redundant:
                    total_rejected += 1
                    pass_actions.append(
                        {"criterion_id": child["id"], "action": "rejected_redundancy"}
                    )
                    if stream_id:
                        log_stream.log(
                            stream_id,
                            f"      '{child['name']}': rejected (redundant)",
                        )
                    continue
                accepted.append(child)
                pass_actions.append({"criterion_id": child["id"], "action": "accepted"})
                if stream_id:
                    log_stream.log(stream_id, f"      '{child['name']}': accepted")

        n_accepted = sum(1 for a in pass_actions if a["action"] == "accepted")
        n_mis = sum(1 for a in pass_actions if a["action"] == "rejected_misalignment")
        n_red = sum(1 for a in pass_actions if a["action"] == "rejected_redundancy")
        if stream_id:
            log_stream.log(
                stream_id,
                f"  Pass {pass_num} done:"
                f" {n_accepted} accepted, {n_mis} misaligned, {n_red} redundant"
                f" (total rejected so far: {total_rejected})",
            )

        refinement_passes.append(
            {
                "pass": pass_num,
                "actions": pass_actions,
                "total_rejected": total_rejected,
            }
        )
        current_criteria = accepted

    else:
        stopping_reason = "max_passes_reached"

    if total_rejected >= _MAX_REJECTED_PROPOSALS:
        stopping_reason = "rejection_threshold_reached"

    # Module coverage check: flag modules with no criteria after refinement
    populated_modules = {
        c.get("module_id") for c in current_criteria if c.get("module_id") is not None
    }
    empty_modules = (
        [mid for mid in [1, 2, 3, 4] if mid not in populated_modules] if populated_modules else []
    )

    if stream_id:
        elapsed_refine = time.time() - t_refine
        log_stream.log(
            stream_id,
            f"  Refinement done in {elapsed_refine:.0f}s: {stopping_reason},"
            f" {len(refinement_passes)} passes, {total_rejected} rejected.",
        )
        for line in ledger_report("stage 2d").split("\n"):
            log_stream.log(stream_id, line)

    return {
        "criteria": await _compute_wu_weights(current_criteria, centroid_texts, stream_id),
        "decomposition_tree": decomposition_tree,
        "refinement_passes": refinement_passes,
        "stopping_metadata": {
            "reason": stopping_reason,
            "total_rejected": total_rejected,
            "passes_completed": len(refinement_passes),
            "empty_modules": empty_modules,
        },
        "conditioning_sample": list(centroid_texts),
    }


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


async def build_rubric(
    stream_id: str,
    question: str,
    case_text: str | None = None,
) -> dict:
    """
    Full rubric-construction pipeline (standalone).

    Returns a dict with all fields needed for RubricRepository.update_rubric_data().
    When ``case_text`` is provided, runs Phase 2.5 screening and Phase 2 extraction
    before the main RRD pipeline.
    """
    log_stream.log(stream_id, "Rubric construction pipeline started.")
    t_total = time.time()
    ledger_reset()

    # Phase 2.5: source intake screening -> Phase 2: source extraction
    screening_result: dict | None = None
    source_extraction: dict | None = None
    if case_text:
        screening_result = await screen_source_intake(stream_id, case_text, question)
        log_stream.log(stream_id, "  Cooling down 5s after source screening...")
        await asyncio.sleep(5)
        source_extraction = await extract_source(stream_id, case_text, question)
        log_stream.log(stream_id, "  Cooling down 10s after source extraction...")
        await asyncio.sleep(10)

    # Phase 3: doctrine pack routing
    routing_metadata: dict | None = None
    doctrine_pack: str | None = None
    if source_extraction is not None:
        routing_metadata = await route_to_doctrine_pack(stream_id, source_extraction, question)
        doctrine_pack = routing_metadata["selected_pack"]
        log_stream.log(stream_id, "  Cooling down 5s after routing...")
        await asyncio.sleep(5)

    # Phase 10: question validation (informational -- does not block pipeline)
    question_analysis: dict | None = None
    if source_extraction is not None:
        question_analysis = await validate_question(
            stream_id, question, source_extraction, doctrine_pack
        )
        overall = question_analysis.get("overall_pass", True)
        log_stream.log(
            stream_id,
            f"[Phase 10] Question validation: {'PASS' if overall else 'WARNINGS'}",
        )

    # Phase 4: gold packet mapping + failure mode prediction
    gold_packet_mapping: dict | None = None
    predicted_failure_modes: list | None = None
    if doctrine_pack is not None:
        gold_packet_mapping = await generate_gold_packet_mapping(
            stream_id, source_extraction, doctrine_pack, question
        )
        log_stream.log(stream_id, "  Cooling down 5s after gold packet mapping...")
        await asyncio.sleep(5)
        predicted_failure_modes = await predict_failure_modes(
            stream_id, source_extraction, gold_packet_mapping, doctrine_pack
        )
        log_stream.log(stream_id, "  Cooling down 10s after failure mode prediction...")
        await asyncio.sleep(10)

    # Initialize rotation pool: all setup models + control model
    pool_models = [m.id for m in SETUP_MODELS] + [_CONTROL_MODEL]
    init_rotation_pool(pool_models)
    log_stream.log(
        stream_id,
        f"  Rotation pool ({len(list(dict.fromkeys(pool_models)))} models):"
        f" {list(dict.fromkeys(pool_models))}",
    )

    gold_answer: str | None = None
    controller_card: dict | None = None
    if case_text and gold_packet_mapping is not None and doctrine_pack is not None:
        # FI Phase A: generate weak reference and gold answer, then run self-audit.
        # Setup responses are deferred to Phase B (after human approval).
        weak_text = await generate_weak_reference(question, stream_id)
        gold_answer = await generate_gold_answer(
            stream_id, source_extraction, gold_packet_mapping, doctrine_pack, question
        )
        strong_text = gold_answer

        controller_card = await generate_controller_card(
            stream_id,
            source_extraction,
            gold_packet_mapping,
            doctrine_pack,
            question,
            gold_answer,
            routing_metadata,
        )
        log_stream.log(stream_id, "  Cooling down 5s after controller card generation...")
        await asyncio.sleep(5)

        log_stream.log(stream_id, "  Cooling down 5s before self-audit...")
        await asyncio.sleep(5)

        self_audit_result = await run_self_audit(
            stream_id=stream_id,
            gold_answer=gold_answer,
            source_extraction=source_extraction,  # type: ignore[arg-type]
            doctrine_pack=doctrine_pack,
            routing_metadata=routing_metadata,  # type: ignore[arg-type]
        )

        # PIPELINE PAUSES — return intermediate payload; _build_rubric_background
        # will detect fi_status="awaiting_review" and save without freezing.
        log_stream.log(stream_id, "[GATE] Pipeline paused -- awaiting human review.")
        return {
            "fi_status": "awaiting_review",
            "fi_stream_id": stream_id,
            "gold_answer": gold_answer,
            "strong_reference_text": strong_text,
            "weak_reference_text": weak_text,
            "self_audit_result": self_audit_result,
            "screening_result": screening_result,
            "source_extraction": source_extraction,
            "routing_metadata": routing_metadata,
            "doctrine_pack": doctrine_pack,
            "gold_packet_mapping": gold_packet_mapping,
            "predicted_failure_modes": predicted_failure_modes,
            "question_analysis": question_analysis,
            "controller_card": controller_card,
            "controller_card_version": _CONTROLLER_CARD_VERSION,
            "workflow_source_case_name": source_extraction.get("canonical_source_case_name"),
            "workflow_source_case_citation": source_extraction.get(
                "canonical_source_case_citation"
            ),
            "case_citation_verification_mode": controller_card.get(
                "case_citation_verification_mode", False
            ),
        }
    else:
        setup_responses, (strong_text, weak_text) = await asyncio.gather(
            generate_setup_responses(
                question,
                stream_id,
                source_extraction=source_extraction,
                doctrine_pack=doctrine_pack,
            ),
            generate_reference_pair(question, stream_id),
        )
    # Log stage 2a cost
    for line in ledger_report("stage 2a").split("\n"):
        log_stream.log(stream_id, line)
    log_stream.log(stream_id, "  Cooling down 10s before clustering...")
    await asyncio.sleep(10)

    centroid_texts = await cluster_to_centroids(setup_responses, stream_id)

    # Cooldown before rubric proposal
    log_stream.log(stream_id, "  Cooling down 15s before rubric proposal...")
    await asyncio.sleep(15)

    initial_criteria = await propose_initial_rubric(
        question, centroid_texts, stream_id, doctrine_pack=doctrine_pack
    )

    # Cooldown before refinement
    log_stream.log(stream_id, "  Cooling down 15s before refinement loop...")
    await asyncio.sleep(15)

    # Enforce a hard call ceiling for stages 2d-2f
    set_call_budget(0, _REFINEMENT_CALL_CEILING)
    msg = f"  Call budget set: {_REFINEMENT_CALL_CEILING} calls for stages 2d-2f"
    log_stream.log(stream_id, msg)
    try:
        result = await run_refinement_loop(
            initial_criteria, centroid_texts, strong_text, weak_text, stream_id
        )
    except CallBudgetExceeded:
        log_stream.log(
            stream_id,
            f"  Call budget exhausted ({_REFINEMENT_CALL_CEILING} calls)."
            " Aborting refinement — returning initial criteria with uniform weights.",
        )
        uniform_w = round(1.0 / len(initial_criteria), 6) if initial_criteria else 1.0
        result = {
            "criteria": [{**c, "weight": uniform_w} for c in initial_criteria],
            "decomposition_tree": {},
            "refinement_passes": [],
            "stopping_metadata": {
                "reason": "call_budget_exhausted",
                "total_rejected": 0,
                "passes_completed": 0,
            },
            "conditioning_sample": list(centroid_texts),
        }
    finally:
        reset_call_budget()
    elapsed_total = time.time() - t_total
    log_stream.log(
        stream_id,
        f"Rubric construction complete: {len(result['criteria'])} final criteria"
        f" in {elapsed_total:.0f}s.",
    )
    for line in ledger_report("rubric total").split("\n"):
        log_stream.log(stream_id, line)
    result["setup_responses"] = setup_responses  # list[{"model": str, "text": str}]
    result["strong_reference_text"] = strong_text
    result["weak_reference_text"] = weak_text
    result["gold_answer"] = gold_answer
    result["screening_result"] = screening_result
    result["source_extraction"] = source_extraction
    result["routing_metadata"] = routing_metadata
    result["doctrine_pack"] = doctrine_pack
    result["gold_packet_mapping"] = gold_packet_mapping
    result["predicted_failure_modes"] = predicted_failure_modes
    result["question_analysis"] = question_analysis
    return result


async def build_rubric_phase_b(
    stream_id: str,
    question: str,
    gold_answer: str,
    weak_text: str | None,
    source_extraction: dict | None,
    doctrine_pack: str | None,
    controller_card: dict | None = None,
    selected_lane_code: str | None = None,
    dual_rubric_mode: bool = False,
) -> dict:
    """Phase B of the FI rubric pipeline (runs after human approval of the gold answer).

    Generates setup responses, clusters them, proposes and refines the rubric criteria
    using the pre-approved gold answer as the strong reference.

    Returns the standard build_rubric payload dict (same shape as the non-FI path).
    """
    log_stream.log(stream_id, "[Phase B] Resuming pipeline after human approval...")
    ledger_reset()

    pool_models = [m.id for m in SETUP_MODELS] + [_CONTROL_MODEL]
    init_rotation_pool(pool_models)
    log_stream.log(
        stream_id,
        f"  Rotation pool ({len(list(dict.fromkeys(pool_models)))} models):"
        f" {list(dict.fromkeys(pool_models))}",
    )

    # Generate setup responses; if weak_text is missing, also generate it now.
    if weak_text:
        setup_responses = await generate_setup_responses(
            question,
            stream_id,
            source_extraction=source_extraction,
            doctrine_pack=doctrine_pack,
        )
    else:
        setup_responses, weak_text_gen = await asyncio.gather(
            generate_setup_responses(
                question,
                stream_id,
                source_extraction=source_extraction,
                doctrine_pack=doctrine_pack,
            ),
            generate_weak_reference(question, stream_id),
        )
        weak_text = weak_text_gen

    for line in ledger_report("phase b stage 2a").split("\n"):
        log_stream.log(stream_id, line)
    log_stream.log(stream_id, "  Cooling down 10s before clustering...")
    await asyncio.sleep(10)

    centroid_texts = await cluster_to_centroids(setup_responses, stream_id)

    log_stream.log(stream_id, "  Cooling down 15s before rubric proposal...")
    await asyncio.sleep(15)

    initial_criteria = await propose_initial_rubric(
        question, centroid_texts, stream_id, doctrine_pack=doctrine_pack
    )

    log_stream.log(stream_id, "  Cooling down 15s before refinement loop...")
    await asyncio.sleep(15)

    set_call_budget(0, _REFINEMENT_CALL_CEILING)
    log_stream.log(stream_id, f"  Call budget set: {_REFINEMENT_CALL_CEILING} calls for 2d-2f")
    t_total = time.time()
    try:
        result = await run_refinement_loop(
            initial_criteria, centroid_texts, gold_answer, weak_text, stream_id
        )
    except CallBudgetExceeded:
        log_stream.log(
            stream_id,
            f"  Call budget exhausted ({_REFINEMENT_CALL_CEILING} calls)."
            " Aborting refinement — returning initial criteria with uniform weights.",
        )
        uniform_w = round(1.0 / len(initial_criteria), 6) if initial_criteria else 1.0
        result = {
            "criteria": [{**c, "weight": uniform_w} for c in initial_criteria],
            "decomposition_tree": {},
            "refinement_passes": [],
            "stopping_metadata": {
                "reason": "call_budget_exhausted",
                "total_rejected": 0,
                "passes_completed": 0,
            },
            "conditioning_sample": list(centroid_texts),
        }
    finally:
        reset_call_budget()

    if doctrine_pack and controller_card:
        enriched_criteria = await enrich_criteria_with_row_cards(
            stream_id,
            result["criteria"],
            controller_card,
            doctrine_pack,
        )
        result["criteria"] = await run_overlap_audit(stream_id, enriched_criteria, controller_card)

    if dual_rubric_mode and doctrine_pack and controller_card:
        variation_rubric_result = await generate_variation_rubric(
            stream_id,
            result["criteria"],
            controller_card,
            doctrine_pack,
        )
        result["variation_criteria"] = variation_rubric_result["variation_criteria"]
        result["delta_log"] = variation_rubric_result["delta_log"]
        result["selected_variation_answer_posture"] = variation_rubric_result[
            "selected_variation_answer_posture"
        ]

    elapsed_total = time.time() - t_total
    log_stream.log(
        stream_id,
        f"Phase B complete: {len(result['criteria'])} final criteria in {elapsed_total:.0f}s.",
    )
    for line in ledger_report("phase b rubric total").split("\n"):
        log_stream.log(stream_id, line)

    result["setup_responses"] = setup_responses
    result["strong_reference_text"] = gold_answer
    result["weak_reference_text"] = weak_text
    result["gold_answer"] = gold_answer
    result["source_extraction"] = source_extraction
    result["doctrine_pack"] = doctrine_pack
    result["controller_card"] = controller_card
    result["controller_card_version"] = _CONTROLLER_CARD_VERSION if controller_card else None
    result["selected_lane_code"] = selected_lane_code
    result["dual_rubric_mode"] = dual_rubric_mode
    result["variation_question"] = (
        controller_card.get("selected_variation_question_text") if controller_card else None
    )
    return result


# ---------------------------------------------------------------------------
# Validation utility (kept for internal use and tests)
# ---------------------------------------------------------------------------


def _validate_criteria(criteria: list[dict]) -> None:
    required_keys = {"id", "name", "description", "weight"}
    for item in criteria:
        missing = required_keys - item.keys()
        if missing:
            raise ValueError(f"Criterion missing keys: {missing}")
        if not isinstance(item["weight"], (int, float)) or item["weight"] <= 0:
            raise ValueError(f"Invalid weight for criterion '{item['id']}'")
    if criteria:
        total = sum(item["weight"] for item in criteria)
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"Criterion weights must sum to 1.0, got {total:.6f}")


# ---------------------------------------------------------------------------
# Phase 10: Question validation & generation
# ---------------------------------------------------------------------------


async def validate_question(
    stream_id: str | None,
    question: str,
    source_extraction: dict | None = None,
    doctrine_pack: str | None = None,
) -> dict:
    """Run FI question-writing checklist against a question.

    Returns a dict with keys: checks, red_flags, overall_pass, suggestions.
    Never raises -- on parse error returns a dict with parse_error key.
    """
    if stream_id:
        log_stream.log(stream_id, "[Phase 10] Validating question against FI checklist...")
    messages = build_question_validation_messages(question, source_extraction, doctrine_pack)
    raw = await chat_completion(messages=messages, model=_CONTROL_MODEL, temperature=0.0)
    if not raw:
        return {
            "checks": [],
            "red_flags": [],
            "overall_pass": False,
            "suggestions": [],
            "parse_error": "empty response",
        }
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "checks": [],
            "red_flags": [],
            "overall_pass": False,
            "suggestions": [],
            "parse_error": raw[:200],
        }
    return result


async def generate_question(
    stream_id: str | None,
    source_extraction: dict,
    gold_packet_mapping: dict,
    doctrine_pack: str | None = None,
) -> dict:
    """Generate a neutral exam-style question from source extraction + gold packet mapping.

    Returns a dict with keys: question, internal_notes.
    Never raises -- on parse error returns a dict with parse_error key.
    """
    if stream_id:
        log_stream.log(stream_id, "[Phase 10] Generating question from source extraction...")
    pack_content = _get_pack_content(doctrine_pack)
    messages = build_question_generation_messages(
        source_extraction, gold_packet_mapping, pack_content
    )
    raw = await chat_completion(messages=messages, model=_CONTROL_MODEL, temperature=0.3)
    if not raw:
        return {"question": "", "internal_notes": {}, "parse_error": "empty response"}
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"question": "", "internal_notes": {}, "parse_error": raw[:200]}
    return result


# ---------------------------------------------------------------------------
# Phase 12: Operating modes A, C, E
# ---------------------------------------------------------------------------


async def run_mode_a(
    stream_id: str | None,
    case_text: str,
    question: str,
) -> dict:
    """Mode A: source intake screening + extraction + doctrine routing only.

    Returns a dict with keys: screening_result, source_extraction,
    routing_metadata, doctrine_pack.
    """
    if stream_id:
        log_stream.log(stream_id, "[Mode A] Running source extraction only pipeline...")
    screening_result = await screen_source_intake(stream_id or "", case_text, question)
    source_extraction = await extract_source(stream_id or "", case_text, question)
    routing = await route_to_doctrine_pack(stream_id or "", source_extraction, question)
    return {
        "screening_result": screening_result,
        "source_extraction": source_extraction,
        "routing_metadata": routing,
        "doctrine_pack": routing.get("selected_pack"),
    }


async def compare_draft_to_source(
    stream_id: str | None,
    draft_text: str,
    source_extraction: dict,
    doctrine_pack: str | None = None,
) -> dict:
    """Mode C: compare a draft answer against source extraction.

    Returns an 8-key dict matching the Mode C comparison headings.
    Never raises -- returns a dict with parse_error key on failure.
    """
    if stream_id:
        log_stream.log(stream_id, "[Mode C] Comparing draft to source...")
    pack_content = _get_pack_content(doctrine_pack)
    messages = build_draft_comparison_messages(draft_text, source_extraction, pack_content)
    raw = await chat_completion(messages=messages, model=_CONTROL_MODEL, temperature=0.0)
    if not raw:
        return {"parse_error": "empty response"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"parse_error": raw[:200]}


async def run_mode_e(
    stream_id: str | None,
    source_extraction: dict,
    doctrine_pack: str,
    gold_packet_mapping: dict | None = None,
    question: str = "",
) -> list:
    """Mode E: predict failure modes from source extraction.

    If gold_packet_mapping is None, generates it first.
    Returns a list of failure mode dicts with keys: code, label, description, severity.
    """
    if stream_id:
        log_stream.log(stream_id, "[Mode E] Drafting failure modes...")
    if gold_packet_mapping is None:
        gold_packet_mapping = await generate_gold_packet_mapping(
            stream_id or "", source_extraction, doctrine_pack, question
        )
    return await predict_failure_modes(
        stream_id or "", source_extraction, gold_packet_mapping, doctrine_pack
    )
