from study_review_graph.retrieval import retrieve_relevant_chunks
from study_review_graph.state import ChunkRecord, SourceReference, StudyGraphState


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
