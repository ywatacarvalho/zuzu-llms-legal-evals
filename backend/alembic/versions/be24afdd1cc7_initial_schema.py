"""initial_schema

Revision ID: be24afdd1cc7
Revises:
Create Date: 2026-04-16 22:01:37.617003

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "be24afdd1cc7"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- legal_cases ---
    op.create_table(
        "legal_cases",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- rubrics ---
    op.create_table(
        "rubrics",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("case_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["case_id"], ["legal_cases.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_rubrics_case_id", "rubrics", ["case_id"])

    # --- evaluations ---
    op.create_table(
        "evaluations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("case_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("model_names", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "done", "failed", name="status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["case_id"], ["legal_cases.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_evaluations_case_id", "evaluations", ["case_id"])
    op.create_index("ix_evaluations_status", "evaluations", ["status"])

    # --- model_responses ---
    op.create_table(
        "model_responses",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("evaluation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("run_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_model_responses_evaluation_id", "model_responses", ["evaluation_id"])

    # --- analyses ---
    op.create_table(
        "analyses",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("evaluation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("k", sa.Integer(), nullable=False),
        sa.Column("clusters", sa.JSON(), nullable=True),
        sa.Column("centroid_indices", sa.JSON(), nullable=True),
        sa.Column("scores", sa.JSON(), nullable=True),
        sa.Column("winning_cluster", sa.Integer(), nullable=True),
        sa.Column("model_shares", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_analyses_evaluation_id", "analyses", ["evaluation_id"])


def downgrade() -> None:
    op.drop_table("analyses")
    op.drop_table("model_responses")
    op.drop_table("evaluations")
    op.execute("DROP TYPE IF EXISTS status_enum")
    op.drop_table("rubrics")
    op.drop_table("legal_cases")
    op.drop_table("users")
