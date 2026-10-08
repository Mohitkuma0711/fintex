from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampSoftDelete, UUIDPrimaryKey


class Document(UUIDPrimaryKey, TimestampSoftDelete, Base):
    __tablename__ = "documents"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    document_type: Mapped[str] = mapped_column(String(32), nullable=False, default="form16")
    scan_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_scanned")
    extraction_error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
