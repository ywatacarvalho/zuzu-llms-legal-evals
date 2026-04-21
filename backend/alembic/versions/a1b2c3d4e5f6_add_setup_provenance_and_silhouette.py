"""add_setup_provenance_and_silhouette

Revision ID: a1b2c3d4e5f6
Revises: 0f1a2b3c4d5e
Create Date: 2026-04-18 00:00:00.000000

Changes:
- rubrics: add setup_responses (JSON), strong_reference_text (Text),
  weak_reference_text (Text) — preserves rubric-building inputs for full
  user recoverability
- analyses: add silhouette_scores_by_k (JSON) — records per-k silhouette
  scores from the adaptive sweep so users can audit cluster count selection
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "0f1a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # rubrics: setup-stage provenance
    op.add_column("rubrics", sa.Column("setup_responses", sa.JSON(), nullable=True))
    op.add_column("rubrics", sa.Column("strong_reference_text", sa.Text(), nullable=True))
    op.add_column("rubrics", sa.Column("weak_reference_text", sa.Text(), nullable=True))

    # analyses: silhouette scores per k
    op.add_column("analyses", sa.Column("silhouette_scores_by_k", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "silhouette_scores_by_k")
    op.drop_column("rubrics", "weak_reference_text")
    op.drop_column("rubrics", "strong_reference_text")
    op.drop_column("rubrics", "setup_responses")
