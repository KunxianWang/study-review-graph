"""Example generation module."""

from __future__ import annotations

from study_review_graph.state import ExampleArtifact, StudyGraphState


def generate_examples_node(state: StudyGraphState) -> list[ExampleArtifact]:
    """Create deterministic example prompts from formulas or concepts."""

    examples: list[ExampleArtifact] = []

    for index, formula in enumerate(state.formulas):
        title = f"Example for {formula.expression}"
        prompt = (
            f"Work through a concrete scenario that uses {formula.expression}. "
            "Identify the known values, the unknown quantity, and explain why the formula applies."
        )
        examples.append(
            ExampleArtifact(
                example_id=f"example-{index}",
                title=title,
                prompt=prompt,
                formula_id=formula.formula_id,
                reasoning_context="Generated from a formula-centered study pass.",
                references=formula.references,
            )
        )

    if not examples:
        for index, concept in enumerate(state.concepts[:3]):
            examples.append(
                ExampleArtifact(
                    example_id=f"example-concept-{index}",
                    title=f"Concept application: {concept.name}",
                    prompt=(
                        f"Construct a concrete study example for the concept '{concept.name}' "
                        "using only the provided material."
                    ),
                    reasoning_context="Fallback concept-driven example because no formulas were extracted.",
                    references=concept.references,
                )
            )

    return examples
