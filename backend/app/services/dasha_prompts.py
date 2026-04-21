"""
Dasha-specific prompt builders for the analysis scoring overlay layer.

Three named roles:
  1. METADATA_TAGS       — structured Module 0 metadata extraction per centroid
  2. CITATION_VERIFY     — case mention extraction and hallucination classification
  3. SCORING_OVERLAY     — P_ penalty and CAP_ cap application on top of rubric subtotal

All functions return a messages list ready for chat_completion().
"""

import json


def build_metadata_tags_messages(
    centroid_text: str,
    rubric_criteria: list[dict],
    module_schema: dict,
    citation_mode: bool = False,
    workflow_source_case_name: str | None = None,
    workflow_source_case_citation: str | None = None,
) -> list[dict]:
    """Build messages for structured Module 0 metadata extraction.

    Returns a messages list. The model must return JSON matching the base schema:
    {
      "bottom_line_outcome": "...",
      "outcome_correctness": "correct | incorrect | partial | unclear",
      "reasoning_alignment": "aligned | misaligned | partial",
      "jurisdiction_assumption": "...",
      "controlling_doctrine_named": "..."
    }

    When citation_mode is True, also returns citation fields:
    {
      "case_mention_status": "none | mentioned",
      "citation_accuracy_status": "...",
      "source_case_reference_status": "...",
      "verified_case_mentions": [...],
      "hallucinated_case_mentions": [...],
      "case_verification_review_flag": true | false
    }
    """
    base_schema = """\
{
  "bottom_line_outcome": "<one-sentence summary of the answer's outcome>",
  "outcome_correctness": "correct | incorrect | partial | unclear",
  "reasoning_alignment": "aligned | misaligned | partial",
  "jurisdiction_assumption": "<jurisdiction the answer assumes or states>",
  "controlling_doctrine_named": "<doctrine the answer treats as controlling>"
}"""

    citation_schema = """\
,
  "case_mention_status": "none | mentioned",
  "citation_accuracy_status": "<accurate | inaccurate | unverifiable | not_applicable>",
  "source_case_reference_status": "<cited_correctly | cited_incorrectly"
    " | not_cited | not_applicable>",
  "verified_case_mentions": ["<case name> — <citation>"],
  "hallucinated_case_mentions": ["<case name>"],
  "case_verification_review_flag": true"""

    schema_block = base_schema
    if citation_mode:
        schema_block = base_schema[:-1] + citation_schema + "\n}"

    modules_summary = ""
    if module_schema and "modules" in module_schema:
        lines = []
        for mod_id, mod in module_schema["modules"].items():
            if int(mod_id) == 0:
                continue
            lines.append(
                f"  Module {mod_id} — {mod['name']} (weight {mod.get('weight', '?')}%): "
                f"{mod.get('description', '')}"
            )
        modules_summary = "\n".join(lines)

    source_note = ""
    if citation_mode and workflow_source_case_name:
        source_note = f"\n\nSource case for citation verification: {workflow_source_case_name}" + (
            f" ({workflow_source_case_citation})" if workflow_source_case_citation else ""
        )

    system = (
        "You are an expert legal evaluator. Your task is to extract structured Module 0 "
        "metadata from a model response to a legal question.\n\n"
        "Module 0 fields are NOT scored — they describe the answer's outcome and reasoning "
        "alignment for human review.\n\n"
        "Module structure for context:\n"
        + modules_summary
        + source_note
        + "\n\nReturn ONLY valid JSON matching this exact schema, with no text outside the JSON:\n"
        + schema_block
    )

    criteria_summary = json.dumps(
        [{"id": c["id"], "name": c.get("name", "")} for c in rubric_criteria], indent=2
    )
    user = (
        f"Rubric criteria (for context only — do not score them):\n{criteria_summary}\n\n"
        f"Model response:\n{centroid_text}\n\n"
        "Extract Module 0 metadata now."
    )

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_case_citation_verification_messages(
    centroid_text: str,
    source_case_name: str,
    source_case_citation: str,
) -> list[dict]:
    """Build messages for case citation extraction and hallucination classification.

    Extracts all case mentions from centroid_text, classifies each as verified,
    uncertain, or hallucinated relative to the source case. Does not apply
    automatic penalties — metadata only.

    The model must return JSON:
    {
      "case_mentions": [
        {
          "name": "<case name as written in the response>",
          "citation_as_written": "<citation string or null>",
          "classification": "verified | uncertain | hallucinated",
          "classification_reason": "<one sentence>"
        }
      ],
      "source_case_referenced": true | false,
      "source_case_reference_accurate": true | false | null,
      "review_flag": true | false
    }
    """
    system = (
        "You are an expert legal citation auditor. Extract every case citation or case name "
        "mentioned in the model response and classify each one.\n\n"
        "Classification definitions:\n"
        "  verified       — the case name and citation match the known source case exactly\n"
        "  uncertain      — the case exists but details are incomplete or unverifiable\n"
        "  hallucinated   — the case name or citation appears fabricated or materially wrong\n\n"
        "Do NOT apply any penalty scores. Record metadata only.\n\n"
        "Set review_flag to true if any hallucinated mention is present or if the source "
        "case is cited inaccurately.\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "case_mentions": [\n'
        "    {\n"
        '      "name": "<case name>",\n'
        '      "citation_as_written": "<citation or null>",\n'
        '      "classification": "verified | uncertain | hallucinated",\n'
        '      "classification_reason": "<one sentence>"\n'
        "    }\n"
        "  ],\n"
        '  "source_case_referenced": true,\n'
        '  "source_case_reference_accurate": true,\n'
        '  "review_flag": false\n'
        "}"
    )

    user = (
        f"Source case: {source_case_name} ({source_case_citation})\n\n"
        f"Model response:\n{centroid_text}\n\n"
        "Extract and classify all case mentions now."
    )

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_scoring_overlay_messages(
    centroid_text: str,
    subtotal: float,
    criteria_scores: dict,
    penalty_codes: list[str],
    cap_codes: list[str],
    controller_card: dict,
) -> list[dict]:
    """Build messages for Dasha Phase 6 scoring overlay (P_ penalties and CAP_ caps).

    Applies penalty codes and cap codes on top of the rubric subtotal (0–100 scale).

    Formula applied by the model:
      post_penalty_score = max(0, subtotal - sum(penalty_points))
      final_score = cap if triggered, else post_penalty_score

    The model must return JSON:
    {
      "penalties_applied": [
        {"code": "P_...", "points": <float>, "label": "<short label>"}
      ],
      "cap_status": {"cap_code": "CAP_..." | null, "applied": false},
      "post_penalty_score": <float 0–100>,
      "final_score": <float 0–100>
    }
    """
    penalty_block = (
        "\n".join(f"  {code}" for code in penalty_codes) if penalty_codes else "  (none defined)"
    )
    cap_block = "\n".join(f"  {code}" for code in cap_codes) if cap_codes else "  (none defined)"

    lane_note = ""
    if controller_card:
        lane_code = controller_card.get("selected_lane_code")
        if lane_code and lane_code != "none":
            lane_note = (
                f"\nActive variation lane: {lane_code}. Apply lane-specific penalty rules if any."
            )

    system = (
        "You are a legal scoring auditor applying penalty deductions and score caps to a "
        "rubric-scored model response.\n\n"
        f"Available penalty codes (P_):\n{penalty_block}\n\n"
        f"Available cap codes (CAP_):\n{cap_block}\n\n"
        "Instructions:\n"
        "1. Review the response and criterion scores.\n"
        "2. For each P_ code that applies, record the code, deduction in points (0–100 scale), "
        "and a short label.\n"
        "3. Compute: post_penalty_score = max(0, subtotal - sum(penalty_points)).\n"
        "4. If a CAP_ code is triggered, apply the cap ceiling. Set applied=true and record "
        "the cap_code. Otherwise cap_code is null and applied is false.\n"
        "5. final_score = capped value if cap applied, else post_penalty_score.\n"
        "6. If no penalties apply, return an empty penalties_applied list and the "
        "subtotal as both post_penalty_score and final_score.\n"
        + lane_note
        + "\n\nReturn ONLY valid JSON:\n"
        "{\n"
        '  "penalties_applied": [{"code": "P_...", "points": 5.0, "label": "..."}],\n'
        '  "cap_status": {"cap_code": null, "applied": false},\n'
        '  "post_penalty_score": 87.5,\n'
        '  "final_score": 87.5\n'
        "}"
    )

    scores_block = json.dumps(criteria_scores, indent=2)
    card_summary = {}
    if controller_card:
        for key in ("doctrine_pack", "selected_lane_code", "workflow_source_case_name"):
            if controller_card.get(key):
                card_summary[key] = controller_card[key]

    user = (
        f"Rubric subtotal (0–100 scale): {subtotal}\n\n"
        f"Per-criterion scores (0.0–1.0):\n{scores_block}\n\n"
        + (
            f"Controller card context:\n{json.dumps(card_summary, indent=2)}\n\n"
            if card_summary
            else ""
        )
        + f"Model response:\n{centroid_text}\n\n"
        "Apply penalties and caps now."
    )

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
