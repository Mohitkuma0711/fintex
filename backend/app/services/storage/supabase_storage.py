from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import UUID

import httpx
import structlog

from app.core.config import Settings
from app.services.extraction.errors import ExtractionError, ExtractionErrorCode

logger = structlog.get_logger(__name__)

_ALLOWED_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png"]


class SupabaseStorage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        key = self.settings.supabase_service_role_key or self.settings.supabase_anon_key
        if not self.settings.supabase_url or key is None:
            raise ExtractionError(
                ExtractionErrorCode.NOT_CONFIGURED, "Private document storage is not configured."
            )
        secret = key.get_secret_value()
        return {"apikey": secret, "Authorization": f"Bearer {secret}"}

    def object_url(self, object_path: str) -> str:
        parts = PurePosixPath(object_path).parts
        if not parts or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("Invalid private storage object path")
        safe_path = quote("/".join(parts), safe="/")
        return (
            f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/"
            f"{self.settings.supabase_storage_bucket}/{safe_path}"
        )

    async def ensure_private_bucket(self) -> None:
        headers = self._headers()
        base_url = f"{self.settings.supabase_url.rstrip('/')}/storage/v1/bucket"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{base_url}/{self.settings.supabase_storage_bucket}",
                    headers=headers,
                )
                if response.status_code == 404:
                    created = await client.post(
                        base_url,
                        json={
                            "id": self.settings.supabase_storage_bucket,
                            "name": self.settings.supabase_storage_bucket,
                            "public": False,
                            "file_size_limit": self.settings.max_upload_size_bytes,
                            "allowed_mime_types": _ALLOWED_MIME_TYPES,
                        },
                        headers=headers,
                    )
                    created.raise_for_status()
                    return
                response.raise_for_status()
                bucket = response.json()
                if not isinstance(bucket, dict) or bucket.get("public") is not False:
                    raise ExtractionError(
                        ExtractionErrorCode.STORAGE_UNAVAILABLE,
                        "The configured Supabase Storage bucket must be private.",
                    )
        except ExtractionError:
            raise
        except httpx.HTTPStatusError as error:
            logger.warning(
                "private_storage_bucket_check_failed",
                status_code=error.response.status_code,
            )
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Private document storage is unavailable.",
            ) from error
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("private_storage_bucket_check_failed", error_type=type(error).__name__)
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Private document storage is unavailable.",
            ) from error

    async def upload(self, object_path: str, content: bytes, mime_type: str) -> None:
        await self.ensure_private_bucket()
        headers = self._headers()
        headers.update({"Content-Type": mime_type, "x-upsert": "false"})
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    self.object_url(object_path),
                    content=content,
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as error:
            logger.warning(
                "private_storage_upload_failed",
                status_code=error.response.status_code,
            )
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Document upload to private storage failed.",
            ) from error
        except httpx.HTTPError as error:
            logger.warning("private_storage_upload_failed", error_type=type(error).__name__)
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Document upload to private storage failed.",
            ) from error

    async def download(self, object_path: str) -> bytes:
        headers = self._headers()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(self.object_url(object_path), headers=headers)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as error:
            logger.warning("private_storage_download_failed", error_type=type(error).__name__)
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Document could not be retrieved from private storage.",
            ) from error

    async def delete(self, object_path: str) -> None:
        headers = self._headers()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.delete(
                    (
                        f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/"
                        f"{self.settings.supabase_storage_bucket}"
                    ),
                    json={"prefixes": [object_path]},
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning("private_storage_delete_failed", error_type=type(error).__name__)
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Document could not be removed from private storage.",
            ) from error

    async def create_signed_url(self, object_path: str) -> str:
        headers = self._headers()
        try:
            object_url = self.object_url(object_path)
            path_segment = "/storage/v1/object/"
            encoded_path = object_url.split(path_segment, maxsplit=1)[1]
            _bucket, encoded_path = encoded_path.split("/", maxsplit=1)
            sign_url = (
                f"{self.settings.supabase_url.rstrip('/')}/storage/v1/object/sign/"
                f"{self.settings.supabase_storage_bucket}/{encoded_path}"
            )
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    sign_url,
                    json={"expiresIn": self.settings.storage_signed_url_ttl_seconds},
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
                signed_path = payload.get("signedURL")
                if not isinstance(signed_path, str):
                    raise ValueError("Missing signed URL")
        except httpx.HTTPStatusError as error:
            logger.warning(
                "private_storage_sign_failed",
                status_code=error.response.status_code,
            )
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "A private document link could not be created.",
            ) from error
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("private_storage_sign_failed", error_type=type(error).__name__)
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "A private document link could not be created.",
            ) from error

        if signed_path.startswith("http://") or signed_path.startswith("https://"):
            return signed_path
        return self.settings.supabase_url.rstrip("/") + (
            signed_path if signed_path.startswith("/") else f"/{signed_path}"
        )

    @staticmethod
    def object_path(user_id: UUID, document_id: UUID, extension: str) -> str:
        return f"{user_id}/{document_id}.{extension}"
