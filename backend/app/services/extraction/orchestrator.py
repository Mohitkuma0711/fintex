from pydantic import BaseModel

from app.core.config import Settings
from app.services.extraction.errors import ExtractionError
from app.services.extraction.gemini import GeminiExtractor, extraction_schema, prompt_for_document
from app.services.extraction.strategy import select_extraction_input
from app.services.storage.supabase_storage import SupabaseStorage


class ExtractionOrchestrator:
    def __init__(self, settings: Settings, storage: SupabaseStorage) -> None:
        self.settings = settings
        self.storage = storage
        self.gemini = GeminiExtractor(settings)

    async def extract(
        self,
        *,
        object_path: str,
        mime_type: str,
        document_type: str,
        content: bytes | None = None,
    ) -> tuple[BaseModel, str]:
        try:
            schema = extraction_schema(document_type)
            _prompt, prompt_version = prompt_for_document(document_type)
        except ExtractionError:
            raise
        document_content = (
            content if content is not None else await self.storage.download(object_path)
        )
        source = select_extraction_input(
            document_content,
            mime_type,
            self.settings.extraction_max_pdf_pages,
        )
        result = await self.gemini.extract(
            document_type=document_type,
            mime_type=source.mime_type,
            schema=schema,
            pages=source.pages,
            document_bytes=source.document_bytes,
        )
        return result, prompt_version
