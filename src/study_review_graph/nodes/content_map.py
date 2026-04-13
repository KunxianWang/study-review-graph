"""Content-map construction nodes."""

from __future__ import annotations

import re
from collections import Counter

from study_review_graph.model_client import get_model_client
from study_review_graph.retrieval import collect_top_terms, retrieve_relevant_chunks
from study_review_graph.state import ConceptRecord, StudyGraphState

GENERIC_SECTION_NAMES = {
    "introduction",
    "overview",
    "summary",
    "notes",
    "symbols",
    "equations",
    "examples",
    "lecture",
    "lecture notes",
}


def build_content_map_node(state: StudyGraphState) -> tuple[list[ConceptRecord], list[str]]:
    """Build a grounded concept map from headings and repeated source terms."""

    warnings: list[str] = []
    weighted_candidates: Counter[str] = Counter()
    for doc in state.normalized_docs:
        for section in doc.sections:
            cleaned = _clean_candidate(section)
            if cleaned:
                weighted_candidates[cleaned] += 3

    for term in collect_top_terms((chunk.text for chunk in state.chunks), limit=20):
        cleaned = _clean_candidate(term)
        if cleaned:
            weighted_candidates[cleaned] += 1

    ranked_candidates = [
        candidate for candidate, _score in weighted_candidates.most_common(8)
    ]

    model_client = get_model_client()
    model_warning = model_client.availability_warning()
    if model_warning:
        warnings.append(model_warning)

    concepts: list[ConceptRecord] = []
    for index, candidate in enumerate(ranked_candidates):
        supporting_chunks = retrieve_relevant_chunks(candidate, state, top_k=2)
        references = _collect_references(supporting_chunks)
        description = _build_grounded_description(candidate, supporting_chunks)
        llm_description, llm_warning = _build_llm_description(
            candidate=candidate,
            supporting_chunks=supporting_chunks,
            model_client=model_client,
        )
        if llm_description:
            description = llm_description
        if llm_warning and llm_warning not in warnings:
            warnings.append(llm_warning)
        concepts.append(
            ConceptRecord(
                concept_id=f"concept-{index}",
                name=candidate,
                description=description,
                references=references,
            )
        )

    if not concepts:
        warnings.append("No concepts were identified from the current materials.")

    return concepts, warnings


def _clean_candidate(candidate: str) -> str:
    cleaned = re.sub(r"\s+", " ", candidate).strip(" -#:\t")
    if not cleaned:
        return ""
    if cleaned.lower() in GENERIC_SECTION_NAMES:
        return ""
    if len(cleaned) < 3:
        return ""
    return cleaned


def _collect_references(chunks) -> list:
    references = []
    seen = set()
    for chunk in chunks:
        for reference in chunk.references:
            key = (reference.source_path, reference.chunk_id)
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
    return references


def _build_grounded_description(candidate: str, chunks) -> str:
    for chunk in chunks:
        for sentence in _sentence_candidates(chunk.text):
            if candidate.lower() in sentence.lower():
                return sentence
    for chunk in chunks:
        for sentence in _sentence_candidates(chunk.text):
            return sentence
    return f"TODO: add a grounded description for '{candidate}' from stronger local evidence."


def _sentence_candidates(text: str) -> list[str]:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
        if sentence.strip()
    ]
    return [sentence for sentence in sentences if len(sentence.split()) >= 4]


def _build_llm_description(candidate: str, supporting_chunks, model_client) -> tuple[str | None, str | None]:
    if not supporting_chunks:
        return None, None

    result = model_client.generate_json(
        task_name=f"content map concept '{candidate}'",
        system_prompt=(
            "You are improving a study content map. "
            "Use only the provided local excerpts. "
            "Do not invent concepts or unsupported claims. "
            "Return JSON with one key: description."
        ),
        user_prompt=(
            f"Concept name: {candidate}\n\n"
            "Retrieved source excerpts:\n"
            f"{_render_chunk_context(supporting_chunks)}\n\n"
            "Write a concise, grounded study description in one or two sentences. "
            "If the evidence is weak, make that limitation explicit."
        ),
    )
    if not result.payload:
        return None, result.warning

    description = str(result.payload.get("description", "")).strip()
    if not description:
        return None, result.warning
    return description, result.warning


def _render_chunk_context(chunks) -> str:
    lines = []
    for chunk in chunks:
        lines.append(f"- {chunk.source_path} [{chunk.chunk_id}]: {chunk.text[:500].strip()}")
    return "\n".join(lines)
