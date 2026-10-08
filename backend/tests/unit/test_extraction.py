import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.schemas.extraction import Form16Extraction
from app.services.extraction import gemini
from app.services.extraction.errors import ExtractionError, ExtractionErrorCode
from app.services.extraction.strategy import select_extraction_input

FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "documents" / "synthetic_form16_extraction.json"
)
FORM16_RESPONSE = FIXTURE_PATH.read_text(encoding="utf-8")


class FakeModels:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = iter(outcomes)
        self.calls = 0

    async def generate_content(self, **_kwargs: object) -> SimpleNamespace:
        self.calls += 1
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome)


class FakeAioClient:
    def __init__(self, models: FakeModels) -> None:
        self.models = models

    async def __aenter__(self) -> "FakeAioClient":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


class FakeGenAIClient:
    def __init__(self, models: FakeModels) -> None:
        self.aio = FakeAioClient(models)


@pytest.mark.asyncio
async def test_gemini_retries_timeouts_then_validates_structured_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    models = FakeModels([TimeoutError(), FORM16_RESPONSE])
    monkeypatch.setattr(gemini.genai, "Client", lambda **_kwargs: FakeGenAIClient(models))

    async def skip_delay(_seconds: float) -> None:
        return None

    monkeypatch.setattr(gemini.asyncio, "sleep", skip_delay)
    result = await gemini.GeminiExtractor(Settings(google_api_key="test-key")).extract(
        document_type="form16",
        mime_type="image/png",
        schema=Form16Extraction,
        document_bytes=b"\x89PNG",
    )

    assert isinstance(result, Form16Extraction)
    assert result.gross_salary.value == "12345"
    assert models.calls == 2


@pytest.mark.asyncio
async def test_gemini_rejects_malformed_structured_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    models = FakeModels(["{}"])
    monkeypatch.setattr(gemini.genai, "Client", lambda **_kwargs: FakeGenAIClient(models))

    with pytest.raises(ExtractionError) as error:
        await gemini.GeminiExtractor(Settings(google_api_key="test-key")).extract(
            document_type="form16",
            mime_type="image/png",
            schema=Form16Extraction,
            document_bytes=b"\x89PNG",
        )

    assert error.value.code == ExtractionErrorCode.INVALID_RESPONSE
    assert models.calls == 1


@pytest.mark.asyncio
async def test_gemini_fails_explicitly_when_not_configured() -> None:
    with pytest.raises(ExtractionError) as error:
        await gemini.GeminiExtractor(Settings()).extract(
            document_type="form16",
            mime_type="image/png",
            schema=Form16Extraction,
            document_bytes=b"\x89PNG",
        )

    assert error.value.code == ExtractionErrorCode.NOT_CONFIGURED


def test_pdf_strategy_uses_page_labelled_text(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePDF:
        pages = [
            SimpleNamespace(extract_text=lambda: "salary statement"),
            SimpleNamespace(extract_text=lambda: None),
        ]

        def __enter__(self) -> "FakePDF":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr("app.services.extraction.strategy.pdfplumber.open", lambda _file: FakePDF())

    result = select_extraction_input(b"%PDF-test", "application/pdf", max_pages=2)

    assert result.strategy == "pdfplumber_text"
    assert result.pages == [(1, "salary statement")]


def test_pdf_strategy_rejects_page_count_above_configured_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePDF:
        pages = [SimpleNamespace(extract_text=lambda: "page")] * 2

        def __enter__(self) -> "FakePDF":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr("app.services.extraction.strategy.pdfplumber.open", lambda _file: FakePDF())

    with pytest.raises(ExtractionError) as error:
        select_extraction_input(b"%PDF-test", "application/pdf", max_pages=1)

    assert error.value.code == ExtractionErrorCode.UNSUPPORTED_DOCUMENT


def test_image_strategy_passes_bytes_to_multimodal_model() -> None:
    content = b"synthetic image bytes"
    result = select_extraction_input(content, "image/png", max_pages=50)

    assert result.strategy == "gemini_multimodal"
    assert result.document_bytes == content


def test_fixture_is_synthetic_json() -> None:
    assert json.loads(FORM16_RESPONSE)["gross_salary"]["value"] == "12345"
