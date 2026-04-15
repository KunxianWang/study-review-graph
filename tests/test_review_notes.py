import shutil
from pathlib import Path
from uuid import uuid4

from study_review_graph.exporters.markdown import export_markdown_bundle
from study_review_graph.nodes.review_notes import generate_review_notes_node
from study_review_graph.state import (
    ConceptRecord,
    ExampleArtifact,
    FormulaArtifact,
    RuntimeConfig,
    SourceReference,
    StudyGraphState,
    WorkedSolution,
)


def test_review_notes_default_to_full_review_structure():
    state = _build_state()
    notes = generate_review_notes_node(state)

    assert notes.mode == "full_review"
    assert any(line.startswith("本章主要围绕") for line in notes.concise_summary)
    assert any("### 公式 formula-0" == line for line in notes.formula_highlights)
    assert any("核心关系" in line for line in notes.detailed_explanations)
    assert any("### 例题：牛顿第二定律" == line for line in notes.example_highlights)
    assert any("还没看清题目在求什么" in line for line in notes.common_mistakes)
    assert any("看到 F = m * a 时" in line for line in notes.study_questions)


def test_review_notes_deep_dive_respects_focus_topic():
    state = _build_state(study_mode="deep_dive", focus_topic="Kinetic Energy")
    notes = generate_review_notes_node(state)

    assert notes.mode == "deep_dive"
    assert notes.focus_target == "Kinetic Energy"
    assert notes.focus_selection_note is None
    assert any("Kinetic Energy" in line for line in notes.concise_summary)
    assert any("E_k = 1/2 * m * v^2" in line for line in notes.formula_highlights)
    assert any("例题：动能计算" in line for line in notes.example_highlights)
    assert any("动能" in line or "E_k" in line for line in notes.study_questions)


def test_review_notes_deep_dive_auto_selects_focus_when_missing():
    state = _build_state(study_mode="deep_dive")
    notes = generate_review_notes_node(state)

    assert notes.mode == "deep_dive"
    assert notes.focus_target
    assert notes.focus_selection_note is not None
    assert "自动选择" in notes.focus_selection_note


def test_review_notes_exam_sprint_structure():
    state = _build_state(study_mode="exam_sprint")
    notes = generate_review_notes_node(state)

    assert notes.mode == "exam_sprint"
    assert any("Newton's Second Law" in line for line in notes.concise_summary)
    assert any("F = m * a" in line for line in notes.formula_highlights)
    assert any("高频考点" in line for line in notes.detailed_explanations)
    assert any("例题：牛顿第二定律" in line for line in notes.example_highlights)
    assert notes.study_questions


def test_review_note_export_changes_structure_by_mode():
    state = _build_state(study_mode="exam_sprint")
    state.review_notes = generate_review_notes_node(state)
    temp_root = Path.cwd() / ".runtime_test_dirs"
    temp_root.mkdir(exist_ok=True)
    temp_dir = temp_root / f"review-notes-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        state.config.output_dir = str(temp_dir)
        output_paths = export_markdown_bundle(state)
        review_notes = Path(output_paths["review_notes"]).read_text(encoding="utf-8")

        assert "> 当前模式：`exam_sprint`" in review_notes
        assert "## 必背定义" in review_notes
        assert "## 核心公式" in review_notes
        assert "## 高频考点" in review_notes
        assert "## 一道典型题" in review_notes
        assert "## 速记提醒" in review_notes
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _build_state(
    *,
    study_mode: str = "full_review",
    focus_topic: str | None = None,
) -> StudyGraphState:
    reference = SourceReference(document_id="d1", source_path="notes.md", chunk_id="d1-chunk-0")
    return StudyGraphState(
        course_name="Mechanics",
        user_goal="Deep understanding",
        config=RuntimeConfig(study_mode=study_mode, focus_topic=focus_topic),
        concepts=[
            ConceptRecord(
                concept_id="concept-0",
                name="Newton's Second Law",
                description="Relates force, mass, and acceleration.",
                references=[reference],
            ),
            ConceptRecord(
                concept_id="concept-1",
                name="Kinetic Energy",
                description="Tracks how motion energy depends on mass and speed.",
                references=[reference],
            ),
        ],
        formulas=[
            FormulaArtifact(
                formula_id="formula-0",
                expression="F = m * a",
                symbol_explanations={"F": "net force", "m": "mass", "a": "acceleration"},
                conditions=["Use this law when the mass is treated as constant."],
                concept_links=["concept-0"],
                references=[reference],
            ),
            FormulaArtifact(
                formula_id="formula-1",
                expression="E_k = 1/2 * m * v^2",
                symbol_explanations={"E_k": "kinetic energy", "m": "mass", "v": "velocity"},
                conditions=["Use this when motion remains non-relativistic."],
                concept_links=["concept-1"],
                references=[reference],
            ),
        ],
        examples=[
            ExampleArtifact(
                example_id="example-0",
                title="例题：牛顿第二定律",
                problem_statement="已知质量 2 kg、加速度 3 m/s^2，请利用 `F = m * a` 求净力。",
                formula_ids=["formula-0"],
                difficulty="introductory",
                study_value="适合练习牛顿第二定律中的直接代入。",
                known_values={"m": "2 kg", "a": "3 m/s^2"},
                target_symbol="F",
                prompt="已知质量 2 kg、加速度 3 m/s^2，请利用 `F = m * a` 求净力。",
                formula_id="formula-0",
                references=[reference],
            ),
            ExampleArtifact(
                example_id="example-1",
                title="例题：动能计算",
                problem_statement="已知质量 2 kg、速度 4 m/s，请利用 `E_k = 1/2 * m * v^2` 求动能。",
                formula_ids=["formula-1"],
                difficulty="introductory",
                study_value="适合练习动能公式里的平方项和单位检查。",
                known_values={"m": "2 kg", "v": "4 m/s"},
                target_symbol="E_k",
                prompt="已知质量 2 kg、速度 4 m/s，请利用 `E_k = 1/2 * m * v^2` 求动能。",
                formula_id="formula-1",
                references=[reference],
            ),
        ],
        worked_solutions=[
            WorkedSolution(
                solution_id="solution-0",
                example_id="example-0",
                plan_steps=["先明确要求什么：目标量是 净力（`F`）。"],
                detailed_steps=["先写出 `F = m * a`，再代入 `m = 2`、`a = 3`。"],
                common_mistakes=["还没看清题目在求什么，就直接往公式里代数字。"],
                references=[reference],
            ),
            WorkedSolution(
                solution_id="solution-1",
                example_id="example-1",
                plan_steps=["先明确要求什么：目标量是 动能（`E_k`）。"],
                detailed_steps=["先写出 `E_k = 1/2 * m * v^2`，再逐步代入。"],
                common_mistakes=["忘记速度平方，只把 `v` 当成一次项代入。"],
                references=[reference],
            ),
        ],
    )
