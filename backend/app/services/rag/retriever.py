import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from google import genai
from google.genai import types
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.services.tax_engine.rules import OFFICIAL_SOURCE_HOSTS


class KnowledgeBaseUnavailable(RuntimeError):
    """Raised when an official-source index cannot be queried safely."""


class SourceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    section: str
    link: AnyHttpUrl
    effective_date: str


class RetrievedChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    citation: SourceCitation
    similarity: float = Field(ge=-1, le=1)


Reranker = Callable[[str, list[RetrievedChunk]], Awaitable[list[RetrievedChunk]]]


def workspace_path(path: Path) -> Path:
    return path if path.is_absolute() else Path(__file__).resolve().parents[3] / path


def is_official_source_host(host: str) -> bool:
    normalized = host.lower().rstrip(".")
    return any(
        normalized == official_host or normalized.endswith(f".{official_host}")
        for official_host in OFFICIAL_SOURCE_HOSTS
    )


async def embed_text(text: str, settings: Settings) -> list[float]:
    api_key = settings.google_api_key or settings.gemini_api_key
    if api_key is None:
        raise KnowledgeBaseUnavailable("Gemini embeddings are not configured.")
    client = genai.Client(api_key=api_key.get_secret_value())
    async with client.aio as async_client:
        response = await async_client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=768),
        )
    if not response.embeddings or not response.embeddings[0].values:
        raise KnowledgeBaseUnavailable("The embedding service returned no vector.")
    return [float(value) for value in response.embeddings[0].values]


@dataclass(frozen=True)
class KnowledgeBase:
    settings: Settings
    embedder: Callable[[str, Settings], Awaitable[list[float]]] = embed_text

    async def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        reranker: Reranker | None = None,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        index_dir = workspace_path(self.settings.rag_index_dir)
        index_path = index_dir / "index.faiss"
        metadata_path = index_dir / "chunks.json"
        if not index_path.is_file() or not metadata_path.is_file():
            raise KnowledgeBaseUnavailable("The official-source index has not been built.")
        try:
            import faiss

            index = await asyncio.to_thread(faiss.read_index, str(index_path))
            payload: Any = json.loads(
                await asyncio.to_thread(metadata_path.read_text, encoding="utf-8")
            )
        except (ImportError, OSError, ValueError, json.JSONDecodeError) as error:
            raise KnowledgeBaseUnavailable("The official-source index is unavailable.") from error
        if not isinstance(payload, list) or any(not isinstance(record, dict) for record in payload):
            raise KnowledgeBaseUnavailable("The official-source index metadata is invalid.")
        records: list[dict[str, Any]] = payload
        if index.ntotal == 0 or not records:
            return []
        if index.ntotal != len(records):
            raise KnowledgeBaseUnavailable("The official-source index metadata is inconsistent.")
        vector = await self.embedder(query, self.settings)
        query_vector = np.asarray([vector], dtype="float32")
        if query_vector.shape[1] != index.d:
            raise KnowledgeBaseUnavailable(
                "The query embedding dimension does not match the index."
            )
        faiss.normalize_L2(query_vector)
        requested = min(top_k or self.settings.rag_top_k, index.ntotal)
        scores, indexes = await asyncio.to_thread(index.search, query_vector, requested)
        matches: list[RetrievedChunk] = []
        for score, row_index in zip(scores[0].tolist(), indexes[0].tolist(), strict=True):
            if row_index < 0 or score < float(self.settings.rag_similarity_threshold):
                continue
            if row_index >= len(records):
                raise KnowledgeBaseUnavailable(
                    "The official-source index metadata is inconsistent."
                )
            try:
                match = RetrievedChunk.model_validate({**records[row_index], "similarity": score})
            except (ValueError, TypeError) as error:
                raise KnowledgeBaseUnavailable(
                    "The official-source index metadata is invalid."
                ) from error
            if not is_official_source_host(match.citation.link.host):
                raise KnowledgeBaseUnavailable("The index contains a non-official citation.")
            matches.append(match)
        if reranker is not None and matches:
            reranked = await reranker(query, matches)
            allowed = {match.model_dump_json() for match in matches}
            if any(match.model_dump_json() not in allowed for match in reranked):
                raise KnowledgeBaseUnavailable("The reranker returned an unknown passage.")
            matches = reranked
        return matches[:requested]
