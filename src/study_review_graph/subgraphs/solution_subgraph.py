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
CHINESE_TERM_MAP = {
    "acceleration": "加速度",
    "force": "力",
    "kinetic energy": "动能",
    "mass": "质量",
    "net force": "净力",
    "velocity": "速度",
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
            "先读题，判断这道题到底在练哪个概念或方法。",
            "列出题目已经明确给出的信息。",
            "先用文字解释关系，再决定要不要代入计算。",
            "如果原材料缺少条件，就明确写出 TODO 提醒。",
        ]

    concept_names = _linked_concept_names(formula, state)
    target_label = _target_label(example, formula)
    plan_steps = [
        f"先明确要求什么：目标量是 {target_label}。",
        f"列出已知条件：{_known_values_text(example) or 'TODO: 需要进一步确认题目的已知量。'}",
        f"选择 `{formula.expression}` 作为这道题的主公式，对应 {concept_names[0] if concept_names else '当前方法'}。",
        "代入之前先检查符号、单位和公式适用条件，再开始计算。",
    ]
    if formula.conditions:
        plan_steps.append(f"回到原材料确认条件：{formula.conditions[0]}")
    else:
        plan_steps.append("TODO: 需要先确认本题是否满足公式适用条件。")
    return plan_steps


def _build_detailed_solution(
    example: ExampleArtifact,
    formula: FormulaArtifact | None,
    state: StudyGraphState,
) -> tuple[list[str], list[str]]:
    if not formula:
        return (
            [
                f"先看题意：{example.problem_statement or example.prompt}",
                "先用中文把这道题在练什么讲清楚，再去决定是否需要公式。",
                "TODO: 目前缺少稳定公式，后续应补上更具体的推导过程。",
            ],
            [
                "这是无公式时的保底讲解路径，目的是先保住学习顺序而不是假装已经完整求解。",
            ],
        )

    detailed_steps = [
        f"先把题目主线说清楚：{example.problem_statement}",
        f"这一步要求我们求 { _target_label(example, formula) }，已知量是 {_known_values_text(example)}。",
        f"对应的核心公式是 `{formula.expression}`。",
    ]
    if formula.conditions:
        detailed_steps.append(f"先检查题目是否满足原材料里的条件提醒：{formula.conditions[0]}")
    else:
        detailed_steps.append("TODO: 原材料里没有给出足够清晰的适用条件，需要回源材料确认。")

    substitution_step = _build_substitution_step(example, formula)
    detailed_steps.append(substitution_step)
    detailed_steps.append(
        f"最后把结果放回 {(_linked_concept_names(formula, state) or ['本题'])[0]} 的语境里解释，不要只停在数字本身。"
    )

    rationale = [
        "先讲题意和已知量，可以避免一上来就机械代公式。",
        f"选择 `{formula.expression}` 是因为它正是这道例题所依赖的主关系式。",
    ]
    if formula.conditions:
        rationale.append(f"整段讲解都围绕原材料中的条件提示展开：{formula.conditions[0]}")
    else:
        rationale.append("TODO: 公式条件还需要更强的本地证据支持。")
    if "TODO:" in substitution_step:
        rationale.append("TODO: 数值计算部分还需要结合更明确的条件或变形过程来复核。")

    return detailed_steps, rationale


def _build_common_mistakes(example: ExampleArtifact, formula: FormulaArtifact | None) -> list[str]:
    mistakes = [
        "还没看清题目在求什么，就直接往公式里代数字。",
        "只记住公式外形，没有先检查原材料里的适用条件。",
    ]
    if formula:
        mistakes.append(f"把 `{formula.expression}` 里的符号对应关系弄混，或者把目标量也当成已知量直接代进去。")
    else:
        mistakes.append("把概念解释误当成已经完成的定量解题。")
    if not example.known_values:
        mistakes.append("TODO: 题目给定信息还偏少，后续要先确认已知量再做完整演算。")
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
            "You are refining a grounded Chinese worked solution for study use. "
            "Use only the provided local excerpts, formula data, and example data. "
            "Preserve course-native notation and keep the explanation in the order of intuition, formula, substitution, interpretation, and mistakes. "
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
            "Write the output in Chinese by default. "
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
            return f"{CHINESE_TERM_MAP.get(meaning.lower(), meaning)}（`{example.target_symbol}`）"
    return f"`{example.target_symbol or _left_side_symbol(formula.expression) or '目标量'}`"


def _known_values_text(example: ExampleArtifact) -> str:
    if not example.known_values:
        return ""
    return ", ".join(f"`{symbol}` = {value}" for symbol, value in example.known_values.items())


def _build_substitution_step(example: ExampleArtifact, formula: FormulaArtifact) -> str:
    left_symbol, right_expression = _split_formula(formula.expression)
    if not left_symbol or not right_expression:
        return "TODO: 需要先把公式整理成便于代入的形式，再继续演算。"

    substituted_expression = right_expression.replace("^", "**")
    numeric_values = {
        symbol: _numeric_value(raw_value)
        for symbol, raw_value in example.known_values.items()
    }
    rhs_symbols = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", right_expression)))
    if any(symbol not in numeric_values or numeric_values[symbol] is None for symbol in rhs_symbols):
        return (
            "TODO: 当前例题缺少必要数值，暂时还不能完整代入计算。"
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
            f"把已知量代入 `{formula.expression}` 后继续逐步计算。"
            " TODO: 当前数值计算还需要人工复核。"
        )

    formatted_result = _format_number(result)
    arithmetic_expression = substituted_expression.replace("**", "^")
    return (
        f"逐步代入 `{formula.expression}`："
        f"`{left_symbol} = {arithmetic_expression} = {formatted_result}`。"
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
