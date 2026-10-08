"""Create core FinTax AI persistence tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    uuid = sa.Uuid(as_uuid=True)
    op.create_table(
        "users",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("preferred_financial_year", sa.String(20), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "documents",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_table(
        "extraction_results",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("document_id", uuid, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_extraction_results_document_id", "extraction_results", ["document_id"])
    op.create_table(
        "tax_computations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("financial_year", sa.String(20), nullable=False),
        sa.Column("rules_version", sa.String(80), nullable=False),
        sa.Column("computation_type", sa.String(20), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_tax_computations_user_id", "tax_computations", ["user_id"])
    op.create_table(
        "suggestions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tax_computation_id", uuid, sa.ForeignKey("tax_computations.id"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_suggestions_user_id", "suggestions", ["user_id"])
    op.create_table(
        "chat_sessions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_table(
        "chat_messages",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("chat_session_id", uuid, sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_chat_messages_chat_session_id", "chat_messages", ["chat_session_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_chat_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
    op.drop_index("ix_suggestions_user_id", table_name="suggestions")
    op.drop_table("suggestions")
    op.drop_index("ix_tax_computations_user_id", table_name="tax_computations")
    op.drop_table("tax_computations")
    op.drop_index("ix_extraction_results_document_id", table_name="extraction_results")
    op.drop_table("extraction_results")
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
