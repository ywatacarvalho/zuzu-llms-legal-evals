import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Rubric(Base, TimestampMixin):
    __tablename__ = "rubrics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evaluations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legal_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="building")
    criteria: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    decomposition_tree: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    refinement_passes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    stopping_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    conditioning_sample: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_frozen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Setup-stage provenance — saved so users can recover rubric-building inputs
    setup_responses: Mapped[list | None] = mapped_column(JSON, nullable=True)
    strong_reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    weak_reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # FrankInstructions pipeline data
    screening_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_extraction: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    gold_packet_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    doctrine_pack: Mapped[str | None] = mapped_column(Text, nullable=True)
    routing_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    predicted_failure_modes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    gold_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    self_audit_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    question_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # FrankInstructions HITL gate fields
    fi_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    fi_stream_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Locked controller card (Step 2A)
    controller_card: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    controller_card_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Variation / dual-rubric fields
    selected_lane_code: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    dual_rubric_mode: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    base_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_gold_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    variation_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    variation_criteria: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    # Citation verification
    workflow_source_case_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_source_case_citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    case_citation_verification_mode: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
