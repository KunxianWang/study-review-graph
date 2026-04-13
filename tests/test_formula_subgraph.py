from study_review_graph.model_client import ModelCallResult
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


def test_formula_subgraph_uses_llm_enrichment_when_available(monkeypatch):
    class FakeClient:
        def availability_warning(self):
            return None

    monkeypatch.setattr(
        "study_review_graph.subgraphs.formula_subgraph.get_model_client",
        lambda: FakeClient(),
    )
    monkeypatch.setattr(
        "study_review_graph.subgraphs.formula_subgraph.get_cached_formula_enrichment",
        lambda **_kwargs: ModelCallResult(
            payload={
                "symbol_explanations": {
                    "F": "net force from the local notes",
                    "m": "mass from the local notes",
                    "a": "acceleration from the local notes",
                },
                "conditions": ["Use this law when the mass is treated as constant."],
                "linked_concepts": ["Mechanics"],
                "note": "TODO: derivation is not yet checked.",
            }
        ),
    )

    doc_text = (
        "# Mechanics\n\n"
        "Newton's second law states that force equals mass times acceleration.\n"
        "F = m * a\n"
        "- F: force\n"
        "- m: mass\n"
        "- a: acceleration\n"
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
        references=[SourceReference(document_id="d1", source_path="notes.md", chunk_id="d1-chunk-0")],
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

    assert formulas[0].symbol_explanations["F"] == "net force from the local notes"
    assert "Use this law when the mass is treated as constant." in formulas[0].conditions
    assert formulas[0].concept_links == ["concept-0"]
