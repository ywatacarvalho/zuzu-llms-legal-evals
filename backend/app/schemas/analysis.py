import uuid
from datetime import datetime

from pydantic import BaseModel


class ClusterDetail(BaseModel):
    cluster_id: int
    response_indices: list[int]
    centroid_index: int
    centroid_response_text: str | None = None
    model_counts: dict[str, int] | None = None
    composition: dict | None = None
    overlay: dict | None = None


class AnalysisOut(BaseModel):
    id: uuid.UUID
    evaluation_id: uuid.UUID
    k: int
    clusters: list[ClusterDetail] | None
    centroid_indices: list[int] | None
    scores: dict[str, float] | None
    winning_cluster: int | None
    model_shares: dict[str, float] | None
    weighting_mode: str | None = None
    baseline_scores: dict | None = None
    weighting_comparison: dict | None = None
    silhouette_scores_by_k: dict | None = None
    failure_tags: dict | None = None
    centroid_composition: dict | None = None
    penalties_applied: dict | None = None
    cap_status: dict | None = None
    final_scores: dict | list | None = None
    case_citation_metadata: dict | None = None
    judge_panel: dict | None = None
    judge_votes: dict | None = None
    zak_review_flag: dict | None = None
    variation_scores: dict | list | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalysisRunRequest(BaseModel):
    judge_models: list[str] | None = None
