"""Add private upload and extraction workflow metadata.

Revision ID: 0002_extraction
Revises: 0001_initial
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_extraction"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("document_type", sa.String(32), server_default="form16", nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column("scan_status", sa.String(32), server_default="not_scanned", nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column("extraction_error_code", sa.String(60), nullable=True),
    )
    op.add_column(
        "extraction_results",
        sa.Column("extraction_type", sa.String(32), server_default="form16", nullable=False),
    )
    op.add_column(
        "extraction_results",
        sa.Column("model_version", sa.String(100), server_default="unknown", nullable=False),
    )
    op.add_column(
        "extraction_results",
        sa.Column("prompt_version", sa.String(50), server_default="unknown", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("extraction_results", "prompt_version")
    op.drop_column("extraction_results", "model_version")
    op.drop_column("extraction_results", "extraction_type")
    op.drop_column("documents", "extraction_error_code")
    op.drop_column("documents", "scan_status")
    op.drop_column("documents", "document_type")
