from study_review_graph.model_client import ModelCallResult
from study_review_graph.subgraphs.solution_subgraph import run_solution_subgraph
from study_review_graph.state import (
    ChunkRecord,
    ExampleArtifact,
    FormulaArtifact,
    SourceReference,
    StudyGraphState,
)


def test_solution_subgraph_builds_local_worked_solution():
    reference = SourceReference(document_id="d1", source_path="notes.md", chunk_id="d1-chunk-0")
    state = StudyGraphState(
        chunks=[
            ChunkRecord(
                chunk_id="d1-chunk-0",
                document_id="d1",
                source_path="notes.md",
                order=0,
                text="F = m * a\nUse this law when the mass is treated as constant.\n",
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
    )

    solutions = run_solution_subgraph(state)

    assert len(solutions) == 1
    solution = solutions[0]
    assert solution.example_id == "example-0"
    assert solution.plan_steps
    assert any("F = 2 * 3 = 6" in step for step in solution.detailed_steps)
    assert any("mass is treated as constant" in step for step in solution.detailed_steps)
    assert solution.plan_steps[0].startswith("先明确要求什么")
    assert solution.rationale
    assert solution.common_mistakes
    assert solution.references


def test_solution_subgraph_uses_llm_refinement_when_available(monkeypatch):
    class FakeClient:
        def generate_json(self, **_kwargs):
            return ModelCallResult(
                payload={
                    "plan_steps": [
                        "先看题目要求的目标量是净力。",
                        "再用 `F = m * a` 把质量和加速度连起来。",
                    ],
                    "detailed_steps": [
                        "先写出 `F = m * a`。",
                        "把 `m = 2`、`a = 3` 代入，得到 `F = 6`。",
                    ],
                    "rationale": [
                        "这样做可以保证每一步都紧扣牛顿第二定律。",
                    ],
                    "common_mistakes": [
                        "容易把目标量净力和已知量混在一起。",
                    ],
                }
            )

    monkeypatch.setattr("study_review_graph.subgraphs.solution_subgraph.get_model_client", lambda: FakeClient())

    reference = SourceReference(document_id="d1", source_path="notes.md", chunk_id="d1-chunk-0")
    state = StudyGraphState(
        chunks=[
            ChunkRecord(
                chunk_id="d1-chunk-0",
                document_id="d1",
                source_path="notes.md",
                order=0,
                text="F = m * a\nUse this law when the mass is treated as constant.\n",
                references=[reference],
            )
        ],
        formulas=[
            FormulaArtifact(
                formula_id="formula-0",
                expression="F = m * a",
                symbol_explanations={"F": "net force", "m": "mass", "a": "acceleration"},
                references=[reference],
            )
        ],
        examples=[
            ExampleArtifact(
                example_id="example-0",
                title="例题：牛顿第二定律",
                problem_statement="已知质量 2 kg、加速度 3 m/s^2，请利用 `F = m * a` 求净力。",
                formula_ids=["formula-0"],
                known_values={"m": "2 kg", "a": "3 m/s^2"},
                target_symbol="F",
                prompt="已知质量 2 kg、加速度 3 m/s^2，请利用 `F = m * a` 求净力。",
                formula_id="formula-0",
                references=[reference],
            )
        ],
    )

    solutions = run_solution_subgraph(state)

    assert solutions[0].plan_steps == [
        "先看题目要求的目标量是净力。",
        "再用 `F = m * a` 把质量和加速度连起来。",
    ]
    assert solutions[0].detailed_steps[1] == "把 `m = 2`、`a = 3` 代入，得到 `F = 6`。"
    assert solutions[0].common_mistakes == ["容易把目标量净力和已知量混在一起。"]
