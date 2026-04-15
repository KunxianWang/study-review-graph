from study_review_graph.model_client import ModelCallResult
from study_review_graph.nodes.practice_set import generate_practice_set_node
from study_review_graph.state import (
    ChunkRecord,
    ConceptRecord,
    ExampleArtifact,
    FormulaArtifact,
    ReviewNotes,
    RuntimeConfig,
    SourceReference,
    StudyGraphState,
    WorkedSolution,
)


def test_generate_practice_set_builds_three_grounded_item_types():
    state = _build_state()

    items, warnings = generate_practice_set_node(state)

    assert not warnings
    assert len(items) == 3
    assert {item.question_type for item in items} == {
        "concept_question",
        "formula_application",
        "worked_calculation",
    }
    concept_item = next(item for item in items if item.question_type == "concept_question")
    formula_item = next(item for item in items if item.question_type == "formula_application")
    calc_item = next(item for item in items if item.question_type == "worked_calculation")

    assert concept_item.concept_ids == ["concept-0"]
    assert "Newton's Second Law" in concept_item.prompt
    assert concept_item.references

    assert formula_item.formula_ids == ["formula-0"]
    assert "F = m * a" in formula_item.prompt
    assert "适用条件" in formula_item.hint

    assert calc_item.formula_ids == ["formula-0"]
    assert calc_item.concept_ids == ["concept-0"]
    assert "标准解法" in calc_item.expected_answer


def test_generate_practice_set_uses_llm_refinement_when_available(monkeypatch):
    class FakeClient:
        def availability_warning(self):
            return None

        def generate_json(self, **_kwargs):
            return ModelCallResult(
                payload={
                    "prompt": "请说明什么时候应该使用 `F = m * a`，并指出已知量与目标量。",
                    "hint": "先检查质量是否可视为常量。",
                    "expected_answer": "参考答案：先确认净力、质量、加速度三者关系，再检查条件。",
                }
            )

    monkeypatch.setattr("study_review_graph.nodes.practice_set.get_model_client", lambda: FakeClient())

    items, _warnings = generate_practice_set_node(_build_state())

    assert any(item.prompt.startswith("请说明什么时候应该使用") for item in items)
    assert any(item.hint.startswith("先检查质量") for item in items)


def test_generate_practice_set_respects_disabled_flag():
    state = _build_state(include_practice_set=False)

    items, warnings = generate_practice_set_node(state)

    assert items == []
    assert warnings == []


def _build_state(*, include_practice_set: bool = True) -> StudyGraphState:
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
        config=RuntimeConfig(include_practice_set=include_practice_set),
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
    )
