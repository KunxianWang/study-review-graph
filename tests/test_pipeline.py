from pathlib import Path

from study_review_graph.graph import invoke_study_graph
from study_review_graph.state import RuntimeConfig, StudyGraphState


def test_pipeline_runs_end_to_end(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    (input_dir / "notes.md").write_text(
        (
            "# Newtonian Mechanics\n\n"
            "This section states core relationships for motion.\n"
            "Newton's second law relates force, mass, and acceleration.\n"
            "F = m * a\n"
            "- F: force\n- m: mass\n- a: acceleration\n"
            "Use this law when the mass is treated as constant.\n\n"
            "# Kinetic Energy\n\n"
            "Kinetic energy depends on mass and velocity.\n"
            "KE = 0.5 * m * v^2\n"
            "Use this relationship when the speed is non-relativistic.\n"
        ),
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
    assert final_state.concepts
    assert final_state.examples
    assert final_state.worked_solutions
    assert "content_map" in final_state.output_paths
    assert "formula_sheet" in final_state.output_paths
    assert "worked_examples" in final_state.output_paths
    assert "worked_solutions" in final_state.output_paths
    assert (output_dir / "content_map.md").exists()
    assert (output_dir / "formula_sheet.md").exists()
    assert (output_dir / "worked_examples.md").exists()
    assert (output_dir / "worked_solutions.md").exists()
    content_map = (output_dir / "content_map.md").read_text(encoding="utf-8")
    formula_sheet = (output_dir / "formula_sheet.md").read_text(encoding="utf-8")
    worked_examples = (output_dir / "worked_examples.md").read_text(encoding="utf-8")
    worked_solutions = (output_dir / "worked_solutions.md").read_text(encoding="utf-8")

    assert "# Content Map" in content_map
    assert "## Newtonian Mechanics" in content_map
    assert "## Kinetic Energy" in content_map
    assert "## With" not in content_map
    assert "## This" not in content_map
    assert "## States" not in content_map
    assert "## Core" not in content_map
    assert "## Law Mass" not in content_map

    assert "F = m * a" in formula_sheet
    assert "KE = 0.5 * m * v^2" in formula_sheet
    assert "- Newtonian Mechanics (`concept-" in formula_sheet
    assert "- Kinetic Energy (`concept-" in formula_sheet
    assert "Use this law when the mass is treated as constant." in formula_sheet
    assert "Use this relationship when the speed is non-relativistic." in formula_sheet
    assert "- This (" not in formula_sheet

    assert "# Worked Examples" in worked_examples
    assert "### Target formulas" in worked_examples
    assert "### Problem Statement" in worked_examples
    assert "`F = m * a` (`formula-0`)" in worked_examples

    assert "# Worked Solutions" in worked_solutions
    assert "### Problem Statement" in worked_solutions
    assert "### Detailed Steps" in worked_solutions
    assert "F = 2 * 3 = 6" in worked_solutions
