from study_review_graph.model_client import ModelCallResult
from study_review_graph.nodes.examples import generate_examples_node
from study_review_graph.state import (
    ChunkRecord,
    ConceptRecord,
    FormulaArtifact,
    SourceReference,
    StudyGraphState,
)


def test_generate_examples_builds_grounded_formula_example():
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
    state = StudyGraphState(
        chunks=[chunk],
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
        concepts=[
            ConceptRecord(
                concept_id="concept-0",
                name="Newton's Second Law",
                description="Relates force, mass, and acceleration.",
                references=[reference],
            )
        ],
    )

    examples, warnings = generate_examples_node(state)

    assert not warnings
    assert len(examples) == 1
    example = examples[0]
    assert example.formula_id == "formula-0"
    assert example.formula_ids == ["formula-0"]
    assert example.target_symbol == "F"
    assert example.difficulty == "introductory"
    assert example.known_values == {"m": "2 kg", "a": "3 m/s^2"}
    assert "F = m * a" in example.problem_statement
    assert "净力" in example.problem_statement
    assert "这题适合复习" in example.study_value
    assert "最小可算例题" in example.reasoning_context
    assert example.references


def test_generate_examples_uses_llm_refinement_when_available(monkeypatch):
    class FakeClient:
        def availability_warning(self):
            return None

        def generate_json(self, **_kwargs):
            return ModelCallResult(
                payload={
                    "title": "例题：牛顿第二定律",
                    "difficulty": "introductory",
                    "problem_statement": "已知质量 2 kg、加速度 3 m/s^2，请利用 `F = m * a` 求净力。",
                    "study_value": "适合练习牛顿第二定律中的直接代入。",
                }
            )

    monkeypatch.setattr("study_review_graph.nodes.examples.get_model_client", lambda: FakeClient())

    reference = SourceReference(document_id="d1", source_path="notes.md", chunk_id="d1-chunk-0")
    chunk = ChunkRecord(
        chunk_id="d1-chunk-0",
        document_id="d1",
        source_path="notes.md",
        order=0,
        text="F = m * a",
        references=[reference],
    )
    state = StudyGraphState(
        chunks=[chunk],
        formulas=[
            FormulaArtifact(
                formula_id="formula-0",
                expression="F = m * a",
                symbol_explanations={"F": "net force", "m": "mass", "a": "acceleration"},
                references=[reference],
            )
        ],
    )

    examples, _warnings = generate_examples_node(state)

    assert examples[0].title == "例题：牛顿第二定律"
    assert examples[0].problem_statement.startswith("已知质量 2 kg")
    assert examples[0].study_value.startswith("适合练习")
