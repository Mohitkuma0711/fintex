import json
from datetime import date
from pathlib import Path

import faiss
import numpy as np
import pytest
from pydantic import AnyHttpUrl

from app.core.config import Settings
from app.services.rag.ingest import SourceMetadata, _source_documents, section_chunks
from app.services.rag.retriever import KnowledgeBase, RetrievedChunk


def _source(url: str = "https://www.incometax.gov.in/iec/foportal/help/acts"):
    return SourceMetadata(
        source="Synthetic official-source fixture",
        url=AnyHttpUrl(url),
        effective_date=date(2026, 4, 1),
    )


def test_markdown_is_split_by_section_with_source_metadata(tmp_path: Path) -> None:
    document = tmp_path / "act.md"
    document.write_text(
        "# Chapter One\nTax provision alpha.\n\n## Section 4\nTax provision beta.",
        encoding="utf-8",
    )
    chunks = section_chunks(document, _source())
    assert [item["citation"]["section"] for item in chunks] == [
        "Chapter One",
        "Section 4",
    ]
    assert all(item["citation"]["source"] == "Synthetic official-source fixture" for item in chunks)


def test_source_discovery_only_reads_official_documents(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Documentation, not source material.", encoding="utf-8")
    official_dir = tmp_path / "official"
    official_dir.mkdir()
    source = official_dir / "act.md"
    source.write_text("# Section 1\nSource text.", encoding="utf-8")
    (official_dir / "notes.txt").write_text("Unsupported file.", encoding="utf-8")

    assert _source_documents(tmp_path) == [source]


def test_html_ingestion_skips_script_text_and_keeps_heading(tmp_path: Path) -> None:
    document = tmp_path / "faq.html"
    document.write_text(
        "<html><body><script>ignore this text</script><h2>FAQ topic</h2>"
        "<p>Official guidance content.</p></body></html>",
        encoding="utf-8",
    )
    chunks = section_chunks(document, _source())
    assert chunks[0]["citation"]["section"] == "FAQ topic"
    assert "Official guidance content" in chunks[0]["content"]
    assert "ignore this text" not in chunks[0]["content"]


def test_reject_non_official_source_url(tmp_path: Path) -> None:
    document = tmp_path / "not-written.pdf"
    metadata_path = tmp_path / "not-written.pdf.metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "source": "untrusted",
                "url": "https://example.com/pretend-official",
                "effective_date": "2026-04-01",
            }
        ),
        encoding="utf-8",
    )
    try:
        with pytest.raises(ValueError, match="official Income Tax source"):
            from app.services.rag.ingest import _source_metadata

            _source_metadata(document)
    finally:
        metadata_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_retrieval_applies_similarity_threshold_and_official_citation(
    tmp_path: Path,
) -> None:
    index = faiss.IndexFlatIP(2)
    vectors = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype="float32")
    faiss.normalize_L2(vectors)
    index.add(vectors)
    faiss.write_index(index, str(tmp_path / "index.faiss"))
    records = [
        {
            "content": "Official tax rule source passage.",
            "citation": {
                "source": "Official source",
                "section": "Synthetic section",
                "link": "https://www.incometax.gov.in/iec/foportal/help/acts",
                "effective_date": "2026-04-01",
            },
        },
        {
            "content": "Unrelated official-source passage.",
            "citation": {
                "source": "Official source",
                "section": "Other section",
                "link": "https://www.incometax.gov.in/iec/foportal/help/acts",
                "effective_date": "2026-04-01",
            },
        },
    ]
    (tmp_path / "chunks.json").write_text(json.dumps(records), encoding="utf-8")
    settings = Settings(
        rag_index_dir=tmp_path,
        rag_similarity_threshold=0.8,
        google_api_key=None,
    )

    async def embedder(_query: str, _settings: Settings) -> list[float]:
        return [1.0, 0.0]

    matches = await KnowledgeBase(settings, embedder).search("tax question")
    assert len(matches) == 1
    assert matches[0].content == "Official tax rule source passage."
    assert matches[0].similarity == pytest.approx(1.0)


def test_official_source_host_allows_department_subdomain_not_suffix_attack() -> None:
    from app.services.rag.retriever import is_official_source_host

    assert is_official_source_host("www.incometax.gov.in")
    assert not is_official_source_host("incometax.gov.in.attacker.example")


def test_retrieved_chunk_validation_rejects_invalid_similarity() -> None:
    with pytest.raises(ValueError):
        RetrievedChunk.model_validate(
            {
                "content": "text",
                "citation": {
                    "source": "Official source",
                    "section": "Section",
                    "link": "https://www.incometax.gov.in/iec/foportal/help",
                    "effective_date": "2026-04-01",
                },
                "similarity": 2,
            }
        )
