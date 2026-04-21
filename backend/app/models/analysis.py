import uuid

from sqlalchemy import JSON, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Analysis(Base, TimestampMixin):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    k: Mapped[int] = mapped_column(Integer, nullable=False)
    clusters: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    centroid_indices: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    scores: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    winning_cluster: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_shares: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    weighting_mode: Mapped[str | None] = mapped_column(Text, nullable=True)
    baseline_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    weighting_comparison: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    silhouette_scores_by_k: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # FrankInstructions failure-mode and metadata tagging per centroid
    failure_tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Centroid composition (Dasha Phase 2A)
    centroid_composition: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Dasha scoring layer (Phase 6)
    penalties_applied: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cap_status: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    final_scores: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    case_citation_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Judge panel (Phase 8)
    judge_panel: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    judge_votes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Zak escalation (Phase 9)
    zak_review_flag: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Dual-track scoring (Phase 5)
    variation_scores: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
