import shutil
from pathlib import Path
from uuid import uuid4

from study_review_graph.exporters.markdown import export_answer_feedback_markdown
from study_review_graph.nodes.answer_check import check_answer_node
from study_review_graph.state import (
    ChunkRecord,
    ConceptRecord,
    ExampleArtifact,
    FormulaArtifact,
    PracticeItem,
    ReviewNotes,
    SourceReference,
    StudyGraphState,
    WorkedSolution,
)


def test_check_answer_selects_practice_item_by_id():
    state = _build_state()

    feedback, warnings = check_answer_node(
        state,
        practice_id="practice-formula-0",
        user_answer="先看净力、质量和加速度之间的关系，再确认质量可以视为常量，所以应该用 F = m * a。",
    )

    assert not warnings
    assert feedback.practice_id == "practice-formula-0"
    assert feedback.result_label in {"correct", "partially_correct"}
    assert "formula-0" in feedback.formula_ids
    assert feedback.references


def test_check_answer_flags_needs_improvement_for_wrong_formula_answer():
    state = _build_state()

    feedback, _warnings = check_answer_node(
        state,
        practice_id="practice-calculation-0",
        user_answer="我觉得这里直接用 KE = 1/2 * m * v^2 就可以，不用再看净力。",
    )

    assert feedback.result_label == "needs_improvement"
    assert any("不匹配" in issue or "没有明确点出" in issue for issue in feedback.key_issues)
    assert any("回看公式" in item for item in feedback.review_guidance)


def test_check_answer_markdown_export_is_structured():
    state = _build_state()
    feedback, _warnings = check_answer_node(
        state,
        practice_id="practice-concept-0",
        user_answer="牛顿第二定律说明净力、质量和加速度之间的关系，常用于解释受力和运动的联系。",
    )

    temp_root = Path.cwd() / ".runtime_test_dirs"
    temp_root.mkdir(exist_ok=True)
    temp_dir = temp_root / f"answer-feedback-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        output_path = export_answer_feedback_markdown(feedback, output_dir=temp_dir)
        content = Path(output_path).read_text(encoding="utf-8")

        assert "# 作答反馈" in content
        assert "## 题目" in content
        assert "## 你的答案" in content
        assert "## 结果判断" in content
        assert "## 关键问题" in content
        assert "## 正确思路" in content
        assert "## 建议回看" in content
        assert "## 来源" in content
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _build_state() -> StudyGraphState:
    reference = SourceReference(document_id="d1", source_path="notes.md", chunk_id="d1-chunk-0")
    chunk = ChunkRecord(
        chunk_id="d1-chunk-0",
        document_id="d1",
        source_path="notes.md",
        order=0,
        text=(
            "Newton's second law states that force equals mass times acceleration.\n"
            "F = m * a\n"
            "Use this law when the mass is treated as constant.\n"
        ),
        references=[reference],
    )
    return StudyGraphState(
        chunks=[chunk],
        concepts=[
            ConceptRecord(
                concept_id="concept-0",
                name="Newton's Second Law",
                description="Relates force, mass, and acceleration.",
                references=[reference],
            )
        ],
        formulas=[
            FormulaArtifact(
                formula_id="formula-0",
                expression="F = m * a",
                symbol_explanations={"F": "net force", "m": "mass", "a": "acceleration"},
                conditions=["Use this law when the mass is treated as constant."],
                concept_links=["concept-0"],
                references=[reference],
            )
        ],
        examples=[
            ExampleArtifact(
                example_id="example-0",
                title="例题：牛顿第二定律",
                problem_statement="已知质量 2 kg、加速度 3 m/s^2，请利用 `F = m * a` 求净力。",
                formula_ids=["formula-0"],
                study_value="适合练习牛顿第二定律中的直接代入。",
                prompt="已知质量 2 kg、加速度 3 m/s^2，请利用 `F = m * a` 求净力。",
                formula_id="formula-0",
                references=[reference],
            )
        ],
        worked_solutions=[
            WorkedSolution(
                solution_id="solution-0",
                example_id="example-0",
                detailed_steps=[
                    "先写出 `F = m * a`。",
                    "再代入 `m = 2 kg` 和 `a = 3 m/s^2`。",
                    "最后得到 `F = 6 N`。",
                ],
                references=[reference],
            )
        ],
        review_notes=ReviewNotes(
            common_mistakes=["还没看清题目在求什么，就直接往公式里代数字。"],
            study_questions=["看到 F = m * a 时先检查条件是否满足。"],
        ),
        practice_items=[
            PracticeItem(
                practice_id="practice-concept-0",
                question_type="concept_question",
                concept_ids=["concept-0"],
                formula_ids=["formula-0"],
                prompt="请解释 Newton's Second Law 在本章里解决什么问题。",
                hint="先解释净力、质量和加速度之间的关系。",
                expected_answer="应说明净力、质量、加速度三者关系，并指出常见使用场景。",
                references=[reference],
            ),
            PracticeItem(
                practice_id="practice-formula-0",
                question_type="formula_application",
                concept_ids=["concept-0"],
                formula_ids=["formula-0"],
                prompt="什么时候应该使用 `F = m * a`？",
                hint="先检查适用条件，再确认已知量和目标量。",
                expected_answer="应先说明净力、质量、加速度的关系，再说明适用条件。",
                references=[reference],
            ),
            PracticeItem(
                practice_id="practice-calculation-0",
                question_type="worked_calculation",
                concept_ids=["concept-0"],
                formula_ids=["formula-0"],
                prompt="已知质量 2 kg、加速度 3 m/s^2，请利用 `F = m * a` 求净力。",
                hint="先列已知量，再代入公式。",
                expected_answer="先写出 F = m * a，再代入 m=2, a=3，得到 F=6。",
                references=[reference],
            ),
        ],
    )
