"""Persist verified extraction values and the confirmed taxpayer profile.

Revision ID: 0003_confirmed
Revises: 0002_extraction
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_confirmed"
down_revision: str | None = "0002_extraction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "extraction_results",
        sa.Column("confirmed_profile", sa.JSON(), nullable=True),
    )
    op.add_column(
        "extraction_results",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("confirmed_profile", sa.JSON(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("profile_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "profile_confirmed_at")
    op.drop_column("users", "confirmed_profile")
    op.drop_column("extraction_results", "confirmed_at")
    op.drop_column("extraction_results", "confirmed_profile")
