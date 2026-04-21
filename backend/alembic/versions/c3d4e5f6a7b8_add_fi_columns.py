"""add_fi_columns

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-20 00:00:00.000000

Changes:
- rubrics: add 13 FrankInstructions columns:
    10 FI pipeline data columns (screening_result, source_extraction,
    gold_packet_mapping, doctrine_pack, routing_metadata,
    predicted_failure_modes, gold_answer, generated_question,
    self_audit_result, question_analysis)
    3 HITL gate columns (fi_status, fi_stream_id, review_notes)
- analyses: add failure_tags (JSON) for FI failure-mode and metadata tagging
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- rubrics: FI pipeline data columns ---
    op.add_column("rubrics", sa.Column("screening_result", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("source_extraction", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("gold_packet_mapping", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("doctrine_pack", sa.Text(), nullable=True))
    op.add_column("rubrics", sa.Column("routing_metadata", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("predicted_failure_modes", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("gold_answer", sa.Text(), nullable=True))
    op.add_column("rubrics", sa.Column("generated_question", sa.Text(), nullable=True))
    op.add_column("rubrics", sa.Column("self_audit_result", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("question_analysis", sa.JSON(), nullable=True))

    # --- rubrics: HITL gate columns ---
    op.add_column("rubrics", sa.Column("fi_status", sa.Text(), nullable=True))
    op.add_column("rubrics", sa.Column("fi_stream_id", sa.Text(), nullable=True))
    op.add_column("rubrics", sa.Column("review_notes", sa.Text(), nullable=True))

    # --- analyses: FI failure-mode tagging ---
    op.add_column("analyses", sa.Column("failure_tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "failure_tags")

    op.drop_column("rubrics", "review_notes")
    op.drop_column("rubrics", "fi_stream_id")
    op.drop_column("rubrics", "fi_status")

    op.drop_column("rubrics", "question_analysis")
    op.drop_column("rubrics", "self_audit_result")
    op.drop_column("rubrics", "generated_question")
    op.drop_column("rubrics", "gold_answer")
    op.drop_column("rubrics", "predicted_failure_modes")
    op.drop_column("rubrics", "routing_metadata")
    op.drop_column("rubrics", "doctrine_pack")
    op.drop_column("rubrics", "gold_packet_mapping")
    op.drop_column("rubrics", "source_extraction")
    op.drop_column("rubrics", "screening_result")
