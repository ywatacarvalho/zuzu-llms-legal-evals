import enum
import uuid

from sqlalchemy import JSON, Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class StatusEnum(str, enum.Enum):
    pending = "pending"
    rubric_building = "rubric_building"
    rubric_frozen = "rubric_frozen"
    running = "running"
    done = "done"
    failed = "failed"


class Evaluation(Base, TimestampMixin):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("legal_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rubric_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "rubrics.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_evaluations_rubric_id",
        ),
        nullable=True,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    model_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[StatusEnum] = mapped_column(
        Enum(StatusEnum, name="status_enum"),
        nullable=False,
        default=StatusEnum.pending,
        index=True,
    )
