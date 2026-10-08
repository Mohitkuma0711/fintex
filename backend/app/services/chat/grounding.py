import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.chat import Citation
from app.services.rag.retriever import RetrievedChunk, is_official_source_host

NOT_SURE_ANSWER = (
    "I'm not sure I can verify that from the official sources and calculation tools "
    "available to me. This is guidance, not professional tax advice."
)
OUT_OF_SCOPE_ANSWER = (
    "I can help with Indian income-tax topics, but not that subject. I'm not sure "
    "about it. This is guidance, not professional tax advice."
)
_NUMBER_PATTERN = re.compile(r"(?<![\w])₹?\s*-?\d[\d,]*(?:\.\d+)?%?")
_DOCUMENT_INJECTION_PATTERN = re.compile(
    r"\b(?:ignore|disregard|override|forget)\b.{0,80}\b"
    r"(?:previous|prior|above|all|system|instructions?|rules?)\b"
    r"|\b(?:reveal|expose|disclose)\b.{0,60}\b"
    r"(?:private|personal|secret|confidential)\b",
    re.IGNORECASE | re.DOTALL,
)


def citation_for_chunk(chunk: RetrievedChunk) -> Citation:
    return Citation(
        source=chunk.citation.source,
        section=chunk.citation.section,
        link=chunk.citation.link,
    )


def unique_official_citations(citations: list[Citation]) -> list[Citation]:
    unique: dict[str, Citation] = {}
    for citation in citations:
        if is_official_source_host(citation.link.host):
            unique.setdefault(
                f"{citation.link}|{citation.section}|{citation.source}",
                citation,
            )
    return list(unique.values())


def _numeric_values(text: str) -> set[Decimal]:
    values: set[Decimal] = set()
    for match in _NUMBER_PATTERN.finditer(text):
        numeric = match.group().replace("₹", "").replace(",", "").replace("%", "").strip()
        try:
            values.add(Decimal(numeric))
        except InvalidOperation:
            continue
    return values


def answer_is_grounded(
    answer: str,
    *,
    tool_outputs: list[dict[str, Any]],
    source_chunks: list[RetrievedChunk],
    citations: list[Citation],
) -> bool:
    valid_citations = unique_official_citations(citations)
    if not answer.strip() or not valid_citations or not source_chunks:
        return False
    if any(_DOCUMENT_INJECTION_PATTERN.search(chunk.content) for chunk in source_chunks):
        return False

    evidence = json.dumps(tool_outputs, ensure_ascii=False, default=str)
    evidence += "\n" + "\n".join(
        "\n".join(
            (
                chunk.content,
                chunk.citation.source,
                chunk.citation.section,
                chunk.citation.effective_date,
            )
        )
        for chunk in source_chunks
    )
    return _numeric_values(answer).issubset(_numeric_values(evidence))


def grounded_or_unsure(
    answer: str,
    *,
    tool_outputs: list[dict[str, Any]],
    source_chunks: list[RetrievedChunk],
    citations: list[Citation],
) -> str:
    if answer_is_grounded(
        answer,
        tool_outputs=tool_outputs,
        source_chunks=source_chunks,
        citations=citations,
    ):
        return answer.strip()
    return NOT_SURE_ANSWER
