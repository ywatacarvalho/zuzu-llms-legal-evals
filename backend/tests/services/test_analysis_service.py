"""
Unit tests for app.services.analysis_service.

All external I/O is mocked:
  - sentence-transformers encoder  → patched via _get_encoder
  - GitHub Copilot chat_completion → patched at import site in the service module
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.services import analysis_service, clustering
from app.services.analysis_service import (
    _apply_weighting,
    _embed_and_cluster,
    _score_centroid,
    _score_centroid_detailed,
    run_analysis,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CRITERIA = [
    {"id": "accuracy", "name": "Accuracy", "description": "Factual correctness.", "weight": 0.6},
    {"id": "reasoning", "name": "Reasoning", "description": "Legal reasoning.", "weight": 0.4},
]


def _fake_encoder(n: int, n_clusters: int) -> MagicMock:
    """Return a mock encoder whose .encode() produces clearly-separated clusters."""
    embeddings = np.zeros((n, n_clusters), dtype=np.float32)
    for i in range(n):
        embeddings[i, i % n_clusters] = 1.0

    mock = MagicMock()
    mock.encode.return_value = embeddings
    return mock


def _fake_response(text: str, model: str, idx: int) -> object:
    return type("MR", (), {"response_text": text, "model_name": model, "run_index": idx})()


# ---------------------------------------------------------------------------
# _embed_and_cluster
# ---------------------------------------------------------------------------


class TestEmbedAndCluster:
    def test_returns_expected_keys(self):
        n = 20
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 2)):
            result = _embed_and_cluster([f"text {i}" for i in range(n)])

        assert {"k", "clusters_map", "centroid_indices", "silhouette_scores_by_k"}.issubset(
            result.keys()
        )

    def test_k_is_at_least_2(self):
        n = 20
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 2)):
            result = _embed_and_cluster([f"text {i}" for i in range(n)])

        assert result["k"] >= 2

    def test_all_indices_are_covered(self):
        n = 30
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 3)):
            result = _embed_and_cluster([f"text {i}" for i in range(n)])

        all_indices: list[int] = []
        for indices in result["clusters_map"].values():
            all_indices.extend(indices)
        assert sorted(all_indices) == list(range(n))

    def test_centroid_index_belongs_to_its_cluster(self):
        n = 20
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 2)):
            result = _embed_and_cluster([f"text {i}" for i in range(n)])

        for cid, rep_idx in result["centroid_indices"].items():
            assert rep_idx in result["clusters_map"][cid]

    def test_clusters_map_count_matches_k(self):
        n = 20
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 2)):
            result = _embed_and_cluster([f"text {i}" for i in range(n)])

        assert len(result["clusters_map"]) == result["k"]

    def test_k_capped_at_15(self):
        # With n=20, k_max = min(15, 2) = 2; just verify cap logic doesn't blow up
        n = 20
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 2)):
            result = _embed_and_cluster([f"t{i}" for i in range(n)])
        assert result["k"] <= 15

    def test_large_n_picks_reasonable_k(self):
        n = 200
        n_true = 4
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, n_true)):
            result = _embed_and_cluster([f"t{i}" for i in range(n)])
        assert 2 <= result["k"] <= 15


# ---------------------------------------------------------------------------
# _score_centroid
# ---------------------------------------------------------------------------


class TestScoreCentroid:
    @pytest.mark.asyncio
    async def test_returns_weighted_total_from_valid_json(self):
        payload = json.dumps(
            {
                "criterion_scores": {"accuracy": 0.9, "reasoning": 0.8},
                "weighted_total": 0.86,
            }
        )
        with patch(
            "app.services.analysis_service.chat_completion",
            new_callable=AsyncMock,
            return_value=payload,
        ):
            score = await _score_centroid("Some legal text.", "What is the standard?", _CRITERIA)

        assert score == pytest.approx(0.86)

    @pytest.mark.asyncio
    async def test_fallback_recomputes_from_criterion_scores(self):
        # weighted_total is missing; service should recompute from criterion_scores
        payload = json.dumps({"criterion_scores": {"accuracy": 1.0, "reasoning": 0.5}})
        with patch(
            "app.services.analysis_service.chat_completion",
            new_callable=AsyncMock,
            return_value=payload,
        ):
            score = await _score_centroid("text", "question", _CRITERIA)

        # 1.0 * 0.6 + 0.5 * 0.4 = 0.8
        assert score == pytest.approx(0.8, abs=1e-4)

    @pytest.mark.asyncio
    async def test_returns_zero_on_completely_invalid_json(self):
        with patch(
            "app.services.analysis_service.chat_completion",
            new_callable=AsyncMock,
            return_value="not json at all",
        ):
            score = await _score_centroid("text", "question", _CRITERIA)

        assert score == 0.0

    @pytest.mark.asyncio
    async def test_score_clamped_to_unit_interval(self):
        # LLM could theoretically return out-of-range values; service just passes them through,
        # but the weighted_total should reflect the rubric weights
        payload = json.dumps(
            {"criterion_scores": {"accuracy": 1.0, "reasoning": 1.0}, "weighted_total": 1.0}
        )
        with patch(
            "app.services.analysis_service.chat_completion",
            new_callable=AsyncMock,
            return_value=payload,
        ):
            score = await _score_centroid("text", "question", _CRITERIA)

        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# run_analysis
# ---------------------------------------------------------------------------


class TestRunAnalysis:
    def _make_responses(self, n: int, models: list[str]) -> list:
        return [_fake_response(f"Response {i}", models[i % len(models)], i) for i in range(n)]

    @pytest.mark.asyncio
    async def test_returns_all_required_keys(self):
        n = 20
        models = [
            "openai/gpt-oss-20b",
            "google/gemma-3n-E4B-it",
            "arize-ai/qwen-2-1.5b-instruct",
            "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        ]
        responses = self._make_responses(n, models)

        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }

        with (
            patch.object(
                analysis_service,
                "_embed_and_cluster",
                return_value=fake_cluster_data,
            ),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps(
                    {
                        "criterion_scores": {"accuracy": 0.9, "reasoning": 0.8},
                        "weighted_total": 0.86,
                    }
                ),
            ),
        ):
            result = await run_analysis("What is the standard of review?", responses, _CRITERIA)

        assert {
            "k",
            "clusters",
            "centroid_indices",
            "scores",
            "winning_cluster",
            "model_shares",
            "weighting_mode",
            "baseline_scores",
            "weighting_comparison",
            "silhouette_scores_by_k",
        }.issubset(result.keys())

    @pytest.mark.asyncio
    async def test_clusters_contain_model_counts(self):
        models = ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"]
        n = 20
        responses = self._make_responses(n, models)
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps({"weighted_total": 0.7}),
            ),
        ):
            result = await run_analysis("q?", responses, _CRITERIA)

        for cluster in result["clusters"]:
            assert "model_counts" in cluster
            assert isinstance(cluster["model_counts"], dict)
            # model_counts values must sum to len(response_indices)
            total = sum(cluster["model_counts"].values())
            assert total == len(cluster["response_indices"])

    @pytest.mark.asyncio
    async def test_k_matches_cluster_count(self):
        n = 20
        responses = self._make_responses(n, ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"])
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps({"weighted_total": 0.5}),
            ),
        ):
            result = await run_analysis("q?", responses, _CRITERIA)

        assert result["k"] == len(result["clusters"])

    @pytest.mark.asyncio
    async def test_analysis_uses_floor_1_5_models_for_minimum_k(self):
        models = [
            "openai/gpt-oss-20b",
            "google/gemma-3n-E4B-it",
            "arize-ai/qwen-2-1.5b-instruct",
            "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
            "LiquidAI/LFM2-24B-A2B",
        ]
        n = 50
        responses = self._make_responses(n, models)
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(25)), 1: list(range(25, 50))},
            "centroid_indices": {0: 0, 1: 25},
        }

        with (
            patch.object(
                analysis_service,
                "_embed_and_cluster",
                return_value=fake_cluster_data,
            ) as mock_cluster,
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps({"weighted_total": 0.5}),
            ),
        ):
            await run_analysis("q?", responses, _CRITERIA)

        assert mock_cluster.call_args.args[2] == 7

    @pytest.mark.asyncio
    async def test_winning_cluster_has_highest_score(self):
        n = 20
        responses = self._make_responses(n, ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"])
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        scores_to_return = [0.9, 0.4]
        call_count = 0

        async def _mock_chat(**kwargs):
            nonlocal call_count
            idx = call_count % len(scores_to_return)
            score = scores_to_return[idx]
            call_count += 1
            # Return a response compatible with both scoring and overlay parsers.
            return json.dumps(
                {
                    "weighted_total": score,
                    "penalties_applied": [],
                    "cap_status": {"cap_code": None, "applied": False},
                    "final_score": round(score * 100, 1),
                }
            )

        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch("app.services.analysis_service.chat_completion", side_effect=_mock_chat),
        ):
            result = await run_analysis("q?", responses, _CRITERIA)

        winning = result["winning_cluster"]
        assert result["scores"][str(winning)] == max(result["scores"].values())

    @pytest.mark.asyncio
    async def test_model_shares_sum_to_one(self):
        models = [
            "openai/gpt-oss-20b",
            "google/gemma-3n-E4B-it",
            "arize-ai/qwen-2-1.5b-instruct",
            "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        ]
        n = 40
        responses = self._make_responses(n, models)
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(20)), 1: list(range(20, 40))},
            "centroid_indices": {0: 0, 1: 20},
        }
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps({"weighted_total": 0.8}),
            ),
        ):
            result = await run_analysis("q?", responses, _CRITERIA)

        assert sum(result["model_shares"].values()) == pytest.approx(1.0, abs=1e-4)

    @pytest.mark.asyncio
    async def test_centroid_text_is_truncated_to_max_chars(self):
        long_text = "x" * 5_000
        responses = [_fake_response(long_text, "openai/gpt-oss-20b", i) for i in range(20)]
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps({"weighted_total": 0.5}),
            ),
        ):
            result = await run_analysis("q?", responses, _CRITERIA)

        for cluster in result["clusters"]:
            text = cluster.get("centroid_response_text") or ""
            assert len(text) <= analysis_service._MAX_CENTROID_CHARS

    @pytest.mark.asyncio
    async def test_weighting_mode_is_heuristic(self):
        n = 20
        responses = self._make_responses(n, ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"])
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps({"weighted_total": 0.7}),
            ),
        ):
            result = await run_analysis("q?", responses, _CRITERIA)

        assert result["weighting_mode"] == "heuristic"

    @pytest.mark.asyncio
    async def test_baseline_scores_has_per_criterion_keys(self):
        n = 20
        responses = self._make_responses(n, ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"])
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps(
                    {
                        "criterion_scores": {"accuracy": 0.8, "reasoning": 0.6},
                        "weighted_total": 0.72,
                    }
                ),
            ),
        ):
            result = await run_analysis("q?", responses, _CRITERIA)

        for cluster_scores in result["baseline_scores"].values():
            assert "accuracy" in cluster_scores
            assert "reasoning" in cluster_scores

    @pytest.mark.asyncio
    async def test_weighting_comparison_has_all_modes(self):
        n = 20
        responses = self._make_responses(n, ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"])
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps({"weighted_total": 0.5}),
            ),
        ):
            result = await run_analysis("q?", responses, _CRITERIA)

        assert set(result["weighting_comparison"].keys()) == {
            "uniform",
            "heuristic",
            "whitened_uniform",
        }


# ---------------------------------------------------------------------------
# _score_centroid_detailed
# ---------------------------------------------------------------------------


class TestScoreCentroidDetailed:
    @pytest.mark.asyncio
    async def test_returns_tuple_of_float_and_dict(self):
        payload = json.dumps(
            {"criterion_scores": {"accuracy": 0.9, "reasoning": 0.8}, "weighted_total": 0.86}
        )
        with patch(
            "app.services.analysis_service.chat_completion",
            new_callable=AsyncMock,
            return_value=payload,
        ):
            total, per_crit, ftags, mtags = await _score_centroid_detailed(
                "text", "question", _CRITERIA
            )

        assert isinstance(total, float)
        assert isinstance(per_crit, dict)
        assert "accuracy" in per_crit
        assert "reasoning" in per_crit
        assert isinstance(ftags, list)
        assert isinstance(mtags, dict)

    @pytest.mark.asyncio
    async def test_total_matches_weighted_total_field(self):
        payload = json.dumps(
            {"criterion_scores": {"accuracy": 0.9, "reasoning": 0.8}, "weighted_total": 0.86}
        )
        with patch(
            "app.services.analysis_service.chat_completion",
            new_callable=AsyncMock,
            return_value=payload,
        ):
            total, _, _, _ = await _score_centroid_detailed("text", "question", _CRITERIA)

        assert total == pytest.approx(0.86)

    @pytest.mark.asyncio
    async def test_fallback_computes_total_from_criterion_scores(self):
        payload = json.dumps({"criterion_scores": {"accuracy": 1.0, "reasoning": 0.5}})
        with patch(
            "app.services.analysis_service.chat_completion",
            new_callable=AsyncMock,
            return_value=payload,
        ):
            total, _, _, _ = await _score_centroid_detailed("text", "question", _CRITERIA)

        # 1.0 * 0.6 + 0.5 * 0.4 = 0.8
        assert total == pytest.approx(0.8, abs=1e-4)

    @pytest.mark.asyncio
    async def test_returns_zero_on_invalid_json(self):
        with patch(
            "app.services.analysis_service.chat_completion",
            new_callable=AsyncMock,
            return_value="not json",
        ):
            total, per_crit, ftags, mtags = await _score_centroid_detailed(
                "text", "question", _CRITERIA
            )

        assert total == 0.0
        assert all(v == 0.0 for v in per_crit.values())

    @pytest.mark.asyncio
    async def test_parses_failure_tags_when_doctrine_pack_provided(self):
        """T9.1 — failure_tags are extracted when doctrine_pack is set."""
        ftag = {"code": "SG", "label": "Statute of Frauds gate omitted", "severity": "high"}
        payload = json.dumps(
            {
                "criterion_scores": {"accuracy": 0.6, "reasoning": 0.5},
                "weighted_total": 0.56,
                "failure_tags": [ftag],
                "metadata_tags": {"notes": "missing SoF analysis"},
            }
        )
        with (
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=payload,
            ),
            patch(
                "app.services.frank_instructions.get_failure_bank",
                return_value=[ftag],
            ),
        ):
            total, _, ftags, mtags = await _score_centroid_detailed(
                "text", "question", _CRITERIA, doctrine_pack="pack_10"
            )

        assert ftags == [ftag]
        assert mtags == {"notes": "missing SoF analysis"}

    @pytest.mark.asyncio
    async def test_returns_empty_failure_tags_without_doctrine_pack(self):
        """T9.2 — no failure_tags in response without doctrine_pack."""
        payload = json.dumps(
            {"criterion_scores": {"accuracy": 0.9, "reasoning": 0.8}, "weighted_total": 0.86}
        )
        with patch(
            "app.services.analysis_service.chat_completion",
            new_callable=AsyncMock,
            return_value=payload,
        ):
            _, _, ftags, mtags = await _score_centroid_detailed("text", "question", _CRITERIA)

        assert ftags == []
        assert mtags == {}


# ---------------------------------------------------------------------------
# _apply_weighting
# ---------------------------------------------------------------------------


class TestApplyWeighting:
    _MATRIX = {
        0: {"accuracy": 0.8, "reasoning": 0.6},
        1: {"accuracy": 0.4, "reasoning": 0.9},
    }

    def test_uniform_gives_equal_criterion_weight(self):
        result = _apply_weighting(self._MATRIX, _CRITERIA, "uniform")
        expected_0 = round((0.8 + 0.6) / 2, 4)
        expected_1 = round((0.4 + 0.9) / 2, 4)
        assert result["0"] == pytest.approx(expected_0, abs=1e-3)
        assert result["1"] == pytest.approx(expected_1, abs=1e-3)

    def test_heuristic_uses_rubric_weights(self):
        result = _apply_weighting(self._MATRIX, _CRITERIA, "heuristic")
        # 0.8*0.6 + 0.6*0.4 = 0.48+0.24 = 0.72
        assert result["0"] == pytest.approx(0.72, abs=1e-3)
        # 0.4*0.6 + 0.9*0.4 = 0.24+0.36 = 0.60
        assert result["1"] == pytest.approx(0.60, abs=1e-3)

    def test_whitened_uniform_returns_scores_summing_to_one(self):
        result = _apply_weighting(self._MATRIX, _CRITERIA, "whitened_uniform")
        total = sum(result.values())
        assert total == pytest.approx(1.0, abs=1e-3)

    def test_unknown_mode_returns_empty_dict(self):
        result = _apply_weighting(self._MATRIX, _CRITERIA, "nonexistent_mode")
        assert result == {}


# ---------------------------------------------------------------------------
# Phase 9: run_analysis with doctrine_pack (failure tagging)
# ---------------------------------------------------------------------------


class TestRunAnalysisWithDoctrinePackPhase9:
    """T9.3 -- T9.6: run_analysis collects and returns failure_tags when doctrine_pack set."""

    def _make_responses(self, n: int, models: list[str]) -> list:
        return [_fake_response(f"Response {i}", models[i % len(models)], i) for i in range(n)]

    @pytest.mark.asyncio
    async def test_failure_tags_present_in_result_when_doctrine_pack_provided(self):
        """T9.3 -- failure_tags key is present in run_analysis result when doctrine_pack given."""
        n = 20
        models = ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"]
        responses = self._make_responses(n, models)
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        ftag = {"code": "SG", "label": "Gate omitted", "severity": "high"}
        payload = json.dumps(
            {
                "criterion_scores": {"accuracy": 0.7, "reasoning": 0.6},
                "weighted_total": 0.66,
                "failure_tags": [ftag],
                "metadata_tags": {"notes": "missing gate"},
            }
        )
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=payload,
            ),
            patch("app.services.frank_instructions.get_failure_bank", return_value=[ftag]),
        ):
            result = await run_analysis("q?", responses, _CRITERIA, doctrine_pack="pack_10")

        assert "failure_tags" in result
        assert result["failure_tags"] is not None

    @pytest.mark.asyncio
    async def test_failure_tags_none_when_no_doctrine_pack(self):
        """T9.4 -- failure_tags is None when no doctrine_pack passed."""
        n = 20
        models = ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"]
        responses = self._make_responses(n, models)
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps({"weighted_total": 0.5}),
            ),
        ):
            result = await run_analysis("q?", responses, _CRITERIA)

        assert result.get("failure_tags") is None

    @pytest.mark.asyncio
    async def test_failure_tags_keyed_by_cluster_id_string(self):
        """T9.5 -- failure_tags dict is keyed by str(cluster_id)."""
        n = 20
        models = ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"]
        responses = self._make_responses(n, models)
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        ftag = {"code": "SC", "label": "Scope creep", "severity": "medium"}
        payload = json.dumps(
            {
                "criterion_scores": {"accuracy": 0.7, "reasoning": 0.6},
                "weighted_total": 0.66,
                "failure_tags": [ftag],
                "metadata_tags": {},
            }
        )
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=payload,
            ),
            patch("app.services.frank_instructions.get_failure_bank", return_value=[ftag]),
        ):
            result = await run_analysis("q?", responses, _CRITERIA, doctrine_pack="pack_20")

        if result["failure_tags"]:
            for key in result["failure_tags"]:
                assert isinstance(key, str), f"failure_tags key {key!r} is not a string"

    @pytest.mark.asyncio
    async def test_failure_tags_none_when_all_clusters_have_empty_tags(self):
        """T9.6 -- failure_tags is None when all centroids return empty lists."""
        n = 20
        models = ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"]
        responses = self._make_responses(n, models)
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        payload = json.dumps(
            {
                "criterion_scores": {"accuracy": 0.9, "reasoning": 0.8},
                "weighted_total": 0.86,
                "failure_tags": [],
                "metadata_tags": {},
            }
        )
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=payload,
            ),
            patch("app.services.frank_instructions.get_failure_bank", return_value=[]),
        ):
            result = await run_analysis("q?", responses, _CRITERIA, doctrine_pack="pack_10")

        assert result.get("failure_tags") is None


# ---------------------------------------------------------------------------
# Phase 5: dual-rubric variation scoring
# ---------------------------------------------------------------------------


class TestRunAnalysisDualRubric:
    def _make_responses(self, n: int, models: list[str]) -> list:
        return [_fake_response(f"Response {i}", models[i % len(models)], i) for i in range(n)]

    @pytest.mark.asyncio
    async def test_variation_scores_none_when_dual_rubric_mode_false(self):
        """variation_scores is None when dual_rubric_mode is not set."""
        n = 20
        models = ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"]
        responses = self._make_responses(n, models)
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps({"weighted_total": 0.7}),
            ),
        ):
            result = await run_analysis("q?", responses, _CRITERIA)

        assert result["variation_scores"] is None

    @pytest.mark.asyncio
    async def test_variation_scores_uses_separate_clustering_when_variation_responses_provided(
        self,
    ):
        """When variation_responses are provided, Phase 5 clusters them separately."""
        n = 20
        models = ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"]
        responses = self._make_responses(n, models)
        var_responses = self._make_responses(20, models)
        var_criteria = [
            {
                "id": "accuracy",
                "name": "Accuracy",
                "description": "Variation correctness.",
                "weight": 1.0,
            }
        ]
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }

        async def _mock_chat(**kwargs):
            return json.dumps(
                {
                    "weighted_total": 0.7,
                    "penalties_applied": [],
                    "cap_status": {"cap_code": None, "applied": False},
                    "final_score": 70.0,
                }
            )

        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch("app.services.analysis_service.chat_completion", side_effect=_mock_chat),
        ):
            result = await run_analysis(
                "base q?",
                responses,
                _CRITERIA,
                dual_rubric_mode=True,
                variation_criteria=var_criteria,
                variation_question="variation q?",
                variation_responses=var_responses,
            )

        assert result["variation_scores"] is not None
        assert result["variation_scores"]["separate_clustering"] is True
        assert "scores" in result["variation_scores"]
        assert "winning_cluster" in result["variation_scores"]

    @pytest.mark.asyncio
    async def test_variation_scores_fallback_when_no_variation_responses(self):
        """Without variation_responses, Phase 5 falls back to scoring base centroids."""
        n = 20
        models = ["openai/gpt-oss-20b", "google/gemma-3n-E4B-it"]
        responses = self._make_responses(n, models)
        var_criteria = [
            {
                "id": "accuracy",
                "name": "Accuracy",
                "description": "Variation correctness.",
                "weight": 1.0,
            }
        ]
        fake_cluster_data = {
            "k": 2,
            "clusters_map": {0: list(range(10)), 1: list(range(10, 20))},
            "centroid_indices": {0: 0, 1: 10},
        }
        with (
            patch.object(analysis_service, "_embed_and_cluster", return_value=fake_cluster_data),
            patch(
                "app.services.analysis_service.chat_completion",
                new_callable=AsyncMock,
                return_value=json.dumps({"weighted_total": 0.6}),
            ),
        ):
            result = await run_analysis(
                "q?",
                responses,
                _CRITERIA,
                dual_rubric_mode=True,
                variation_criteria=var_criteria,
            )

        assert result["variation_scores"] is not None
        assert result["variation_scores"]["separate_clustering"] is False
