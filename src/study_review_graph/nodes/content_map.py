"""Content-map construction nodes."""

from __future__ import annotations

import re
from collections import Counter

from study_review_graph.model_client import get_model_client
from study_review_graph.retrieval import retrieve_relevant_chunks
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
STOPWORD_LIKE_TOKENS = {
    "a",
    "an",
    "and",
    "another",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "core",
    "equals",
    "for",
    "from",
    "if",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "relationship",
    "states",
    "that",
    "the",
    "their",
    "these",
    "this",
    "those",
    "to",
    "use",
    "used",
    "when",
    "with",
}
DOMAIN_SINGLE_WORDS = {
    "acceleration",
    "energy",
    "force",
    "kinetics",
    "kinematics",
    "mass",
    "mechanics",
    "momentum",
    "probability",
    "velocity",
}
GRAMMATICAL_BREAK_WORDS = {
    "are",
    "assuming",
    "describes",
    "explains",
    "if",
    "is",
    "measures",
    "state",
    "states",
    "under",
    "when",
}


def build_content_map_node(state: StudyGraphState) -> tuple[list[ConceptRecord], list[str]]:
    """Build a grounded concept map from headings and repeated source terms."""

    warnings: list[str] = []
    weighted_candidates: Counter[str] = Counter()
    for doc in state.normalized_docs:
        for section in doc.sections:
            cleaned = _clean_candidate(section, from_section=True)
            if cleaned:
                weighted_candidates[cleaned] += 5

    for chunk in state.chunks:
        for candidate, weight in _extract_phrase_candidates(chunk.text).items():
            cleaned = _clean_candidate(candidate, from_section=False)
            if cleaned:
                weighted_candidates[cleaned] += weight

    ranked_candidates = _rank_candidates(weighted_candidates)

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


def _clean_candidate(candidate: str, *, from_section: bool) -> str:
    cleaned = re.sub(r"\s+", " ", candidate).strip(" -#:\t")
    if not cleaned:
        return ""

    cleaned = re.sub(r"(?i)\bnotes?\b$", "", cleaned).strip(" -#:\t")
    cleaned = re.sub(r"(?i)^intro(?:duction)?\b", "", cleaned).strip(" -#:\t")
    cleaned = _truncate_at_break_words(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -#:\t")
    if not cleaned:
        return ""

    lowered = cleaned.lower()
    if lowered in GENERIC_SECTION_NAMES:
        return ""
    if lowered in STOPWORD_LIKE_TOKENS:
        return ""

    tokens = [token for token in re.findall(r"[A-Za-z][A-Za-z'-]*", cleaned)]
    if not tokens:
        return ""

    meaningful_tokens = [token for token in tokens if token.lower() not in STOPWORD_LIKE_TOKENS]
    if not meaningful_tokens:
        return ""

    if len(tokens) == 1:
        token = tokens[0]
        if len(token) < 4:
            return ""
        if not from_section and token.lower() not in DOMAIN_SINGLE_WORDS:
            return ""

    if len(tokens) >= 2 and len(meaningful_tokens) == 1:
        return ""

    return " ".join(token if token.isupper() else token.capitalize() for token in meaningful_tokens)


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


def _truncate_at_break_words(candidate: str) -> str:
    tokens = candidate.split()
    kept: list[str] = []
    for token in tokens:
        normalized = token.lower().strip(".,:;!?")
        if normalized in GRAMMATICAL_BREAK_WORDS and kept:
            break
        kept.append(token)
    return " ".join(kept)


def _extract_phrase_candidates(text: str) -> Counter[str]:
    candidates: Counter[str] = Counter()
    for line in text.splitlines():
        stripped = line.strip().lstrip("-").strip()
        if ":" in stripped:
            key, value = [part.strip() for part in stripped.split(":", 1)]
            if _looks_like_symbol_key(key):
                candidates[value] += 3

    for sentence in _sentence_candidates(text):
        subject_match = re.match(
            r"^([A-Za-z][A-Za-z' -]{2,60}?)\s+(states?|explains?|describes?|measures?|is|are)\b",
            sentence,
            flags=re.IGNORECASE,
        )
        if subject_match:
            candidates[subject_match.group(1).strip()] += 3
    return candidates


def _looks_like_symbol_key(key: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key))


def _rank_candidates(weighted_candidates: Counter[str]) -> list[str]:
    ranked = [
        candidate
        for candidate, score in weighted_candidates.most_common(10)
        if score >= 2
    ]
    return ranked[:8]
