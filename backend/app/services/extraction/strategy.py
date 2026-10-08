from dataclasses import dataclass
from io import BytesIO

import pdfplumber

from app.services.extraction.errors import ExtractionError, ExtractionErrorCode


@dataclass(frozen=True)
class ExtractionInput:
    strategy: str
    mime_type: str
    pages: list[tuple[int, str]] | None = None
    document_bytes: bytes | None = None


def select_extraction_input(content: bytes, mime_type: str, max_pages: int) -> ExtractionInput:
    if mime_type != "application/pdf":
        return ExtractionInput(
            strategy="gemini_multimodal",
            mime_type=mime_type,
            document_bytes=content,
        )
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            if len(pdf.pages) > max_pages:
                raise ExtractionError(
                    ExtractionErrorCode.UNSUPPORTED_DOCUMENT,
                    "PDF contains more pages than the configured extraction limit.",
                )
            pages = [
                (number, (page.extract_text() or "").strip())
                for number, page in enumerate(pdf.pages, start=1)
            ]
    except ExtractionError:
        raise
    except Exception as error:
        raise ExtractionError(
            ExtractionErrorCode.UNSUPPORTED_DOCUMENT, "PDF could not be safely parsed."
        ) from error
    if any(text for _, text in pages):
        return ExtractionInput(
            strategy="pdfplumber_text",
            mime_type=mime_type,
            pages=[(number, text) for number, text in pages if text],
        )
    return ExtractionInput(
        strategy="gemini_multimodal",
        mime_type=mime_type,
        document_bytes=content,
    )
