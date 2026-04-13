from study_review_graph.nodes.content_map import build_content_map_node
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
    assert concepts[0].name == "Newtonian Mechanics"
    assert concepts[0].description
    assert concepts[0].references


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
