"""Persist suggestion identities, rule versions, and user plans.

Revision ID: 0004_suggestion_plans
Revises: 0003_confirmed
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_suggestion_plans"
down_revision: str | None = "0003_confirmed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("suggestions", sa.Column("suggestion_key", sa.String(40), nullable=True))
    op.add_column("suggestions", sa.Column("financial_year", sa.String(20), nullable=True))
    op.add_column("suggestions", sa.Column("rules_version", sa.String(80), nullable=True))
    op.add_column(
        "suggestions",
        sa.Column("planned_to_do", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index(
        "uq_suggestions_user_year_rules_key",
        "suggestions",
        ["user_id", "financial_year", "rules_version", "suggestion_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_suggestions_user_year_rules_key", table_name="suggestions")
    op.drop_column("suggestions", "planned_to_do")
    op.drop_column("suggestions", "rules_version")
    op.drop_column("suggestions", "financial_year")
    op.drop_column("suggestions", "suggestion_key")
