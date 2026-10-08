from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampSoftDelete, UUIDPrimaryKey


class Suggestion(UUIDPrimaryKey, TimestampSoftDelete, Base):
    __tablename__ = "suggestions"
    __table_args__ = (
        Index(
            "uq_suggestions_user_year_rules_key",
            "user_id",
            "financial_year",
            "rules_version",
            "suggestion_key",
            unique=True,
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    tax_computation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tax_computations.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    suggestion_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    financial_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rules_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    planned_to_do: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
