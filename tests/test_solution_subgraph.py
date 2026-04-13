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
                title="Newton's second law worked example",
                problem_statement="Use `F = m * a` to find net force when mass = 2 kg and acceleration = 3 m/s^2.",
                formula_ids=["formula-0"],
                difficulty="introductory",
                study_value="Practice a direct substitution into the force relationship.",
                known_values={"m": "2 kg", "a": "3 m/s^2"},
                target_symbol="F",
                prompt="Use `F = m * a` to find net force when mass = 2 kg and acceleration = 3 m/s^2.",
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
    assert solution.rationale
    assert solution.common_mistakes
    assert solution.references


def test_solution_subgraph_uses_llm_refinement_when_available(monkeypatch):
    class FakeClient:
        def generate_json(self, **_kwargs):
            return ModelCallResult(
                payload={
                    "plan_steps": [
                        "Identify the target net force.",
                        "Use `F = m * a` with the given mass and acceleration.",
                    ],
                    "detailed_steps": [
                        "Write `F = m * a`.",
                        "Substitute `m = 2` and `a = 3` to obtain `F = 6`.",
                    ],
                    "rationale": [
                        "This keeps the computation tied to Newton's second law.",
                    ],
                    "common_mistakes": [
                        "Mixing up the target force with one of the givens.",
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
                title="Newton's second law worked example",
                problem_statement="Use `F = m * a` to find net force when mass = 2 kg and acceleration = 3 m/s^2.",
                formula_ids=["formula-0"],
                known_values={"m": "2 kg", "a": "3 m/s^2"},
                target_symbol="F",
                prompt="Use `F = m * a` to find net force when mass = 2 kg and acceleration = 3 m/s^2.",
                formula_id="formula-0",
                references=[reference],
            )
        ],
    )

    solutions = run_solution_subgraph(state)

    assert solutions[0].plan_steps == [
        "Identify the target net force.",
        "Use `F = m * a` with the given mass and acceleration.",
    ]
    assert solutions[0].detailed_steps[1] == "Substitute `m = 2` and `a = 3` to obtain `F = 6`."
    assert solutions[0].common_mistakes == ["Mixing up the target force with one of the givens."]
