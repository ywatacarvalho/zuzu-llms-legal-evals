"""
Analysis pipeline -- steps 5-8 of the LexEval evaluation workflow.

Step 5  Embed all responses and cluster (data-adaptive k via silhouette score)
Step 6  Find the centroid response per cluster (highest cosine similarity to centroid vector)
Step 7  Score each centroid against the rubric criteria with GPT-4.1 (three weighting modes)
Step 8  Identify the winning cluster and rank models by share within that cluster
"""

import asyncio
import json
import time
from collections import Counter
from math import floor

import numpy as np

from app.services.available_models import CONTROL_MODEL
from app.services.clustering import _EXECUTOR, embed_and_cluster
from app.services.dasha_prompts import (
    build_case_citation_verification_messages,
    build_scoring_overlay_messages,
)
from app.services.github_copilot_client import chat_completion

# Re-export so existing tests can patch analysis_service._embed_and_cluster
_embed_and_cluster = embed_and_cluster
_get_encoder = None  # patched in tests; actual encoder lives in clustering.py

_MAX_CENTROID_CHARS = 3_000

_SCORING_SYSTEM = """\
You are an expert legal reviewer scoring a model response against an evaluation rubric.

For each criterion, assign a score from 0.0 to 1.0 where:
- 0.0  the response completely fails this criterion
- 0.5  the response partially addresses this criterion
- 1.0  the response fully and correctly addresses this criterion

Compute weighted_total as the sum of (score × weight) across all criteria.

Return ONLY valid JSON matching this exact schema, with no text outside the JSON:
{
  "criterion_scores": { "<criterion_id>": <float 0.0–1.0> },
  "weighted_total": <float 0.0–1.0>
}
"""

_SCORING_SYSTEM_WITH_TAGS = """\
You are an expert legal reviewer scoring a model response against an evaluation rubric.

For each criterion, assign a score from 0.0 to 1.0 where:
- 0.0  the response completely fails this criterion
- 0.5  the response partially addresses this criterion
- 1.0  the response fully and correctly addresses this criterion

Compute weighted_total as the sum of (score × weight) across all criteria.

Additionally, identify failure modes present in this response using the failure bank for the
doctrine pack provided, and record structured Module 0 metadata tags.

Return ONLY valid JSON matching this exact schema, with no text outside the JSON:
{
  "criterion_scores": { "<criterion_id>": <float 0.0–1.0> },
  "weighted_total": <float 0.0–1.0>,
  "failure_tags": [{"code": "<code>", "label": "<label>", "severity": "high|medium|low"}],
  "metadata_tags": {
    "bottom_line_outcome": "<one-sentence summary>",
    "outcome_correctness": "correct | incorrect | partial | unclear",
    "reasoning_alignment": "aligned | misaligned | partial",
    "jurisdiction_assumption": "<jurisdiction>",
    "controlling_doctrine_named": "<doctrine>"
  }
}
"""


async def _score_centroid_detailed(
    centroid_text: str,
    question: str,
    criteria: list[dict],
    evaluation_id: str | None = None,
    doctrine_pack: str | None = None,
    judge_model: str | None = None,
) -> tuple[float, dict[str, float], list[dict], dict]:
    """Score a centroid.

    Returns (weighted_total, {criterion_id: score}, failure_tags, metadata_tags).
    Uses judge_model when provided, otherwise falls back to CONTROL_MODEL.
    """
    model = judge_model or CONTROL_MODEL
    if doctrine_pack:
        from app.services.frank_instructions import get_failure_bank  # noqa: PLC0415

        failure_bank = get_failure_bank(doctrine_pack)
        system_prompt = _SCORING_SYSTEM_WITH_TAGS
        failure_bank_section = (
            f"\n\nFailure bank for {doctrine_pack}:\n{json.dumps(failure_bank, indent=2)}"
        )
    else:
        system_prompt = _SCORING_SYSTEM
        failure_bank_section = ""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Legal question: {question}\n\n"
                f"Rubric criteria:\n{json.dumps(criteria, indent=2)}"
                + failure_bank_section
                + f"\n\nModel response:\n{centroid_text}\n\nScore this response now."
            ),
        },
    ]
    raw = await chat_completion(
        messages=messages,
        model=model,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=evaluation_id,
    )
    empty_scores = {c["id"]: 0.0 for c in criteria}
    try:
        parsed = json.loads(raw)
        raw_scores = parsed.get("criterion_scores", {})
        cscores = {c["id"]: float(raw_scores.get(c["id"], 0.0)) for c in criteria}
        try:
            total = float(parsed["weighted_total"])
        except (KeyError, ValueError):
            total = round(sum(cscores[c["id"]] * float(c["weight"]) for c in criteria), 4)
        failure_tags: list[dict] = parsed.get("failure_tags") or []
        metadata_tags: dict = parsed.get("metadata_tags") or {}
        return total, cscores, failure_tags, metadata_tags
    except (json.JSONDecodeError, KeyError, ValueError):
        pass
    try:
        raw_scores = parsed.get("criterion_scores", {})  # type: ignore[possibly-undefined]
        cscores = {c["id"]: float(raw_scores.get(c["id"], 0.0)) for c in criteria}
        total = round(sum(cscores[c["id"]] * float(c["weight"]) for c in criteria), 4)
        return total, cscores, [], {}
    except Exception:  # noqa: BLE001
        return 0.0, empty_scores, [], {}


async def _score_centroid(
    centroid_text: str,
    question: str,
    criteria: list[dict],
    evaluation_id: str | None = None,
) -> float:
    """Score a centroid. Returns weighted total only."""
    total, _, _, _ = await _score_centroid_detailed(
        centroid_text, question, criteria, evaluation_id
    )
    return total


def _compute_centroid_composition(cluster_responses: list[dict]) -> dict:
    """Compute per-cluster composition summary from a list of {model, text} dicts.

    Returns:
      cluster_size_total, model_breakdown, represented_model_count,
      dominant_model_name, dominant_model_count, dominant_model_share
    """
    total = len(cluster_responses)
    counts: Counter = Counter(r["model"] for r in cluster_responses)
    breakdown = [
        {
            "model_name": model,
            "answer_count": count,
            "answer_share": round(count / total, 4) if total else 0.0,
        }
        for model, count in counts.most_common()
    ]
    dominant = breakdown[0] if breakdown else {}
    return {
        "cluster_size_total": total,
        "model_breakdown": breakdown,
        "represented_model_count": len(counts),
        "dominant_model_name": dominant.get("model_name", ""),
        "dominant_model_count": dominant.get("answer_count", 0),
        "dominant_model_share": dominant.get("answer_share", 0.0),
    }


async def run_case_citation_verification(
    centroid_text: str,
    workflow_source_case_name: str,
    workflow_source_case_citation: str,
    evaluation_id: str | None = None,
) -> dict:
    """Run case citation extraction and hallucination classification for a centroid.

    Returns structured citation metadata dict. Does not apply penalties.
    """
    messages = build_case_citation_verification_messages(
        centroid_text, workflow_source_case_name, workflow_source_case_citation
    )
    raw = await chat_completion(
        messages=messages,
        model=CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.0,
        stream_id=evaluation_id,
    )
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}


async def apply_scoring_overlays(
    centroid_text: str,
    subtotal: float,
    criteria_scores: dict,
    controller_card: dict,
    evaluation_id: str | None = None,
) -> dict:
    """Apply Dasha Phase 6 P_ penalty codes and CAP_ caps to a rubric subtotal.

    subtotal is on the 0–100 scale (already converted).
    Returns overlay result dict with penalties_applied, cap_status,
    post_penalty_score, and final_score.
    """
    try:
        from app.services.frank_instructions import CAP_CODES, PENALTY_CODES  # noqa: PLC0415
    except ImportError:
        PENALTY_CODES = []
        CAP_CODES = []

    messages = build_scoring_overlay_messages(
        centroid_text=centroid_text,
        subtotal=subtotal,
        criteria_scores=criteria_scores,
        penalty_codes=PENALTY_CODES,
        cap_codes=CAP_CODES,
        controller_card=controller_card,
    )
    raw = await chat_completion(
        messages=messages,
        model=CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.0,
        stream_id=evaluation_id,
    )
    try:
        parsed = json.loads(raw)
        penalties = parsed.get("penalties_applied", [])
        cap_status = parsed.get("cap_status", {"cap_code": None, "applied": False})
        penalty_sum = sum(float(p.get("points", 0)) for p in penalties)
        post_penalty = round(max(0.0, min(100.0, subtotal - penalty_sum)), 1)
        cap_code = cap_status.get("cap_code")
        if cap_status.get("applied") and cap_code:
            final = round(min(post_penalty, float(parsed.get("final_score", post_penalty))), 1)
        else:
            final = post_penalty
        return {
            "penalties_applied": penalties,
            "cap_status": cap_status,
            "post_penalty_score": post_penalty,
            "final_score": final,
        }
    except (json.JSONDecodeError, ValueError, KeyError):
        return {
            "penalties_applied": [],
            "cap_status": {"cap_code": None, "applied": False},
            "post_penalty_score": subtotal,
            "final_score": subtotal,
        }


def compute_panel_majority(judge_votes: dict) -> dict:
    """Determine panel majority from per-judge winning cluster votes.

    judge_votes: {judge_model: winning_cluster_index}
    Returns:
      panel_majority_status: "majority" | "no_majority"
      best_centroid: int | None
      disputed_centroids: list[int]
    """
    if not judge_votes:
        return {
            "panel_majority_status": "no_majority",
            "best_centroid": None,
            "disputed_centroids": [],
        }
    vote_counts: Counter = Counter(judge_votes.values())
    total_judges = len(judge_votes)
    best, best_count = vote_counts.most_common(1)[0]
    if best_count > total_judges / 2:
        return {
            "panel_majority_status": "majority",
            "best_centroid": best,
            "disputed_centroids": [],
        }
    disputed = [cluster for cluster, _ in vote_counts.most_common()]
    return {
        "panel_majority_status": "no_majority",
        "best_centroid": None,
        "disputed_centroids": disputed,
    }


async def _run_overlay_for_centroid(
    cid: int,
    centroid_text: str,
    weighted_total: float,
    criteria_scores: dict,
    controller_card: dict,
    case_citation_verification_mode: bool,
    workflow_source_case_name: str | None,
    workflow_source_case_citation: str | None,
    evaluation_id: str | None,
) -> tuple[int, dict, dict]:
    """Run Phase 6 overlay (citation verification + penalty/cap) for a single centroid.

    Returns (cid, overlay_result, citation_meta).
    """
    citation_meta: dict = {}
    if (
        case_citation_verification_mode
        and workflow_source_case_name
        and workflow_source_case_citation
    ):
        citation_meta = await run_case_citation_verification(
            centroid_text=centroid_text,
            workflow_source_case_name=workflow_source_case_name,
            workflow_source_case_citation=workflow_source_case_citation,
            evaluation_id=evaluation_id,
        )

    subtotal = round(weighted_total * 100, 1)
    overlay = await apply_scoring_overlays(
        centroid_text=centroid_text,
        subtotal=subtotal,
        criteria_scores=criteria_scores,
        controller_card=controller_card,
        evaluation_id=evaluation_id,
    )
    return cid, overlay, citation_meta


def _apply_weighting(
    criterion_scores_matrix: dict[int, dict[str, float]],
    criteria: list[dict],
    mode: str,
) -> dict[str, float]:
    """
    Compute a weighted cluster score under the specified mode.

    Parameters
    ----------
    criterion_scores_matrix  {cluster_id: {criterion_id: score}}
    criteria                 list of dicts with "id" and "weight"
    mode                     "uniform" | "heuristic" | "whitened_uniform"

    Returns {str(cluster_id): float}
    """
    cluster_ids = sorted(criterion_scores_matrix.keys())
    criterion_ids = [c["id"] for c in criteria]

    if mode == "uniform":
        w = 1.0 / len(criteria) if criteria else 0.0
        return {
            str(cid): round(
                sum(criterion_scores_matrix[cid].get(c_id, 0.0) for c_id in criterion_ids) * w, 4
            )
            for cid in cluster_ids
        }

    if mode == "heuristic":
        weight_map = {c["id"]: float(c["weight"]) for c in criteria}
        return {
            str(cid): round(
                sum(
                    criterion_scores_matrix[cid].get(c_id, 0.0) * weight_map.get(c_id, 0.0)
                    for c_id in criterion_ids
                ),
                4,
            )
            for cid in cluster_ids
        }

    if mode == "whitened_uniform":
        M = np.array(
            [
                [criterion_scores_matrix[cid].get(c_id, 0.0) for c_id in criterion_ids]
                for cid in cluster_ids
            ],
            dtype=float,
        )
        means = M.mean(axis=0)
        stds = M.std(axis=0)
        M_norm = (M - means) / (stds + 1e-6)
        scores = M_norm.mean(axis=1)
        scores = scores - scores.min()
        total = scores.sum()
        if total > 0:
            scores = scores / total
        return {str(cluster_ids[i]): round(float(scores[i]), 4) for i in range(len(cluster_ids))}

    return {}


def _cluster_model_shares(
    scores: dict[str, float],
    clusters_map: dict[int, list[int]],
    responses: list,
) -> dict:
    winning = max(clusters_map.keys(), key=lambda cid: scores.get(str(cid), 0.0))
    winning_indices = clusters_map[winning]
    counts: Counter = Counter(responses[i].model_name for i in winning_indices)
    total = len(winning_indices)
    shares = {m: round(c / total, 4) for m, c in sorted(counts.items(), key=lambda x: -x[1])}
    return {"scores": scores, "winning_cluster": winning, "model_shares": shares}


async def run_analysis(
    question: str,
    responses: list,
    rubric_criteria: list[dict],
    evaluation_id: str | None = None,
    doctrine_pack: str | None = None,
    judge_models: list[str] | None = None,
    controller_card: dict | None = None,
    case_citation_verification_mode: bool = False,
    workflow_source_case_name: str | None = None,
    workflow_source_case_citation: str | None = None,
    dual_rubric_mode: bool = False,
    variation_criteria: list[dict] | None = None,
    variation_question: str | None = None,
    variation_responses: list | None = None,
) -> dict:
    """
    Run the full analysis pipeline for a completed evaluation.

    Returns a dict ready for AnalysisRepository.create().
    All original keys are preserved. New keys added:
      baseline_scores        — raw per-criterion, per-centroid score matrix
      weighting_comparison   — model_shares ranking under uniform/heuristic/whitened_uniform
      weighting_mode         — primary mode ("heuristic")
      centroid_composition   — per-cluster composition summary
      penalties_applied      — per-centroid penalty deductions (Phase 6)
      cap_status             — per-centroid cap status (Phase 6)
      final_scores           — per-centroid final scores after overlay (Phase 6)
      case_citation_metadata — per-centroid citation audit results (when mode enabled)
      judge_panel            — panel config when multiple judge models provided (Phase 8)
      judge_votes            — per-judge winning cluster votes (Phase 8)
      zak_review_flag        — escalation flag from panel majority check (Phase 9)
      variation_scores       — base-vs-variation side-by-side scoring (when dual mode)
    When doctrine_pack is provided, failure_tags per centroid are also returned.
    """
    from app.services import log_stream  # local import to avoid circular deps

    def _log(msg: str) -> None:
        if evaluation_id:
            log_stream.log(str(evaluation_id), msg)

    texts = [r.response_text or "" for r in responses]
    n_models = len({r.model_name for r in responses})
    k_min = max(floor(n_models * 1.5), 4)
    k_max_est = min(15, max(k_min, len(texts) // 10))
    t_total = time.time()

    _log(
        f"[analysis] Step 1/3 — Embedding {len(texts)} responses ({n_models} models) "
        f"and clustering (sweeping k={k_min}..{k_max_est})"
    )
    t0 = time.time()
    loop = asyncio.get_event_loop()
    cluster_data = await loop.run_in_executor(_EXECUTOR, _embed_and_cluster, texts, None, k_min)

    k: int = cluster_data["k"]
    clusters_map: dict[int, list[int]] = cluster_data["clusters_map"]
    centroid_indices_map: dict[int, int] = cluster_data["centroid_indices"]
    silhouette_scores_by_k: dict[int, float] = cluster_data.get("silhouette_scores_by_k", {})
    cluster_ids = sorted(clusters_map.keys())
    elapsed_embed = time.time() - t0

    best_sil = max(silhouette_scores_by_k.values()) if silhouette_scores_by_k else 0.0
    _log(
        f"[analysis] Embedding + clustering complete in {elapsed_embed:.0f}s — "
        f"k={k} selected (best silhouette={best_sil:.3f})"
    )
    for cid in cluster_ids:
        size = len(clusters_map[cid])
        label = "response" if size == 1 else "responses"
        preview = texts[centroid_indices_map[cid]][:100].replace("\n", " ")
        _log(f"  Cluster {cid}: {size} {label} — centroid: {preview!r}...")

    # Phase 2A — Centroid composition
    centroid_composition: dict[str, dict] = {}
    for cid in cluster_ids:
        cluster_responses = [
            {"model": responses[i].model_name, "text": texts[i]} for i in clusters_map[cid]
        ]
        centroid_composition[str(cid)] = _compute_centroid_composition(cluster_responses)

    # Determine judge models to use
    effective_judges: list[str] = judge_models if judge_models else [CONTROL_MODEL]
    panel_mode = "multi_model_panel" if len(effective_judges) > 1 else "single_model"
    judge_panel: dict | None = None
    if len(effective_judges) > 1:
        judge_panel = {
            "models": effective_judges,
            "mode": panel_mode,
            "aggregation_rule": "average_criterion_scores",
            "homogeneity_status": "pending",
        }
        _log(f"[analysis] Judge panel: {effective_judges}")

    # Score all centroids concurrently, logging each result as it arrives
    n_criteria = len(rubric_criteria)
    _log(
        f"[analysis] Step 2/3 — Scoring {k} centroid responses against rubric "
        f"({n_criteria} criteria, running concurrently)"
    )
    t0 = time.time()

    async def _score_with_judge(
        cid: int, judge: str
    ) -> tuple[int, str, float, dict[str, float], list[dict], dict]:
        total, per_criterion, ftags, mtags = await _score_centroid_detailed(
            texts[centroid_indices_map[cid]],
            question,
            rubric_criteria,
            evaluation_id,
            doctrine_pack=doctrine_pack,
            judge_model=judge,
        )
        return cid, judge, total, per_criterion, ftags, mtags

    # Run all (cluster, judge) pairs concurrently
    judge_tasks = [
        _score_with_judge(cid, judge) for cid in cluster_ids for judge in effective_judges
    ]
    all_scored = await asyncio.gather(*judge_tasks)
    elapsed_score = time.time() - t0

    # Aggregate: if multiple judges, average criterion scores across judges per cluster
    criterion_scores_matrix: dict[int, dict[str, float]] = {}
    totals_map: dict[int, float] = {}
    failure_tags_per_centroid: dict[str, dict] = {}
    judge_votes: dict[str, int] = {}

    for cid in cluster_ids:
        cid_results = [(j, tot, pc, ft, mt) for ci, j, tot, pc, ft, mt in all_scored if ci == cid]
        if len(cid_results) == 1:
            _, total, per_crit, ftags, mtags = cid_results[0]
            criterion_scores_matrix[cid] = per_crit
            totals_map[cid] = total
            if ftags or mtags:
                failure_tags_per_centroid[str(cid)] = {
                    "failure_tags": ftags,
                    "metadata_tags": mtags,
                }
        else:
            # Average criterion scores across judges
            all_crit_ids = [c["id"] for c in rubric_criteria]
            avg_per_crit = {
                c_id: round(
                    sum(pc.get(c_id, 0.0) for _, _, pc, _, _ in cid_results) / len(cid_results), 4
                )
                for c_id in all_crit_ids
            }
            criterion_scores_matrix[cid] = avg_per_crit
            totals_map[cid] = round(
                sum(avg_per_crit[c["id"]] * float(c["weight"]) for c in rubric_criteria), 4
            )
            # Use first judge's failure/metadata tags (primary)
            _, _, _, ftags, mtags = cid_results[0]
            if ftags or mtags:
                failure_tags_per_centroid[str(cid)] = {
                    "failure_tags": ftags,
                    "metadata_tags": mtags,
                }

    # Phase 8 — record each judge's top centroid vote
    if len(effective_judges) > 1:
        for judge in effective_judges:
            judge_cid_scores = {ci: tot for ci, j, tot, _, _, _ in all_scored if j == judge}
            best_cid = max(judge_cid_scores, key=lambda c: judge_cid_scores[c])
            judge_votes[judge] = best_cid
        _log(f"[analysis] Judge votes: {judge_votes}")

    _log(f"[analysis] Scoring complete in {elapsed_score:.0f}s")

    for cid in cluster_ids:
        _log(f"  Cluster {cid} scored: {round(totals_map[cid] * 100, 1)}% weighted total")

    # Primary scores (heuristic = rubric weights, backward-compatible)
    scores: dict[str, float] = {str(cid): round(totals_map[cid], 4) for cid in cluster_ids}
    winning_cluster = max(cluster_ids, key=lambda cid: scores[str(cid)])
    winning_indices = clusters_map[winning_cluster]
    model_counts: Counter = Counter(responses[i].model_name for i in winning_indices)
    total_in_winner = len(winning_indices)
    model_shares: dict[str, float] = {
        model: round(count / total_in_winner, 4)
        for model, count in sorted(model_counts.items(), key=lambda x: -x[1])
    }

    top_model = max(model_shares, key=lambda m: model_shares[m]) if model_shares else "n/a"
    _log(
        f"[analysis] Winning cluster: {winning_cluster} "
        f"(score={round(scores[str(winning_cluster)] * 100, 1)}%) | "
        f"top model: {top_model} ({round(model_shares.get(top_model, 0) * 100, 1)}% share)"
    )

    clusters_list = [
        {
            "cluster_id": cid,
            "response_indices": clusters_map[cid],
            "centroid_index": centroid_indices_map[cid],
            "centroid_response_text": texts[centroid_indices_map[cid]][:_MAX_CENTROID_CHARS],
            "model_counts": dict(
                Counter(responses[i].model_name for i in clusters_map[cid]).most_common()
            ),
        }
        for cid in cluster_ids
    ]

    # Weighting comparison
    _log("[analysis] Step 3/3 — Computing weighting comparisons (uniform / heuristic / whitened)")
    weighting_comparison = {
        mode: _cluster_model_shares(
            _apply_weighting(criterion_scores_matrix, rubric_criteria, mode),
            clusters_map,
            responses,
        )
        for mode in ("uniform", "heuristic", "whitened_uniform")
    }

    for mode, data in weighting_comparison.items():
        wc = data.get("winning_cluster", "?")
        ms = data.get("model_shares", {})
        top = max(ms, key=lambda m: ms[m]) if ms else "n/a"
        share = round(ms.get(top, 0) * 100, 1) if ms else 0
        _log(f"  [{mode}] winner=cluster {wc}, top model: {top} ({share}% share)")

    # Phase 6 — Dasha scoring overlay (citation verification + penalty/cap application)
    _log("[analysis] Phase 6 — Applying Dasha scoring overlays")
    _cc = controller_card or {}
    penalties_per_centroid: dict[str, list] = {}
    cap_status_per_centroid: dict[str, dict] = {}
    final_scores: dict[str, float] = {}
    citation_metadata: dict[str, dict] = {}

    overlay_tasks = [
        _run_overlay_for_centroid(
            cid=cid,
            centroid_text=texts[centroid_indices_map[cid]],
            weighted_total=totals_map[cid],
            criteria_scores=criterion_scores_matrix[cid],
            controller_card=_cc,
            case_citation_verification_mode=case_citation_verification_mode,
            workflow_source_case_name=workflow_source_case_name,
            workflow_source_case_citation=workflow_source_case_citation,
            evaluation_id=evaluation_id,
        )
        for cid in cluster_ids
    ]
    overlay_results = await asyncio.gather(*overlay_tasks)
    for cid, overlay, citation_meta in overlay_results:
        penalties_per_centroid[str(cid)] = overlay.get("penalties_applied", [])
        cap_status_per_centroid[str(cid)] = overlay.get(
            "cap_status", {"cap_code": None, "applied": False}
        )
        final_scores[str(cid)] = overlay.get("final_score", round(totals_map[cid] * 100, 1))
        if citation_meta:
            citation_metadata[str(cid)] = citation_meta

    # Phase 5 — Dual-track variation scoring
    variation_scores: dict | None = None
    if dual_rubric_mode and variation_criteria:
        _log("[analysis] Phase 5 — Scoring variation rubric track")
        if variation_responses:
            # Separate clustering path: cluster variation responses independently.
            var_texts = [r.response_text or "" for r in variation_responses]
            var_k_min = max(floor(len({r.model_name for r in variation_responses}) * 1.5), 4)
            var_cluster_data = await loop.run_in_executor(
                _EXECUTOR, _embed_and_cluster, var_texts, None, var_k_min
            )
            var_cluster_ids = sorted(var_cluster_data["clusters_map"].keys())
            var_centroid_indices: dict[int, int] = var_cluster_data["centroid_indices"]
            _log(
                f"[analysis] Variation track: {len(var_texts)} responses, k={var_cluster_data['k']}"
            )
            var_scored = await asyncio.gather(
                *[
                    _score_centroid_detailed(
                        var_texts[var_centroid_indices[cid]],
                        variation_question or question,
                        variation_criteria,
                        evaluation_id,
                        doctrine_pack=doctrine_pack,
                    )
                    for cid in var_cluster_ids
                ]
            )
            var_totals = {cid: tot for cid, (tot, _, _, _) in zip(var_cluster_ids, var_scored)}
            var_scores_map = {str(cid): round(var_totals[cid], 4) for cid in var_cluster_ids}
            var_winning = max(var_cluster_ids, key=lambda c: var_totals[c])
            var_final = {str(cid): round(var_totals[cid] * 100, 1) for cid in var_cluster_ids}
            separate = True
        else:
            # Fallback: re-score base centroids against variation rubric.
            var_scored = await asyncio.gather(
                *[
                    _score_centroid_detailed(
                        texts[centroid_indices_map[cid]],
                        question,
                        variation_criteria,
                        evaluation_id,
                        doctrine_pack=doctrine_pack,
                    )
                    for cid in cluster_ids
                ]
            )
            var_totals = {cid: tot for cid, (tot, _, _, _) in zip(cluster_ids, var_scored)}
            var_scores_map = {str(cid): round(var_totals[cid], 4) for cid in cluster_ids}
            var_winning = max(cluster_ids, key=lambda c: var_totals[c])
            var_final = {str(cid): round(var_totals[cid] * 100, 1) for cid in cluster_ids}
            separate = False
        variation_scores = {
            "scores": var_scores_map,
            "winning_cluster": var_winning,
            "final_scores": var_final,
            "separate_clustering": separate,
        }

    # Phase 9 — Zak escalation
    zak_review_flag: dict | None = None
    if judge_votes:
        majority_result = compute_panel_majority(judge_votes)
        zak_review_flag = {
            "flag": ("no" if majority_result["panel_majority_status"] == "majority" else "yes"),
            "reason": (
                None if majority_result["panel_majority_status"] == "majority" else "no_majority"
            ),
            "disputed_centroids": majority_result["disputed_centroids"],
        }
        _log(f"[analysis] Zak flag: {zak_review_flag['flag']} — {zak_review_flag['reason']}")

    elapsed_total = time.time() - t_total
    _log(f"[analysis] Pipeline complete in {elapsed_total:.0f}s — results saved")

    result: dict = {
        "k": k,
        "clusters": clusters_list,
        "centroid_indices": [centroid_indices_map[cid] for cid in cluster_ids],
        "scores": scores,
        "winning_cluster": winning_cluster,
        "model_shares": model_shares,
        "weighting_mode": "heuristic",
        "baseline_scores": {str(cid): criterion_scores_matrix[cid] for cid in cluster_ids},
        "weighting_comparison": weighting_comparison,
        "silhouette_scores_by_k": {str(k): v for k, v in silhouette_scores_by_k.items()},
        "failure_tags": failure_tags_per_centroid if failure_tags_per_centroid else None,
        "centroid_composition": centroid_composition,
        "penalties_applied": penalties_per_centroid if penalties_per_centroid else None,
        "cap_status": cap_status_per_centroid if cap_status_per_centroid else None,
        "final_scores": final_scores,
        "case_citation_metadata": citation_metadata if citation_metadata else None,
        "judge_panel": judge_panel,
        "judge_votes": judge_votes if judge_votes else None,
        "zak_review_flag": zak_review_flag,
        "variation_scores": variation_scores,
    }
    return result
