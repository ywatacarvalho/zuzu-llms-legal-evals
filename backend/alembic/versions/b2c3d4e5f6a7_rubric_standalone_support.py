"""rubric_standalone_support

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-18 12:00:00.000000

Changes:
- rubrics: make evaluation_id nullable, change ondelete to SET NULL
- rubrics: add case_id (FK to legal_cases), question (Text), status (Text)
- Enables standalone rubric creation decoupled from evaluations
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make evaluation_id nullable and change ondelete behavior
    op.alter_column("rubrics", "evaluation_id", existing_type=sa.Uuid(), nullable=True)
    op.drop_constraint("rubrics_evaluation_id_fkey", "rubrics", type_="foreignkey")
    op.create_foreign_key(
        "rubrics_evaluation_id_fkey",
        "rubrics",
        "evaluations",
        ["evaluation_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add standalone rubric fields
    op.add_column(
        "rubrics",
        sa.Column(
            "case_id",
            sa.Uuid(),
            sa.ForeignKey("legal_cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("rubrics", sa.Column("question", sa.Text(), nullable=True))
    op.add_column(
        "rubrics",
        sa.Column("status", sa.Text(), nullable=False, server_default="building"),
    )
    op.create_index("ix_rubrics_case_id", "rubrics", ["case_id"])

    # Backfill existing rubrics: mark as frozen (they are already frozen)
    op.execute(sa.text("UPDATE rubrics SET status = 'frozen' WHERE is_frozen = true"))
    op.execute(sa.text("UPDATE rubrics SET status = 'building' WHERE is_frozen = false"))

    # Backfill question from evaluation for existing rubrics
    op.execute(
        sa.text(
            "UPDATE rubrics SET question = e.question, case_id = e.case_id "
            "FROM evaluations e WHERE rubrics.evaluation_id = e.id"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_rubrics_case_id", "rubrics")
    op.drop_column("rubrics", "status")
    op.drop_column("rubrics", "question")
    op.drop_column("rubrics", "case_id")

    # Restore evaluation_id as NOT NULL with CASCADE
    # NOTE: This will fail if any rubrics have NULL evaluation_id
    op.drop_constraint("rubrics_evaluation_id_fkey", "rubrics", type_="foreignkey")
    op.create_foreign_key(
        "rubrics_evaluation_id_fkey",
        "rubrics",
        "evaluations",
        ["evaluation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("rubrics", "evaluation_id", existing_type=sa.Uuid(), nullable=False)
