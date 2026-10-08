import argparse
import asyncio
import json
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, ValidationError

from app.core.config import Settings, get_settings
from app.services.rag.retriever import is_official_source_host, workspace_path

SUPPORTED_SUFFIXES = {".pdf", ".html", ".htm", ".md"}
SECTION_PATTERN = re.compile(
    r"^(?:#{1,6}\s+.+|(?:chapter|part|schedule|section|circular|faq)\b.*)$",
    re.IGNORECASE,
)
MAX_CHUNK_CHARACTERS = 3_000
CHUNK_OVERLAP_CHARACTERS = 300
EMBED_BATCH_SIZE = 64


class SourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    url: AnyHttpUrl
    effective_date: date


class HtmlTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.heading_depth = 0
        self.skip_depth = 0
        self.title_depth = 0

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
        if tag == "title":
            self.title_depth += 1
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_depth = int(tag[1])
        if tag in {"p", "div", "li", "br", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title" and self.title_depth:
            self.title_depth -= 1
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")
            self.heading_depth = 0
        if tag in {"p", "div", "li", "br", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self.heading_depth:
            self.parts.append(f"\n{'#' * self.heading_depth} {text}\n")
        else:
            self.parts.append(f"{text} ")


def _read_document(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            pages = [
                f"\n## Page {page_number}\n{page.extract_text() or ''}"
                for page_number, page in enumerate(pdf.pages, start=1)
            ]
        return "\n".join(pages)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() not in {".html", ".htm"}:
        return text
    parser = HtmlTextParser()
    parser.feed(text)
    return "\n".join(parser.parts)


def _split_section_text(text: str, *, fallback_section: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading = fallback_section
    current_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if SECTION_PATTERN.match(line):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = line.lstrip("# ").strip()
            current_lines = []
        elif line:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_lines))

    chunks: list[tuple[str, str]] = []
    for heading, lines in sections:
        content = "\n".join(lines).strip()
        if not content:
            continue
        while content:
            end = min(len(content), MAX_CHUNK_CHARACTERS)
            if end < len(content):
                split_at = content.rfind("\n", 0, end)
                if split_at >= MAX_CHUNK_CHARACTERS // 2:
                    end = split_at
            chunk = content[:end].strip()
            if chunk:
                chunks.append((heading, chunk))
            if end >= len(content):
                break
            content = content[max(0, end - CHUNK_OVERLAP_CHARACTERS) :]
    return chunks


def section_chunks(path: Path, metadata: SourceMetadata) -> list[dict[str, str]]:
    text = _read_document(path)
    chunks = _split_section_text(text, fallback_section=path.stem.replace("_", " "))
    if not chunks:
        raise ValueError(f"Official source document contains no extractable text: {path.name}")
    return [
        {
            "content": content,
            "citation": {
                "source": metadata.source,
                "section": section,
                "link": str(metadata.url),
                "effective_date": metadata.effective_date.isoformat(),
            },
        }
        for section, content in chunks
    ]


def _source_metadata(path: Path) -> SourceMetadata:
    metadata_path = path.with_name(f"{path.name}.metadata.json")
    try:
        payload: Any = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata = SourceMetadata.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ValueError(f"Invalid or missing metadata for {path.name}.") from error
    if not is_official_source_host(metadata.url.host):
        raise ValueError(f"{path.name} does not have an official Income Tax source URL.")
    return metadata


def _source_documents(source_dir: Path) -> list[Path]:
    official_dir = source_dir / "official"
    return sorted(
        path
        for path in official_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


async def _embed_batch(
    async_client: Any,
    model: str,
    content: list[str],
) -> list[list[float]]:
    response = await async_client.models.embed_content(
        model=model,
        contents=content,
        config=types.EmbedContentConfig(output_dimensionality=768),
    )
    if response.embeddings is None or len(response.embeddings) != len(content):
        raise RuntimeError("The embedding service returned an incomplete batch.")
    vectors: list[list[float]] = []
    for embedding in response.embeddings:
        if not embedding.values:
            raise RuntimeError("The embedding service returned an empty vector.")
        vectors.append([float(value) for value in embedding.values])
    return vectors


async def ingest(settings: Settings) -> int:
    if settings.google_api_key is None:
        raise RuntimeError("GOOGLE_API_KEY is required to build the knowledge-base index.")
    source_dir = workspace_path(settings.knowledge_base_dir)
    documents = _source_documents(source_dir)
    if not documents:
        raise RuntimeError(
            f"No PDF, HTML, or Markdown sources found under {source_dir / 'official'}."
        )

    records: list[dict[str, str]] = []
    for path in documents:
        metadata = _source_metadata(path)
        records.extend(section_chunks(path, metadata))
    texts = [record["content"] for record in records]

    client = genai.Client(api_key=settings.google_api_key.get_secret_value())
    vectors: list[list[float]] = []
    async with client.aio as async_client:
        for offset in range(0, len(texts), EMBED_BATCH_SIZE):
            vectors.extend(
                await _embed_batch(
                    async_client,
                    settings.gemini_embedding_model,
                    texts[offset : offset + EMBED_BATCH_SIZE],
                )
            )

    if not vectors or len(vectors) != len(records):
        raise RuntimeError("The embedding service returned an invalid index batch.")
    dimension = len(vectors[0])
    if any(len(vector) != dimension for vector in vectors):
        raise RuntimeError("The embedding service returned inconsistent vector dimensions.")

    try:
        import faiss
        import numpy as np
    except ImportError as error:
        raise RuntimeError(
            "Install the backend's declared faiss-cpu dependency to ingest sources."
        ) from error

    matrix = np.asarray(vectors, dtype="float32")
    faiss.normalize_L2(matrix)
    index = faiss.IndexFlatIP(dimension)
    index.add(matrix)
    index_dir = workspace_path(settings.rag_index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    index_tmp = index_dir / "index.faiss.tmp"
    chunks_tmp = index_dir / "chunks.json.tmp"
    faiss.write_index(index, str(index_tmp))
    chunks_tmp.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    index_tmp.replace(index_dir / "index.faiss")
    chunks_tmp.replace(index_dir / "chunks.json")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the FinTax AI official-source FAISS index.")
    parser.parse_args()
    count = asyncio.run(ingest(get_settings()))
    print(f"Indexed {count} official-source sections.")


if __name__ == "__main__":
    main()
