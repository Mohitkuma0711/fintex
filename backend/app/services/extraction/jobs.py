from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.pii import mask_pan
from app.models import ExtractionResult
from app.repositories.documents import DocumentRepository
from app.services.extraction.errors import ExtractionError, ExtractionErrorCode
from app.services.extraction.orchestrator import ExtractionOrchestrator
from app.services.extraction.virus_scan import VirusScanner, scan_document
from app.services.storage.supabase_storage import SupabaseStorage

logger = structlog.get_logger(__name__)


class ExtractionJob:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage: SupabaseStorage,
        orchestrator: ExtractionOrchestrator,
        virus_scanner: VirusScanner,
    ) -> None:
        self.session_factory = session_factory
        self.storage = storage
        self.orchestrator = orchestrator
        self.virus_scanner = virus_scanner

    async def run(self, document_id: UUID) -> None:
        try:
            await self._run(document_id)
        except ExtractionError as error:
            async with self.session_factory() as session:
                document = await DocumentRepository(session).get_by_id(document_id)
                if document is not None:
                    await DocumentRepository(session).update(
                        document,
                        status="failed",
                        extraction_error_code=error.code.value,
                    )
            logger.warning(
                "document_extraction_failed",
                document_id=str(document_id),
                error_code=error.code.value,
            )
        except Exception as error:
            async with self.session_factory() as session:
                document = await DocumentRepository(session).get_by_id(document_id)
                if document is not None:
                    await DocumentRepository(session).update(
                        document,
                        status="failed",
                        extraction_error_code=ExtractionErrorCode.INTERNAL_ERROR.value,
                    )
            logger.error(
                "document_extraction_failed",
                document_id=str(document_id),
                error_type=type(error).__name__,
            )

    async def _run(self, document_id: UUID) -> None:
        async with self.session_factory() as session:
            repository = DocumentRepository(session)
            document = await repository.get_by_id(document_id)
            if document is None:
                return
            document = await repository.update(
                document,
                status="processing",
                extraction_error_code=None,
            )
            user_id = document.user_id
            object_path = document.storage_path
            mime_type = document.content_type
            document_type = document.document_type

        content = await self.storage.download(object_path)
        scan_status = await scan_document(self.virus_scanner, document_id, content)
        if scan_status not in {"clean", "not_scanned"}:
            async with self.session_factory() as session:
                document = await DocumentRepository(session).get_by_id(document_id)
                if document is not None:
                    await DocumentRepository(session).update(
                        document,
                        scan_status=scan_status,
                        extraction_error_code=ExtractionErrorCode.VIRUS_DETECTED.value,
                    )
            raise ExtractionError(
                ExtractionErrorCode.VIRUS_DETECTED,
                "The document did not pass the configured virus scanner.",
            )
        result, prompt_version = await self.orchestrator.extract(
            object_path=object_path,
            mime_type=mime_type,
            document_type=document_type,
            content=content,
        )
        result_payload: dict[str, Any] = result.model_dump(mode="json")
        pan_field = result_payload.get("employee_pan")
        if isinstance(pan_field, dict) and isinstance(pan_field.get("value"), str):
            pan_field["value"] = mask_pan(pan_field["value"])
        model_version = self.orchestrator.settings.gemini_model

        async with self.session_factory() as session:
            repository = DocumentRepository(session)
            document = await repository.get_by_id(document_id)
            if document is None or document.user_id != user_id:
                return
            await repository.add_extraction(
                ExtractionResult(
                    document_id=document_id,
                    extraction_type=document_type,
                    model_version=model_version,
                    prompt_version=prompt_version,
                    payload=result_payload,
                )
            )
            await repository.update(
                document,
                status="extracted",
                scan_status=scan_status,
                extraction_error_code=None,
            )
