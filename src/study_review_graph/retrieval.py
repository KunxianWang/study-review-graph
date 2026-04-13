"""Chunking and deterministic retrieval helpers."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from study_review_graph.compat import RecursiveCharacterTextSplitter
from study_review_graph.state import ChunkRecord, NormalizedDocument, SourceReference, StudyGraphState


def chunk_documents(
    normalized_docs: list[NormalizedDocument],
    chunk_size: int,
    chunk_overlap: int,
) -> list[ChunkRecord]:
    """Split normalized documents into retrieval-friendly chunks."""

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks: list[ChunkRecord] = []
    for doc in normalized_docs:
        split_texts = splitter.split_text(doc.content)
        for index, chunk_text in enumerate(split_texts):
            chunk_id = f"{doc.document_id}-chunk-{index}"
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    document_id=doc.document_id,
                    source_path=doc.source_path,
                    order=index,
                    text=chunk_text,
                    references=[
                        SourceReference(
                            document_id=doc.document_id,
                            source_path=doc.source_path,
                            chunk_id=chunk_id,
                            excerpt=chunk_text[:220],
                        )
                    ],
                    metadata={"section_count": str(len(doc.sections))},
                )
            )
    return chunks


def build_retrieval_cache(chunks: list[ChunkRecord]) -> dict[str, list[str]]:
    """Initialize retrieval cache metadata for deterministic lookups."""

    return {"__all__": [chunk.chunk_id for chunk in chunks]}


def retrieve_relevant_chunks(
    query: str,
    state: StudyGraphState,
    top_k: int | None = None,
) -> list[ChunkRecord]:
    """Return the most relevant chunks using token overlap scoring."""

    if not state.chunks:
        return []

    effective_top_k = top_k or state.config.top_k
    query_tokens = _tokenize(query)
    if not query_tokens:
        return state.chunks[:effective_top_k]

    scored = [
        (chunk, _score_chunk(query_tokens, chunk.text))
        for chunk in state.chunks
    ]
    ranked = sorted(scored, key=lambda item: item[1], reverse=True)
    return [chunk for chunk, score in ranked if score > 0][:effective_top_k] or state.chunks[:effective_top_k]


def collect_top_terms(texts: Iterable[str], limit: int = 10) -> list[str]:
    """Return common candidate terms for concept extraction."""

    counter: Counter[str] = Counter()
    for text in texts:
        counter.update(token for token in _tokenize(text) if len(token) > 3)
    return [term for term, _ in counter.most_common(limit)]


def _score_chunk(query_tokens: set[str], text: str) -> int:
    chunk_tokens = _tokenize(text)
    overlap = query_tokens.intersection(chunk_tokens)
    return len(overlap)


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text.lower()))
