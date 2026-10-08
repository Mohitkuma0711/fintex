import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import TypeVar

import httpx
import structlog
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.schemas.extraction import Form16Extraction, SalarySlipExtraction
from app.services.extraction.errors import ExtractionError, ExtractionErrorCode

ExtractionSchema = TypeVar("ExtractionSchema", bound=BaseModel)
logger = structlog.get_logger(__name__)
PROMPT_DIRECTORY = Path(__file__).parent / "prompts"
PROMPT_VERSIONS = {
    "form16": ("form16_v1.txt", "form16-v1"),
    "salary_slip": ("salary_slip_v1.txt", "salary-slip-v1"),
}
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def prompt_for_document(document_type: str) -> tuple[str, str]:
    try:
        file_name, version = PROMPT_VERSIONS[document_type]
    except KeyError as error:
        raise ExtractionError(
            ExtractionErrorCode.UNSUPPORTED_DOCUMENT, "Unsupported document type."
        ) from error
    try:
        return (PROMPT_DIRECTORY / file_name).read_text(encoding="utf-8"), version
    except OSError as error:
        logger.error("extraction_prompt_unavailable", document_type=document_type)
        raise ExtractionError(
            ExtractionErrorCode.INTERNAL_ERROR, "Extraction prompt is unavailable."
        ) from error


def extraction_schema(document_type: str) -> type[BaseModel]:
    schemas: dict[str, type[BaseModel]] = {
        "form16": Form16Extraction,
        "salary_slip": SalarySlipExtraction,
    }
    try:
        return schemas[document_type]
    except KeyError as error:
        raise ExtractionError(
            ExtractionErrorCode.UNSUPPORTED_DOCUMENT, "Unsupported document type."
        ) from error


class GeminiExtractor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def extract(
        self,
        *,
        document_type: str,
        mime_type: str,
        schema: type[ExtractionSchema],
        pages: Sequence[tuple[int, str]] | None = None,
        document_bytes: bytes | None = None,
    ) -> ExtractionSchema:
        if self.settings.google_api_key is None:
            raise ExtractionError(
                ExtractionErrorCode.NOT_CONFIGURED, "Gemini extraction is not configured."
            )
        prompt, _prompt_version = prompt_for_document(document_type)
        contents: list[str | types.Part]
        if pages:
            page_text = "\n\n".join(
                f"[Visible text from page {page_number}]\n{text}" for page_number, text in pages
            )
            contents = [prompt, page_text]
        elif document_bytes is not None:
            contents = [prompt, types.Part.from_bytes(data=document_bytes, mime_type=mime_type)]
        else:
            raise ExtractionError(
                ExtractionErrorCode.INVALID_RESPONSE, "No readable document content was supplied."
            )

        client = genai.Client(
            api_key=self.settings.google_api_key.get_secret_value(),
            http_options=types.HttpOptions(
                timeout=self.settings.gemini_timeout_seconds * 1000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        async with client.aio as async_client:
            for attempt in range(self.settings.gemini_max_attempts):
                try:
                    async with asyncio.timeout(self.settings.gemini_timeout_seconds):
                        response = await async_client.models.generate_content(
                            model=self.settings.gemini_model,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_json_schema=schema.model_json_schema(),
                            ),
                        )
                    if not response.text:
                        raise ExtractionError(
                            ExtractionErrorCode.INVALID_RESPONSE,
                            "Gemini returned no structured extraction.",
                        )
                    return schema.model_validate_json(response.text)
                except TimeoutError as error:
                    code = ExtractionErrorCode.TIMEOUT
                    retryable = True
                    cause: Exception = error
                except genai_errors.APIError as error:
                    retryable = error.code in _RETRYABLE_STATUS_CODES
                    code = (
                        ExtractionErrorCode.RATE_LIMITED
                        if error.code == 429
                        else ExtractionErrorCode.PROVIDER_UNAVAILABLE
                    )
                    cause = error
                except httpx.TransportError as error:
                    retryable = True
                    code = ExtractionErrorCode.PROVIDER_UNAVAILABLE
                    cause = error
                except ValidationError as error:
                    raise ExtractionError(
                        ExtractionErrorCode.INVALID_RESPONSE,
                        "Gemini's structured response did not match the extraction schema.",
                    ) from error
                except ExtractionError:
                    raise
                except (ValueError, TypeError) as error:
                    raise ExtractionError(
                        ExtractionErrorCode.INVALID_RESPONSE,
                        "Gemini returned an invalid structured response.",
                    ) from error

                if not retryable or attempt + 1 >= self.settings.gemini_max_attempts:
                    logger.warning("gemini_extraction_failed", code=code.value)
                    raise ExtractionError(
                        code, "Document extraction could not be completed."
                    ) from cause
                await asyncio.sleep(min(0.5 * (2**attempt), 4.0))

        raise ExtractionError(
            ExtractionErrorCode.PROVIDER_UNAVAILABLE, "Document extraction could not be completed."
        )
