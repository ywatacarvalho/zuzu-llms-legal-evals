"""FI-specific pipeline stages for the LexEval benchmark construction workflow.

This module owns the FrankInstructions (FI) pipeline steps that run before
the RRD loop in build_rubric():

  Phase 2.5  screen_source_intake()     -- 17-item source intake checklist
  Phase 2    extract_source()           -- 15-heading source extraction
  Phase 3    route_to_doctrine_pack()   -- doctrine pack routing
  Phase 4    generate_gold_packet_mapping()
  Phase 4    predict_failure_modes()

build_rubric() in rubric_service.py remains the orchestrator and calls these
functions directly.  All functions are async and accept a ``stream_id`` for
log streaming.
"""

import json
import uuid

from app.db.session import AsyncSessionLocal
from app.repositories.rubric_repository import RubricRepository
from app.services import frank_instructions, log_stream
from app.services.available_models import CONTROL_MODEL, STRONG_REF_MODEL
from app.services.github_copilot_client import chat_completion
from app.services.rubric_prompts import (
    build_failure_mode_prediction_messages,
    build_gold_answer_messages,
    build_gold_packet_mapping_messages,
    build_karthic_row_card_messages,
    build_locked_controller_card_messages,
    build_overlap_audit_messages,
    build_routing_messages,
    build_selected_variation_messages,
    build_self_audit_messages,
    build_source_extraction_messages,
    build_source_intake_screening_messages,
    build_variation_menu_messages,
    build_variation_rubric_messages,
)

_CONTROL_MODEL = CONTROL_MODEL
_STRONG_REF_MODEL = STRONG_REF_MODEL
_VALID_PACK_IDS = {
    "pack_marriage",
    "pack_suretyship",
    "pack_one_year",
    "pack_land",
    "pack_ucc_2201",
    "pack_executor",
}
_LEGACY_PACK_FALLBACKS = {
    "pack_marriage": "pack_10",
    "pack_suretyship": "pack_10",
    "pack_one_year": "pack_10",
    "pack_land": "pack_20",
    "pack_ucc_2201": "pack_40",
    "pack_executor": "pack_30",
}
_CONTROLLER_CARD_VERSION = "step_2a_v1"
_VARIATION_LANES = {
    "A1": "A",
    "A2": "A",
    "A3": "A",
    "A4": "A",
    "B1": "B",
    "B2": "B",
}


def _get_pack_content(pack_id: str) -> dict:
    try:
        return frank_instructions.get_doctrine_pack(pack_id)
    except Exception:  # noqa: BLE001
        legacy_id = _LEGACY_PACK_FALLBACKS.get(pack_id)
        if not legacy_id:
            raise
        return frank_instructions.get_doctrine_pack(legacy_id)


def _get_failure_bank(pack_id: str) -> dict:
    try:
        return frank_instructions.get_failure_bank(pack_id)
    except Exception:  # noqa: BLE001
        legacy_id = _LEGACY_PACK_FALLBACKS.get(pack_id)
        if not legacy_id:
            raise
        bank = frank_instructions.get_failure_bank(legacy_id)
        bank.setdefault("pack_id", pack_id)
        return bank


def _get_worked_examples(pack_id: str) -> list[str]:
    try:
        return frank_instructions.get_worked_examples(pack_id)
    except Exception:  # noqa: BLE001
        legacy_id = _LEGACY_PACK_FALLBACKS.get(pack_id)
        if not legacy_id:
            raise
        return frank_instructions.get_worked_examples(legacy_id)


def _get_clean_benchmarks(pack_id: str) -> list[str]:
    try:
        return frank_instructions.get_clean_benchmarks(pack_id)
    except Exception:  # noqa: BLE001
        legacy_id = _LEGACY_PACK_FALLBACKS.get(pack_id)
        if not legacy_id:
            raise
        return frank_instructions.get_clean_benchmarks(legacy_id)


def _get_confusion_set(pack_a: str, pack_b: str | None) -> dict | None:
    if not pack_b:
        return None
    getter = getattr(frank_instructions, "get_confusion_set", None)
    if callable(getter):
        try:
            return getter(pack_a, pack_b)
        except Exception:  # noqa: BLE001
            pass
    return {
        "candidate_route_a": pack_a,
        "candidate_route_b": pack_b,
        "relationship": "needs_disambiguation",
        "note": "Resolve the competing routes explicitly before freezing the doctrine pack.",
    }


def _extract_secondary_packs(routing: dict) -> list[str]:
    secondary_packs = routing.get("secondary_candidate_packs") or []
    if isinstance(secondary_packs, list):
        cleaned = [
            item for item in secondary_packs if isinstance(item, str) and item in _VALID_PACK_IDS
        ]
        if cleaned:
            return cleaned
    secondary_issues = routing.get("secondary_issues") or []
    if isinstance(secondary_issues, list):
        found: list[str] = []
        for item in secondary_issues:
            text = item if isinstance(item, str) else json.dumps(item)
            for pack_id in _VALID_PACK_IDS:
                if pack_id in text and pack_id not in found:
                    found.append(pack_id)
        return found
    return []


def _derive_routing_status(routing: dict) -> str:
    confidence = routing.get("confidence")
    secondaries = _extract_secondary_packs(routing)
    if confidence == "low" and secondaries:
        return "multiple_plausible"
    if confidence == "low":
        return "unstable"
    return "stable"


def _extract_payload_list(parsed: object, *keys: str) -> list:
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in keys:
            value = parsed.get(key)
            if isinstance(value, list):
                return value
    return []


def _merge_criteria(base_criteria: list[dict], enriched_criteria: list[dict]) -> list[dict]:
    if not enriched_criteria:
        return base_criteria
    by_id = {item.get("id"): item for item in enriched_criteria if isinstance(item, dict)}
    merged: list[dict] = []
    for index, criterion in enumerate(base_criteria):
        match = by_id.get(criterion.get("id"))
        if (
            match is None
            and index < len(enriched_criteria)
            and isinstance(enriched_criteria[index], dict)
        ):
            match = enriched_criteria[index]
        merged.append({**criterion, **(match or {})})
    return merged


def _apply_overlap_audits(criteria: list[dict], audits: list[dict]) -> list[dict]:
    if not audits:
        return criteria
    audits_by_code = {
        audit.get("row_code") or audit.get("id"): audit
        for audit in audits
        if isinstance(audit, dict)
    }
    updated: list[dict] = []
    for criterion in criteria:
        row_code = criterion.get("row_code") or criterion.get("id")
        audit = audits_by_code.get(row_code)
        if not audit:
            updated.append(criterion)
            continue
        merged = dict(criterion)
        if audit.get("distinctness_note"):
            merged["distinctness_note"] = audit["distinctness_note"]
        if audit.get("merge_with"):
            merged["merge_with"] = audit["merge_with"]
        if audit.get("overlap_status"):
            merged["overlap_status"] = audit["overlap_status"]
        updated.append(merged)
    return updated


def _lane_family(selected_lane_code: str | None) -> str:
    if selected_lane_code is None:
        return "none"
    return _VARIATION_LANES.get(selected_lane_code, "none")


def _answer_posture_for_reuse(answer_reuse_level: str | None) -> str:
    if answer_reuse_level == "Ambiguity rewrite required":
        return "ambiguity_rewrite"
    if answer_reuse_level in {"Reuse as-is", "Cosmetic edits only"}:
        return "localized_edit"
    return "same_as_base"


def _normalize_controller_card(
    controller_card: dict,
    source_extraction: dict,
    gold_packet_mapping: dict,
    doctrine_pack: str,
    question: str,
    gold_answer: str,
) -> dict:
    normalized = dict(controller_card)
    normalized.setdefault("selected_pack", doctrine_pack)
    normalized.setdefault(
        "doctrine_family",
        gold_packet_mapping.get("doctrine_family", doctrine_pack),
    )
    normalized.setdefault("benchmark_posture", gold_packet_mapping.get("benchmark_posture"))
    normalized.setdefault("current_question_text", question)
    normalized.setdefault("gold_answer", gold_answer)
    normalized.setdefault(
        "likely_controlling_doctrine",
        gold_packet_mapping.get("controlling_trigger"),
    )
    normalized.setdefault(
        "correct_trigger_test",
        gold_packet_mapping.get("controlling_trigger"),
    )
    normalized.setdefault("trigger_facts", source_extraction.get("trigger_facts"))
    normalized.setdefault(
        "required_gate_order",
        gold_packet_mapping.get("required_gate_order", []),
    )
    normalized.setdefault("writing_status", "omitted")
    normalized.setdefault(
        "allowed_fallbacks",
        gold_packet_mapping.get("possible_substitutes_exceptions", []),
    )
    normalized.setdefault(
        "fallback_limits",
        gold_packet_mapping.get("limits_on_substitutes_exceptions", []),
    )
    normalized.setdefault("omitted_control_fact", "none")
    normalized.setdefault("variation_lane", "none")
    normalized.setdefault("selected_lane_code", "none")
    normalized.setdefault("variation_menu_options", "none")
    normalized.setdefault("selected_variation_summary", "none")
    normalized.setdefault("selected_variation_fact_deltas", [])
    normalized.setdefault("rubric_patch_scope", "base rubric only")
    normalized.setdefault(
        "failure_bank",
        _get_failure_bank(doctrine_pack).get("pack_id", doctrine_pack),
    )
    normalized.setdefault("base_question_text", question)
    normalized.setdefault("base_gold_answer", gold_answer)
    normalized.setdefault("selected_variation_question_text", None)
    normalized.setdefault("selected_variation_answer_posture", "same_as_base")
    normalized.setdefault("dual_rubric_mode", "off")
    normalized.setdefault("rubric_separation_rule", "strict")
    normalized.setdefault("evaluation_tracks", "original_only")
    normalized.setdefault(
        "workflow_source_case_name",
        source_extraction.get("canonical_source_case_name") or "none",
    )
    normalized.setdefault(
        "workflow_source_case_citation",
        source_extraction.get("canonical_source_case_citation") or "none",
    )
    normalized.setdefault(
        "source_case_monitoring",
        "on" if source_extraction.get("source_case_monitoring_relevant") else "off",
    )
    normalized.setdefault(
        "case_citation_verification_mode",
        bool(source_extraction.get("source_case_monitoring_relevant")),
    )
    normalized.setdefault("case_citation_scoring_rule", "metadata_only")
    return normalized


async def _build_selected_variation_package(
    stream_id: str | None,
    controller_card: dict,
    selected_option: dict,
    doctrine_pack: str,
) -> dict:
    messages = build_selected_variation_messages(
        controller_card=controller_card,
        selected_option=selected_option,
        doctrine_pack_content=_get_pack_content(doctrine_pack),
    )
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Selected variation generation returned invalid JSON: {exc}") from exc


def _set_attr_if_present(obj: object, attr: str, value: object) -> bool:
    if not hasattr(obj, attr):
        return False
    setattr(obj, attr, value)
    return True


# ---------------------------------------------------------------------------
# Phase 2.5 + Phase 2: source screening and extraction
# ---------------------------------------------------------------------------


async def screen_source_intake(stream_id: str, case_text: str, question: str) -> dict:
    """Run 17-item source intake screening (FI file 02).

    Returns a dict with 17 checklist fields plus ``stop_triggered``. Never
    aborts the pipeline -- a weak/stop rating is logged as a warning only.
    """
    if stream_id:
        log_stream.log(stream_id, "[Phase 2.5] Source intake screening (17-item checklist)...")
    messages = build_source_intake_screening_messages(case_text, question)
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        result: dict = json.loads(raw)
    except json.JSONDecodeError:
        result = {"parse_error": raw[:500], "stop_triggered": False}
    rating = result.get("final_intake_rating", "")
    stop = bool(result.get("stop_triggered", False))
    if stop or rating == "Not a strong gold-source candidate without additional authority":
        if stream_id:
            log_stream.log(
                stream_id,
                f"  Screening: not a strong candidate (rating={rating!r}, "
                f"stop_triggered={stop}). Pipeline continues.",
            )
    elif stream_id:
        log_stream.log(stream_id, f"  Screening complete. Rating: {rating!r}")
    return result


async def extract_source(stream_id: str, case_text: str, question: str) -> dict:
    """Run FI Step 1 source extraction (18-heading template).

    Returns an 18-key dict. Logs a warning when ``benchmark_use_confidence`` is
    'Weak' or 'Not candidate' but does not abort the pipeline.
    Raises ValueError on unparseable JSON.
    """
    if stream_id:
        log_stream.log(stream_id, "[Phase 2] Source extraction (18-heading template)...")
    messages = build_source_extraction_messages(case_text, question)
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        result: dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Source extraction returned invalid JSON: {exc}") from exc
    confidence = result.get("benchmark_use_confidence", "")
    if confidence in ("Weak", "Not candidate"):
        if stream_id:
            log_stream.log(
                stream_id,
                f"  Extraction: benchmark_use_confidence={confidence!r}. Pipeline continues.",
            )
    elif stream_id:
        log_stream.log(stream_id, f"  Extraction complete. Confidence: {confidence!r}")
    return result


# ---------------------------------------------------------------------------
# Phase 3: doctrine pack routing
# ---------------------------------------------------------------------------


async def route_to_doctrine_pack(stream_id: str, source_extraction: dict, question: str) -> dict:
    """Route source to a doctrine pack (FI file 05).

    Returns a routing dict with keys ``selected_pack``, ``reason``,
    ``secondary_issues``, and ``confidence``. Validates ``selected_pack``
    against the six allowed B-series values. Runs a confusion-set second pass
    when the initial route is low-confidence and a secondary candidate exists.
    Raises ValueError on invalid JSON or an unrecognised pack ID.
    """
    if stream_id:
        log_stream.log(stream_id, "[Phase 3] Doctrine pack routing...")
    messages = build_routing_messages(source_extraction, question)
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        result: dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Routing returned invalid JSON: {exc}") from exc
    pack = result.get("selected_pack", "")
    if pack not in _VALID_PACK_IDS:
        raise ValueError(
            f"Routing returned unrecognised selected_pack: {pack!r}. "
            f"Expected one of {sorted(_VALID_PACK_IDS)}."
        )
    confidence = result.get("confidence", "")
    if confidence == "low":
        secondary_packs = _extract_secondary_packs(result)
        confusion_set = _get_confusion_set(pack, secondary_packs[0] if secondary_packs else None)
        if confusion_set is not None:
            if stream_id:
                log_stream.log(
                    stream_id,
                    "  Routing confidence is low. Running confusion-set pass...",
                )
            second_pass_messages = build_routing_messages(
                source_extraction,
                question,
                confusion_set=confusion_set,
                prior_routing=result,
            )
            second_raw = await chat_completion(
                messages=second_pass_messages,
                model=_CONTROL_MODEL,
                response_format={"type": "json_object"},
                temperature=0.1,
                stream_id=stream_id,
            )
            try:
                second_result: dict = json.loads(second_raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Confusion-set routing returned invalid JSON: {exc}") from exc
            second_pack = second_result.get("selected_pack", "")
            if second_pack not in _VALID_PACK_IDS:
                raise ValueError(
                    f"Confusion-set routing returned unrecognised selected_pack: {second_pack!r}. "
                    f"Expected one of {sorted(_VALID_PACK_IDS)}."
                )
            second_result["initial_routing"] = result
            result = second_result
            confidence = result.get("confidence", confidence)
    result["routing_status"] = result.get("routing_status") or _derive_routing_status(result)
    if confidence == "low" and stream_id:
        log_stream.log(
            stream_id,
            "  Routing: low-confidence selection "
            f"{result.get('selected_pack')!r}. Pipeline continues.",
        )
    elif stream_id:
        log_stream.log(
            stream_id,
            f"  Routing complete. Pack: {result.get('selected_pack')!r}, "
            f"confidence: {confidence!r}, "
            f"status: {result['routing_status']!r}",
        )
    return result


# ---------------------------------------------------------------------------
# Phase 4: gold packet mapping + failure mode prediction
# ---------------------------------------------------------------------------


async def generate_gold_packet_mapping(
    stream_id: str,
    source_extraction: dict,
    doctrine_pack: str,
    question: str,
) -> dict:
    """Generate FI Step 2 gold packet mapping (13-heading template).

    Returns a 13-key dict.  Raises ValueError on invalid JSON.
    """
    if stream_id:
        log_stream.log(stream_id, "[Phase 4] Generating gold packet mapping (13 headings)...")
    pack_content = _get_pack_content(doctrine_pack)
    messages = build_gold_packet_mapping_messages(source_extraction, pack_content, question)
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        result: dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gold packet mapping returned invalid JSON: {exc}") from exc
    if stream_id:
        log_stream.log(stream_id, f"  Gold packet mapping complete. Keys: {len(result)}")
    return result


async def predict_failure_modes(
    stream_id: str,
    source_extraction: dict,
    gold_packet_mapping: dict,
    doctrine_pack: str,
) -> list:
    """Predict 5+ failure modes using the pack failure bank (FI Step 3).

    Returns a list of dicts with keys ``code``, ``label``, ``description``,
    ``severity``.  Raises ValueError on invalid JSON.
    """
    if stream_id:
        log_stream.log(stream_id, "[Phase 4] Predicting failure modes...")
    failure_bank = _get_failure_bank(doctrine_pack)
    messages = build_failure_mode_prediction_messages(
        source_extraction, gold_packet_mapping, failure_bank
    )
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failure mode prediction returned invalid JSON: {exc}") from exc
    # The model may return either a list directly or {"failure_modes": [...]}
    if isinstance(parsed, list):
        result = parsed
    else:
        result = parsed.get("failure_modes", parsed.get("modes", []))
    if stream_id:
        log_stream.log(stream_id, f"  Failure modes predicted: {len(result)}")
    return result


# ---------------------------------------------------------------------------
# Phase 7: gold-answer generation
# ---------------------------------------------------------------------------


async def generate_gold_answer(
    stream_id: str | None,
    source_extraction: dict,
    gold_packet_mapping: dict,
    doctrine_pack: str,
    question: str,
) -> str:
    """Generate a gold-standard benchmark answer for the FI path (Phase 7).

    Uses the strong-reference model (STRONG_REF_MODEL) with the full
    FrankInstructions output-shell format, provenance discipline, and doctrine
    pack gate order.  Returns the raw answer text.
    """
    if stream_id:
        log_stream.log(stream_id, "[Phase 7] Generating gold-standard answer...")
    pack_content = _get_pack_content(doctrine_pack)
    worked_examples = _get_worked_examples(doctrine_pack)
    clean_benchmarks = _get_clean_benchmarks(doctrine_pack)
    messages = build_gold_answer_messages(
        source_extraction=source_extraction,
        gold_packet_mapping=gold_packet_mapping,
        doctrine_pack_content=pack_content,
        question=question,
        worked_examples=worked_examples,
        clean_benchmarks=clean_benchmarks,
    )
    result = await chat_completion(
        messages=messages,
        model=_STRONG_REF_MODEL,
        temperature=0.3,
        stream_id=stream_id,
    )
    if stream_id:
        log_stream.log(stream_id, f"  Gold answer generated ({len(result)} chars).")
    return result


async def generate_controller_card(
    stream_id: str,
    source_extraction: dict,
    gold_packet_mapping: dict,
    doctrine_pack: str,
    question: str,
    gold_answer: str,
    routing_metadata: dict,
) -> dict:
    """Generate the Step 2A locked controller card for downstream rubric work."""
    if stream_id:
        log_stream.log(stream_id, "[Phase 1] Generating locked controller card...")
    messages = build_locked_controller_card_messages(
        source_extraction=source_extraction,
        gold_packet_mapping=gold_packet_mapping,
        doctrine_pack=doctrine_pack,
        question=question,
        gold_answer=gold_answer,
        routing_metadata=routing_metadata,
    )
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        parsed: dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Controller card returned invalid JSON: {exc}") from exc
    controller_card = _normalize_controller_card(
        parsed,
        source_extraction,
        gold_packet_mapping,
        doctrine_pack,
        question,
        gold_answer,
    )
    if stream_id:
        log_stream.log(stream_id, f"  Controller card ready ({len(controller_card)} fields).")
    return controller_card


async def enrich_criteria_with_row_cards(
    stream_id: str,
    criteria: list[dict],
    controller_card: dict,
    doctrine_pack: str,
) -> list[dict]:
    """Enrich finalized criteria with Karthic row-card fields."""
    if not criteria:
        return criteria
    if stream_id:
        log_stream.log(stream_id, "[Phase 4] Enriching criteria with Karthic row cards...")
    messages = build_karthic_row_card_messages(
        criteria=criteria,
        controller_card=controller_card,
        doctrine_pack_content=_get_pack_content(doctrine_pack),
        failure_bank=_get_failure_bank(doctrine_pack),
    )
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        if stream_id:
            log_stream.log(
                stream_id,
                "  Row-card enrichment parse failed. Preserving base criteria.",
            )
        return criteria
    enriched = _extract_payload_list(parsed, "criteria", "rows")
    return _merge_criteria(criteria, enriched)


async def run_overlap_audit(
    stream_id: str,
    criteria: list[dict],
    controller_card: dict,
) -> list[dict]:
    """Run the Karthic overlap audit and annotate criteria with distinctness notes."""
    if not criteria:
        return criteria
    if stream_id:
        log_stream.log(stream_id, "[Phase 4] Running overlap audit...")
    messages = build_overlap_audit_messages(criteria)
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        if stream_id:
            log_stream.log(
                stream_id,
                "  Overlap audit parse failed. Preserving enriched criteria.",
            )
        return criteria
    audits = _extract_payload_list(parsed, "audits")
    return _apply_overlap_audits(criteria, audits)


async def generate_variation_rubric(
    stream_id: str,
    base_criteria: list[dict],
    controller_card: dict,
    doctrine_pack: str,
) -> dict:
    """Generate the selected-variation rubric and delta log for dual-rubric mode."""
    if stream_id:
        log_stream.log(stream_id, "[Phase 5] Generating selected-variation rubric...")
    messages = build_variation_rubric_messages(
        base_criteria=base_criteria,
        controller_card=controller_card,
        doctrine_pack_content=_get_pack_content(doctrine_pack),
    )
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        parsed: dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Variation rubric generation returned invalid JSON: {exc}") from exc
    return {
        "variation_criteria": _extract_payload_list(
            parsed,
            "selected_variation_rubric",
            "variation_criteria",
        ),
        "delta_log": _extract_payload_list(parsed, "delta_log"),
        "selected_variation_answer_posture": parsed.get(
            "selected_variation_answer_posture",
            controller_card.get("selected_variation_answer_posture", "same_as_base"),
        ),
    }


async def generate_variation_menu(
    stream_id: str,
    controller_card: dict,
    doctrine_pack: str,
) -> list[dict]:
    """Generate the short lane-coded variation menu for the approved FI packet."""
    if stream_id:
        log_stream.log(stream_id, "[Phase 7] Generating variation menu...")
    messages = build_variation_menu_messages(
        controller_card=controller_card,
        doctrine_pack_content=_get_pack_content(doctrine_pack),
    )
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Variation menu generation returned invalid JSON: {exc}") from exc
    options = _extract_payload_list(parsed, "options", "recommended_options")
    return options[:6]


async def apply_variation_selection(
    rubric_id: uuid.UUID | str,
    selected_lane_code: str | None,
) -> dict:
    """Apply the user's variation choice and return the Phase B context payload."""
    rubric_uuid = rubric_id if isinstance(rubric_id, uuid.UUID) else uuid.UUID(str(rubric_id))
    async with AsyncSessionLocal() as db:
        repo = RubricRepository(db)
        rubric = await repo.get_by_id(rubric_uuid)
        if rubric is None:
            raise ValueError("Rubric not found.")

        controller_card = dict(getattr(rubric, "controller_card", None) or {})
        doctrine_pack = getattr(rubric, "doctrine_pack", None)
        if doctrine_pack is None:
            raise ValueError("Rubric has no doctrine_pack. Cannot apply variation selection.")

        base_question = controller_card.get("base_question_text") or rubric.question
        base_gold_answer = controller_card.get("base_gold_answer") or rubric.gold_answer
        controller_card.setdefault("selected_pack", doctrine_pack)
        controller_card.setdefault("current_question_text", base_question)
        controller_card.setdefault("base_question_text", base_question)
        controller_card.setdefault("base_gold_answer", base_gold_answer)

        variation_question: str | None = None
        variation_options: list[dict] = []
        variation_package: dict | None = None
        dual_rubric_mode = selected_lane_code is not None

        if selected_lane_code is None:
            controller_card.update(
                {
                    "variation_lane": "none",
                    "selected_lane_code": "none",
                    "variation_menu_options": "none",
                    "selected_variation_summary": "none",
                    "selected_variation_fact_deltas": [],
                    "selected_variation_question_text": None,
                    "selected_variation_answer_posture": "same_as_base",
                    "dual_rubric_mode": "off",
                    "evaluation_tracks": "original_only",
                    "rubric_patch_scope": "base rubric only",
                    "omitted_control_fact": "none",
                    "current_question_text": base_question,
                }
            )
        else:
            stream_id = getattr(rubric, "fi_stream_id", None) or str(rubric_uuid)
            variation_options = await generate_variation_menu(
                stream_id,
                controller_card,
                doctrine_pack,
            )
            option = next(
                (item for item in variation_options if item.get("lane_code") == selected_lane_code),
                None,
            )
            if option is None:
                raise ValueError(
                    f"Selected lane code is not available for this rubric: {selected_lane_code}"
                )
            variation_package = await _build_selected_variation_package(
                stream_id,
                controller_card,
                option,
                doctrine_pack,
            )
            variation_question = variation_package.get("varied_legal_question") or base_question
            controller_card.update(
                {
                    "variation_lane": _lane_family(selected_lane_code),
                    "selected_lane_code": selected_lane_code,
                    "variation_menu_options": [item.get("lane_code") for item in variation_options],
                    "selected_variation_summary": variation_package.get(
                        "selected_variation_summary",
                        option.get("what_changes"),
                    ),
                    "selected_variation_fact_deltas": variation_package.get(
                        "selected_variation_fact_deltas",
                        variation_package.get("swap_log", []),
                    ),
                    "selected_variation_question_text": variation_question,
                    "selected_variation_answer_posture": variation_package.get(
                        "selected_variation_answer_posture",
                        _answer_posture_for_reuse(variation_package.get("answer_reuse_level")),
                    ),
                    "dual_rubric_mode": "on",
                    "evaluation_tracks": "original_and_selected_variation",
                    "rubric_patch_scope": "selected variation only",
                    "omitted_control_fact": variation_package.get("omitted_control_fact", "none"),
                    "current_question_text": variation_question,
                }
            )

        _set_attr_if_present(rubric, "controller_card", controller_card)
        _set_attr_if_present(rubric, "controller_card_version", _CONTROLLER_CARD_VERSION)
        _set_attr_if_present(rubric, "selected_lane_code", selected_lane_code)
        _set_attr_if_present(rubric, "dual_rubric_mode", dual_rubric_mode)
        _set_attr_if_present(rubric, "base_question", base_question)
        _set_attr_if_present(rubric, "base_gold_answer", base_gold_answer)
        _set_attr_if_present(rubric, "variation_question", variation_question)
        await db.commit()

    return {
        "controller_card": controller_card,
        "controller_card_version": _CONTROLLER_CARD_VERSION,
        "selected_lane_code": selected_lane_code,
        "dual_rubric_mode": dual_rubric_mode,
        "base_question": base_question,
        "base_gold_answer": base_gold_answer,
        "variation_question": variation_question,
        "variation_package": variation_package,
    }


# ---------------------------------------------------------------------------
# Phase 8: self-audit
# ---------------------------------------------------------------------------


async def run_self_audit(
    stream_id: str | None,
    gold_answer: str,
    source_extraction: dict,
    doctrine_pack: str,
    routing_metadata: dict,
) -> dict:
    """Run the FI self-audit checklist (file 06) on the gold answer.

    Returns a dict with keys: fast_triage, red_flags, release_check, classification.
    Logs warnings for high-severity classifications.
    """
    if stream_id:
        log_stream.log(stream_id, "[Phase 8] Running self-audit...")
    messages = build_self_audit_messages(
        gold_answer=gold_answer,
        source_extraction=source_extraction,
        doctrine_pack=doctrine_pack,
        routing_metadata=routing_metadata,
    )
    raw = await chat_completion(
        messages=messages,
        model=_CONTROL_MODEL,
        response_format={"type": "json_object"},
        temperature=0.1,
        stream_id=stream_id,
    )
    try:
        result: dict = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "parse_error": raw[:500],
            "classification": "Needs targeted revision",
        }
    classification = result.get("classification", "")
    if stream_id:
        if classification == "Needs rerouting":
            log_stream.log(
                stream_id,
                "  [CRITICAL] Self-audit: Needs rerouting. Manual review required.",
            )
        elif classification == "Needs major rewrite":
            log_stream.log(
                stream_id,
                "  [WARNING] Self-audit: Needs major rewrite. Review recommended.",
            )
        else:
            log_stream.log(stream_id, f"  Self-audit complete. Classification: {classification!r}")
    return result
