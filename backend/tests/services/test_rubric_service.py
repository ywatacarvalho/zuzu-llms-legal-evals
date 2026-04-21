"""Unit tests for app.services.rubric_service."""

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.services import rubric_service
from app.services.rubric_service import (
    _validate_criteria,
    build_rubric,
    build_rubric_phase_b,
    cluster_to_centroids,
    compare_draft_to_source,
    generate_question,
    generate_setup_responses,
    propose_initial_rubric,
    run_mode_a,
    run_mode_e,
    run_refinement_loop,
    validate_question,
)

_VALID_CRITERIA = [
    {"id": "accuracy", "name": "Accuracy", "description": "Factual correctness.", "weight": 0.6},
    {"id": "reasoning", "name": "Reasoning", "description": "Legal reasoning.", "weight": 0.4},
]

_EIGHT_CENTROIDS = [f"Centroid response {i}" for i in range(8)]


# ---------------------------------------------------------------------------
# _validate_criteria (unchanged utility)
# ---------------------------------------------------------------------------


class TestValidateCriteria:
    def test_passes_on_valid_criteria(self):
        _validate_criteria(_VALID_CRITERIA)

    def test_raises_on_missing_key(self):
        bad = [{"id": "x", "name": "X", "weight": 0.5}]
        with pytest.raises(ValueError, match="missing keys"):
            _validate_criteria(bad)

    def test_raises_on_non_positive_weight(self):
        bad = [{"id": "x", "name": "X", "description": "d", "weight": 0.0}]
        with pytest.raises(ValueError, match="Invalid weight"):
            _validate_criteria(bad)

    def test_raises_when_weights_dont_sum_to_one(self):
        bad = [
            {"id": "a", "name": "A", "description": "d", "weight": 0.3},
            {"id": "b", "name": "B", "description": "d", "weight": 0.3},
        ]
        with pytest.raises(ValueError, match="sum to"):
            _validate_criteria(bad)

    def test_passes_within_floating_point_tolerance(self):
        criteria = [
            {"id": "a", "name": "A", "description": "d", "weight": 0.1},
            {"id": "b", "name": "B", "description": "d", "weight": 0.2},
            {"id": "c", "name": "C", "description": "d", "weight": 0.7},
        ]
        _validate_criteria(criteria)


# ---------------------------------------------------------------------------
# _compute_wu_weights
# ---------------------------------------------------------------------------


class TestComputeWuWeights:
    @pytest.mark.asyncio
    async def test_weights_sum_to_one(self):
        with patch.object(
            rubric_service, "_binary_eval_centroid", new_callable=AsyncMock, return_value=True
        ):
            result = await rubric_service._compute_wu_weights(_VALID_CRITERIA, _EIGHT_CENTROIDS)
        total = sum(c["weight"] for c in result)
        assert abs(total - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self):
        result = await rubric_service._compute_wu_weights([], _EIGHT_CENTROIDS)
        assert result == []

    @pytest.mark.asyncio
    async def test_single_criterion_gets_weight_one(self):
        single = [_VALID_CRITERIA[0]]
        result = await rubric_service._compute_wu_weights(single, _EIGHT_CENTROIDS)
        assert result[0]["weight"] == 1.0

    @pytest.mark.asyncio
    async def test_preserves_criterion_fields(self):
        with patch.object(
            rubric_service, "_binary_eval_centroid", new_callable=AsyncMock, return_value=False
        ):
            result = await rubric_service._compute_wu_weights(_VALID_CRITERIA, _EIGHT_CENTROIDS)
        ids = {c["id"] for c in result}
        assert ids == {"accuracy", "reasoning"}


# ---------------------------------------------------------------------------
# generate_setup_responses
# ---------------------------------------------------------------------------


class TestGenerateSetupResponses:
    @pytest.mark.asyncio
    async def test_calls_chat_completion_160_times(self):
        call_count = 0

        async def _mock_chat(**kwargs):
            nonlocal call_count
            call_count += 1
            return f"response {call_count}"

        with patch("app.services.rubric_service.chat_completion", side_effect=_mock_chat):
            results = await generate_setup_responses("What is the standard of review?")

        n_expected = (
            len(__import__("app.services.rubric_service", fromlist=["SETUP_MODELS"]).SETUP_MODELS)
            * __import__(
                "app.services.rubric_service", fromlist=["_SETUP_RESPONSES_PER_MODEL"]
            )._SETUP_RESPONSES_PER_MODEL
        )  # noqa: E501
        assert call_count == n_expected
        assert len(results) == n_expected
        assert all(isinstance(r, dict) and "model" in r and "text" in r for r in results)

    @pytest.mark.asyncio
    async def test_skips_none_responses(self):
        call_count = 0

        async def _mock_chat(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 10 == 0:
                raise Exception("API error")
            return f"response {call_count}"

        with patch("app.services.rubric_service.chat_completion", side_effect=_mock_chat):
            results = await generate_setup_responses("question?")

        n_total = (
            len(__import__("app.services.rubric_service", fromlist=["SETUP_MODELS"]).SETUP_MODELS)
            * __import__(
                "app.services.rubric_service", fromlist=["_SETUP_RESPONSES_PER_MODEL"]
            )._SETUP_RESPONSES_PER_MODEL
        )  # noqa: E501
        assert len(results) < n_total
        assert all(isinstance(r, dict) and r.get("text") is not None for r in results)


# ---------------------------------------------------------------------------
# cluster_to_centroids
# ---------------------------------------------------------------------------


def _fake_cluster_data(texts, k=None):
    n = min(k or 8, len(texts))
    clusters_map = {i: [i] for i in range(n)}
    centroid_indices = {i: i for i in range(n)}
    return {"k": n, "clusters_map": clusters_map, "centroid_indices": centroid_indices}


class TestClusterToCentroids:
    @pytest.mark.asyncio
    async def test_returns_8_texts(self):
        texts = [f"response {i}" for i in range(160)]
        with patch("app.services.rubric_service.embed_and_cluster", side_effect=_fake_cluster_data):
            centroids = await cluster_to_centroids(texts)
        assert len(centroids) == 8

    @pytest.mark.asyncio
    async def test_returned_texts_are_from_input(self):
        texts = [f"response {i}" for i in range(160)]
        with patch("app.services.rubric_service.embed_and_cluster", side_effect=_fake_cluster_data):
            centroids = await cluster_to_centroids(texts)
        for c in centroids:
            assert c in texts

    @pytest.mark.asyncio
    async def test_calls_embed_and_cluster_with_fixed_k(self):
        texts = [f"r {i}" for i in range(20)]
        captured_k = []

        def _capture(t, k=None):
            captured_k.append(k)
            return _fake_cluster_data(t, k)

        with patch("app.services.rubric_service.embed_and_cluster", side_effect=_capture):
            await cluster_to_centroids(texts)

        assert captured_k[0] == 8


# ---------------------------------------------------------------------------
# propose_initial_rubric
# ---------------------------------------------------------------------------


class TestProposeInitialRubric:
    @pytest.mark.asyncio
    async def test_returns_criteria_list(self):
        payload = json.dumps({"criteria": _VALID_CRITERIA})
        with patch(
            "app.services.rubric_service.chat_completion",
            new_callable=AsyncMock,
            return_value=payload,
        ):
            criteria = await propose_initial_rubric("question?", _EIGHT_CENTROIDS)

        assert isinstance(criteria, list)
        assert len(criteria) == 2

    @pytest.mark.asyncio
    async def test_raises_on_invalid_json(self):
        with patch(
            "app.services.rubric_service.chat_completion",
            new_callable=AsyncMock,
            return_value="not json",
        ):
            with pytest.raises(ValueError, match="invalid rubric JSON"):
                await propose_initial_rubric("question?", _EIGHT_CENTROIDS)


# ---------------------------------------------------------------------------
# run_refinement_loop
# ---------------------------------------------------------------------------


class TestRunRefinementLoop:
    @pytest.mark.asyncio
    async def test_returns_required_keys(self):
        with (
            patch.object(
                rubric_service,
                "_check_criterion_breadth",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch.object(
                rubric_service, "_binary_eval_centroid", new_callable=AsyncMock, return_value=True
            ),
        ):
            result = await run_refinement_loop(_VALID_CRITERIA, _EIGHT_CENTROIDS)

        assert set(result.keys()) == {
            "criteria",
            "decomposition_tree",
            "refinement_passes",
            "stopping_metadata",
            "conditioning_sample",
        }

    @pytest.mark.asyncio
    async def test_stops_at_convergence_when_no_broad_criteria(self):
        with (
            patch.object(
                rubric_service,
                "_check_criterion_breadth",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch.object(
                rubric_service, "_binary_eval_centroid", new_callable=AsyncMock, return_value=True
            ),
        ):
            result = await run_refinement_loop(_VALID_CRITERIA, _EIGHT_CENTROIDS)

        assert result["stopping_metadata"]["reason"] == "convergence"

    @pytest.mark.asyncio
    async def test_stops_at_rejection_threshold(self):
        # 16 children all fail misalignment → accumulates _MAX_REJECTED_PROPOSALS (15) rejections
        children = [
            {"id": f"child_{i}", "name": f"Child {i}", "description": "d", "weight": 1.0 / 16}
            for i in range(16)
        ]

        with (
            patch.object(
                rubric_service,
                "_check_criterion_breadth",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch.object(
                rubric_service,
                "_decompose_criterion",
                new_callable=AsyncMock,
                return_value=children,
            ),
            patch.object(
                rubric_service, "_filter_misalignment", new_callable=AsyncMock, return_value=False
            ),
        ):
            result = await run_refinement_loop(_VALID_CRITERIA, _EIGHT_CENTROIDS)

        assert (
            result["stopping_metadata"]["total_rejected"] >= rubric_service._MAX_REJECTED_PROPOSALS
        )

    @pytest.mark.asyncio
    async def test_decomposition_tree_records_parent_children(self):
        child_a = {"id": "child_a", "name": "Child A", "description": "d", "weight": 0.3}
        child_b = {"id": "child_b", "name": "Child B", "description": "d", "weight": 0.3}

        breadth_calls = [True, False]  # first criterion broad, second not
        breadth_iter = iter(breadth_calls * 10)

        async def _breadth(_c, _t, _eid=None):
            try:
                return next(breadth_iter)
            except StopIteration:
                return False

        with (
            patch.object(rubric_service, "_check_criterion_breadth", side_effect=_breadth),
            patch.object(
                rubric_service,
                "_decompose_criterion",
                new_callable=AsyncMock,
                return_value=[child_a, child_b],
            ),
            patch.object(
                rubric_service, "_filter_misalignment", new_callable=AsyncMock, return_value=True
            ),
            patch.object(
                rubric_service, "_filter_redundancy", new_callable=AsyncMock, return_value=True
            ),
            patch.object(
                rubric_service, "_binary_eval_centroid", new_callable=AsyncMock, return_value=True
            ),
        ):
            result = await run_refinement_loop(_VALID_CRITERIA, _EIGHT_CENTROIDS)

        assert "accuracy" in result["decomposition_tree"]
        assert set(result["decomposition_tree"]["accuracy"]) == {"child_a", "child_b"}

    @pytest.mark.asyncio
    async def test_final_criteria_weights_sum_to_one(self):
        with (
            patch.object(
                rubric_service,
                "_check_criterion_breadth",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch.object(
                rubric_service, "_binary_eval_centroid", new_callable=AsyncMock, return_value=True
            ),
        ):
            result = await run_refinement_loop(_VALID_CRITERIA, _EIGHT_CENTROIDS)

        total = sum(c["weight"] for c in result["criteria"])
        assert abs(total - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_conditioning_sample_matches_input(self):
        with (
            patch.object(
                rubric_service,
                "_check_criterion_breadth",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch.object(
                rubric_service, "_binary_eval_centroid", new_callable=AsyncMock, return_value=True
            ),
        ):
            result = await run_refinement_loop(_VALID_CRITERIA, _EIGHT_CENTROIDS)

        assert result["conditioning_sample"] == _EIGHT_CENTROIDS


# ---------------------------------------------------------------------------
# build_rubric
# ---------------------------------------------------------------------------


class TestBuildRubric:
    @pytest.mark.asyncio
    async def test_returns_all_required_keys(self):
        fake_loop_result = {
            "criteria": _VALID_CRITERIA,
            "decomposition_tree": {},
            "refinement_passes": [],
            "stopping_metadata": {
                "reason": "convergence",
                "total_rejected": 0,
                "passes_completed": 1,
            },
            "conditioning_sample": _EIGHT_CENTROIDS,
        }
        with (
            patch.object(
                rubric_service,
                "generate_setup_responses",
                new_callable=AsyncMock,
                return_value=[f"r{i}" for i in range(160)],
            ),
            patch.object(
                rubric_service,
                "generate_reference_pair",
                new_callable=AsyncMock,
                return_value=("strong response", "weak response"),
            ),
            patch.object(
                rubric_service,
                "cluster_to_centroids",
                new_callable=AsyncMock,
                return_value=_EIGHT_CENTROIDS,
            ),
            patch.object(
                rubric_service,
                "propose_initial_rubric",
                new_callable=AsyncMock,
                return_value=_VALID_CRITERIA,
            ),
            patch.object(
                rubric_service,
                "run_refinement_loop",
                new_callable=AsyncMock,
                return_value=fake_loop_result,
            ),
        ):
            result = await build_rubric(stream_id=str(uuid.uuid4()), question="question?")

        assert "criteria" in result
        assert "decomposition_tree" in result
        assert "refinement_passes" in result
        assert "stopping_metadata" in result
        assert "conditioning_sample" in result

    @pytest.mark.asyncio
    async def test_fi_path_returns_awaiting_review_when_case_text_provided(self):
        """T8.11 -- build_rubric pauses and returns fi_status='awaiting_review' on FI path."""
        with (
            patch.object(
                rubric_service,
                "screen_source_intake",
                new_callable=AsyncMock,
                return_value={"screened": True},
            ),
            patch.object(
                rubric_service,
                "extract_source",
                new_callable=AsyncMock,
                return_value={"clean_legal_issue": "q", "black_letter_rule": "rule"},
            ),
            patch.object(
                rubric_service,
                "route_to_doctrine_pack",
                new_callable=AsyncMock,
                return_value={"selected_pack": "pack_marriage", "confidence": "high"},
            ),
            patch.object(
                rubric_service,
                "generate_gold_packet_mapping",
                new_callable=AsyncMock,
                return_value={"mapping": "ok"},
            ),
            patch.object(
                rubric_service,
                "predict_failure_modes",
                new_callable=AsyncMock,
                return_value=[{"code": "SG"}],
            ),
            patch.object(
                rubric_service,
                "generate_weak_reference",
                new_callable=AsyncMock,
                return_value="weak text",
            ),
            patch.object(
                rubric_service,
                "generate_gold_answer",
                new_callable=AsyncMock,
                return_value="Gold answer text.",
            ),
            patch.object(
                rubric_service,
                "run_self_audit",
                new_callable=AsyncMock,
                return_value={"classification": "Ready", "red_flags": [], "release_check": {}},
            ),
        ):
            result = await build_rubric(
                stream_id=str(uuid.uuid4()),
                question="Is this oral promise enforceable?",
                case_text="Alice promised Bob land verbally.",
            )

        assert result.get("fi_status") == "awaiting_review"
        assert result.get("gold_answer") == "Gold answer text."
        assert result.get("self_audit_result") is not None
        assert "criteria" not in result

    @pytest.mark.asyncio
    async def test_fi_path_does_not_run_when_no_case_text(self):
        """T8.12 -- build_rubric uses non-FI path when no case_text is provided."""
        fake_loop_result = {
            "criteria": _VALID_CRITERIA,
            "decomposition_tree": {},
            "refinement_passes": [],
            "stopping_metadata": {
                "reason": "convergence",
                "total_rejected": 0,
                "passes_completed": 1,
            },
            "conditioning_sample": _EIGHT_CENTROIDS,
        }
        with (
            patch.object(
                rubric_service,
                "generate_setup_responses",
                new_callable=AsyncMock,
                return_value=[f"r{i}" for i in range(160)],
            ),
            patch.object(
                rubric_service,
                "generate_reference_pair",
                new_callable=AsyncMock,
                return_value=("strong", "weak"),
            ),
            patch.object(
                rubric_service,
                "cluster_to_centroids",
                new_callable=AsyncMock,
                return_value=_EIGHT_CENTROIDS,
            ),
            patch.object(
                rubric_service,
                "propose_initial_rubric",
                new_callable=AsyncMock,
                return_value=_VALID_CRITERIA,
            ),
            patch.object(
                rubric_service,
                "run_refinement_loop",
                new_callable=AsyncMock,
                return_value=fake_loop_result,
            ),
        ):
            result = await build_rubric(
                stream_id=str(uuid.uuid4()),
                question="question?",
            )

        assert result.get("fi_status") is None
        assert "criteria" in result


# ---------------------------------------------------------------------------
# build_rubric_phase_b
# ---------------------------------------------------------------------------


class TestBuildRubricPhaseB:
    """T8.13 -- T8.15: build_rubric_phase_b() service function tests."""

    @pytest.mark.asyncio
    async def test_returns_criteria_and_setup_responses(self):
        """T8.13 -- Phase B returns a payload with criteria and setup_responses."""
        fake_loop_result = {
            "criteria": _VALID_CRITERIA,
            "decomposition_tree": {},
            "refinement_passes": [],
            "stopping_metadata": {
                "reason": "convergence",
                "total_rejected": 0,
                "passes_completed": 1,
            },
            "conditioning_sample": _EIGHT_CENTROIDS,
        }
        with (
            patch.object(
                rubric_service,
                "generate_setup_responses",
                new_callable=AsyncMock,
                return_value=[f"r{i}" for i in range(160)],
            ),
            patch.object(
                rubric_service,
                "cluster_to_centroids",
                new_callable=AsyncMock,
                return_value=_EIGHT_CENTROIDS,
            ),
            patch.object(
                rubric_service,
                "propose_initial_rubric",
                new_callable=AsyncMock,
                return_value=_VALID_CRITERIA,
            ),
            patch.object(
                rubric_service,
                "run_refinement_loop",
                new_callable=AsyncMock,
                return_value=fake_loop_result,
            ),
        ):
            result = await build_rubric_phase_b(
                stream_id=str(uuid.uuid4()),
                question="Is this enforceable?",
                gold_answer="Gold answer text.",
                weak_text="weak reference",
                source_extraction={"clean_legal_issue": "q"},
                doctrine_pack="pack_marriage",
            )

        assert "criteria" in result
        assert "setup_responses" in result
        assert result["gold_answer"] == "Gold answer text."
        assert result["strong_reference_text"] == "Gold answer text."

    @pytest.mark.asyncio
    async def test_generates_weak_text_when_not_provided(self):
        """T8.14 -- Phase B generates weak reference when weak_text is None."""
        fake_loop_result = {
            "criteria": _VALID_CRITERIA,
            "decomposition_tree": {},
            "refinement_passes": [],
            "stopping_metadata": {
                "reason": "convergence",
                "total_rejected": 0,
                "passes_completed": 1,
            },
            "conditioning_sample": _EIGHT_CENTROIDS,
        }
        with (
            patch.object(
                rubric_service,
                "generate_setup_responses",
                new_callable=AsyncMock,
                return_value=[f"r{i}" for i in range(160)],
            ),
            patch.object(
                rubric_service,
                "generate_weak_reference",
                new_callable=AsyncMock,
                return_value="generated weak",
            ) as mock_weak,
            patch.object(
                rubric_service,
                "cluster_to_centroids",
                new_callable=AsyncMock,
                return_value=_EIGHT_CENTROIDS,
            ),
            patch.object(
                rubric_service,
                "propose_initial_rubric",
                new_callable=AsyncMock,
                return_value=_VALID_CRITERIA,
            ),
            patch.object(
                rubric_service,
                "run_refinement_loop",
                new_callable=AsyncMock,
                return_value=fake_loop_result,
            ),
        ):
            result = await build_rubric_phase_b(
                stream_id=str(uuid.uuid4()),
                question="q?",
                gold_answer="gold",
                weak_text=None,
                source_extraction=None,
                doctrine_pack=None,
            )

        mock_weak.assert_called_once()
        assert result["weak_reference_text"] == "generated weak"

    @pytest.mark.asyncio
    async def test_does_not_generate_weak_text_when_provided(self):
        """T8.15 -- Phase B skips weak reference generation when weak_text is provided."""
        fake_loop_result = {
            "criteria": _VALID_CRITERIA,
            "decomposition_tree": {},
            "refinement_passes": [],
            "stopping_metadata": {
                "reason": "convergence",
                "total_rejected": 0,
                "passes_completed": 1,
            },
            "conditioning_sample": _EIGHT_CENTROIDS,
        }
        with (
            patch.object(
                rubric_service,
                "generate_setup_responses",
                new_callable=AsyncMock,
                return_value=[f"r{i}" for i in range(160)],
            ),
            patch.object(
                rubric_service,
                "generate_weak_reference",
                new_callable=AsyncMock,
                return_value="should not be called",
            ) as mock_weak,
            patch.object(
                rubric_service,
                "cluster_to_centroids",
                new_callable=AsyncMock,
                return_value=_EIGHT_CENTROIDS,
            ),
            patch.object(
                rubric_service,
                "propose_initial_rubric",
                new_callable=AsyncMock,
                return_value=_VALID_CRITERIA,
            ),
            patch.object(
                rubric_service,
                "run_refinement_loop",
                new_callable=AsyncMock,
                return_value=fake_loop_result,
            ),
        ):
            result = await build_rubric_phase_b(
                stream_id=str(uuid.uuid4()),
                question="q?",
                gold_answer="gold",
                weak_text="pre-existing weak",
                source_extraction=None,
                doctrine_pack=None,
            )

        mock_weak.assert_not_called()
        assert result["weak_reference_text"] == "pre-existing weak"


# ---------------------------------------------------------------------------
# Phase 10: validate_question / generate_question
# ---------------------------------------------------------------------------

_Q10_EXTRACTION = {
    "clean_legal_issue": "Whether an oral land contract is enforceable.",
    "jurisdiction_forum": "New York",
    "holding_or_best_supported_answer_path": "Unenforceable under SOF.",
}

_Q10_PACKET = {
    "governing_rule": "SOF land provision",
    "trigger_facts": ["oral promise to sell land"],
}


class TestValidateQuestion:
    """T10.7 -- T10.9: validate_question() service function tests."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_required_keys(self):
        """T10.7 -- validate_question returns dict with checks, red_flags, overall_pass."""
        with patch.object(
            rubric_service,
            "chat_completion",
            new_callable=AsyncMock,
            return_value=json.dumps(
                {
                    "checks": [{"item": "Neutral call", "pass": True, "note": "OK"}],
                    "red_flags": [],
                    "overall_pass": True,
                    "suggestions": [],
                }
            ),
        ):
            result = await validate_question(
                stream_id=None,
                question="Is the agreement enforceable? Analyze.",
                source_extraction=_Q10_EXTRACTION,
                doctrine_pack="pack_marriage",
            )

        assert "checks" in result
        assert "red_flags" in result
        assert "overall_pass" in result

    @pytest.mark.asyncio
    async def test_overall_pass_true_when_all_checks_pass(self):
        """T10.8 -- validate_question reflects overall_pass=True correctly."""
        with patch.object(
            rubric_service,
            "chat_completion",
            new_callable=AsyncMock,
            return_value=json.dumps(
                {
                    "checks": [{"item": "Neutral call", "pass": True, "note": "OK"}],
                    "red_flags": [],
                    "overall_pass": True,
                    "suggestions": [],
                }
            ),
        ):
            result = await validate_question(
                stream_id=None,
                question="Is the promise enforceable? Analyze.",
            )

        assert result["overall_pass"] is True
        assert result["red_flags"] == []

    @pytest.mark.asyncio
    async def test_parse_error_on_invalid_json(self):
        """T10.9 -- validate_question returns parse_error dict when LLM returns invalid JSON."""
        with patch.object(
            rubric_service,
            "chat_completion",
            new_callable=AsyncMock,
            return_value="This is not JSON",
        ):
            result = await validate_question(
                stream_id=None,
                question="Is this a Statute of Frauds issue?",
            )

        assert "parse_error" in result
        assert result["overall_pass"] is False


class TestGenerateQuestion:
    """T10.10 -- T10.11: generate_question() service function tests."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_question_and_internal_notes(self):
        """T10.10 -- generate_question returns dict with question and internal_notes keys."""
        with patch.object(
            rubric_service,
            "chat_completion",
            new_callable=AsyncMock,
            return_value=json.dumps(
                {
                    "question": "Is the oral agreement enforceable? Analyze.",
                    "internal_notes": {
                        "target_doctrine": "SOF land provision",
                        "likely_distractors": ["part performance"],
                        "source_fidelity_notes": "Facts preserved.",
                    },
                }
            ),
        ):
            result = await generate_question(
                stream_id=None,
                source_extraction=_Q10_EXTRACTION,
                gold_packet_mapping=_Q10_PACKET,
                doctrine_pack="pack_marriage",
            )

        assert "question" in result
        assert "internal_notes" in result

    @pytest.mark.asyncio
    async def test_returns_non_empty_question_string(self):
        """T10.11 -- generate_question produces a non-empty question string."""
        with patch.object(
            rubric_service,
            "chat_completion",
            new_callable=AsyncMock,
            return_value=json.dumps(
                {
                    "question": "Does the claimant have the better argument? Analyze.",
                    "internal_notes": {
                        "target_doctrine": "SOF",
                        "likely_distractors": [],
                        "source_fidelity_notes": "",
                    },
                }
            ),
        ):
            result = await generate_question(
                stream_id=None,
                source_extraction=_Q10_EXTRACTION,
                gold_packet_mapping=_Q10_PACKET,
            )

        assert result["question"]
        assert len(result["question"]) > 5


# ---------------------------------------------------------------------------
# Phase 12: run_mode_a, compare_draft_to_source, run_mode_e
# ---------------------------------------------------------------------------

_M12_CASE_TEXT = "Buyer made oral promise to purchase land. Seller seeks enforcement."
_M12_QUESTION = "Is the oral promise enforceable under the SOF?"
_M12_EXTRACTION = {"clean_legal_issue": "SOF land writing requirement", "jurisdiction_forum": "CA"}
_M12_PACK = {"name": "Land contracts", "must_separate_subissues": ["SOF writing"]}


class TestRunModeA:
    """T12.4 -- T12.6: run_mode_a() returns expected keys and persists state."""

    @pytest.mark.asyncio
    async def test_returns_required_keys(self):
        """T12.4 -- run_mode_a returns dict with 4 required keys."""
        with (
            patch(
                "app.services.rubric_service.screen_source_intake",
                new_callable=AsyncMock,
                return_value={"rating": "strong_lead", "reason": "clear SOF issue"},
            ),
            patch(
                "app.services.rubric_service.extract_source",
                new_callable=AsyncMock,
                return_value=_M12_EXTRACTION,
            ),
            patch(
                "app.services.rubric_service.route_to_doctrine_pack",
                new_callable=AsyncMock,
                return_value={
                    "pack_id": "pack_marriage",
                    "pack_content": _M12_PACK,
                    "metadata": {},
                },
            ),
        ):
            result = await run_mode_a(
                stream_id="test-stream",
                case_text=_M12_CASE_TEXT,
                question=_M12_QUESTION,
            )
        assert "screening_result" in result
        assert "source_extraction" in result
        assert "routing_metadata" in result
        assert "doctrine_pack" in result

    @pytest.mark.asyncio
    async def test_calls_all_three_frank_functions(self):
        """T12.5 -- run_mode_a calls all three FI functions."""
        mock_screen = AsyncMock(return_value={"rating": "strong_lead"})
        mock_extract = AsyncMock(return_value=_M12_EXTRACTION)
        mock_route = AsyncMock(
            return_value={"pack_id": "p1", "pack_content": _M12_PACK, "metadata": {}}
        )
        with (
            patch("app.services.rubric_service.screen_source_intake", mock_screen),
            patch("app.services.rubric_service.extract_source", mock_extract),
            patch("app.services.rubric_service.route_to_doctrine_pack", mock_route),
        ):
            await run_mode_a(
                stream_id="s1",
                case_text=_M12_CASE_TEXT,
                question=_M12_QUESTION,
            )
        mock_screen.assert_awaited_once()
        mock_extract.assert_awaited_once()
        mock_route.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_propagates_frank_error(self):
        """T12.6 -- run_mode_a propagates exceptions from underlying frank calls."""
        with patch(
            "app.services.rubric_service.screen_source_intake",
            new_callable=AsyncMock,
            side_effect=RuntimeError("upstream error"),
        ):
            with pytest.raises(RuntimeError, match="upstream error"):
                await run_mode_a(
                    stream_id="s1",
                    case_text=_M12_CASE_TEXT,
                    question=_M12_QUESTION,
                )


class TestCompareDraftToSource:
    """T12.7 -- T12.8: compare_draft_to_source() returns comparison dict."""

    @pytest.mark.asyncio
    async def test_returns_eight_heading_keys(self):
        """T12.7 -- compare_draft_to_source returns dict with 8 heading keys."""
        eight_keys = {
            "source_benchmark_alignment": "OK",
            "controlling_doctrine_match": "OK",
            "gate_order_correctness": "OK",
            "trigger_test_accuracy": "OK",
            "exception_substitute_mapping": "OK",
            "fallback_doctrine_treatment": "OK",
            "factual_fidelity": "OK",
            "provenance_discipline": "OK",
        }
        _model_resp = json.dumps(eight_keys)
        with patch(
            "app.services.rubric_service.chat_completion",
            new_callable=AsyncMock,
            return_value=_model_resp,
        ):
            result = await compare_draft_to_source(
                stream_id=None,
                draft_text="The oral promise is unenforceable.",
                source_extraction=_M12_EXTRACTION,
                doctrine_pack="pack_marriage",
            )
        for key in eight_keys:
            assert key in result

    @pytest.mark.asyncio
    async def test_parse_error_included_on_bad_json(self):
        """T12.8 -- compare_draft_to_source includes parse_error key when model returns bad JSON."""
        with patch(
            "app.services.rubric_service.chat_completion",
            new_callable=AsyncMock,
            return_value="not-json-at-all",
        ):
            result = await compare_draft_to_source(
                stream_id=None,
                draft_text="Some draft.",
                source_extraction=_M12_EXTRACTION,
            )
        assert "parse_error" in result


class TestRunModeE:
    """T12.9: run_mode_e() returns list of failure mode dicts."""

    @pytest.mark.asyncio
    async def test_returns_list(self):
        """T12.9 -- run_mode_e returns a list."""
        failure_modes = [
            {"code": "SG", "label": "Statute gap", "description": "...", "severity": "high"}
        ]
        with (
            patch(
                "app.services.rubric_service.generate_gold_packet_mapping",
                new_callable=AsyncMock,
                return_value={"mapping": "..."},
            ),
            patch(
                "app.services.rubric_service.predict_failure_modes",
                new_callable=AsyncMock,
                return_value=failure_modes,
            ),
        ):
            result = await run_mode_e(
                stream_id="s1",
                source_extraction=_M12_EXTRACTION,
                doctrine_pack=_M12_PACK,
                gold_packet_mapping=None,
                question=_M12_QUESTION,
            )
        assert isinstance(result, list)
        assert result[0]["code"] == "SG"

    @pytest.mark.asyncio
    async def test_skips_gold_packet_generation_when_provided(self):
        """run_mode_e skips generate_gold_packet_mapping when mapping is already present."""
        failure_modes = [{"code": "WR", "label": "Writing req gap"}]
        mock_gen = AsyncMock()
        with (
            patch(
                "app.services.rubric_service.predict_failure_modes",
                new_callable=AsyncMock,
                return_value=failure_modes,
            ),
            patch("app.services.rubric_service.generate_gold_packet_mapping", mock_gen),
        ):
            await run_mode_e(
                stream_id="s1",
                source_extraction=_M12_EXTRACTION,
                doctrine_pack=_M12_PACK,
                gold_packet_mapping={"existing": True},
                question=_M12_QUESTION,
            )
        mock_gen.assert_not_awaited()
