from study_review_graph.nodes.content_map import _clean_candidate, build_content_map_node
from study_review_graph.model_client import ModelCallResult
from study_review_graph.state import ChunkRecord, NormalizedDocument, SourceReference, StudyGraphState


def test_content_map_prefers_sections_and_adds_grounded_description():
    normalized = NormalizedDocument(
        document_id="d1",
        source_path="notes.md",
        content=(
            "# Newtonian Mechanics\n\n"
            "Newton's second law explains how force, mass, and acceleration are related.\n"
            "Kinetic energy measures motion and depends on mass and velocity.\n"
        ),
        sections=["Newtonian Mechanics", "Kinetic Energy"],
    )
    chunks = [
        ChunkRecord(
            chunk_id="d1-chunk-0",
            document_id="d1",
            source_path="notes.md",
            order=0,
            text=normalized.content,
            references=[
                SourceReference(
                    document_id="d1",
                    source_path="notes.md",
                    chunk_id="d1-chunk-0",
                    excerpt="Newton's second law explains how force, mass, and acceleration are related.",
                )
            ],
        )
    ]

    concepts, warnings = build_content_map_node(
        StudyGraphState(normalized_docs=[normalized], chunks=chunks)
    )

    assert not warnings
    assert concepts
    concept_names = {concept.name for concept in concepts}
    assert "Newtonian Mechanics" in concept_names
    assert "Kinetic Energy" in concept_names
    assert all(concept.description for concept in concepts)
    assert all(concept.references for concept in concepts)


def test_content_map_uses_llm_description_when_available(monkeypatch):
    class FakeClient:
        def availability_warning(self):
            return None

        def generate_json(self, **_kwargs):
            return ModelCallResult(
                payload={"description": "Newtonian mechanics studies the force-motion relationship."}
            )

    monkeypatch.setattr("study_review_graph.nodes.content_map.get_model_client", lambda: FakeClient())

    normalized = NormalizedDocument(
        document_id="d1",
        source_path="notes.md",
        content="# Newtonian Mechanics\n\nForce, mass, and acceleration are related.\n",
        sections=["Newtonian Mechanics"],
    )
    chunks = [
        ChunkRecord(
            chunk_id="d1-chunk-0",
            document_id="d1",
            source_path="notes.md",
            order=0,
            text=normalized.content,
            references=[SourceReference(document_id="d1", source_path="notes.md", chunk_id="d1-chunk-0")],
        )
    ]

    concepts, _warnings = build_content_map_node(
        StudyGraphState(normalized_docs=[normalized], chunks=chunks)
    )

    assert concepts[0].description == "Newtonian mechanics studies the force-motion relationship."


def test_content_map_filters_low_value_candidates():
    assert _clean_candidate("with", from_section=False) == ""
    assert _clean_candidate("this", from_section=False) == ""
    assert _clean_candidate("states", from_section=False) == ""
    assert _clean_candidate("core", from_section=False) == ""
    assert _clean_candidate("force", from_section=False) == "Force"


def test_content_map_excludes_bad_concepts_before_description_step():
    normalized = NormalizedDocument(
        document_id="d1",
        source_path="notes.md",
        content=(
            "# Newtonian Mechanics\n\n"
            "This section states core relationships for motion.\n"
            "Force describes the interaction that changes motion.\n"
            "Use this law when the mass is treated as constant.\n"
            "Kinetic energy measures motion and depends on mass and velocity.\n"
        ),
        sections=["Newtonian Mechanics"],
    )
    chunks = [
        ChunkRecord(
            chunk_id="d1-chunk-0",
            document_id="d1",
            source_path="notes.md",
            order=0,
            text=normalized.content,
            references=[SourceReference(document_id="d1", source_path="notes.md", chunk_id="d1-chunk-0")],
        )
    ]

    concepts, _warnings = build_content_map_node(
        StudyGraphState(normalized_docs=[normalized], chunks=chunks)
    )

    concept_names = {concept.name for concept in concepts}
    assert "Newtonian Mechanics" in concept_names
    assert "Force" in concept_names
    assert "With" not in concept_names
    assert "This" not in concept_names
    assert "States" not in concept_names
    assert "Core" not in concept_names
    assert "Law Mass" not in concept_names
