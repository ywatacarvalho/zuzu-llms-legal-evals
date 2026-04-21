"""
Shared clustering utilities used by both rubric_service and analysis_service.

embed_and_cluster() handles two modes:
  - k=None  → data-adaptive: sweep k via silhouette score (used in analysis pipeline)
  - k=int   → fixed k (used in rubric setup pipeline with k=8)
"""

from concurrent.futures import ThreadPoolExecutor

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

_EMBEDDING_MODEL = "all-mpnet-base-v2"
_EXECUTOR = ThreadPoolExecutor(max_workers=2)

_encoder = None


def _get_encoder():
    global _encoder  # noqa: PLW0603
    if _encoder is None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        _encoder = SentenceTransformer(_EMBEDDING_MODEL)
    return _encoder


def embed_and_cluster(texts: list[str], k: int | None = None, k_min: int = 2) -> dict:
    """
    Embed texts and cluster them.

    Parameters
    ----------
    texts   List of response strings to embed.
    k       If None, sweep k from k_min to min(15, n//10) and choose via silhouette score.
            If an integer, use that fixed value (no sweep).
    k_min   Minimum number of clusters for the adaptive sweep (default 2).
            Useful to prevent trivial 2-cluster solutions when comparing multiple models.

    Returns
    -------
    dict with keys:
      k                    int
      clusters_map         dict[int, list[int]]   cluster_id → response indices
      centroid_indices     dict[int, int]         cluster_id → representative response index
      silhouette_scores_by_k  dict[int, float]   k → score for adaptive sweep (empty for fixed k)
    """
    encoder = _get_encoder()
    embeddings = encoder.encode(texts, show_progress_bar=False, batch_size=64)
    norms: np.ndarray = normalize(embeddings)

    n = len(texts)
    silhouette_scores_by_k: dict[int, float] = {}

    if k is not None:
        best_k = max(2, min(k, n))
    else:
        sweep_min = max(2, min(k_min, n - 1))
        best_k, best_score = sweep_min, -1.0
        k_max = min(15, max(sweep_min, n // 10))
        for candidate_k in range(sweep_min, k_max + 1):
            km = KMeans(n_clusters=candidate_k, random_state=42, n_init=10)
            labels = km.fit_predict(norms)
            if len(set(labels)) < 2:
                continue
            score = float(silhouette_score(norms, labels))
            silhouette_scores_by_k[candidate_k] = round(score, 6)
            if score > best_score:
                best_score, best_k = score, candidate_k

    km_final = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels: np.ndarray = km_final.fit_predict(norms)
    centroids: np.ndarray = km_final.cluster_centers_

    clusters_map: dict[int, list[int]] = {}
    for idx, lbl in enumerate(labels.tolist()):
        clusters_map.setdefault(int(lbl), []).append(idx)

    centroid_indices: dict[int, int] = {}
    for cid, indices in clusters_map.items():
        centroid_vec = centroids[cid]
        sims = [float(np.dot(norms[i], centroid_vec)) for i in indices]
        centroid_indices[cid] = indices[int(np.argmax(sims))]

    return {
        "k": best_k,
        "clusters_map": clusters_map,
        "centroid_indices": centroid_indices,
        "silhouette_scores_by_k": silhouette_scores_by_k,
    }
