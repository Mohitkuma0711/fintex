"""Add opt-in document auto-deletion timestamps.

Revision ID: 0005_document_retention
Revises: 0004_suggestion_plans
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_document_retention"
down_revision: str | None = "0004_suggestion_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("auto_delete_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("documents", "auto_delete_at")
