"""lexeval_rrd_v2_schema

Revision ID: 0f1a2b3c4d5e
Revises: be24afdd1cc7
Create Date: 2026-04-17 00:00:00.000000

Changes:
- rubrics: replace case_id FK with evaluation_id FK; add RRD refinement columns
- evaluations: add rubric_id FK (circular, deferred);
  add rubric_building/rubric_frozen status values
- analyses: add weighting_mode, baseline_scores, weighting_comparison columns

Downgrade note: removing ENUM values in PostgreSQL requires recreating the type.
The downgrade for status_enum is documented as a best-effort manual step.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0f1a2b3c4d5e"
down_revision: Union[str, Sequence[str], None] = "be24afdd1cc7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Extend status_enum with new intermediate states ---
    op.execute(sa.text("ALTER TYPE status_enum ADD VALUE IF NOT EXISTS 'rubric_building'"))
    op.execute(sa.text("ALTER TYPE status_enum ADD VALUE IF NOT EXISTS 'rubric_frozen'"))

    # --- rubrics: replace case_id with evaluation_id ---
    op.drop_index("ix_rubrics_case_id", table_name="rubrics")
    op.drop_constraint("rubrics_case_id_fkey", "rubrics", type_="foreignkey")
    op.drop_column("rubrics", "case_id")

    op.add_column("rubrics", sa.Column("evaluation_id", sa.Uuid(as_uuid=True), nullable=False))
    op.create_foreign_key(
        "rubrics_evaluation_id_fkey",
        "rubrics",
        "evaluations",
        ["evaluation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_rubrics_evaluation_id", "rubrics", ["evaluation_id"])

    # --- rubrics: add RRD refinement columns ---
    op.add_column("rubrics", sa.Column("decomposition_tree", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("refinement_passes", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("stopping_metadata", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("conditioning_sample", sa.JSON(), nullable=True))
    op.add_column(
        "rubrics",
        sa.Column("is_frozen", sa.Boolean(), nullable=False, server_default="false"),
    )

    # --- evaluations: add rubric_id (deferred FK to avoid circular dependency at creation) ---
    op.add_column("evaluations", sa.Column("rubric_id", sa.Uuid(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_evaluations_rubric_id",
        "evaluations",
        "rubrics",
        ["rubric_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_evaluations_rubric_id", "evaluations", ["rubric_id"])

    # --- analyses: add weighting comparison columns ---
    op.add_column("analyses", sa.Column("weighting_mode", sa.Text(), nullable=True))
    op.add_column("analyses", sa.Column("baseline_scores", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("weighting_comparison", sa.JSON(), nullable=True))


def downgrade() -> None:
    # analyses
    op.drop_column("analyses", "weighting_comparison")
    op.drop_column("analyses", "baseline_scores")
    op.drop_column("analyses", "weighting_mode")

    # evaluations
    op.drop_index("ix_evaluations_rubric_id", table_name="evaluations")
    op.drop_constraint("fk_evaluations_rubric_id", "evaluations", type_="foreignkey")
    op.drop_column("evaluations", "rubric_id")

    # rubrics: remove new columns
    op.drop_column("rubrics", "is_frozen")
    op.drop_column("rubrics", "conditioning_sample")
    op.drop_column("rubrics", "stopping_metadata")
    op.drop_column("rubrics", "refinement_passes")
    op.drop_column("rubrics", "decomposition_tree")

    # rubrics: restore case_id
    op.drop_index("ix_rubrics_evaluation_id", table_name="rubrics")
    op.drop_constraint("rubrics_evaluation_id_fkey", "rubrics", type_="foreignkey")
    op.drop_column("rubrics", "evaluation_id")

    op.add_column("rubrics", sa.Column("case_id", sa.Uuid(as_uuid=True), nullable=False))
    op.create_foreign_key(
        "rubrics_case_id_fkey",
        "rubrics",
        "legal_cases",
        ["case_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_rubrics_case_id", "rubrics", ["case_id"])

    # NOTE: removing 'rubric_building' and 'rubric_frozen' from status_enum
    # requires recreating the type in PostgreSQL. This is a manual step.
    # ALTER TYPE status_enum RENAME TO status_enum_old;
    # CREATE TYPE status_enum AS ENUM ('pending', 'running', 'done', 'failed');
    # ALTER TABLE evaluations ALTER COLUMN status TYPE status_enum USING status::text::status_enum;
    # DROP TYPE status_enum_old;
