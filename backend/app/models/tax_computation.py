from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampSoftDelete, UUIDPrimaryKey


class TaxComputation(UUIDPrimaryKey, TimestampSoftDelete, Base):
    __tablename__ = "tax_computations"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    financial_year: Mapped[str] = mapped_column(String(20), nullable=False)
    rules_version: Mapped[str] = mapped_column(String(80), nullable=False)
    computation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    result: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
