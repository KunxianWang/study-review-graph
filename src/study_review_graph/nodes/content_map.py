"""Content-map construction nodes."""

from __future__ import annotations

from study_review_graph.retrieval import collect_top_terms
from study_review_graph.state import ConceptRecord, StudyGraphState


def build_content_map_node(state: StudyGraphState) -> tuple[list[ConceptRecord], list[str]]:
    """Build a lightweight concept map from sections and frequent terms."""

    candidates = []
    for doc in state.normalized_docs:
        candidates.extend(doc.sections)

    if not candidates:
        candidates.extend(collect_top_terms((chunk.text for chunk in state.chunks), limit=6))

    concepts: list[ConceptRecord] = []
    for index, candidate in enumerate(dict.fromkeys(candidates)):
        if not candidate:
            continue
        supporting_chunk = next(
            (chunk for chunk in state.chunks if candidate.lower() in chunk.text.lower()),
            None,
        )
        references = supporting_chunk.references if supporting_chunk else []
        concepts.append(
            ConceptRecord(
                concept_id=f"concept-{index}",
                name=candidate.strip(),
                description=f"Core topic inferred from the study materials: {candidate.strip()}",
                references=references,
            )
        )

    warnings = []
    if not concepts:
        warnings.append("No concepts were identified from the current materials.")

    return concepts, warnings
