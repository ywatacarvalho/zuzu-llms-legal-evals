import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis


class AnalysisRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_evaluation_id(self, evaluation_id: uuid.UUID) -> Analysis | None:
        result = await self.db.execute(
            select(Analysis).where(Analysis.evaluation_id == evaluation_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        evaluation_id: uuid.UUID,
        k: int,
        clusters: list[dict],
        centroid_indices: list[int],
        scores: dict[str, float],
        winning_cluster: int,
        model_shares: dict[str, float],
        weighting_mode: str | None = None,
        baseline_scores: dict | None = None,
        weighting_comparison: dict | None = None,
        silhouette_scores_by_k: dict | None = None,
        failure_tags: dict | None = None,
        centroid_composition: dict | None = None,
        penalties_applied: dict | None = None,
        cap_status: dict | None = None,
        final_scores: dict | list | None = None,
        case_citation_metadata: dict | None = None,
        judge_panel: dict | None = None,
        judge_votes: dict | None = None,
        zak_review_flag: dict | None = None,
        variation_scores: dict | list | None = None,
    ) -> Analysis:
        analysis = Analysis(
            evaluation_id=evaluation_id,
            k=k,
            clusters=clusters,
            centroid_indices=centroid_indices,
            scores=scores,
            winning_cluster=winning_cluster,
            model_shares=model_shares,
            weighting_mode=weighting_mode,
            baseline_scores=baseline_scores,
            weighting_comparison=weighting_comparison,
            silhouette_scores_by_k=silhouette_scores_by_k,
            failure_tags=failure_tags,
            centroid_composition=centroid_composition,
            penalties_applied=penalties_applied,
            cap_status=cap_status,
            final_scores=final_scores,
            case_citation_metadata=case_citation_metadata,
            judge_panel=judge_panel,
            judge_votes=judge_votes,
            zak_review_flag=zak_review_flag,
            variation_scores=variation_scores,
        )
        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)
        return analysis

    async def save_analysis(
        self,
        evaluation_id: uuid.UUID,
        k: int,
        clusters: list[dict],
        centroid_indices: list[int],
        scores: dict[str, float],
        winning_cluster: int,
        model_shares: dict[str, float],
        weighting_mode: str | None = None,
        baseline_scores: dict | None = None,
        weighting_comparison: dict | None = None,
        silhouette_scores_by_k: dict | None = None,
        failure_tags: dict | None = None,
        centroid_composition: dict | None = None,
        penalties_applied: dict | None = None,
        cap_status: dict | None = None,
        final_scores: dict | list | None = None,
        case_citation_metadata: dict | None = None,
        judge_panel: dict | None = None,
        judge_votes: dict | None = None,
        zak_review_flag: dict | None = None,
        variation_scores: dict | list | None = None,
    ) -> Analysis:
        """Persist an analysis payload.

        This mirrors ``create`` and gives Agent 3 a stable method name for the
        expanded Dasha output contract.
        """
        return await self.create(
            evaluation_id=evaluation_id,
            k=k,
            clusters=clusters,
            centroid_indices=centroid_indices,
            scores=scores,
            winning_cluster=winning_cluster,
            model_shares=model_shares,
            weighting_mode=weighting_mode,
            baseline_scores=baseline_scores,
            weighting_comparison=weighting_comparison,
            silhouette_scores_by_k=silhouette_scores_by_k,
            failure_tags=failure_tags,
            centroid_composition=centroid_composition,
            penalties_applied=penalties_applied,
            cap_status=cap_status,
            final_scores=final_scores,
            case_citation_metadata=case_citation_metadata,
            judge_panel=judge_panel,
            judge_votes=judge_votes,
            zak_review_flag=zak_review_flag,
            variation_scores=variation_scores,
        )
