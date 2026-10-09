from uuid import UUID

import firebase_admin
import structlog
from firebase_admin import storage as firebase_storage

from app.core.config import Settings
from app.services.extraction.errors import ExtractionError, ExtractionErrorCode

logger = structlog.get_logger(__name__)

_ALLOWED_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png"]


def _get_bucket(bucket_name: str | None):
    if not firebase_admin._apps:
        raise ExtractionError(
            ExtractionErrorCode.STORAGE_UNAVAILABLE,
            "Firebase not initialized.",
        )
    return firebase_storage.bucket(bucket_name)


class FirebaseStorage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def object_path(user_id: UUID, document_id: UUID, extension: str) -> str:
        return f"{user_id}/{document_id}.{extension}"

    async def ensure_bucket(self) -> None:
        try:
            bucket = _get_bucket(self.settings.firebase_storage_bucket)
            bucket.reload()
        except Exception as error:
            logger.warning("firebase_bucket_check_failed", error_type=type(error).__name__)
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Firebase Storage bucket is unavailable.",
            ) from error

    async def upload(self, object_path: str, content: bytes, mime_type: str) -> None:
        await self.ensure_bucket()
        try:
            bucket = _get_bucket(self.settings.firebase_storage_bucket)
            blob = bucket.blob(object_path)
            blob.upload_from_string(
                content,
                content_type=mime_type,
            )
        except Exception as error:
            logger.warning("firebase_upload_failed", error_type=type(error).__name__)
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Document upload to Firebase Storage failed.",
            ) from error

    async def download(self, object_path: str) -> bytes:
        await self.ensure_bucket()
        try:
            bucket = _get_bucket(self.settings.firebase_storage_bucket)
            blob = bucket.blob(object_path)
            content = blob.download_as_bytes()
            return content
        except Exception as error:
            logger.warning("firebase_download_failed", error_type=type(error).__name__)
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Document could not be retrieved from Firebase Storage.",
            ) from error

    async def delete(self, object_path: str) -> None:
        await self.ensure_bucket()
        try:
            bucket = _get_bucket(self.settings.firebase_storage_bucket)
            blob = bucket.blob(object_path)
            blob.delete()
        except Exception as error:
            logger.warning("firebase_delete_failed", error_type=type(error).__name__)
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Document could not be removed from Firebase Storage.",
            ) from error

    async def create_signed_url(self, object_path: str) -> str:
        await self.ensure_bucket()
        try:
            bucket = _get_bucket(self.settings.firebase_storage_bucket)
            blob = bucket.blob(object_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=self.settings.storage_signed_url_ttl_seconds,
            )
            return url
        except Exception as error:
            logger.warning("firebase_sign_failed", error_type=type(error).__name__)
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "A private document link could not be created.",
            ) from error
