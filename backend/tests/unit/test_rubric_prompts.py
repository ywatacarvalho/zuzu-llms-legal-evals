"""Unit tests for app.services.rubric_prompts — pure, no mocking needed."""

from app.services.rubric_prompts import (
    _MAX_CASE_TEXT_CHARS,
    build_binary_eval_messages,
    build_decompose_messages,
    build_draft_comparison_messages,
    build_failure_mode_prediction_messages,
    build_filter_redundancy_messages,
    build_gold_answer_messages,
    build_gold_packet_mapping_messages,
    build_initial_proposal_messages,
    build_question_generation_messages,
    build_question_validation_messages,
    build_routing_messages,
    build_self_audit_messages,
    build_setup_system_prompt,
    build_source_extraction_messages,
    build_source_intake_screening_messages,
)

_CRITERION = {
    "id": "factual_accuracy",
    "name": "Factual Accuracy",
    "description": "Correctly identifies key facts.",
    "weight": 0.5,
}
_CENTROIDS = [f"Centroid response {i}" for i in range(8)]
_ACCEPTED = [
    {
        "id": "legal_reasoning",
        "name": "Legal Reasoning",
        "description": "Sound doctrine.",
        "weight": 0.5,
    }
]


def _is_valid_messages(msgs: list) -> bool:
    return (
        isinstance(msgs, list)
        and len(msgs) >= 2
        and all(isinstance(m, dict) and "role" in m and "content" in m for m in msgs)
        and msgs[0]["role"] == "system"
        and msgs[-1]["role"] == "user"
    )


class TestBuildInitialProposalMessages:
    def test_returns_valid_messages_structure(self):
        msgs = build_initial_proposal_messages("What is the standard of review?", _CENTROIDS)
        assert _is_valid_messages(msgs)

    def test_question_appears_in_user_message(self):
        question = "What is the applicable standard of review?"
        msgs = build_initial_proposal_messages(question, _CENTROIDS)
        assert question in msgs[-1]["content"]

    def test_all_centroids_appear_in_user_message(self):
        msgs = build_initial_proposal_messages("question?", _CENTROIDS)
        for centroid in _CENTROIDS:
            assert centroid in msgs[-1]["content"]

    def test_system_message_mentions_weight_requirement(self):
        msgs = build_initial_proposal_messages("question?", _CENTROIDS)
        assert "weight" in msgs[0]["content"].lower()

    def test_system_message_mentions_discriminative(self):
        msgs = build_initial_proposal_messages("question?", _CENTROIDS)
        content = msgs[0]["content"].lower()
        assert "discriminative" in content or "discriminat" in content


class TestBuildDecomposeMessages:
    def test_returns_valid_messages_structure(self):
        msgs = build_decompose_messages(_CRITERION, _CENTROIDS)
        assert _is_valid_messages(msgs)

    def test_criterion_id_appears_in_user_message(self):
        msgs = build_decompose_messages(_CRITERION, _CENTROIDS)
        assert _CRITERION["id"] in msgs[-1]["content"]

    def test_all_centroids_appear_in_user_message(self):
        msgs = build_decompose_messages(_CRITERION, _CENTROIDS)
        for centroid in _CENTROIDS:
            assert centroid in msgs[-1]["content"]


class TestBuildFilterRedundancyMessages:
    def test_returns_valid_messages_structure(self):
        msgs = build_filter_redundancy_messages(_CRITERION, _ACCEPTED)
        assert _is_valid_messages(msgs)

    def test_candidate_appears_in_user_message(self):
        msgs = build_filter_redundancy_messages(_CRITERION, _ACCEPTED)
        assert _CRITERION["id"] in msgs[-1]["content"]

    def test_accepted_criteria_appear_in_user_message(self):
        msgs = build_filter_redundancy_messages(_CRITERION, _ACCEPTED)
        assert _ACCEPTED[0]["id"] in msgs[-1]["content"]

    def test_system_message_mentions_redundant(self):
        msgs = build_filter_redundancy_messages(_CRITERION, _ACCEPTED)
        assert '"redundant"' in msgs[0]["content"]

    def test_empty_accepted_list_still_returns_valid_messages(self):
        msgs = build_filter_redundancy_messages(_CRITERION, [])
        assert _is_valid_messages(msgs)


class TestBuildBinaryEvalMessages:
    def test_returns_valid_messages_structure(self):
        msgs = build_binary_eval_messages(_CRITERION, "A response text.")
        assert _is_valid_messages(msgs)

    def test_criterion_appears_in_user_message(self):
        msgs = build_binary_eval_messages(_CRITERION, "A response text.")
        assert _CRITERION["id"] in msgs[-1]["content"]

    def test_response_text_appears_in_user_message(self):
        response = "The court applied a de novo standard."
        msgs = build_binary_eval_messages(_CRITERION, response)
        assert response in msgs[-1]["content"]

    def test_system_message_mentions_passes(self):
        msgs = build_binary_eval_messages(_CRITERION, "text")
        assert '"passes"' in msgs[0]["content"]

    def test_distinct_from_redundancy_prompt(self):
        binary_msgs = build_binary_eval_messages(_CRITERION, "text")
        redundancy_msgs = build_filter_redundancy_messages(_CRITERION, _ACCEPTED)
        assert binary_msgs[0]["content"] != redundancy_msgs[0]["content"]


_CASE_TEXT = "This is a sample case text about a contract dispute over oral promises."
_QUESTION = "Is the oral promise enforceable under the Statute of Frauds?"


class TestBuildSourceIntakeScreeningMessages:
    """T2.5.1 -- T2.5.4: source intake screening prompt tests."""

    def test_returns_valid_messages_structure(self):
        # T2.5.1
        msgs = build_source_intake_screening_messages(_CASE_TEXT, _QUESTION)
        assert _is_valid_messages(msgs)

    def test_system_message_contains_all_17_screening_items(self):
        # T2.5.2
        msgs = build_source_intake_screening_messages(_CASE_TEXT, _QUESTION)
        system = msgs[0]["content"]
        expected_keys = [
            "candidate_source",
            "source_type_authority_level",
            "target_doctrine_family_likely_pack",
            "clean_legal_issue",
            "black_letter_rule_extractable",
            "trigger_facts_identifiable",
            "holding_usable_for_benchmark",
            "limits_boundaries_identifiable",
            "procedural_noise_level",
            "jurisdiction_sensitivity_split_risk",
            "benchmark_answer_suitability",
            "reverse_engineering_suitability",
            "benchmark_posture",
            "failure_mode_yield",
            "jd_review_burden",
            "final_intake_rating",
            "recommendation",
        ]
        for key in expected_keys:
            assert key in system, f"Missing checklist key: {key!r}"

    def test_system_message_contains_stop_rule(self):
        # T2.5.3
        msgs = build_source_intake_screening_messages(_CASE_TEXT, _QUESTION)
        system = msgs[0]["content"].lower()
        assert "stop" in system and "stop_triggered" in msgs[0]["content"]

    def test_system_message_contains_rating_scale(self):
        # T2.5.4
        msgs = build_source_intake_screening_messages(_CASE_TEXT, _QUESTION)
        system = msgs[0]["content"]
        assert "Strong lead source" in system
        assert "Moderate" in system
        assert "Weak" in system
        assert "Not a strong gold-source candidate" in system

    def test_user_message_contains_case_text(self):
        msgs = build_source_intake_screening_messages(_CASE_TEXT, _QUESTION)
        assert _CASE_TEXT in msgs[-1]["content"]

    def test_user_message_contains_question(self):
        msgs = build_source_intake_screening_messages(_CASE_TEXT, _QUESTION)
        assert _QUESTION in msgs[-1]["content"]

    def test_case_text_truncated_at_12000_chars(self):
        long_text = "x" * 15000
        msgs = build_source_intake_screening_messages(long_text, _QUESTION)
        assert len(msgs[-1]["content"]) < 15000 + len(_QUESTION) + 100
        assert "\u2026" in msgs[-1]["content"]


class TestBuildSourceExtractionMessages:
    """T2.1 -- T2.6: source extraction prompt tests."""

    def test_returns_valid_messages_structure(self):
        # T2.1
        msgs = build_source_extraction_messages(_CASE_TEXT, _QUESTION)
        assert _is_valid_messages(msgs)

    def test_system_message_contains_all_15_headings(self):
        # T2.2
        msgs = build_source_extraction_messages(_CASE_TEXT, _QUESTION)
        system = msgs[0]["content"]
        expected_keys = [
            "selected_doctrine_pack",
            "candidate_source",
            "source_type_authority_level",
            "jurisdiction_forum",
            "procedural_posture",
            "clean_legal_issue",
            "black_letter_rule",
            "trigger_facts",
            "holding_or_best_supported_answer_path",
            "why_that_result_follows",
            "limits_boundaries",
            "what_source_does_not_decide",
            "jurisdiction_sensitivity_split_risk",
            "benchmark_use_confidence",
            "jd_review_needed",
        ]
        for key in expected_keys:
            assert key in system, f"Missing extraction key: {key!r}"

    def test_user_message_contains_case_text(self):
        # T2.3
        msgs = build_source_extraction_messages(_CASE_TEXT, _QUESTION)
        assert _CASE_TEXT in msgs[-1]["content"]

    def test_user_message_contains_question(self):
        # T2.4
        msgs = build_source_extraction_messages(_CASE_TEXT, _QUESTION)
        assert _QUESTION in msgs[-1]["content"]

    def test_case_text_truncated_at_12000_chars(self):
        # T2.5
        prefix = "a" * _MAX_CASE_TEXT_CHARS
        overflow = "OVERFLOW_SENTINEL_XYZ"
        long_text = prefix + overflow
        msgs = build_source_extraction_messages(long_text, _QUESTION)
        user_content = msgs[-1]["content"]
        assert "\u2026" in user_content
        assert prefix in user_content
        assert overflow not in user_content

    def test_system_message_contains_traceability_tags(self):
        # T2.6
        msgs = build_source_extraction_messages(_CASE_TEXT, _QUESTION)
        system = msgs[0]["content"]
        assert "Supported by source" in system
        assert "Inference from source" in system
        assert "Background generalization" in system


_SOURCE_EXTRACTION = {
    "selected_doctrine_pack": "pack_20",
    "candidate_source": "Smith v. Jones",
    "benchmark_use_confidence": "Strong",
}
_PACK_CONTENT = {
    "name": "Land Contracts",
    "must_separate_subissues": ["land transfer", "written memorandum"],
}
_FAILURE_BANK = {
    "pack_id": "pack_20",
    "label_families": {
        "SG": "Missing writing requirement analysis",
        "SC": "Omits part performance doctrine",
        "XD": "Wrong jurisdiction rule applied",
    },
}
_GOLD_PACKET_MAPPING = {
    "doctrine_family": "Land Contracts [Supported by source]",
    "controlling_trigger": "contract for transfer of land",
    "required_gate_order": "1. Covered; 2. Writing; 3. Exceptions",
}


class TestBuildRoutingMessages:
    """T3.1 -- T3.4: doctrine pack routing prompt tests."""

    def test_returns_valid_messages_structure(self):
        # T3.1
        msgs = build_routing_messages(_SOURCE_EXTRACTION, _QUESTION)
        assert _is_valid_messages(msgs)

    def test_system_message_contains_all_four_pack_descriptions(self):
        # T3.2
        msgs = build_routing_messages(_SOURCE_EXTRACTION, _QUESTION)
        system = msgs[0]["content"]
        for pack in ("pack_10", "pack_20", "pack_30", "pack_40"):
            assert pack in system, f"System message missing pack description: {pack!r}"

    def test_system_message_contains_priority_rules(self):
        # T3.3
        msgs = build_routing_messages(_SOURCE_EXTRACTION, _QUESTION)
        system = msgs[0]["content"]
        assert "Priority rules" in system

    def test_user_message_contains_serialized_source_extraction(self):
        # T3.4
        msgs = build_routing_messages(_SOURCE_EXTRACTION, _QUESTION)
        user = msgs[-1]["content"]
        assert "Smith v. Jones" in user
        assert _QUESTION in user


class TestBuildGoldPacketMappingMessages:
    """T4.1 -- T4.2b: gold packet mapping prompt tests."""

    def test_system_message_contains_13_mapping_headings(self):
        # T4.1
        msgs = build_gold_packet_mapping_messages(_SOURCE_EXTRACTION, _PACK_CONTENT, _QUESTION)
        system = msgs[0]["content"]
        headings = [
            "doctrine_family",
            "controlling_trigger",
            "required_gate_order",
            "what_makes_doctrine_apply",
            "what_does_not_satisfy_it",
            "independent_competing_barriers",
            "possible_substitutes_exceptions",
            "limits_on_substitutes_exceptions",
            "likely_jurisdiction_sensitive_points",
            "likely_model_mistakes",
            "candidate_fact_pattern_ingredients",
            "reverse_engineering_suitability",
            "benchmark_posture",
        ]
        for heading in headings:
            assert heading in system, f"System message missing mapping heading: {heading!r}"

    def test_system_message_includes_doctrine_pack_content(self):
        # T4.2
        msgs = build_gold_packet_mapping_messages(_SOURCE_EXTRACTION, _PACK_CONTENT, _QUESTION)
        system = msgs[0]["content"]
        assert "Land Contracts" in system
        assert "land transfer" in system

    def test_system_message_includes_traceability_tag_instruction(self):
        # T4.2b
        msgs = build_gold_packet_mapping_messages(_SOURCE_EXTRACTION, _PACK_CONTENT, _QUESTION)
        system = msgs[0]["content"]
        assert "Supported by source" in system
        assert "Inference from source" in system
        assert "Background generalization" in system


class TestBuildFailureModePredictionMessages:
    """T4.3 -- T4.4: failure mode prediction prompt tests."""

    def test_system_message_includes_failure_bank_vocabulary(self):
        # T4.3
        msgs = build_failure_mode_prediction_messages(
            _SOURCE_EXTRACTION, _GOLD_PACKET_MAPPING, _FAILURE_BANK
        )
        system = msgs[0]["content"]
        assert "SG" in system
        assert "SC" in system
        assert "XD" in system
        assert "pack_20" in system

    def test_user_message_contains_source_extraction(self):
        # T4.4
        msgs = build_failure_mode_prediction_messages(
            _SOURCE_EXTRACTION, _GOLD_PACKET_MAPPING, _FAILURE_BANK
        )
        user = msgs[-1]["content"]
        assert "Smith v. Jones" in user


_SETUP_EXTRACTION = {
    "clean_legal_issue": "Whether an oral promise requires writing",
    "black_letter_rule": "Oral promises fall under SoF",
    "holding_or_best_supported_answer_path": "Not enforceable without writing",
    "jurisdiction_forum": "Massachusetts",
}


class TestBuildSetupSystemPrompt:
    """T5.1 -- T5.5: setup system prompt tests (embedding quality guard)."""

    def test_does_not_contain_8_heading_output_shell(self):
        # T5.1 — embedding quality guard: no rigid structure imposed
        prompt = build_setup_system_prompt()
        for heading in (
            "## I. Issue",
            "## II. Rule",
            "## III. Application",
            "## IV. Conclusion",
        ):
            assert heading not in prompt, f"Prompt must not contain heading: {heading!r}"

    def test_does_not_contain_gate_by_gate_analysis_instruction(self):
        # T5.2 — structure reserved for gold answer only
        prompt = build_setup_system_prompt()
        assert "gate-by-gate" not in prompt.lower()
        assert "output shell" not in prompt.lower()

    def test_includes_source_extraction_context_when_provided(self):
        # T5.3
        prompt = build_setup_system_prompt(source_extraction=_SETUP_EXTRACTION)
        assert "oral promise" in prompt.lower()
        assert "Massachusetts" in prompt

    def test_includes_doctrine_pack_when_provided(self):
        # T5.4
        prompt = build_setup_system_prompt(doctrine_pack="pack_10")
        assert "pack_10" in prompt

    def test_falls_back_to_base_prompt_without_extraction(self):
        # T5.5
        prompt = build_setup_system_prompt()
        assert "expert legal analyst" in prompt.lower()


# ---------------------------------------------------------------------------
# Phase 6: Module skeleton constraint layer (T6.1 -- T6.4)
# ---------------------------------------------------------------------------


class TestBuildInitialProposalMessagesPhase6:
    """T6.1 -- T6.2: initial proposal messages contain module framework."""

    def test_system_contains_four_modules(self):
        # T6.1 — 4 scored modules (1-4) must be listed
        messages = build_initial_proposal_messages("q?", _CENTROIDS)
        system = next(m["content"] for m in messages if m["role"] == "system")
        for mod_id in [1, 2, 3, 4]:
            assert f"Module {mod_id}" in system, f"Module {mod_id} not found in system prompt"

    def test_system_contains_module_default_weights(self):
        # T6.2 — all four module weights must appear
        messages = build_initial_proposal_messages("q?", _CENTROIDS)
        system = next(m["content"] for m in messages if m["role"] == "system")
        for weight in ["28%", "40%", "19%", "13%"]:
            assert weight in system, f"Module weight {weight} not found in system prompt"

    def test_system_contains_module_id_in_json_example(self):
        # T6.2b — LLM is instructed to return module_id in each criterion
        messages = build_initial_proposal_messages("q?", _CENTROIDS)
        system = next(m["content"] for m in messages if m["role"] == "system")
        assert "module_id" in system

    def test_doctrine_pack_included_when_provided(self):
        messages = build_initial_proposal_messages("q?", _CENTROIDS, doctrine_pack="pack_10")
        system = next(m["content"] for m in messages if m["role"] == "system")
        assert "pack_10" in system

    def test_doctrine_pack_absent_when_not_provided(self):
        messages = build_initial_proposal_messages("q?", _CENTROIDS)
        system = next(m["content"] for m in messages if m["role"] == "system")
        # No stray pack mention in default prompt
        assert "pack_10" not in system


class TestBuildDecomposeMessagesPhase6:
    """T6.3 -- T6.4: decompose messages respect module boundary."""

    def test_system_contains_module_boundary_constraint_when_module_id_set(self):
        # T6.3
        criterion_with_module = {**_CRITERION, "module_id": 2}
        messages = build_decompose_messages(criterion_with_module, _CENTROIDS)
        system = next(m["content"] for m in messages if m["role"] == "system")
        assert "Module 2" in system
        assert "MODULE BOUNDARY" in system

    def test_system_contains_parent_module_description(self):
        # T6.4 — module description from MODULE_SKELETON must appear in the prompt
        criterion_with_module = {**_CRITERION, "module_id": 2}
        messages = build_decompose_messages(criterion_with_module, _CENTROIDS)
        system = next(m["content"] for m in messages if m["role"] == "system")
        # Module 2 description contains "Primary doctrine gates" / "core doctrinal analysis"
        assert "Primary doctrine gates" in system or "core doctrinal" in system.lower()

    def test_no_module_boundary_when_module_id_absent(self):
        messages = build_decompose_messages(_CRITERION, _CENTROIDS)
        system = next(m["content"] for m in messages if m["role"] == "system")
        assert "MODULE BOUNDARY" not in system


# ---------------------------------------------------------------------------
# Phase 7: Gold-answer prompt tests (T7.1 -- T7.5c)
# ---------------------------------------------------------------------------

_GOLD_DOCTRINE_PACK = {
    "name": "Oral Promise",
    "must_separate_subissues": [
        "Whether the promise is within the Statute of Frauds",
        "Whether a writing satisfies the requirement",
        "Whether an exception (part performance, estoppel) applies",
    ],
    "benchmark_headings": [
        "Jurisdiction assumption",
        "Bottom-line outcome",
        "Controlling doctrine",
        "Formation",
        "Statute of Frauds Gates",
        "Exceptions/Promissory Estoppel",
        "Defenses/Mistake",
        "Strongest counterargument",
    ],
}


class TestBuildGoldAnswerMessages:
    """T7.1 -- T7.5c: build_gold_answer_messages() prompt structure tests."""

    def test_system_contains_all_8_output_shell_headings(self):
        # T7.1 — all 8 OUTPUT_SHELL_HEADINGS must appear in the system message
        from app.services.frank_instructions import OUTPUT_SHELL_HEADINGS

        msgs = build_gold_answer_messages(
            source_extraction=_SOURCE_EXTRACTION,
            gold_packet_mapping=_GOLD_PACKET_MAPPING,
            doctrine_pack_content=_GOLD_DOCTRINE_PACK,
            question=_QUESTION,
        )
        system = msgs[0]["content"]
        for heading in OUTPUT_SHELL_HEADINGS:
            assert heading in system, f"Output shell heading missing: {heading!r}"

    def test_system_contains_provenance_banned_words_list(self):
        # T7.2 — PROVENANCE_BANNED_WORDS must be referenced (at least core terms)
        from app.services.frank_instructions import PROVENANCE_BANNED_WORDS

        msgs = build_gold_answer_messages(
            source_extraction=_SOURCE_EXTRACTION,
            gold_packet_mapping=_GOLD_PACKET_MAPPING,
            doctrine_pack_content=_GOLD_DOCTRINE_PACK,
            question=_QUESTION,
        )
        system = msgs[0]["content"]
        for word in ("source", "case", "court"):
            assert word in system, f"Banned word not referenced in provenance rules: {word!r}"
        assert len(PROVENANCE_BANNED_WORDS) >= 3

    def test_system_contains_doctrine_pack_gate_order(self):
        # T7.3 — gate order / separation rules from doctrine pack must appear
        msgs = build_gold_answer_messages(
            source_extraction=_SOURCE_EXTRACTION,
            gold_packet_mapping=_GOLD_PACKET_MAPPING,
            doctrine_pack_content=_GOLD_DOCTRINE_PACK,
            question=_QUESTION,
        )
        system = msgs[0]["content"]
        for rule in _GOLD_DOCTRINE_PACK["must_separate_subissues"]:
            assert rule in system, f"Gate order rule not in system prompt: {rule!r}"

    def test_worked_examples_included_when_provided(self):
        # T7.4 — examples should appear in messages when passed
        example_text = "WORKED_EXAMPLE_UNIQUE_SENTINEL_XYZ"
        msgs = build_gold_answer_messages(
            source_extraction=_SOURCE_EXTRACTION,
            gold_packet_mapping=_GOLD_PACKET_MAPPING,
            doctrine_pack_content=_GOLD_DOCTRINE_PACK,
            question=_QUESTION,
            worked_examples=[example_text],
        )
        full_text = " ".join(m["content"] for m in msgs)
        assert example_text in full_text

    def test_worked_examples_absent_when_none(self):
        # T7.5 — no reference to structural examples when worked_examples is None
        msgs = build_gold_answer_messages(
            source_extraction=_SOURCE_EXTRACTION,
            gold_packet_mapping=_GOLD_PACKET_MAPPING,
            doctrine_pack_content=_GOLD_DOCTRINE_PACK,
            question=_QUESTION,
            worked_examples=None,
        )
        full_text = " ".join(m["content"] for m in msgs)
        assert "STRUCTURAL REFERENCES" not in full_text

    def test_clean_benchmarks_included_when_provided(self):
        # T7.5b — benchmarks appear in messages when passed
        bench_text = "CLEAN_BENCHMARK_UNIQUE_SENTINEL_ABC"
        msgs = build_gold_answer_messages(
            source_extraction=_SOURCE_EXTRACTION,
            gold_packet_mapping=_GOLD_PACKET_MAPPING,
            doctrine_pack_content=_GOLD_DOCTRINE_PACK,
            question=_QUESTION,
            clean_benchmarks=[bench_text],
        )
        full_text = " ".join(m["content"] for m in msgs)
        assert bench_text in full_text

    def test_pack_suretyship_get_worked_examples_returns_at_least_one_item(self):
        from app.services.frank_instructions import get_worked_examples

        examples = get_worked_examples("pack_suretyship")
        assert isinstance(examples, list)
        assert len(examples) >= 1


# ---------------------------------------------------------------------------
# Phase 8: Self-audit prompt tests (T8.1 -- T8.5)
# ---------------------------------------------------------------------------

_SELF_AUDIT_SOURCE = {
    "clean_legal_issue": "Whether an oral promise requires writing",
    "black_letter_rule": "Oral promises fall under SoF",
    "holding_or_best_supported_answer_path": "Not enforceable without writing",
    "jurisdiction_forum": "Massachusetts",
}
_SELF_AUDIT_ROUTING = {
    "selected_pack": "pack_10",
    "confidence": "high",
    "reasoning": "Issue fits oral promise doctrine",
}
_GOLD_ANSWER_TEXT = (
    "BOTTOM LINE: The oral promise is likely unenforceable under the Statute of Frauds.\n"
    "RULE: Oral promises for land transfers must be in writing...\n"
)


class TestBuildSelfAuditMessages:
    """T8.1 -- T8.5: build_self_audit_messages() prompt structure tests."""

    def test_returns_valid_messages_structure(self):
        # T8.1 - returns list of role/content dicts with system + user
        msgs = build_self_audit_messages(
            gold_answer=_GOLD_ANSWER_TEXT,
            source_extraction=_SELF_AUDIT_SOURCE,
            doctrine_pack="pack_10",
            routing_metadata=_SELF_AUDIT_ROUTING,
        )
        assert _is_valid_messages(msgs)

    def test_system_contains_all_four_fast_triage_items(self):
        # T8.2 - all 4 fast-triage item names must appear
        from app.services.frank_instructions import SELF_AUDIT_FAST_TRIAGE

        msgs = build_self_audit_messages(
            gold_answer=_GOLD_ANSWER_TEXT,
            source_extraction=_SELF_AUDIT_SOURCE,
            doctrine_pack="pack_10",
            routing_metadata=_SELF_AUDIT_ROUTING,
        )
        system = msgs[0]["content"]
        for item in SELF_AUDIT_FAST_TRIAGE:
            assert item["name"] in system, f"Fast-triage item missing: {item['name']!r}"

    def test_system_contains_red_flags(self):
        # T8.3 - at least the first red flag must appear
        from app.services.frank_instructions import SELF_AUDIT_RED_FLAGS

        msgs = build_self_audit_messages(
            gold_answer=_GOLD_ANSWER_TEXT,
            source_extraction=_SELF_AUDIT_SOURCE,
            doctrine_pack="pack_10",
            routing_metadata=_SELF_AUDIT_ROUTING,
        )
        system = msgs[0]["content"]
        assert SELF_AUDIT_RED_FLAGS[0] in system

    def test_system_contains_all_four_classifications(self):
        # T8.4 - all classification labels must appear in system prompt
        from app.services.frank_instructions import SELF_AUDIT_CLASSIFICATIONS

        msgs = build_self_audit_messages(
            gold_answer=_GOLD_ANSWER_TEXT,
            source_extraction=_SELF_AUDIT_SOURCE,
            doctrine_pack="pack_10",
            routing_metadata=_SELF_AUDIT_ROUTING,
        )
        system = msgs[0]["content"]
        for classification in SELF_AUDIT_CLASSIFICATIONS:
            assert classification in system, f"Classification label missing: {classification!r}"

    def test_user_message_contains_gold_answer(self):
        # T8.5 - user message must contain the gold answer text
        msgs = build_self_audit_messages(
            gold_answer=_GOLD_ANSWER_TEXT,
            source_extraction=_SELF_AUDIT_SOURCE,
            doctrine_pack="pack_10",
            routing_metadata=_SELF_AUDIT_ROUTING,
        )
        user = msgs[-1]["content"]
        assert "BOTTOM LINE" in user
        assert "Statute of Frauds" in user

    def test_system_contains_doctrine_pack_name(self):
        # T8.5b - doctrine pack ID must appear in system message
        msgs = build_self_audit_messages(
            gold_answer=_GOLD_ANSWER_TEXT,
            source_extraction=_SELF_AUDIT_SOURCE,
            doctrine_pack="pack_10",
            routing_metadata=_SELF_AUDIT_ROUTING,
        )
        system = msgs[0]["content"]
        assert "pack_10" in system

    def test_system_includes_routing_confidence(self):
        # T8.5c - routing confidence from metadata must appear in system
        msgs = build_self_audit_messages(
            gold_answer=_GOLD_ANSWER_TEXT,
            source_extraction=_SELF_AUDIT_SOURCE,
            doctrine_pack="pack_10",
            routing_metadata=_SELF_AUDIT_ROUTING,
        )
        system = msgs[0]["content"]
        assert "high" in system


# ---------------------------------------------------------------------------
# Phase 10: build_question_validation_messages + build_question_generation_messages
# ---------------------------------------------------------------------------

_Q10_SOURCE = {
    "clean_legal_issue": "Whether an oral contract for the sale of land is enforceable.",
    "jurisdiction_forum": "New York",
    "holding_or_best_supported_answer_path": "The oral contract is unenforceable under the SOF.",
    "black_letter_rule": "Contracts for the sale of land must be in writing.",
}

_Q10_GOLD_PACKET = {
    "governing_rule": "SOF land provision",
    "trigger_facts": ["oral promise to sell land"],
    "gate_1": {"heading": "Writing requirement", "analysis": "oral contract"},
}

_Q10_PACK_CONTENT = {
    "name": "Land contracts",
    "scope": "Contracts for the transfer of land or a land interest.",
}


class TestBuildQuestionValidationMessages:
    """T10.1 -- T10.3: build_question_validation_messages() prompt structure tests."""

    def test_system_contains_seven_design_goals(self):
        # T10.1 - system must embed all 7 design goals
        from app.services.frank_instructions import QUESTION_CHECKLIST

        msgs = build_question_validation_messages("Is the agreement enforceable?")
        system = msgs[0]["content"]
        for goal in QUESTION_CHECKLIST["design_goals"]:
            assert goal[:30] in system, f"Design goal missing in system: {goal[:30]!r}"

    def test_system_contains_seven_body_checks(self):
        # T10.2 - system must embed all 7 body checks
        from app.services.frank_instructions import QUESTION_CHECKLIST

        msgs = build_question_validation_messages("Is the agreement enforceable?")
        system = msgs[0]["content"]
        for check in QUESTION_CHECKLIST["body_checks"]:
            assert check[:30] in system, f"Body check missing in system: {check[:30]!r}"

    def test_system_contains_red_flags(self):
        # T10.3 - system must mention red-flag categories
        msgs = build_question_validation_messages("Is the agreement enforceable?")
        system = msgs[0]["content"]
        assert "RED FLAGS" in system
        assert "doctrine" in system.lower() or "names a specific" in system

    def test_user_message_contains_question(self):
        question = "Is the oral promise enforceable? Analyze."
        msgs = build_question_validation_messages(question)
        user = msgs[-1]["content"]
        assert question in user

    def test_user_message_contains_source_extraction(self):
        msgs = build_question_validation_messages(
            "Is the agreement enforceable?", source_extraction=_Q10_SOURCE
        )
        user = msgs[-1]["content"]
        assert "clean_legal_issue" in user or "oral contract" in user.lower()

    def test_works_without_source_extraction(self):
        msgs = build_question_validation_messages("Is the agreement enforceable?")
        assert _is_valid_messages(msgs)

    def test_includes_doctrine_pack_hint_when_provided(self):
        msgs = build_question_validation_messages(
            "Is the agreement enforceable?", doctrine_pack="pack_20"
        )
        system = msgs[0]["content"]
        assert "pack_20" in system


class TestBuildQuestionGenerationMessages:
    """T10.4 -- T10.6: build_question_generation_messages() prompt structure tests."""

    def test_system_contains_neutral_call_rules(self):
        # T10.4 - system must explain neutral-call requirement
        msgs = build_question_generation_messages(_Q10_SOURCE, _Q10_GOLD_PACKET, _Q10_PACK_CONTENT)
        system = msgs[0]["content"]
        assert "neutral" in system.lower()
        assert "call" in system.lower()

    def test_system_contains_no_leakage_rules(self):
        # T10.5 - system must explicitly prohibit answer leakage
        msgs = build_question_generation_messages(_Q10_SOURCE, _Q10_GOLD_PACKET, _Q10_PACK_CONTENT)
        system = msgs[0]["content"]
        assert "leakage" in system.lower() or "not name" in system.lower() or "NO-LEAKAGE" in system

    def test_user_message_contains_source_extraction(self):
        # T10.6 - user message must include source extraction data
        msgs = build_question_generation_messages(_Q10_SOURCE, _Q10_GOLD_PACKET, _Q10_PACK_CONTENT)
        user = msgs[-1]["content"]
        assert "clean_legal_issue" in user or "oral contract" in user.lower()

    def test_user_message_contains_gold_packet_mapping(self):
        msgs = build_question_generation_messages(_Q10_SOURCE, _Q10_GOLD_PACKET, _Q10_PACK_CONTENT)
        user = msgs[-1]["content"]
        assert "governing_rule" in user or "SOF land" in user

    def test_pack_name_appears_in_system(self):
        msgs = build_question_generation_messages(_Q10_SOURCE, _Q10_GOLD_PACKET, _Q10_PACK_CONTENT)
        system = msgs[0]["content"]
        assert "Land contracts" in system

    def test_valid_messages_structure(self):
        msgs = build_question_generation_messages(_Q10_SOURCE, _Q10_GOLD_PACKET, _Q10_PACK_CONTENT)
        assert _is_valid_messages(msgs)


# ---------------------------------------------------------------------------
# Phase 12: build_draft_comparison_messages
# ---------------------------------------------------------------------------

_PACK_CONTENT_12 = {"name": "Land contracts", "must_separate_subissues": ["SOF writing"]}
_SOURCE_EXTRACTION_12 = {
    "clean_legal_issue": "SOF land writing requirement",
    "jurisdiction_forum": "CA",
}


class TestBuildDraftComparisonMessages:
    """T12.1 -- T12.3: build_draft_comparison_messages() prompt structure tests."""

    def test_system_contains_eight_mode_c_headings(self):
        """T12.1 -- system message contains all 8 Mode C comparison headings."""
        from app.services.frank_instructions import MODE_C_COMPARISON_HEADINGS

        msgs = build_draft_comparison_messages(
            "Draft text.", _SOURCE_EXTRACTION_12, _PACK_CONTENT_12
        )
        system = msgs[0]["content"]
        for heading in MODE_C_COMPARISON_HEADINGS:
            assert heading in system, f"Missing heading: {heading}"

    def test_system_contains_mode_c_rules(self):
        """T12.2 -- system message contains Mode C rules."""
        msgs = build_draft_comparison_messages(
            "Draft text.", _SOURCE_EXTRACTION_12, _PACK_CONTENT_12
        )
        system = msgs[0]["content"]
        assert "authority" in system.lower() or "source" in system.lower()
        assert "unsupported certainty" in system.lower()

    def test_user_message_contains_draft_and_extraction(self):
        """T12.3 -- user message contains draft_text and source extraction."""
        draft = "The oral promise is unenforceable under SOF."
        msgs = build_draft_comparison_messages(draft, _SOURCE_EXTRACTION_12, _PACK_CONTENT_12)
        user = msgs[1]["content"]
        assert draft in user
        assert "SOF land writing requirement" in user

    def test_valid_messages_structure(self):
        msgs = build_draft_comparison_messages(
            "Draft text.", _SOURCE_EXTRACTION_12, _PACK_CONTENT_12
        )
        assert _is_valid_messages(msgs)

    def test_pack_name_in_system(self):
        msgs = build_draft_comparison_messages("Draft.", _SOURCE_EXTRACTION_12, _PACK_CONTENT_12)
        assert "Land contracts" in msgs[0]["content"]
