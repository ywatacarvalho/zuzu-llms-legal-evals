"""Unit tests for app.services.frank_instructions (updated for B-series 6-pack taxonomy)."""

import pytest

from app.services.frank_instructions import (
    B_SERIES_ROUTING_GATES,
    CAP_CODES,
    CORE_PROMPT_BLOCK,
    JUDGE_MODELS,
    MODE_C_COMPARISON_HEADINGS,
    MODULE_0_METADATA_TAGS,
    MODULE_SKELETON,
    OUTPUT_SHELL_HEADINGS,
    PENALTY_CODES,
    PROVENANCE_BANNED_WORDS,
    QUESTION_CHECKLIST,
    ROUTING_MATRIX,
    SELF_AUDIT_RELEASE_CHECK,
    SOURCE_INTAKE_CHECKLIST,
    TRACEABILITY_TAGS,
    VARIATION_LANE_CODES,
    get_clean_benchmarks,
    get_confusion_set,
    get_doctrine_pack,
    get_failure_bank,
    get_worked_examples,
)

B_SERIES_PACK_IDS = (
    "pack_marriage",
    "pack_suretyship",
    "pack_one_year",
    "pack_land",
    "pack_ucc_2201",
    "pack_executor",
)


class TestModuleSkeleton:
    def test_has_5_modules(self):
        assert len(MODULE_SKELETON["modules"]) == 5

    def test_weights_sum_to_100(self):
        total = sum(m["weight"] for m in MODULE_SKELETON["modules"].values())
        assert total == 100

    def test_modules_1_to_4_have_non_empty_criteria_ids(self):
        for mod_id in range(1, 5):
            criteria_ids = MODULE_SKELETON["modules"][mod_id]["criteria_ids"]
            assert len(criteria_ids) > 0, f"Module {mod_id} has empty criteria_ids"

    def test_module_0_has_zero_weight(self):
        assert MODULE_SKELETON["modules"][0]["weight"] == 0

    def test_scoring_anchors_cover_0_to_4(self):
        anchors = MODULE_SKELETON["scoring_anchors"]
        for score in range(5):
            assert score in anchors


class TestModule0MetadataTags:
    def test_has_exactly_5_items(self):
        assert len(MODULE_0_METADATA_TAGS) == 5

    def test_contains_expected_items(self):
        tags_lower = [t.lower() for t in MODULE_0_METADATA_TAGS]
        assert any("outcome" in t for t in tags_lower)
        assert any("reasoning" in t for t in tags_lower)
        assert any("jurisdiction" in t for t in tags_lower)
        assert any("controlling" in t or "doctrine" in t for t in tags_lower)


class TestRoutingMatrix:
    def test_has_6_packs(self):
        assert len(ROUTING_MATRIX["packs"]) == 6

    def test_packs_have_required_keys(self):
        for pack_id, pack in ROUTING_MATRIX["packs"].items():
            assert "name" in pack, f"{pack_id} missing name"
            assert "categories" in pack, f"{pack_id} missing categories"
            assert "source_file" in pack, f"{pack_id} missing source_file"

    def test_routing_matrix_has_core_routing_rule(self):
        assert "core_routing_rule" in ROUTING_MATRIX
        assert len(ROUTING_MATRIX["core_routing_rule"]) > 0

    def test_all_6_pack_ids_present(self):
        for pid in B_SERIES_PACK_IDS:
            assert pid in ROUTING_MATRIX["packs"]

    def test_routing_status_values_present(self):
        assert "routing_status_values" in ROUTING_MATRIX
        assert len(ROUTING_MATRIX["routing_status_values"]) >= 3


class TestOutputShellHeadings:
    def test_has_exactly_8_items(self):
        assert len(OUTPUT_SHELL_HEADINGS) == 8

    def test_first_heading_is_jurisdiction(self):
        assert "Jurisdiction" in OUTPUT_SHELL_HEADINGS[0]

    def test_last_heading_is_counterargument(self):
        assert "counterargument" in OUTPUT_SHELL_HEADINGS[-1].lower()


class TestGetDoctrinePack:
    def test_returns_dict_with_required_keys_for_each_pack(self):
        for pid in B_SERIES_PACK_IDS:
            pack = get_doctrine_pack(pid)
            assert "id" in pack
            assert "name" in pack
            assert "categories" in pack
            assert "must_separate_subissues" in pack

    def test_raises_value_error_on_invalid_pack_id(self):
        with pytest.raises(ValueError, match="Unknown pack_id"):
            get_doctrine_pack("invalid_pack")

    def test_raises_on_old_pack_ids(self):
        for old_id in ("pack_10", "pack_20", "pack_30", "pack_40"):
            with pytest.raises(ValueError):
                get_doctrine_pack(old_id)

    def test_includes_raw_text_key(self):
        pack = get_doctrine_pack("pack_marriage")
        assert "raw_text" in pack

    def test_pack_ids_match_their_id_field(self):
        for pid in B_SERIES_PACK_IDS:
            pack = get_doctrine_pack(pid)
            assert pack["id"] == pid


class TestGetFailureBank:
    def test_returns_non_empty_dict_for_each_pack(self):
        for pid in B_SERIES_PACK_IDS:
            bank = get_failure_bank(pid)
            assert isinstance(bank, dict)
            assert len(bank) > 0

    def test_contains_label_families(self):
        bank = get_failure_bank("pack_marriage")
        assert "label_families" in bank

    def test_raises_value_error_on_invalid_pack_id(self):
        with pytest.raises(ValueError, match="Unknown pack_id"):
            get_failure_bank("bad_pack")

    def test_all_packs_have_label_families(self):
        for pid in B_SERIES_PACK_IDS:
            bank = get_failure_bank(pid)
            assert "label_families" in bank, f"{pid} missing label_families"
            assert len(bank["label_families"]) > 0


class TestQuestionChecklist:
    def test_has_design_goals_body_checks_release_checks(self):
        assert "design_goals" in QUESTION_CHECKLIST
        assert "body_checks" in QUESTION_CHECKLIST
        assert "release_checks" in QUESTION_CHECKLIST

    def test_design_goals_has_7_items(self):
        assert len(QUESTION_CHECKLIST["design_goals"]) == 7

    def test_release_checks_has_at_least_10_items(self):
        assert len(QUESTION_CHECKLIST["release_checks"]) >= 10


class TestSelfAuditReleaseCheck:
    def test_has_exactly_12_items(self):
        assert len(SELF_AUDIT_RELEASE_CHECK) == 12


class TestProvenanceBannedWords:
    def test_contains_core_words(self):
        for word in ("source", "case", "opinion", "court", "holding"):
            assert word in PROVENANCE_BANNED_WORDS


class TestCorePromptBlock:
    def test_is_non_empty_string(self):
        assert isinstance(CORE_PROMPT_BLOCK, str)
        assert len(CORE_PROMPT_BLOCK) > 0

    def test_contains_output_shell_headings(self):
        for heading in OUTPUT_SHELL_HEADINGS:
            assert heading in CORE_PROMPT_BLOCK, f"Missing heading in CORE_PROMPT_BLOCK: {heading}"


class TestGetWorkedExamples:
    def test_returns_list_for_each_pack(self):
        for pid in B_SERIES_PACK_IDS:
            examples = get_worked_examples(pid)
            assert isinstance(examples, list)
            assert len(examples) >= 1, f"{pid} returned empty worked examples"

    def test_raises_on_invalid_pack(self):
        with pytest.raises(ValueError):
            get_worked_examples("unknown")

    def test_raises_on_old_pack_ids(self):
        with pytest.raises(ValueError):
            get_worked_examples("pack_10")


class TestGetCleanBenchmarks:
    def test_returns_list_for_each_pack(self):
        for pid in B_SERIES_PACK_IDS:
            benchmarks = get_clean_benchmarks(pid)
            assert isinstance(benchmarks, list)
            assert len(benchmarks) >= 1, f"{pid} returned empty clean benchmarks"

    def test_raises_on_invalid_pack(self):
        with pytest.raises(ValueError):
            get_clean_benchmarks("unknown")

    def test_raises_on_old_pack_ids(self):
        with pytest.raises(ValueError):
            get_clean_benchmarks("pack_30")


class TestSourceIntakeChecklist:
    def test_has_exactly_17_output_headings(self):
        assert len(SOURCE_INTAKE_CHECKLIST["output_headings"]) == 17

    def test_contains_final_intake_rating_and_recommendation(self):
        headings_text = " ".join(SOURCE_INTAKE_CHECKLIST["output_headings"])
        assert "Final intake rating" in headings_text
        assert "Recommendation" in headings_text


class TestTraceabilityTags:
    def test_has_exactly_3_items(self):
        assert len(TRACEABILITY_TAGS) == 3

    def test_contains_expected_tags(self):
        assert "Supported by source" in TRACEABILITY_TAGS
        assert "Inference from source" in TRACEABILITY_TAGS
        assert "Background generalization" in TRACEABILITY_TAGS


class TestModeCComparisonHeadings:
    def test_has_exactly_8_items(self):
        assert len(MODE_C_COMPARISON_HEADINGS) == 8


class TestVariationLaneCodes:
    def test_has_6_lane_codes(self):
        assert len(VARIATION_LANE_CODES) == 6

    def test_contains_a_series_and_b_series(self):
        for code in ("A1", "A2", "A3", "A4", "B1", "B2"):
            assert code in VARIATION_LANE_CODES, f"Missing lane code: {code}"

    def test_each_code_has_label_and_description(self):
        for code, meta in VARIATION_LANE_CODES.items():
            assert "label" in meta, f"{code} missing label"
            assert "description" in meta, f"{code} missing description"
            assert len(meta["label"]) > 0
            assert len(meta["description"]) > 0

    def test_b_series_codes_are_ambiguity_or_omission(self):
        b1_desc = VARIATION_LANE_CODES["B1"]["description"].lower()
        b2_desc = VARIATION_LANE_CODES["B2"]["description"].lower()
        assert any(w in b1_desc for w in ("omit", "blur", "remov", "ambig"))
        assert any(w in b2_desc for w in ("general", "uncertain", "bounded"))


class TestBSeriesRoutingGates:
    def test_has_3_gates(self):
        assert len(B_SERIES_ROUTING_GATES) == 3

    def test_contains_g1_g2_g3(self):
        for gate in ("G1", "G2", "G3"):
            assert gate in B_SERIES_ROUTING_GATES

    def test_each_gate_has_label_and_description(self):
        for gate, meta in B_SERIES_ROUTING_GATES.items():
            assert "label" in meta, f"{gate} missing label"
            assert "description" in meta, f"{gate} missing description"


class TestPenaltyCodes:
    def test_has_exactly_11_codes(self):
        assert len(PENALTY_CODES) == 11

    def test_all_codes_start_with_p_prefix(self):
        for code in PENALTY_CODES:
            assert code.startswith("P_"), f"Penalty code missing P_ prefix: {code}"

    def test_contains_hallucinated_case_citation(self):
        assert "P_HallucinatedCaseCitation" in PENALTY_CODES

    def test_contains_controlling_doctrine_omitted(self):
        assert "P_ControllingDoctrineOmitted" in PENALTY_CODES


class TestCapCodes:
    def test_has_exactly_5_codes(self):
        assert len(CAP_CODES) == 5

    def test_all_codes_start_with_cap_prefix(self):
        for code in CAP_CODES:
            assert code.startswith("CAP_"), f"Cap code missing CAP_ prefix: {code}"

    def test_contains_controlling_doctrine_cap(self):
        assert any("ControllingDoctrineOmitted" in c for c in CAP_CODES)


class TestJudgeModels:
    def test_has_exactly_4_models(self):
        assert len(JUDGE_MODELS) == 4

    def test_contains_deepseek_v3(self):
        assert any("DeepSeek-V3" in m for m in JUDGE_MODELS)

    def test_contains_deepseek_r1(self):
        assert any("DeepSeek-R1" in m for m in JUDGE_MODELS)

    def test_no_overlap_with_comparison_pool_format(self):
        # Comparison pool models are the 14 non-internal models.
        # All judge models must be internal (DeepSeek or Qwen or Llama 70B family).
        internal_providers = ("deepseek-ai", "Qwen", "meta-llama")
        for m in JUDGE_MODELS:
            assert any(m.startswith(p) for p in internal_providers), (
                f"Unexpected judge model provider: {m}"
            )

    def test_all_model_ids_contain_slash(self):
        for m in JUDGE_MODELS:
            assert "/" in m, f"Model ID missing provider/name format: {m}"


class TestGetConfusionSet:
    def test_returns_dict_with_required_keys_for_known_pair(self):
        result = get_confusion_set("pack_marriage", "pack_land")
        assert "pack_a" in result
        assert "pack_b" in result
        assert "source_file" in result
        assert "raw_text" in result

    def test_pair_order_does_not_matter(self):
        r1 = get_confusion_set("pack_marriage", "pack_land")
        r2 = get_confusion_set("pack_land", "pack_marriage")
        assert r1["source_file"] == r2["source_file"]

    def test_raises_on_invalid_pack_id(self):
        with pytest.raises(ValueError, match="Unknown pack_id"):
            get_confusion_set("pack_marriage", "invalid_pack")

    def test_raises_on_unregistered_pair(self):
        with pytest.raises(ValueError):
            get_confusion_set("pack_marriage", "pack_executor")

    def test_executor_suretyship_pair_exists(self):
        result = get_confusion_set("pack_executor", "pack_suretyship")
        assert result["source_file"] != ""

    def test_ucc_one_year_pair_exists(self):
        result = get_confusion_set("pack_ucc_2201", "pack_one_year")
        assert result["source_file"] != ""
