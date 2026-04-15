"""Grounded answer-checking utility for one practice item at a time."""

from __future__ import annotations

import re

from study_review_graph.model_client import get_model_client
from study_review_graph.retrieval import retrieve_relevant_chunks
from study_review_graph.state import (
    AnswerFeedback,
    ConceptRecord,
    FormulaArtifact,
    PracticeItem,
    SourceReference,
    StudyGraphState,
    WorkedSolution,
)

FEEDBACK_LABEL_ZH = {
    "correct": "基本正确",
    "partially_correct": "部分正确",
    "needs_improvement": "需要改进",
}


def check_answer_node(
    state: StudyGraphState,
    *,
    practice_id: str,
    user_answer: str,
) -> tuple[AnswerFeedback, list[str]]:
    """Check one user answer against the current grounded practice artifacts."""

    practice_item = _find_practice_item(state, practice_id)
    if practice_item is None:
        raise ValueError(f"Could not find practice item '{practice_id}'.")

    related_formulas = _related_formulas(practice_item, state)
    related_concepts = _related_concepts(practice_item, state)
    linked_examples, linked_solutions = _related_examples_and_solutions(practice_item, state)

    feedback = _build_heuristic_feedback(
        practice_item=practice_item,
        user_answer=user_answer,
        formulas=related_formulas,
        concepts=related_concepts,
        linked_examples=linked_examples,
        linked_solutions=linked_solutions,
    )

    warnings: list[str] = []
    model_client = get_model_client()
    model_warning = model_client.availability_warning()
    if model_warning:
        warnings.append(model_warning)

    refined_feedback, refine_warning = _refine_feedback(
        feedback=feedback,
        practice_item=practice_item,
        state=state,
        model_client=model_client,
    )
    if refine_warning and refine_warning not in warnings:
        warnings.append(refine_warning)

    return refined_feedback, warnings


def feedback_label_zh(label: str) -> str:
    """Return the Chinese label used in markdown output and CLI summaries."""

    return FEEDBACK_LABEL_ZH.get(label, label)


def _find_practice_item(state: StudyGraphState, practice_id: str) -> PracticeItem | None:
    for item in state.practice_items:
        if item.practice_id == practice_id:
            return item
    return None


def _build_heuristic_feedback(
    *,
    practice_item: PracticeItem,
    user_answer: str,
    formulas: list[FormulaArtifact],
    concepts: list[ConceptRecord],
    linked_examples,
    linked_solutions: list[WorkedSolution],
) -> AnswerFeedback:
    normalized_answer = _normalize_text(user_answer)
    answer_tokens = _extract_tokens(user_answer)
    expected_text = " ".join(
        [practice_item.expected_answer]
        + [formula.expression for formula in formulas]
        + [concept.name for concept in concepts]
        + [solution_text for solution in linked_solutions for solution_text in solution.detailed_steps[:3]]
    )
    expected_tokens = _extract_tokens(expected_text)
    overlap_ratio = _token_overlap_ratio(answer_tokens, expected_tokens)

    linked_formula_match = any(
        _normalize_formula(formula.expression) in normalized_answer
        or _formula_symbol_overlap(formula.expression, answer_tokens)
        for formula in formulas
    )
    wrong_formula_mentioned = any(
        token in {"ke", "ek"} for token in answer_tokens
    ) and not any("E_k" in formula.expression for formula in formulas)

    reasoning_markers = sum(
        1
        for marker in ("先", "再", "因为", "所以", "条件", "代入", "公式", "概念")
        if marker in user_answer
    )

    label = _classify_feedback(
        overlap_ratio=overlap_ratio,
        linked_formula_match=linked_formula_match,
        wrong_formula_mentioned=wrong_formula_mentioned,
        reasoning_markers=reasoning_markers,
        question_type=practice_item.question_type,
    )

    key_issues = _build_key_issues(
        label=label,
        overlap_ratio=overlap_ratio,
        linked_formula_match=linked_formula_match,
        wrong_formula_mentioned=wrong_formula_mentioned,
        reasoning_markers=reasoning_markers,
        practice_item=practice_item,
    )
    correct_approach = _build_correct_approach(practice_item, formulas, linked_solutions)
    review_guidance = _build_review_guidance(concepts, formulas, linked_examples, linked_solutions)
    references = _collect_references(
        [practice_item.references]
        + [formula.references for formula in formulas]
        + [concept.references for concept in concepts]
        + [example.references for example in linked_examples]
        + [solution.references for solution in linked_solutions]
    )

    return AnswerFeedback(
        practice_id=practice_item.practice_id,
        question_type=practice_item.question_type,
        result_label=label,
        question_prompt=practice_item.prompt,
        user_answer=user_answer,
        concept_ids=list(practice_item.concept_ids),
        formula_ids=list(practice_item.formula_ids),
        linked_examples=[example.example_id for example in linked_examples],
        linked_solutions=[solution.solution_id for solution in linked_solutions],
        key_issues=key_issues,
        correct_approach=correct_approach,
        review_guidance=review_guidance,
        references=references,
    )


def _classify_feedback(
    *,
    overlap_ratio: float,
    linked_formula_match: bool,
    wrong_formula_mentioned: bool,
    reasoning_markers: int,
    question_type: str,
) -> str:
    if wrong_formula_mentioned and overlap_ratio < 0.45:
        return "needs_improvement"
    if overlap_ratio >= 0.6 and (linked_formula_match or question_type == "concept_question"):
        return "correct"
    if overlap_ratio >= 0.3 or linked_formula_match or reasoning_markers >= 2:
        return "partially_correct"
    return "needs_improvement"


def _build_key_issues(
    *,
    label: str,
    overlap_ratio: float,
    linked_formula_match: bool,
    wrong_formula_mentioned: bool,
    reasoning_markers: int,
    practice_item: PracticeItem,
) -> list[str]:
    issues: list[str] = []
    if label == "correct":
        issues.append("你的主要思路和当前练习题的参考答案基本一致。")
    if wrong_formula_mentioned:
        issues.append("答案里出现了与本题不匹配的公式 / 概念线索，容易把题型带偏。")
    if practice_item.question_type != "concept_question" and not linked_formula_match:
        issues.append("答案里没有明确点出本题对应的核心公式或公式关系。")
    if overlap_ratio < 0.3:
        issues.append("答案缺少题目要求的关键概念、条件或结论。")
    if practice_item.question_type == "worked_calculation" and reasoning_markers < 2:
        issues.append("答案给出的推理步骤偏少，计算或代入过程还不够完整。")
    if not issues:
        issues.append("整体方向对了，但还可以把关键条件和步骤说得更完整。")
    return issues


def _build_correct_approach(
    practice_item: PracticeItem,
    formulas: list[FormulaArtifact],
    linked_solutions: list[WorkedSolution],
) -> list[str]:
    lines = [
        "先回到题目本身，确认它到底在问什么。",
        practice_item.expected_answer or "TODO: 需要补足当前题目的参考答案。",
    ]
    if formulas:
        lines.append(
            "本题优先应想到的公式是："
            + "、".join(f"`{formula.expression}`" for formula in formulas)
        )
    if linked_solutions and linked_solutions[0].detailed_steps:
        lines.extend(linked_solutions[0].detailed_steps[:3])
    return lines


def _build_review_guidance(
    concepts: list[ConceptRecord],
    formulas: list[FormulaArtifact],
    linked_examples,
    linked_solutions: list[WorkedSolution],
) -> list[str]:
    guidance: list[str] = []
    guidance.extend(f"回看概念：{concept.name}（`{concept.concept_id}`）" for concept in concepts[:3])
    guidance.extend(
        f"回看公式：`{formula.formula_id}` 对应 `{formula.expression}`" for formula in formulas[:3]
    )
    guidance.extend(
        f"回看例题：{example.title}（`{example.example_id}`）" for example in linked_examples[:2]
    )
    guidance.extend(
        f"回看详解：`{solution.solution_id}`" for solution in linked_solutions[:2]
    )
    return guidance or ["TODO: 当前还缺少足够的 grounded artifact 来给出回看建议。"]


def _refine_feedback(
    *,
    feedback: AnswerFeedback,
    practice_item: PracticeItem,
    state: StudyGraphState,
    model_client,
) -> tuple[AnswerFeedback, str | None]:
    supporting_chunks = retrieve_relevant_chunks(
        " ".join(
            part
            for part in [practice_item.prompt, practice_item.expected_answer, feedback.user_answer]
            if part
        ),
        state,
        top_k=2,
    )
    if not supporting_chunks:
        return feedback, None

    result = model_client.generate_json(
        task_name=f"answer feedback '{feedback.practice_id}'",
        system_prompt=(
            "You are refining grounded Chinese study feedback for one practice answer. "
            "Use only the provided local excerpts and baseline feedback. "
            "Do not change the result label. "
            "Return JSON with keys: key_issues, correct_approach, review_guidance."
        ),
        user_prompt=(
            f"Practice ID: {feedback.practice_id}\n"
            f"Question type: {feedback.question_type}\n"
            f"Question prompt: {feedback.question_prompt}\n"
            f"User answer: {feedback.user_answer}\n"
            f"Result label: {feedback.result_label}\n"
            f"Baseline key issues: {feedback.key_issues}\n"
            f"Baseline correct approach: {feedback.correct_approach}\n"
            f"Baseline review guidance: {feedback.review_guidance}\n\n"
            "Retrieved local excerpts:\n"
            f"{_render_chunk_context(supporting_chunks)}\n\n"
            "Improve clarity and pedagogical usefulness while staying grounded."
        ),
    )
    if not result.payload:
        return feedback, result.warning

    return (
        feedback.model_copy(
            update={
                "key_issues": _merge_string_list(feedback.key_issues, result.payload.get("key_issues")),
                "correct_approach": _merge_string_list(
                    feedback.correct_approach,
                    result.payload.get("correct_approach"),
                ),
                "review_guidance": _merge_string_list(
                    feedback.review_guidance,
                    result.payload.get("review_guidance"),
                ),
            }
        ),
        result.warning,
    )


def _related_formulas(practice_item: PracticeItem, state: StudyGraphState) -> list[FormulaArtifact]:
    formula_lookup = {formula.formula_id: formula for formula in state.formulas}
    return [formula_lookup[formula_id] for formula_id in practice_item.formula_ids if formula_id in formula_lookup]


def _related_concepts(practice_item: PracticeItem, state: StudyGraphState) -> list[ConceptRecord]:
    concept_lookup = {concept.concept_id: concept for concept in state.concepts}
    return [concept_lookup[concept_id] for concept_id in practice_item.concept_ids if concept_id in concept_lookup]


def _related_examples_and_solutions(practice_item: PracticeItem, state: StudyGraphState):
    linked_examples = [
        example
        for example in state.examples
        if any(formula_id in practice_item.formula_ids for formula_id in example.formula_ids)
    ]
    solution_lookup = {solution.example_id: solution for solution in state.worked_solutions}
    linked_solutions = [
        solution_lookup[example.example_id]
        for example in linked_examples
        if example.example_id in solution_lookup
    ]
    return linked_examples, linked_solutions


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text.lower())


def _extract_tokens(text: str) -> set[str]:
    return set(token.lower() for token in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text))


def _token_overlap_ratio(answer_tokens: set[str], expected_tokens: set[str]) -> float:
    if not expected_tokens:
        return 0.0
    return len(answer_tokens & expected_tokens) / len(expected_tokens)


def _normalize_formula(expression: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", expression.lower())


def _formula_symbol_overlap(expression: str, answer_tokens: set[str]) -> bool:
    symbols = {token.lower() for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expression)}
    return len(symbols & answer_tokens) >= max(1, min(2, len(symbols)))


def _merge_string_list(existing: list[str], candidate) -> list[str]:
    if not isinstance(candidate, list):
        return existing
    cleaned = [str(item).strip() for item in candidate if str(item).strip()]
    return cleaned or existing


def _collect_references(reference_groups: list[list[SourceReference]]) -> list[SourceReference]:
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
    return "\n".join(
        f"- {chunk.source_path} [{chunk.chunk_id}]: {chunk.text[:500].strip()}"
        for chunk in chunks
    )
