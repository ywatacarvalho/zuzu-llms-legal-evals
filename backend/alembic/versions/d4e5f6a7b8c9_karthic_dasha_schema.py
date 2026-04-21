"""karthic_dasha_schema

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-20 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- rubrics: controller card, variation, dual-rubric, and citation metadata ---
    op.add_column("rubrics", sa.Column("controller_card", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("controller_card_version", sa.Text(), nullable=True))
    op.add_column("rubrics", sa.Column("selected_lane_code", sa.Text(), nullable=True))
    op.add_column(
        "rubrics",
        sa.Column(
            "dual_rubric_mode",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("rubrics", sa.Column("base_question", sa.Text(), nullable=True))
    op.add_column("rubrics", sa.Column("base_gold_answer", sa.Text(), nullable=True))
    op.add_column("rubrics", sa.Column("variation_question", sa.Text(), nullable=True))
    op.add_column("rubrics", sa.Column("variation_criteria", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("workflow_source_case_name", sa.Text(), nullable=True))
    op.add_column("rubrics", sa.Column("workflow_source_case_citation", sa.Text(), nullable=True))
    op.add_column(
        "rubrics",
        sa.Column(
            "case_citation_verification_mode",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "ix_rubrics_selected_lane_code",
        "rubrics",
        ["selected_lane_code"],
        unique=False,
    )
    op.create_index(
        "ix_rubrics_dual_rubric_mode",
        "rubrics",
        ["dual_rubric_mode"],
        unique=False,
    )

    # --- analyses: Dasha outputs, overlays/caps, judge panel, and dual-track scores ---
    op.add_column("analyses", sa.Column("centroid_composition", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("penalties_applied", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("cap_status", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("final_scores", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("case_citation_metadata", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("judge_panel", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("judge_votes", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("zak_review_flag", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("variation_scores", sa.JSON(), nullable=True))

    # --- model responses: identify base-question vs variation-question responses ---
    op.add_column(
        "model_responses",
        sa.Column(
            "question_version",
            sa.Text(),
            nullable=False,
            server_default="base",
        ),
    )


def downgrade() -> None:
    op.drop_column("model_responses", "question_version")

    op.drop_column("analyses", "variation_scores")
    op.drop_column("analyses", "zak_review_flag")
    op.drop_column("analyses", "judge_votes")
    op.drop_column("analyses", "judge_panel")
    op.drop_column("analyses", "case_citation_metadata")
    op.drop_column("analyses", "final_scores")
    op.drop_column("analyses", "cap_status")
    op.drop_column("analyses", "penalties_applied")
    op.drop_column("analyses", "centroid_composition")

    op.drop_index("ix_rubrics_dual_rubric_mode", table_name="rubrics")
    op.drop_index("ix_rubrics_selected_lane_code", table_name="rubrics")
    op.drop_column("rubrics", "case_citation_verification_mode")
    op.drop_column("rubrics", "workflow_source_case_citation")
    op.drop_column("rubrics", "workflow_source_case_name")
    op.drop_column("rubrics", "variation_criteria")
    op.drop_column("rubrics", "variation_question")
    op.drop_column("rubrics", "base_gold_answer")
    op.drop_column("rubrics", "base_question")
    op.drop_column("rubrics", "dual_rubric_mode")
    op.drop_column("rubrics", "selected_lane_code")
    op.drop_column("rubrics", "controller_card_version")
    op.drop_column("rubrics", "controller_card")
