from study_review_graph.subgraphs.formula_subgraph import run_formula_subgraph
from study_review_graph.state import (
    ChunkRecord,
    ConceptRecord,
    NormalizedDocument,
    SourceReference,
    StudyGraphState,
)


def test_formula_subgraph_produces_structured_formula_artifact():
    doc_text = (
        "# Mechanics\n\n"
        "Newton's second law states that force equals mass times acceleration.\n"
        "F = m * a\n"
        "- F: net force\n"
        "- m: mass\n"
        "- a: acceleration\n"
        "Use this law when the mass is treated as constant.\n"
    )
    normalized = NormalizedDocument(
        document_id="d1",
        source_path="notes.md",
        content=doc_text,
        sections=["Mechanics"],
    )
    chunk = ChunkRecord(
        chunk_id="d1-chunk-0",
        document_id="d1",
        source_path="notes.md",
        order=0,
        text=doc_text,
        references=[
            SourceReference(
                document_id="d1",
                source_path="notes.md",
                chunk_id="d1-chunk-0",
                excerpt="F = m * a",
            )
        ],
    )
    state = StudyGraphState(
        normalized_docs=[normalized],
        chunks=[chunk],
        concepts=[
            ConceptRecord(
                concept_id="concept-0",
                name="Mechanics",
                description="Mechanics studies force and motion.",
                references=chunk.references,
            )
        ],
    )

    formulas = run_formula_subgraph(state)

    assert formulas
    assert formulas[0].formula_id == "formula-0"
    assert formulas[0].expression == "F = m * a"
    assert "F" in formulas[0].symbol_explanations
    assert formulas[0].conditions
    assert formulas[0].references
