import asyncio
from pathlib import Path
from uuid import UUID

from app.core.config import Settings
from app.services.extraction.errors import ExtractionError, ExtractionErrorCode


class LocalStorage:
    """Filesystem-backed storage adapter for local development."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def object_path(user_id: UUID, document_id: UUID, extension: str) -> str:
        return f"{user_id}/{document_id}.{extension}"

    @property
    def base_dir(self) -> Path:
        return Path(self.settings.local_storage_dir).resolve()

    def resolve(self, object_path: str) -> Path:
        target = (self.base_dir / object_path).resolve()
        if not target.is_relative_to(self.base_dir):
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Invalid storage path.",
            )
        return target

    async def ensure_bucket(self) -> None:
        try:
            await asyncio.to_thread(self.base_dir.mkdir, parents=True, exist_ok=True)
        except OSError as error:
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Local storage directory is unavailable.",
            ) from error

    async def upload(self, object_path: str, content: bytes, mime_type: str) -> None:
        del mime_type
        await self.ensure_bucket()
        try:
            target = self.resolve(object_path)
            await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(target.write_bytes, content)
        except ExtractionError:
            raise
        except OSError as error:
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Document upload to local storage failed.",
            ) from error

    async def download(self, object_path: str) -> bytes:
        await self.ensure_bucket()
        try:
            return await asyncio.to_thread(self.resolve(object_path).read_bytes)
        except ExtractionError:
            raise
        except (FileNotFoundError, OSError) as error:
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Document could not be retrieved from local storage.",
            ) from error

    async def delete(self, object_path: str) -> None:
        await self.ensure_bucket()
        try:
            await asyncio.to_thread(self.resolve(object_path).unlink)
        except FileNotFoundError:
            return
        except ExtractionError:
            raise
        except OSError as error:
            raise ExtractionError(
                ExtractionErrorCode.STORAGE_UNAVAILABLE,
                "Document could not be removed from local storage.",
            ) from error

    async def create_signed_url(self, object_path: str) -> str:
        base = self.settings.public_base_url.rstrip("/")
        prefix = self.settings.api_v1_prefix.rstrip("/")
        return f"{base}{prefix}/dev-storage/{object_path}"
