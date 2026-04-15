import shutil
import tempfile
from pathlib import Path

from study_review_graph.graph import invoke_study_graph
from study_review_graph.state import RuntimeConfig, StudyGraphState


def test_pipeline_runs_end_to_end():
    temp_root = Path.cwd() / ".test_tmp"
    temp_root.mkdir(exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="pipeline-", dir=temp_root))
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    input_dir.mkdir()

    try:
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
        assert "review_notes" in final_state.output_paths
        assert (output_dir / "content_map.md").exists()
        assert (output_dir / "formula_sheet.md").exists()
        assert (output_dir / "worked_examples.md").exists()
        assert (output_dir / "worked_solutions.md").exists()
        assert (output_dir / "review_notes.md").exists()
        content_map = (output_dir / "content_map.md").read_text(encoding="utf-8")
        formula_sheet = (output_dir / "formula_sheet.md").read_text(encoding="utf-8")
        worked_examples = (output_dir / "worked_examples.md").read_text(encoding="utf-8")
        worked_solutions = (output_dir / "worked_solutions.md").read_text(encoding="utf-8")
        review_notes = (output_dir / "review_notes.md").read_text(encoding="utf-8")

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
        assert "$$" in formula_sheet

        assert "# 例题讲解" in worked_examples
        assert "### 这题在练什么" in worked_examples
        assert "### 对应公式" in worked_examples
        assert "### 题目" in worked_examples
        assert "$F = m \\cdot a$ (`formula-0`)" in worked_examples

        assert "# 例题详解" in worked_solutions
        assert "### 题意直觉" in worked_solutions
        assert "### 公式选择" in worked_solutions
        assert "### 逐步代入 / 推导" in worked_solutions
        assert "### 易错点" in worked_solutions
        assert "F = 2 * 3 = 6" in worked_solutions

        assert "# 复习笔记" in review_notes
        assert "> 当前模式：`full_review`" in review_notes
        assert "## 本章主线" in review_notes
        assert "## 关键定义与公式" in review_notes
        assert "## 算法 / 方法逐个讲解" in review_notes
        assert "## 每个主要方法对应的例题 / worked example" in review_notes
        assert "## 易错点 / 混淆点" in review_notes
        assert "## 考前速记版" in review_notes
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
