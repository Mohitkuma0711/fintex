from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.pii import mask_pan, mask_pans_in_text
from app.models import Document, User
from app.repositories.documents import DocumentRepository
from app.schemas.extraction import (
    DocumentExtractionResponse,
    DocumentUploadResponse,
    Form16Extraction,
    SalarySlipExtraction,
)
from app.services.extraction.errors import ExtractionError
from app.services.storage.firebase_storage import FirebaseStorage

_FILE_TYPES = {
    ".pdf": ("application/pdf", "pdf"),
    ".jpg": ("image/jpeg", "jpg"),
    ".jpeg": ("image/jpeg", "jpg"),
    ".png": ("image/png", "png"),
}


def detect_document_type(content: bytes) -> tuple[str, str]:
    if b"%PDF-" in content[:1024]:
        return "application/pdf", "pdf"
    if (
        content.startswith(b"\x89PNG\r\n\x1a\n")
        and len(content) >= 24
        and content[12:16] == b"IHDR"
    ):
        return "image/png", "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Only valid PDF, JPG, and PNG documents are accepted.",
    )


class DocumentService:
    def __init__(self, session: AsyncSession, settings: Settings, storage: FirebaseStorage) -> None:
        self.repository = DocumentRepository(session)
        self.settings = settings
        self.storage = storage

    async def list(self, user: User) -> list[Document]:
        return await self.repository.list_for_user(user.id)

    async def upload(
        self,
        *,
        user: User,
        file_name: str,
        declared_content_type: str,
        content: bytes,
        document_type: str,
        auto_delete_after_30_days: bool = False,
    ) -> tuple[DocumentUploadResponse, Document]:
        if len(content) > self.settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Document exceeds the upload size limit.",
            )
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded document is empty."
            )
        safe_name = mask_pans_in_text(PurePosixPath(file_name.replace("\\", "/")).name)
        if (
            not safe_name
            or len(safe_name) > 255
            or any(ord(character) < 32 for character in safe_name)
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Document filename is invalid.",
            )
        try:
            detected_content_type, extension = detect_document_type(content)
        except HTTPException:
            raise
        declared_extension = PurePosixPath(safe_name).suffix.lower()
        expected_type = _FILE_TYPES.get(declared_extension)
        if (
            expected_type is None
            or expected_type[0] != detected_content_type
            or declared_content_type.lower() != detected_content_type
        ):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Document extension, media type, and file signature must match.",
            )

        document_id = uuid4()
        object_path = FirebaseStorage.object_path(user.id, document_id, extension)
        await self.storage.upload(object_path, content, detected_content_type)
        try:
            signed_url = await self.storage.create_signed_url(object_path)
        except ExtractionError:
            await self.storage.delete(object_path)
            raise
        document = Document(
            id=document_id,
            user_id=user.id,
            file_name=safe_name,
            storage_path=object_path,
            content_type=detected_content_type,
            size_bytes=len(content),
            status="pending",
            document_type=document_type,
            scan_status="not_scanned",
            auto_delete_at=(
                datetime.now(UTC) + timedelta(days=30) if auto_delete_after_30_days else None
            ),
        )
        try:
            document = await self.repository.add(document)
        except SQLAlchemyError:
            await self.storage.delete(object_path)
            raise

        response = DocumentUploadResponse(
            id=document.id,
            file_name=document.file_name,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            document_type=document.document_type,
            status=document.status,
            scan_status=document.scan_status,
            signed_url=signed_url,
            signed_url_expires_in=self.settings.storage_signed_url_ttl_seconds,
            auto_delete_at=(
                document.auto_delete_at.isoformat() if document.auto_delete_at else None
            ),
        )
        return response, document

    async def get_extraction(self, user: User, document_id: UUID) -> DocumentExtractionResponse:
        document = await self.repository.get_for_user(document_id, user.id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        extraction_model = (
            Form16Extraction if document.document_type == "form16" else SalarySlipExtraction
        )
        extraction = await self.repository.get_extraction_for_document(document.id)
        if extraction:
            payload_data = dict(extraction.payload)
            pan_field = payload_data.get("employee_pan")
            if isinstance(pan_field, dict) and isinstance(pan_field.get("value"), str):
                pan_field["value"] = mask_pan(pan_field["value"])
            payload = extraction_model.model_validate(payload_data)
        else:
            payload = None
        return DocumentExtractionResponse(
            id=document.id,
            extraction_id=extraction.id if extraction else None,
            file_name=mask_pans_in_text(document.file_name),
            document_type=document.document_type,
            status=document.status,
            scan_status=document.scan_status,
            extraction=payload,
            error_code=document.extraction_error_code,
        )

    async def retry_extraction(self, user: User, document_id: UUID) -> Document:
        document = await self.repository.get_for_user(document_id, user.id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        if document.status != "failed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only failed document extractions can be retried.",
            )
        return await self.repository.update(
            document,
            status="pending",
            extraction_error_code=None,
        )

    async def delete(self, user: User, document_id: UUID) -> None:
        document = await self.repository.get_for_user(document_id, user.id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        await self.storage.delete(document.storage_path)
        await self.repository.soft_delete(document)
