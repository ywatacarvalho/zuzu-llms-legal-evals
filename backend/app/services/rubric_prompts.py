"""
Prompt contract definitions for the RRD rubric-construction pipeline.

Four named roles map to the paper's prompt-level structure:
  1. INITIAL_PROPOSAL  — propose a rubric conditioned on the task + 8 centroid responses
  2. DECOMPOSE         — decompose a broad criterion into narrower subcriteria
  3. FILTER_REDUNDANCY — check whether a criterion overlaps with existing criteria
  4. BINARY_EVAL       — binary pass/fail evaluation of a single response against a criterion

All functions return a messages list ready for chat_completion().
All prompts enforce atomic criteria, prompt-specific wording, binary pass-fail judgeability,
non-overlap across criteria, and prohibit criteria that merely restate the answer.
"""

import json

from app.services.frank_instructions import (
    MODE_C_COMPARISON_HEADINGS,
    MODULE_SKELETON,
    QUESTION_CHECKLIST,
)

_MAX_CENTROID_CHARS = 800  # truncate each centroid to stay within API payload limits
_BASE_SETUP_PROMPT = "You are an expert legal analyst. Answer the legal question thoroughly."


def build_setup_system_prompt(
    source_extraction: dict | None = None,
    doctrine_pack: str | None = None,
) -> str:
    """Build the system prompt used for setup responses (diversity-exploration phase).

    IMPORTANT: This prompt intentionally does NOT impose the 8-heading output shell.
    Setup responses feed the embedding -> k-means -> centroid pipeline and must
    preserve maximum semantic diversity.  FI context is added as *enrichment* only
    (background material the model may use) so the responses can still range freely
    across valid approaches.
    """
    parts = [_BASE_SETUP_PROMPT]
    if source_extraction:
        key_fields = {
            k: source_extraction[k]
            for k in (
                "clean_legal_issue",
                "black_letter_rule",
                "holding_or_best_supported_answer_path",
                "jurisdiction_forum",
            )
            if k in source_extraction and source_extraction[k]
        }
        if key_fields:
            parts.append(
                "Consider the following source material extracted from the uploaded authority:\n"
                + json.dumps(key_fields, indent=2)
            )
    if doctrine_pack:
        parts.append(f"The controlling doctrine family has been identified as: {doctrine_pack}.")
    return "\n\n".join(parts)


def _truncate_centroids(texts: list[str], max_chars: int = _MAX_CENTROID_CHARS) -> list[str]:
    return [t[:max_chars] + ("…" if len(t) > max_chars else "") for t in texts]


def _build_module_skeleton_block() -> str:
    """Return a formatted description of the 4 scored modules for prompt injection."""
    lines = []
    for mod_id in [1, 2, 3, 4]:
        m = MODULE_SKELETON["modules"][mod_id]
        lines.append(
            f"  Module {mod_id} — {m['name']} (default weight: {m['weight']}%): {m['description']}"
        )
    return "\n".join(lines)


def _dump_json(data: object, max_chars: int | None = None) -> str:
    text = json.dumps(data, indent=2)
    if max_chars is None or len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def build_initial_proposal_messages(
    question: str,
    centroid_texts: list[str],
    doctrine_pack: str | None = None,
) -> list[dict]:
    centroids_block = "\n\n".join(
        f"[Response {i + 1}]\n{text}" for i, text in enumerate(_truncate_centroids(centroid_texts))
    )
    modules_block = _build_module_skeleton_block()
    pack_hint = f"\nThe controlling doctrine family is: {doctrine_pack}.\n" if doctrine_pack else ""
    system = (
        "You are a legal expert designing evaluation rubrics for assessing legal reasoning.\n\n"
        "Your task: given a legal question and a set of representative model responses, "
        "propose an evaluation rubric that would meaningfully differentiate response quality.\n\n"
        "MODULE FRAMEWORK:\n"
        "Organize your proposed criteria within the following 4-module framework. "
        "Each criterion MUST belong to exactly one module. "
        "Module default weights are: M1=28%, M2=40%, M3=19%, M4=13%. "
        "You may adjust individual criterion weights but each module's total should approximate "
        "its default.\n\n" + modules_block + pack_hint + "\n\nRules:\n"
        "- Generate between 3 and 7 criteria based on what the responses reveal.\n"
        "- Each criterion must be ATOMIC (measures exactly one thing).\n"
        "- Each criterion must be DISCRIMINATIVE: some of the provided responses should pass "
        "it and some should fail it. Do not include criteria that all responses satisfy "
        "or none can satisfy.\n"
        "- Each criterion must be BINARY-EVALUABLE: a reviewer can clearly say pass or fail.\n"
        "- Criteria must not overlap with each other.\n"
        "- Criteria must not simply restate the answer itself.\n"
        "- Assign a weight to each criterion (positive, all weights sum to 1.0).\n\n"
        "Return ONLY valid JSON:\n"
        '{"criteria": [{"id": "snake_case_id", "name": "Short Name", '
        '"description": "What this measures and how to evaluate it.",'
        ' "weight": 0.20, "module_id": 1}]}'
    )
    user = (
        f"Legal question: {question}\n\n"
        f"Representative responses:\n\n{centroids_block}\n\n"
        "Propose the evaluation rubric now."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_decompose_messages(
    criterion: dict,
    centroid_texts: list[str],
) -> list[dict]:
    centroids_block = "\n\n".join(
        f"[Response {i + 1}]\n{text}" for i, text in enumerate(_truncate_centroids(centroid_texts))
    )
    module_id = criterion.get("module_id")
    if module_id is not None and module_id in MODULE_SKELETON["modules"]:
        m = MODULE_SKELETON["modules"][module_id]
        module_constraint = (
            f"MODULE BOUNDARY: The parent criterion belongs to Module {module_id} "
            f"({m['name']}): {m['description']} "
            f"All subcriteria MUST remain within Module {module_id}.\n\n"
        )
    else:
        module_constraint = ""
    system = (
        "You are a legal evaluation expert. A rubric criterion is too broad — it applies to "
        "too many of the provided responses and therefore does not discriminate between them.\n\n"
        "Your task: decompose this broad criterion into 2 or 3 narrower, more specific "
        "subcriteria that together cover the same ground but are each individually "
        "more discriminative.\n\n" + module_constraint + "Rules for subcriteria:\n"
        "- Each must be atomic and binary-evaluable.\n"
        "- Each must be discriminative against the provided responses.\n"
        "- Together they should cover the intent of the parent criterion.\n"
        "- No overlap between subcriteria.\n"
        "- Assign weights that sum to the parent's weight.\n\n"
        "Return ONLY valid JSON:\n"
        '{"children": [{"id": "snake_case_id", "name": "Short Name", '
        '"description": "...", "weight": 0.10, "module_id": 1}]}'
    )
    user = (
        f"Parent criterion:\n{json.dumps(criterion, indent=2)}\n\n"
        f"Representative responses:\n\n{centroids_block}\n\n"
        "Decompose this criterion now."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_filter_redundancy_messages(
    candidate: dict,
    accepted_criteria: list[dict],
) -> list[dict]:
    system = (
        "You are reviewing a candidate rubric criterion for redundancy.\n\n"
        "A criterion is REDUNDANT if it measures substantially the same dimension as "
        "one or more already-accepted criteria, such that scoring both would double-count "
        "the same aspect of response quality.\n\n"
        "A criterion is NOT redundant if it captures a meaningfully distinct aspect, "
        "even if related.\n\n"
        'Return ONLY valid JSON: {"redundant": true/false, "reason": "brief explanation"}'
    )
    user = (
        f"Candidate criterion:\n{json.dumps(candidate, indent=2)}\n\n"
        f"Already-accepted criteria:\n{json.dumps(accepted_criteria, indent=2)}\n\n"
        "Is the candidate redundant?"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_binary_eval_messages(
    criterion: dict,
    centroid_text: str,
) -> list[dict]:
    system = (
        "You are evaluating whether a legal model response passes a specific rubric criterion.\n\n"
        "Answer PASS if the response clearly satisfies the criterion.\n"
        "Answer FAIL if the response clearly does not satisfy it.\n\n"
        'Return ONLY valid JSON: {"passes": true/false}'
    )
    user = (
        f"Criterion:\n{json.dumps(criterion, indent=2)}\n\n"
        f"Model response:\n{centroid_text}\n\n"
        "Does this response pass the criterion?"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


_MAX_CASE_TEXT_CHARS = 12000


def build_source_intake_screening_messages(case_text: str, question: str) -> list[dict]:
    """Build messages for the 17-item source intake screening checklist (FI file 02).

    Returns a messages list for the control model. The model is asked to evaluate
    whether the source can anchor a gold-standard benchmark evaluation packet and
    to return a JSON object with 17 checklist keys plus ``stop_triggered``.
    """
    system = (
        "You are an expert legal analyst screening whether a source authority can anchor a "
        "gold-standard benchmark evaluation packet.\n\n"
        "Evaluate this source against the 17-item screening checklist below. "
        "Return a JSON object with exactly these 18 keys (17 checklist items + stop_triggered).\n\n"
        "Checklist keys (use these exact snake_case names):\n"
        "1. candidate_source\n"
        "2. source_type_authority_level\n"
        "3. target_doctrine_family_likely_pack\n"
        "4. clean_legal_issue\n"
        "5. black_letter_rule_extractable\n"
        "6. trigger_facts_identifiable\n"
        "7. holding_usable_for_benchmark\n"
        "8. limits_boundaries_identifiable\n"
        "9. procedural_noise_level\n"
        "10. jurisdiction_sensitivity_split_risk\n"
        "11. benchmark_answer_suitability\n"
        "12. reverse_engineering_suitability\n"
        "13. benchmark_posture (one of: "
        "'Narrow source-grounded benchmark only', "
        "'Generalizable only with supporting authority', "
        "'Portable benchmark under stated assumptions')\n"
        "14. failure_mode_yield\n"
        "15. jd_review_burden\n"
        "16. final_intake_rating (one of: "
        "'Strong lead source', "
        "'Moderate; usable with supporting authority', "
        "'Weak; support/contrast source only', "
        "'Not a strong gold-source candidate without additional authority')\n"
        "17. recommendation (one of: "
        "'Use as lead source', "
        "'Use with supporting authority', "
        "'Contrast/support source only', "
        "'Do not use')\n"
        "18. stop_triggered (bool)\n\n"
        "Set stop_triggered=true if ANY of the following apply:\n"
        "- Source is mostly headnotes, synopsis, syllabus, or editorial material\n"
        "- No clear doctrinal holding on the target issue\n"
        "- Too procedural to support a stable benchmark answer\n"
        "- Too fact-bound to generalize without distortion\n"
        "- Too jurisdiction-split to support a clean benchmark answer without added authority\n"
        "- No clear path to a narrow reverse-engineered question\n"
        "- No clean doctrinal center or no stable routing path to a single doctrine family\n\n"
        "Return ONLY valid JSON."
    )
    truncated = case_text[:_MAX_CASE_TEXT_CHARS] + (
        "\u2026" if len(case_text) > _MAX_CASE_TEXT_CHARS else ""
    )
    user = f"Source text:\n{truncated}\n\nQuestion: {question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_source_extraction_messages(case_text: str, question: str) -> list[dict]:
    """Build messages for FI Step 1 source extraction (18-heading template).

    Returns a messages list for the control model. The model is asked to extract
    structured information from the source and return a JSON object with 18 keys.
    """
    headings = (
        "1. selected_doctrine_pack\n"
        "2. candidate_source\n"
        "3. source_type_authority_level\n"
        "4. jurisdiction_forum\n"
        "5. procedural_posture\n"
        "6. clean_legal_issue\n"
        "7. black_letter_rule\n"
        "8. trigger_facts\n"
        "9. holding_or_best_supported_answer_path\n"
        "10. why_that_result_follows\n"
        "11. limits_boundaries\n"
        "12. what_source_does_not_decide\n"
        "13. jurisdiction_sensitivity_split_risk\n"
        "14. benchmark_use_confidence "
        "(one of: 'Strong', 'Moderate', 'Weak', 'Not candidate')\n"
        "15. jd_review_needed (one of: 'yes', 'no', 'partial')\n"
        "16. canonical_source_case_name\n"
        "17. canonical_source_case_citation\n"
        "18. source_case_monitoring_relevant (boolean)"
    )
    system = (
        "You are an expert legal analyst extracting structured information from a legal source "
        "authority for benchmark evaluation.\n\n"
        "Extract information using exactly these 18 snake_case keys. "
        "For each major legal proposition, append one of these traceability tags in brackets: "
        "[Supported by source], [Inference from source], or [Background generalization].\n\n"
        f"Keys:\n{headings}\n\n"
        "Rules:\n"
        "- Use only what the source text contains. Do not invent facts, holdings, or "
        "jurisdiction-specific rules.\n"
        "- If a heading does not apply, use null.\n"
        "- benchmark_use_confidence must be exactly one of: "
        "'Strong', 'Moderate', 'Weak', 'Not candidate'.\n"
        "- jd_review_needed must be exactly one of: 'yes', 'no', 'partial'.\n"
        "- Use null for canonical_source_case_name and canonical_source_case_citation when the "
        "benchmark is not grounded in a single lead case.\n"
        "- source_case_monitoring_relevant must be true only when the benchmark should track "
        "mentions of that lead case during downstream evaluation.\n"
        "Return ONLY valid JSON."
    )
    truncated = case_text[:_MAX_CASE_TEXT_CHARS] + (
        "\u2026" if len(case_text) > _MAX_CASE_TEXT_CHARS else ""
    )
    user = f"Source text:\n{truncated}\n\nQuestion: {question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_routing_messages(
    source_extraction: dict,
    question: str,
    confusion_set: dict | None = None,
    prior_routing: dict | None = None,
) -> list[dict]:
    """Build messages for doctrine pack routing (FI file 05).

    Returns a messages list for the control model.  The model must choose one of
    the six valid B-series pack IDs and return a JSON object with routing details.
    """
    pack_descriptions = (
        "pack_marriage -- Marriage provision. Use when marriage is the consideration for the "
        "promise.\n"
        "pack_suretyship -- Suretyship provision. Use when the promise is collateral and answers "
        "for another person's debt or default.\n"
        "pack_one_year -- One-year provision. Use when full performance is impossible within one "
        "year from contract formation.\n"
        "pack_land -- Land provision. Use when the promise transfers or materially affects an "
        "interest in land.\n"
        "pack_ucc_2201 -- UCC 2-201 provision. Use when Article 2 governs a sale-of-goods "
        "transaction and the writing or substitute route is the controller.\n"
        "pack_executor -- Executor or administrator personal-promise provision. Use when a "
        "fiduciary allegedly promises to answer personally for an estate obligation."
    )
    classification_gates = (
        "Gate G1 -- governing law family first.\n"
        "Gate G2 -- test whether the Statute of Frauds provision is actually triggered.\n"
        "Gate G3 -- if the route is unstable, identify that explicitly before offering any "
        "variation workflow."
    )
    priority_rules = (
        "Priority rules: classify first, route by the controlling issue, and preserve "
        "secondary candidates explicitly rather than collapsing them."
    )
    legacy_aliases = (
        "Legacy aliases retained for compatibility: pack_10 -> marriage/suretyship/one-year, "
        "pack_20 -> pack_land, pack_30 -> pack_executor, pack_40 -> pack_ucc_2201."
    )
    no_silent_change_rules = (
        "Do not silently change governing-law family, goods-vs-services classification, land "
        "status, party-role direction, primary-vs-collateral liability, capacity, threshold side, "
        "or writing status while routing."
    )
    confusion_block = ""
    if confusion_set:
        confusion_block = (
            "\n\nCONFUSION-SET ANCHOR:\n"
            + _dump_json(confusion_set, max_chars=3000)
            + "\nUse it to resolve whether this is a dual-trigger, priority, split-transaction, "
            "or needs-classification-first problem."
        )
    prior_routing_block = ""
    if prior_routing:
        prior_routing_block = "\n\nPRIOR ROUTING ATTEMPT:\n" + _dump_json(prior_routing)
    system = (
        "You are a legal doctrine routing expert for Statute of Frauds benchmark evaluation.\n\n"
        "Route the source to exactly ONE controlling B-series pack after you classify the problem. "
        "Identify serious secondary candidates without collapsing them into the primary route.\n\n"
        f"Available packs:\n{pack_descriptions}\n\n"
        f"Global classification gates:\n{classification_gates}\n\n"
        f"{priority_rules}\n\n"
        f"{legacy_aliases}\n\n"
        f"No-silent-change rules:\n{no_silent_change_rules}"
        f"{confusion_block}{prior_routing_block}\n\n"
        "Return ONLY valid JSON:\n"
        '{"selected_pack": '
        '"pack_marriage|pack_suretyship|pack_one_year|pack_land|pack_ucc_2201|pack_executor", '
        '"reason": "one sentence", '
        '"secondary_issues": [], '
        '"secondary_candidate_packs": [], '
        '"governing_law_candidate": "...", '
        '"main_gate_order": [], '
        '"confidence": "high|moderate|low", '
        '"routing_status": "stable|multiple_plausible|unstable"}'
    )
    user = (
        f"Source extraction:\n{_dump_json(source_extraction, max_chars=5000)}\n\n"
        f"Question: {question}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_locked_controller_card_messages(
    source_extraction: dict,
    gold_packet_mapping: dict,
    doctrine_pack: str,
    question: str,
    gold_answer: str,
    routing_metadata: dict,
) -> list[dict]:
    system = (
        "You are drafting the Locked Controller Card for Step 2A of the Frank workflow. "
        "Return one JSON object with exactly the 36 controller-card fields. "
        "Treat the card as a downstream contract for rubric drafting and evaluation.\n\n"
        "Required defaults: selected_lane_code='none', variation_lane='none', "
        "variation_menu_options='none', selected_variation_summary='none', "
        "selected_variation_fact_deltas=[], rubric_patch_scope='base rubric only', "
        "base_question_text=current_question_text, base_gold_answer=gold_answer, "
        "selected_variation_question_text=null, "
        "selected_variation_answer_posture='same_as_base', "
        "dual_rubric_mode='off', rubric_separation_rule='strict', "
        "evaluation_tracks='original_only', "
        "case_citation_verification_mode=false, case_citation_scoring_rule='metadata_only'."
    )
    user = (
        f"Doctrine pack: {doctrine_pack}\n\n"
        f"Source extraction:\n{_dump_json(source_extraction, max_chars=4000)}\n\n"
        f"Gold packet mapping:\n{_dump_json(gold_packet_mapping, max_chars=3500)}\n\n"
        f"Routing metadata:\n{_dump_json(routing_metadata, max_chars=1500)}\n\n"
        f"Current question:\n{question}\n\nGold answer:\n{gold_answer[:5000]}\n\n"
        "Return the full Locked Controller Card as JSON."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_karthic_row_card_messages(
    criteria: list[dict],
    controller_card: dict,
    doctrine_pack_content: dict,
    failure_bank: list[dict] | dict,
) -> list[dict]:
    system = (
        "You are Karthic. Enrich each finalized rubric criterion with row-card metadata without "
        "changing the criterion's legal substance, module, or weight unless clearly necessary.\n\n"
        'Return ONLY valid JSON: {"criteria": [...]} using the same criterion ids and order. '
        "Each enriched criterion must add these fields: row_code, na_guidance, "
        "golden_target_summary, golden_contains, allowed_omissions, contradiction_flags, "
        "comparison_guidance, scoring_anchors, primary_failure_labels, row_status."
    )
    user = (
        f"Controller card:\n{_dump_json(controller_card, max_chars=2500)}\n\n"
        f"Doctrine pack content:\n{_dump_json(doctrine_pack_content, max_chars=2500)}\n\n"
        f"Failure bank:\n{_dump_json(failure_bank, max_chars=2000)}\n\n"
        f"Criteria to enrich:\n{_dump_json(criteria, max_chars=6000)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_overlap_audit_messages(criteria: list[dict]) -> list[dict]:
    system = (
        "Run Karthic Step 6A overlap audit. For each scored row, decide whether it remains "
        "distinct, needs a distinctness note, or should merge with another row.\n\n"
        'Return ONLY valid JSON: {"audits": [{"row_code": "...", '
        '"distinctness_note": "...", "merge_with": null, "overlap_status": '
        '"clean|needs_note|merge"}]}'
    )
    user = f"Criteria:\n{_dump_json(criteria, max_chars=7000)}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_variation_rubric_messages(
    base_criteria: list[dict],
    controller_card: dict,
    doctrine_pack_content: dict,
) -> list[dict]:
    system = (
        "Generate a selected-variation rubric from the preserved base rubric. "
        "Lane A keeps doctrine and weights stable except for localized fact references. "
        "Lane B may patch rows that assumed an omitted control fact and may add a bounded-"
        "uncertainty row when required.\n\n"
        "Return ONLY valid JSON with keys selected_variation_rubric, delta_log, and "
        "selected_variation_answer_posture. Each delta_log entry must mark the difference as "
        "cosmetic, localized_factual, ambiguity_sensitive, or doctrinally_material."
    )
    user = (
        f"Controller card:\n{_dump_json(controller_card, max_chars=3000)}\n\n"
        f"Doctrine pack content:\n{_dump_json(doctrine_pack_content, max_chars=2200)}\n\n"
        f"Base rubric:\n{_dump_json(base_criteria, max_chars=7000)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_variation_menu_messages(
    controller_card: dict,
    doctrine_pack_content: dict,
) -> list[dict]:
    system = (
        "Offer a short, lane-coded variation menu following B00, B01, and B02. "
        "Offer 3 to 6 options maximum, use only options that genuinely fit the routed problem, "
        "and do not generate full variation packages yet.\n\n"
        'Return ONLY valid JSON: {"options": [{"lane_code": "A1", "label": '
        '"...", "what_changes": "...", "why_it_fits": "...", '
        '"expected_answer_reuse": "Reuse as-is|Cosmetic edits only|Unsafe|'
        'Ambiguity rewrite required", '
        '"main_red_flag": "..."}]}'
    )
    user = (
        f"Controller card:\n{_dump_json(controller_card, max_chars=3000)}\n\n"
        f"Doctrine pack content:\n{_dump_json(doctrine_pack_content, max_chars=2200)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_selected_variation_messages(
    controller_card: dict,
    selected_option: dict,
    doctrine_pack_content: dict,
) -> list[dict]:
    system = (
        "Generate exactly one selected variation package for the chosen lane code. "
        "Do not generate any unselected options. Preserve doctrine unless the selected lane is a "
        "designed ambiguity test.\n\n"
        "Return ONLY valid JSON with keys: selected_variation_code, variation_lane, "
        "variation_type, "
        "expected_result_type, variation_status, answer_reuse_level, varied_legal_question, "
        "updated_model_answer, swap_log, rubric_patch_notes, selected_variation_summary, "
        "selected_variation_fact_deltas, selected_variation_answer_posture, "
        "omitted_control_fact, "
        "red_flags, status."
    )
    user = (
        f"Controller card:\n{_dump_json(controller_card, max_chars=2800)}\n\n"
        f"Doctrine pack content:\n{_dump_json(doctrine_pack_content, max_chars=2000)}\n\n"
        f"Selected option:\n{_dump_json(selected_option)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_gold_packet_mapping_messages(
    source_extraction: dict,
    doctrine_pack_content: dict,
    question: str,
) -> list[dict]:
    """Build messages for FI Step 2 gold packet mapping (13-heading template).

    Returns a messages list for the control model.  The model must return a JSON
    object with exactly 13 keys matching the gold packet mapping headings.
    """
    headings = (
        "1. doctrine_family\n"
        "2. controlling_trigger\n"
        "3. required_gate_order\n"
        "4. what_makes_doctrine_apply\n"
        "5. what_does_not_satisfy_it\n"
        "6. independent_competing_barriers\n"
        "7. possible_substitutes_exceptions\n"
        "8. limits_on_substitutes_exceptions\n"
        "9. likely_jurisdiction_sensitive_points\n"
        "10. likely_model_mistakes\n"
        "11. candidate_fact_pattern_ingredients\n"
        "12. reverse_engineering_suitability\n"
        "13. benchmark_posture (one of: "
        "'Pack-specific benchmark only', "
        "'Generalizable only with supporting authority', "
        "'Portable benchmark within the selected pack')"
    )
    pack_name = doctrine_pack_content.get("name", "")
    pack_subissues = doctrine_pack_content.get("must_separate_subissues", [])
    pack_context = f"Doctrine pack: {pack_name}\nMust-separate subissues:\n" + "\n".join(
        f"  - {s}" for s in pack_subissues
    )
    system = (
        "You are an expert legal analyst mapping source material to benchmark evaluation "
        "criteria for a Statute of Frauds evaluation pack.\n\n"
        "Complete the gold packet mapping using exactly these 13 snake_case keys. "
        "For each major proposition, append one of: "
        "[Supported by source], [Inference from source], or [Background generalization].\n\n"
        f"Keys:\n{headings}\n\n"
        f"Doctrine pack context:\n{pack_context}\n\n"
        "Rules:\n"
        "- Use only what the source extraction contains. Do not invent facts or holdings.\n"
        "- If a heading does not apply, use null.\n"
        "- benchmark_posture must be exactly one of the three options listed.\n"
        "Return ONLY valid JSON."
    )
    user = f"Source extraction:\n{json.dumps(source_extraction, indent=2)}\n\nQuestion: {question}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_failure_mode_prediction_messages(
    source_extraction: dict,
    gold_packet_mapping: dict,
    failure_bank: dict,
) -> list[dict]:
    """Build messages for FI Step 3 failure mode prediction.

    Returns a messages list for the control model.  The model must return a JSON
    list of at least 5 dicts with keys ``code``, ``label``, ``description``,
    and ``severity``.
    """
    label_families = failure_bank.get("label_families", {})
    vocabulary_lines = "\n".join(
        f"  {code}: {description}" for code, description in label_families.items()
    )
    pack_id = failure_bank.get("pack_id", "unknown")
    system = (
        "You are an expert legal evaluator predicting the most likely failure modes for "
        "LLM responses to a Statute of Frauds legal question.\n\n"
        f"Use the failure bank vocabulary for {pack_id}:\n{vocabulary_lines}\n\n"
        "Predict 5 or more failure modes. For each, assign:\n"
        "- code: one of the label family codes above (e.g. SG, SC, XD)\n"
        "- label: a short descriptive name\n"
        "- description: one sentence explaining the specific failure\n"
        "- severity: 'high', 'medium', or 'low'\n\n"
        "Return ONLY valid JSON:\n"
        '[{"code": "SG", "label": "...", "description": "...", "severity": "high"}, ...]'
    )
    user = (
        f"Source extraction:\n{json.dumps(source_extraction, indent=2)}\n\n"
        f"Gold packet mapping:\n{json.dumps(gold_packet_mapping, indent=2)}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


_MAX_WORKED_EXAMPLE_CHARS = 3000  # trim long examples to stay within token budget
_MAX_EXTRACTION_CHARS = 4000


def build_gold_answer_messages(
    source_extraction: dict,
    gold_packet_mapping: dict,
    doctrine_pack_content: dict,
    question: str,
    worked_examples: list[str] | None = None,
    clean_benchmarks: list[str] | None = None,
) -> list[dict]:
    """Build messages for FI Step 4 gold-answer generation.

    Uses the 8-heading output shell, provenance-blind writing rules, and doctrine
    pack gate order.  Optionally includes few-shot structural references (worked
    examples) and provenance-blind format references (clean benchmarks).
    """
    from app.services.frank_instructions import (
        OUTPUT_SHELL_HEADINGS,
        PROVENANCE_BANNED_WORDS,
    )

    headings_block = "\n".join(f"{h}:" for h in OUTPUT_SHELL_HEADINGS)
    banned_words = ", ".join(f'"{w}"' for w in PROVENANCE_BANNED_WORDS)
    gate_order = doctrine_pack_content.get("must_separate_subissues", [])
    gate_lines = "\n".join(f"- {rule}" for rule in gate_order) if gate_order else ""
    pack_name = doctrine_pack_content.get("name", "the controlling doctrine family")

    system_parts = [
        "You are an expert legal analyst drafting a gold-standard benchmark answer for "
        "legal-AI evaluation purposes.\n\n"
        "DRAFTING RULES:\n"
        "- Use black-letter-law style; do not invent facts, writings, signatures, or parties.\n"
        "- Name the likely controlling doctrine early.\n"
        "- Keep independent barriers separate.\n"
        "- Address fallback theories only after the main writing or formality analysis.\n"
        "- Do not cite outside authority unless the task asks for it.\n"
        "- If uncertainty remains, identify the specific source of uncertainty.\n\n"
        "PROVENANCE DISCIPLINE:\n"
        f"Do NOT use these words or phrases anywhere in your output: {banned_words}.\n"
        "Write as if you are analyzing the question from your own legal knowledge — "
        "never signal the existence of a source document.\n\n"
        f"DOCTRINE PACK: {pack_name}\n"
        "Gate-order and separation rules you MUST follow:\n" + gate_lines + "\n\n"
        "OUTPUT FORMAT — use exactly these 8 section headings and no others:\n" + headings_block,
    ]

    if worked_examples:
        examples_block = "\n\n---\n".join(
            f"[Structural Reference {i + 1}]\n{ex[:_MAX_WORKED_EXAMPLE_CHARS]}"
            for i, ex in enumerate(worked_examples)
        )
        system_parts.append(
            "STRUCTURAL REFERENCES (show the source-grounded analysis style; "
            "do not treat these as legal authority):\n\n" + examples_block
        )

    if clean_benchmarks:
        benchmarks_block = "\n\n---\n".join(
            f"[Provenance-Blind Format Reference {i + 1}]\n{bm[:_MAX_WORKED_EXAMPLE_CHARS]}"
            for i, bm in enumerate(clean_benchmarks)
        )
        system_parts.append(
            "PROVENANCE-BLIND FORMAT REFERENCES (show the correct final-output style; "
            "note how these avoid any source signals):\n\n" + benchmarks_block
        )

    system = "\n\n".join(system_parts)

    extraction_summary = json.dumps(source_extraction, indent=2)[:_MAX_EXTRACTION_CHARS]
    mapping_summary = json.dumps(gold_packet_mapping, indent=2)[:_MAX_EXTRACTION_CHARS]
    user = (
        f"Question: {question}\n\n"
        f"Source extraction:\n{extraction_summary}\n\n"
        f"Gold packet mapping:\n{mapping_summary}\n\n"
        "Draft the gold-standard benchmark answer now, using the 8 required section headings."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_self_audit_messages(
    gold_answer: str,
    source_extraction: dict,
    doctrine_pack: str,
    routing_metadata: dict,
) -> list[dict]:
    """Build messages for FI Phase 8 self-audit (file 06_CORE_SELF_AUDIT).

    Runs the four-item fast triage, red-flag overlays, and 12-item release check
    against the generated gold answer. Returns a messages list ready for
    chat_completion() with response_format={"type": "json_object"}.
    """
    from app.services.frank_instructions import (
        SELF_AUDIT_CLASSIFICATIONS,
        SELF_AUDIT_FAST_TRIAGE,
        SELF_AUDIT_RED_FLAGS,
        SELF_AUDIT_RELEASE_CHECK,
    )

    # Build fast-triage block
    triage_lines: list[str] = []
    for item in SELF_AUDIT_FAST_TRIAGE:
        triage_lines.append(f"  {item['id']}. {item['name']}:")
        for check in item["checks"]:
            triage_lines.append(f"    - {check}")
    triage_block = "\n".join(triage_lines)

    red_flags_block = "\n".join(f"- {flag}" for flag in SELF_AUDIT_RED_FLAGS)
    release_block = "\n".join(f"- {item}" for item in SELF_AUDIT_RELEASE_CHECK)
    classifications_block = ", ".join(f'"{c}"' for c in SELF_AUDIT_CLASSIFICATIONS)

    confidence = routing_metadata.get("confidence", "unknown")

    system = (
        "You are an expert legal evaluator performing a self-audit on a gold-standard "
        "benchmark answer before it is frozen.\n\n"
        f"The answer was generated for doctrine pack: {doctrine_pack} "
        f"(routing confidence: {confidence}).\n\n"
        "FAST TRIAGE (4 items — evaluate every check):\n" + triage_block + "\n\n"
        "RED-FLAG OVERLAYS — any of these triggers a mandatory review:\n" + red_flags_block + "\n\n"
        "FINAL RELEASE CHECK (12 items):\n" + release_block + "\n\n"
        "For each fast-triage item, evaluate all checks and summarise as pass/fail + notes.\n"
        "List any red flags present in the answer.\n"
        "Evaluate each release-check item as pass or fail.\n"
        "Classify the answer as one of: " + classifications_block + "\n\n"
        "Return ONLY valid JSON:\n"
        '{"fast_triage": {"1": {"pass": true, "notes": "..."}, '
        '"2": {"pass": true, "notes": "..."}, '
        '"3": {"pass": true, "notes": "..."}, '
        '"4": {"pass": true, "notes": "..."}}, '
        '"red_flags": [], '
        '"release_check": {"all_pass": true, "failures": []}, '
        '"classification": "Ready"}'
    )
    extraction_summary = json.dumps(source_extraction, indent=2)[:_MAX_EXTRACTION_CHARS]
    routing_summary = json.dumps(routing_metadata, indent=2)[:1000]
    user = (
        f"Gold answer to audit:\n{gold_answer}\n\n"
        f"Source extraction:\n{extraction_summary}\n\n"
        f"Routing metadata:\n{routing_summary}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_question_validation_messages(
    question: str,
    source_extraction: dict | None = None,
    doctrine_pack: str | None = None,
) -> list[dict]:
    """Validate a question against the FI question-writing checklist (file 04)."""
    design_goals = "\n".join(
        f"  {i + 1}. {g}" for i, g in enumerate(QUESTION_CHECKLIST["design_goals"])
    )
    body_checks = "\n".join(
        f"  {i + 1}. {c}" for i, c in enumerate(QUESTION_CHECKLIST["body_checks"])
    )
    release_checks = "\n".join(
        f"  {i + 1}. {c}" for i, c in enumerate(QUESTION_CHECKLIST["release_checks"])
    )
    neutral_examples = "\n".join(f"  - {e}" for e in QUESTION_CHECKLIST["neutral_call_examples"])
    pack_hint = f"\nControlling doctrine family: {doctrine_pack}.\n" if doctrine_pack else ""
    system = (
        "You are a legal benchmark quality evaluator. Assess whether the submitted question "
        "satisfies the FrankInstructions question-writing standards.\n\n"
        "DESIGN GOALS (7 items):\n" + design_goals + "\n\n"
        "BODY CHECKS (7 items):\n" + body_checks + "\n\n"
        "FINAL RELEASE CHECKS (10 items):\n" + release_checks + "\n\n"
        "NEUTRAL CALL EXAMPLES (for reference):\n" + neutral_examples + pack_hint + "\n\n"
        "RED FLAGS (automatic fail):\n"
        "  - Question names a specific doctrine in the call "
        "('Is this a Statute of Frauds issue?')\n"
        "  - Question gives away the answer direction "
        "('Why is this contract unenforceable?')\n"
        "  - Question invents facts not in the source\n"
        "  - Question omits jurisdiction when the answer depends on it\n\n"
        "Evaluate each body check and release check as pass or fail with a brief note. "
        "List any red flags found. Give an overall pass/fail and concise suggestions.\n\n"
        "Return ONLY valid JSON:\n"
        '{"checks": [{"item": "...", "pass": true, "note": "..."}], '
        '"red_flags": [], "overall_pass": true, "suggestions": []}'
    )
    context_parts: list[str] = [f"Question to evaluate:\n{question}"]
    if source_extraction:
        key_fields = {
            k: source_extraction[k]
            for k in (
                "clean_legal_issue",
                "jurisdiction_forum",
                "holding_or_best_supported_answer_path",
            )
            if k in source_extraction and source_extraction[k]
        }
        if key_fields:
            context_parts.append("Source extraction context:\n" + json.dumps(key_fields, indent=2))
    user = "\n\n".join(context_parts)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_question_generation_messages(
    source_extraction: dict,
    gold_packet_mapping: dict,
    doctrine_pack_content: dict,
) -> list[dict]:
    """Generate a neutral exam-style legal question per FI Step 5 rules (file 04)."""
    design_goals = "\n".join(
        f"  {i + 1}. {g}" for i, g in enumerate(QUESTION_CHECKLIST["design_goals"])
    )
    neutral_examples = "\n".join(f"  - {e}" for e in QUESTION_CHECKLIST["neutral_call_examples"])
    pack_name = doctrine_pack_content.get("name", "")
    pack_hint = f"\nThe controlling doctrine family is: {pack_name}.\n" if pack_name else ""
    system = (
        "You are a legal benchmark designer. Generate a neutral, exam-style legal question "
        "from the provided source extraction and gold packet mapping.\n\n"
        "QUESTION DESIGN GOALS:\n" + design_goals + pack_hint + "\n\n"
        "NO-LEAKAGE RULES:\n"
        "  - Do not name the controlling doctrine in the call of the question\n"
        "  - Do not signal the expected answer direction\n"
        "  - Preserve only the facts needed to trigger the target legal path "
        "plus one or two realistic distractors\n"
        "  - Preserve explicit jurisdiction or governing-law cues\n\n"
        "NEUTRAL CALL EXAMPLES:\n" + neutral_examples + "\n\n"
        "Return ONLY valid JSON:\n"
        '{"question": "...", "internal_notes": {"target_doctrine": "...", '
        '"likely_distractors": [], "source_fidelity_notes": "..."}}'
    )
    extraction_summary = json.dumps(source_extraction, indent=2)[:1500]
    mapping_summary = json.dumps(gold_packet_mapping, indent=2)[:1000]
    user = (
        f"Source extraction:\n{extraction_summary}\n\n"
        f"Gold packet mapping:\n{mapping_summary}\n\n"
        "Generate the question now."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ---------------------------------------------------------------------------
# Phase 12: Mode C -- Draft-to-Source Comparison
# ---------------------------------------------------------------------------


def build_draft_comparison_messages(
    draft_text: str,
    source_extraction: dict,
    doctrine_pack_content: dict,
) -> list[dict]:
    """Build messages for Mode C draft-to-source comparison.

    Compares a draft answer against the source extraction and doctrine pack using
    the 8 Mode C comparison headings from 01_CORE_WORKFLOW_TEMPLATE.txt.
    Returns a messages list ready for chat_completion().
    """
    headings_block = "\n".join(f"  {h}" for h in MODE_C_COMPARISON_HEADINGS)
    pack_name = doctrine_pack_content.get("name", "the controlling doctrine family")
    system = (
        "You are an expert legal analyst comparing a draft answer against its source authority "
        "and selected doctrine pack.\n\n"
        "Compare the draft against the uploaded authority first, then against the selected "
        "doctrine pack. Treat unsupported certainty as a defect.\n\n"
        f"Doctrine pack: {pack_name}\n\n"
        "Evaluate the draft on exactly these 8 dimensions:\n" + headings_block + "\n\n"
        "For each dimension, provide a concise assessment. "
        "Use 'No issues' when the draft performs well on that dimension.\n\n"
        "Return ONLY valid JSON with the 8 snake_case keys derived from the headings:\n"
        '{"source_benchmark_alignment": "...", '
        '"controlling_doctrine_match": "...", '
        '"gate_order_correctness": "...", '
        '"trigger_test_accuracy": "...", '
        '"exception_substitute_mapping": "...", '
        '"fallback_doctrine_treatment": "...", '
        '"factual_fidelity": "...", '
        '"provenance_discipline": "..."}'
    )
    extraction_summary = json.dumps(source_extraction, indent=2)[:_MAX_EXTRACTION_CHARS]
    user = f"Draft answer:\n{draft_text}\n\nSource extraction:\n{extraction_summary}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
