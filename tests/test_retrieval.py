from study_review_graph.retrieval import chunk_documents, retrieve_relevant_chunks
from study_review_graph.state import (
    ChunkRecord,
    NormalizedDocument,
    SourceReference,
    StudyGraphState,
)


def test_retrieval_prefers_overlapping_terms():
    chunk_force = ChunkRecord(
        chunk_id="c1",
        document_id="d1",
        source_path="notes.md",
        order=0,
        text="Force depends on mass and acceleration in classical mechanics.",
        references=[SourceReference(document_id="d1", source_path="notes.md", chunk_id="c1")],
    )
    chunk_energy = ChunkRecord(
        chunk_id="c2",
        document_id="d1",
        source_path="notes.md",
        order=1,
        text="Kinetic energy depends on mass and velocity.",
        references=[SourceReference(document_id="d1", source_path="notes.md", chunk_id="c2")],
    )
    state = StudyGraphState(chunks=[chunk_force, chunk_energy])

    hits = retrieve_relevant_chunks("force acceleration", state, top_k=1)

    assert hits[0].chunk_id == "c1"


def test_chunk_documents_preserves_order_and_overlap_metadata():
    docs = [
        NormalizedDocument(
            document_id="d1",
            source_path="notes.md",
            content="A" * 80 + " B" * 80,
            sections=["Mechanics"],
        )
    ]

    chunks = chunk_documents(docs, chunk_size=90, chunk_overlap=20)

    assert len(chunks) >= 2
    assert chunks[0].order == 0
    assert chunks[1].order == 1
    assert chunks[0].references[0].chunk_id == chunks[0].chunk_id
