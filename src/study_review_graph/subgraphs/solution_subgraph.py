"""Worked-solution subgraph for example expansion."""

from __future__ import annotations

import ast
import operator
import re
from functools import lru_cache
from typing import Any

from study_review_graph.compat import END, START, StateGraph
from study_review_graph.model_client import get_model_client
from study_review_graph.retrieval import retrieve_relevant_chunks
from study_review_graph.state import ExampleArtifact, FormulaArtifact, SourceReference, StudyGraphState, WorkedSolution

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def plan_solution_steps_node(state: StudyGraphState) -> list[WorkedSolution]:
    """Create grounded solution plans for each example."""

    solutions: list[WorkedSolution] = []
    formula_lookup = {formula.formula_id: formula for formula in state.formulas}

    for index, example in enumerate(state.examples):
        formula = _primary_formula(example, formula_lookup)
        solutions.append(
            WorkedSolution(
                solution_id=f"solution-{index}",
                example_id=example.example_id,
                plan_steps=_build_plan_steps(example, formula, state),
                references=_collect_references(example.references, formula.references if formula else []),
            )
        )
    return solutions


def expand_solution_steps_node(state: StudyGraphState) -> list[WorkedSolution]:
    """Expand planned steps into grounded worked explanations."""

    expanded: list[WorkedSolution] = []
    example_lookup = {example.example_id: example for example in state.examples}
    formula_lookup = {formula.formula_id: formula for formula in state.formulas}

    for solution in state.worked_solutions:
        example = example_lookup[solution.example_id]
        formula = _primary_formula(example, formula_lookup)
        detailed_steps, rationale = _build_detailed_solution(example, formula, state)
        expanded.append(
            solution.model_copy(
                update={
                    "detailed_steps": detailed_steps,
                    "rationale": rationale,
                    "references": _collect_references(
                        solution.references,
                        example.references,
                        formula.references if formula else [],
                    ),
                }
            )
        )
    return expanded


def annotate_common_mistakes_node(state: StudyGraphState) -> list[WorkedSolution]:
    """Attach common-mistake reminders and optional LLM refinements."""

    updated: list[WorkedSolution] = []
    example_lookup = {example.example_id: example for example in state.examples}
    formula_lookup = {formula.formula_id: formula for formula in state.formulas}
    model_client = get_model_client()

    for solution in state.worked_solutions:
        example = example_lookup[solution.example_id]
        formula = _primary_formula(example, formula_lookup)
        common_mistakes = _build_common_mistakes(example, formula)
        merged_solution = solution.model_copy(update={"common_mistakes": common_mistakes})
        llm_payload = _generate_solution_enrichment(
            example=example,
            formula=formula,
            solution=merged_solution,
            state=state,
            model_client=model_client,
        )
        if llm_payload:
            merged_solution = merged_solution.model_copy(
                update={
                    "plan_steps": _merge_string_list(
                        merged_solution.plan_steps,
                        llm_payload.get("plan_steps"),
                    ),
                    "detailed_steps": _merge_string_list(
                        merged_solution.detailed_steps,
                        llm_payload.get("detailed_steps"),
                    ),
                    "rationale": _merge_string_list(
                        merged_solution.rationale,
                        llm_payload.get("rationale"),
                    ),
                    "common_mistakes": _merge_string_list(
                        merged_solution.common_mistakes,
                        llm_payload.get("common_mistakes"),
                    ),
                }
            )
        updated.append(merged_solution)
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


def _primary_formula(
    example: ExampleArtifact,
    formula_lookup: dict[str, FormulaArtifact],
) -> FormulaArtifact | None:
    formula_ids = list(example.formula_ids)
    if example.formula_id and example.formula_id not in formula_ids:
        formula_ids.insert(0, example.formula_id)
    for formula_id in formula_ids:
        if formula_id in formula_lookup:
            return formula_lookup[formula_id]
    return None


def _build_plan_steps(
    example: ExampleArtifact,
    formula: FormulaArtifact | None,
    state: StudyGraphState,
) -> list[str]:
    if not formula:
        return [
            "Read the example carefully and identify the main study idea.",
            "List the known information from the problem statement.",
            "Explain the relationship in words before trying to compute anything.",
            "Mark any missing assumptions with TODO notes.",
        ]

    concept_names = _linked_concept_names(formula, state)
    target_label = _target_label(example, formula)
    plan_steps = [
        f"Identify the target quantity: {target_label}.",
        f"List the givens from the example: {_known_values_text(example) or 'TODO: confirm the known quantities.'}",
        f"Use `{formula.expression}` as the governing relationship for {concept_names[0] if concept_names else 'this example'}.",
        "Substitute the known values carefully before interpreting the result.",
    ]
    if formula.conditions:
        plan_steps.append(f"Check the local condition cue: {formula.conditions[0]}")
    else:
        plan_steps.append("TODO: confirm the local conditions or assumptions before final interpretation.")
    return plan_steps


def _build_detailed_solution(
    example: ExampleArtifact,
    formula: FormulaArtifact | None,
    state: StudyGraphState,
) -> tuple[list[str], list[str]]:
    if not formula:
        return (
            [
                f"Start from the problem statement: {example.problem_statement or example.prompt}",
                "Explain the relevant concept in plain language using the local study material.",
                "TODO: add a more specific worked derivation when a supporting formula is available.",
            ],
            [
                "This fallback path preserves a study explanation even when no formula is available.",
            ],
        )

    detailed_steps = [
        f"Restate the task: {example.problem_statement}",
        f"Identify the target as { _target_label(example, formula) } and collect the givens: {_known_values_text(example)}.",
        f"Write the governing relationship: `{formula.expression}`.",
    ]
    if formula.conditions:
        detailed_steps.append(f"Check that the local condition cue fits the example: {formula.conditions[0]}")
    else:
        detailed_steps.append("TODO: confirm the exact assumptions for applying this formula.")

    substitution_step = _build_substitution_step(example, formula)
    detailed_steps.append(substitution_step)
    detailed_steps.append(
        f"Interpret the result in the language of {(_linked_concept_names(formula, state) or ['the example'])[0]} rather than stopping at the numeric output."
    )

    rationale = [
        "The solution starts by identifying the target and givens so the algebra stays tied to the study goal.",
        f"`{formula.expression}` is used because it is the main relationship attached to this example.",
    ]
    if formula.conditions:
        rationale.append(f"The explanation stays local to the source cue: {formula.conditions[0]}")
    else:
        rationale.append("TODO: verify the formula conditions against stronger nearby evidence.")
    if "TODO:" in substitution_step:
        rationale.append("TODO: the numerical computation should be checked if the formula needs rearrangement or more assumptions.")

    return detailed_steps, rationale


def _build_common_mistakes(example: ExampleArtifact, formula: FormulaArtifact | None) -> list[str]:
    mistakes = [
        "Skipping the step where the target quantity is identified before substituting values.",
        "Using memorized algebra without checking whether the local formula conditions actually apply.",
    ]
    if formula:
        mistakes.append(f"Mixing up the symbols in `{formula.expression}` or substituting the wrong value for the target quantity.")
    else:
        mistakes.append("Treating a concept explanation as if it were already a solved quantitative example.")
    if not example.known_values:
        mistakes.append("TODO: verify the givens if the example statement is still too qualitative.")
    return mistakes


def _generate_solution_enrichment(
    *,
    example: ExampleArtifact,
    formula: FormulaArtifact | None,
    solution: WorkedSolution,
    state: StudyGraphState,
    model_client,
) -> dict[str, Any] | None:
    if not formula:
        return None

    supporting_chunks = retrieve_relevant_chunks(
        " ".join(
            part
            for part in [
                example.problem_statement,
                formula.expression,
                " ".join(formula.conditions[:1]),
                " ".join(_linked_concept_names(formula, state)),
            ]
            if part
        ),
        state,
        top_k=2,
    )
    if not supporting_chunks:
        return None

    result = model_client.generate_json(
        task_name=f"worked solution '{solution.solution_id}'",
        system_prompt=(
            "You are refining a grounded worked solution for study use. "
            "Use only the provided local excerpts, formula data, and example data. "
            "Do not invent extra formulas or unsupported mathematical claims. "
            "Return JSON with keys: plan_steps, detailed_steps, rationale, common_mistakes."
        ),
        user_prompt=(
            f"Course: {state.course_name}\n"
            f"User goal: {state.user_goal}\n"
            f"Example title: {example.title}\n"
            f"Problem statement: {example.problem_statement}\n"
            f"Difficulty: {example.difficulty}\n"
            f"Study value: {example.study_value}\n"
            f"Known values: {example.known_values}\n"
            f"Target symbol: {example.target_symbol}\n"
            f"Formula expression: {formula.expression}\n"
            f"Symbol explanations: {formula.symbol_explanations}\n"
            f"Formula conditions: {formula.conditions}\n"
            f"Linked concepts: {_linked_concept_names(formula, state)}\n"
            f"Current plan steps: {solution.plan_steps}\n"
            f"Current detailed steps: {solution.detailed_steps}\n"
            f"Current rationale: {solution.rationale}\n"
            f"Current common mistakes: {solution.common_mistakes}\n\n"
            "Retrieved local excerpts:\n"
            f"{_render_chunk_context(supporting_chunks)}\n\n"
            "Improve the teaching clarity while staying close to the same formula and local evidence. "
            "If evidence is weak, keep TODO markers instead of pretending certainty."
        ),
    )
    return result.payload if result.payload else None


def _linked_concept_names(formula: FormulaArtifact, state: StudyGraphState) -> list[str]:
    concept_lookup = {concept.concept_id: concept.name for concept in state.concepts}
    return [concept_lookup[concept_id] for concept_id in formula.concept_links if concept_id in concept_lookup]


def _target_label(example: ExampleArtifact, formula: FormulaArtifact) -> str:
    if example.target_symbol and example.target_symbol in formula.symbol_explanations:
        meaning = formula.symbol_explanations[example.target_symbol]
        if meaning and "TODO:" not in meaning:
            return f"{meaning} (`{example.target_symbol}`)"
    return f"`{example.target_symbol or _left_side_symbol(formula.expression) or 'target quantity'}`"


def _known_values_text(example: ExampleArtifact) -> str:
    if not example.known_values:
        return ""
    return ", ".join(f"`{symbol}` = {value}" for symbol, value in example.known_values.items())


def _build_substitution_step(example: ExampleArtifact, formula: FormulaArtifact) -> str:
    left_symbol, right_expression = _split_formula(formula.expression)
    if not left_symbol or not right_expression:
        return "TODO: restate the formula in a simple solved form before substituting values."

    substituted_expression = right_expression.replace("^", "**")
    numeric_values = {
        symbol: _numeric_value(raw_value)
        for symbol, raw_value in example.known_values.items()
    }
    rhs_symbols = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", right_expression)))
    if any(symbol not in numeric_values or numeric_values[symbol] is None for symbol in rhs_symbols):
        return (
            "TODO: confirm the numeric givens needed for substitution; the current example data is incomplete."
        )

    for symbol in sorted(rhs_symbols, key=len, reverse=True):
        substituted_expression = re.sub(
            rf"\b{re.escape(symbol)}\b",
            _format_number(numeric_values[symbol]),
            substituted_expression,
        )

    result = _safe_eval(substituted_expression)
    if result is None:
        return (
            f"Substitute the known values into `{formula.expression}` and carry out the arithmetic carefully. "
            "TODO: check the exact numerical evaluation."
        )

    formatted_result = _format_number(result)
    arithmetic_expression = substituted_expression.replace("**", "^")
    return (
        f"Substitute the givens into `{formula.expression}`: "
        f"`{left_symbol} = {arithmetic_expression} = {formatted_result}`."
    )


def _split_formula(expression: str) -> tuple[str | None, str | None]:
    left, separator, right = expression.partition("=")
    if not separator:
        return None, None
    return left.strip() or None, right.strip() or None


def _left_side_symbol(expression: str) -> str | None:
    left, _right = _split_formula(expression)
    return left


def _numeric_value(raw_value: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", raw_value)
    if not match:
        return None
    return float(match.group(0))


def _safe_eval(expression: str) -> float | None:
    try:
        node = ast.parse(expression, mode="eval")
        return float(_eval_ast(node.body))
    except Exception:
        return None


def _eval_ast(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPERATORS:
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        return SAFE_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPERATORS:
        return SAFE_OPERATORS[type(node.op)](_eval_ast(node.operand))
    raise ValueError("Unsupported expression")


def _merge_string_list(existing: list[str], candidate: Any) -> list[str]:
    if not isinstance(candidate, list):
        return existing
    cleaned = [str(item).strip() for item in candidate if str(item).strip()]
    return cleaned or existing


def _collect_references(*reference_groups: list[SourceReference]) -> list[SourceReference]:
    references: list[SourceReference] = []
    seen: set[tuple[str, str | None]] = set()
    for group in reference_groups:
        for reference in group:
            key = (reference.source_path, reference.chunk_id)
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
    return references


def _render_chunk_context(chunks) -> str:
    lines = []
    for chunk in chunks:
        lines.append(f"- {chunk.source_path} [{chunk.chunk_id}]: {chunk.text[:500].strip()}")
    return "\n".join(lines)


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")
