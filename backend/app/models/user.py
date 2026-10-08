from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampSoftDelete, UUIDPrimaryKey


class User(UUIDPrimaryKey, TimestampSoftDelete, Base):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    preferred_financial_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confirmed_profile: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    profile_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
