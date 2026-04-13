from pathlib import Path

from study_review_graph.graph import invoke_study_graph
from study_review_graph.state import RuntimeConfig, StudyGraphState


def test_pipeline_runs_end_to_end(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    (input_dir / "notes.md").write_text(
        "# Mechanics\n\nF = m * a\n\n- F: force\n- m: mass\n- a: acceleration\n",
        encoding="utf-8",
    )

    initial_state = StudyGraphState(
        course_name="Mechanics",
        user_goal="Deep understanding",
        config=RuntimeConfig(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            chunk_size=400,
            chunk_overlap=40,
            top_k=3,
        ),
    )

    final_state = invoke_study_graph(initial_state)

    assert final_state.formulas
    assert final_state.examples
    assert final_state.worked_solutions
    assert "review_notes" in final_state.output_paths
    assert (output_dir / "review_notes.md").exists()
