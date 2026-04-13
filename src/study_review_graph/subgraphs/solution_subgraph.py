"""Worked-solution subgraph for example expansion."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from study_review_graph.compat import END, START, StateGraph
from study_review_graph.state import StudyGraphState, WorkedSolution


def plan_solution_steps_node(state: StudyGraphState) -> list[WorkedSolution]:
    """Create step plans for each example."""

    solutions: list[WorkedSolution] = []
    formula_lookup = {formula.formula_id: formula for formula in state.formulas}

    for index, example in enumerate(state.examples):
        linked_formula = formula_lookup.get(example.formula_id or "")
        formula_text = linked_formula.expression if linked_formula else "the relevant concept relationship"
        solutions.append(
            WorkedSolution(
                solution_id=f"solution-{index}",
                example_id=example.example_id,
                plan_steps=[
                    "Identify the known quantities and the target unknown.",
                    f"Select {formula_text} as the governing relationship.",
                    "Substitute values carefully and track units or meanings.",
                    "Interpret the result in words.",
                ],
                references=example.references,
            )
        )
    return solutions


def expand_solution_steps_node(state: StudyGraphState) -> list[WorkedSolution]:
    """Expand planned steps into worked explanations."""

    expanded: list[WorkedSolution] = []
    example_lookup = {example.example_id: example for example in state.examples}

    for solution in state.worked_solutions:
        example = example_lookup[solution.example_id]
        detailed_steps = [
            f"Start from the example prompt: {example.prompt}",
            "List the givens and identify the unknown before manipulating any formula.",
            "Use the selected relationship to connect the givens to the unknown quantity.",
            "Explain each substitution in plain language so the reasoning remains teachable.",
            "Check whether the final answer makes sense in context.",
        ]
        rationale = [
            "This preserves conceptual understanding before algebraic manipulation.",
            "Grounding each step in the source materials improves explainability.",
        ]
        expanded.append(
            solution.model_copy(
                update={
                    "detailed_steps": detailed_steps,
                    "rationale": rationale,
                }
            )
        )
    return expanded


def annotate_common_mistakes_node(state: StudyGraphState) -> list[WorkedSolution]:
    """Attach common-mistake reminders for each worked solution."""

    updated: list[WorkedSolution] = []
    for solution in state.worked_solutions:
        updated.append(
            solution.model_copy(
                update={
                    "common_mistakes": [
                        "Skipping unit or meaning checks before interpreting the answer.",
                        "Substituting values without confirming the formula conditions.",
                        "Treating memorized steps as interchangeable with conceptual reasoning.",
                    ]
                }
            )
        )
    return updated


def run_solution_subgraph(state: StudyGraphState) -> list[WorkedSolution]:
    """Invoke the solution subgraph and return updated worked solutions."""

    result = _compiled_solution_subgraph().invoke(state.model_dump(mode="python"))
    validated = StudyGraphState.model_validate(result)
    return validated.worked_solutions


@lru_cache(maxsize=1)
def _compiled_solution_subgraph():
    workflow = StateGraph(StudyGraphState)
    workflow.add_node("plan_solution_steps", _plan_solution_steps_graph_node)
    workflow.add_node("expand_solution_steps", _expand_solution_steps_graph_node)
    workflow.add_node("annotate_common_mistakes", _annotate_common_mistakes_graph_node)
    workflow.add_edge(START, "plan_solution_steps")
    workflow.add_edge("plan_solution_steps", "expand_solution_steps")
    workflow.add_edge("expand_solution_steps", "annotate_common_mistakes")
    workflow.add_edge("annotate_common_mistakes", END)
    return workflow.compile()


def _plan_solution_steps_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    return {
        "worked_solutions": [
            solution.model_dump(mode="python") for solution in plan_solution_steps_node(state)
        ]
    }


def _expand_solution_steps_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    return {
        "worked_solutions": [
            solution.model_dump(mode="python") for solution in expand_solution_steps_node(state)
        ]
    }


def _annotate_common_mistakes_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    return {
        "worked_solutions": [
            solution.model_dump(mode="python")
            for solution in annotate_common_mistakes_node(state)
        ]
    }
