"""Unit tests for app.services.clustering."""

from unittest.mock import MagicMock, patch

import numpy as np

from app.services import clustering
from app.services.clustering import embed_and_cluster


def _fake_encoder(n: int, n_clusters: int) -> MagicMock:
    embeddings = np.zeros((n, n_clusters), dtype=np.float32)
    for i in range(n):
        embeddings[i, i % n_clusters] = 1.0
    mock = MagicMock()
    mock.encode.return_value = embeddings
    return mock


class TestEmbedAndCluster:
    def test_returns_expected_keys(self):
        n = 20
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 2)):
            result = embed_and_cluster([f"text {i}" for i in range(n)])
        assert {"k", "clusters_map", "centroid_indices", "silhouette_scores_by_k"}.issubset(
            result.keys()
        )

    def test_data_adaptive_k_at_least_2(self):
        n = 20
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 2)):
            result = embed_and_cluster([f"text {i}" for i in range(n)])
        assert result["k"] >= 2

    def test_fixed_k_is_respected(self):
        n = 40
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 4)):
            result = embed_and_cluster([f"text {i}" for i in range(n)], k=8)
        assert result["k"] == 8

    def test_fixed_k_capped_at_n(self):
        n = 5
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 2)):
            result = embed_and_cluster([f"text {i}" for i in range(n)], k=100)
        assert result["k"] <= n

    def test_all_indices_covered(self):
        n = 30
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 3)):
            result = embed_and_cluster([f"text {i}" for i in range(n)])
        all_indices: list[int] = []
        for indices in result["clusters_map"].values():
            all_indices.extend(indices)
        assert sorted(all_indices) == list(range(n))

    def test_centroid_index_belongs_to_cluster(self):
        n = 20
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 2)):
            result = embed_and_cluster([f"text {i}" for i in range(n)])
        for cid, rep_idx in result["centroid_indices"].items():
            assert rep_idx in result["clusters_map"][cid]

    def test_clusters_map_count_matches_k(self):
        n = 20
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 2)):
            result = embed_and_cluster([f"text {i}" for i in range(n)])
        assert len(result["clusters_map"]) == result["k"]

    def test_fixed_k_8_returns_8_clusters(self):
        n = 80
        with patch.object(clustering, "_get_encoder", return_value=_fake_encoder(n, 8)):
            result = embed_and_cluster([f"text {i}" for i in range(n)], k=8)
        assert result["k"] == 8
        assert len(result["clusters_map"]) == 8
        assert len(result["centroid_indices"]) == 8
