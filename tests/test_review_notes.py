from study_review_graph.nodes.review_notes import generate_review_notes_node
from study_review_graph.state import (
    ConceptRecord,
    ExampleArtifact,
    FormulaArtifact,
    SourceReference,
    StudyGraphState,
    WorkedSolution,
)


def test_review_notes_follow_skill_oriented_structure():
    reference = SourceReference(document_id="d1", source_path="notes.md", chunk_id="d1-chunk-0")
    state = StudyGraphState(
        course_name="Mechanics",
        user_goal="Deep understanding",
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
                references=[reference],
            )
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
            )
        ],
        worked_solutions=[
            WorkedSolution(
                solution_id="solution-0",
                example_id="example-0",
                common_mistakes=["还没看清题目在求什么，就直接往公式里代数字。"],
                references=[reference],
            )
        ],
    )

    notes = generate_review_notes_node(state)

    assert any(line.startswith("本章主要围绕") for line in notes.concise_summary)
    assert any("F = m * a" in line for line in notes.formula_highlights)
    assert any("核心关系" in line for line in notes.detailed_explanations)
    assert any("看到 F = m * a 时" in line for line in notes.study_questions)
    assert notes.references
