"""Practice-set generation node built from grounded study artifacts."""

from __future__ import annotations

from study_review_graph.model_client import get_model_client
from study_review_graph.retrieval import retrieve_relevant_chunks
from study_review_graph.state import (
    ConceptRecord,
    ExampleArtifact,
    FormulaArtifact,
    PracticeItem,
    SourceReference,
    StudyGraphState,
    WorkedSolution,
)


def generate_practice_set_node(state: StudyGraphState) -> tuple[list[PracticeItem], list[str]]:
    """Generate a compact grounded practice set from existing workflow artifacts."""

    if not state.config.include_practice_set:
        return [], []

    warnings: list[str] = []
    model_client = get_model_client()
    model_warning = model_client.availability_warning()
    if model_warning:
        warnings.append(model_warning)

    items: list[PracticeItem] = []

    concept = _primary_concept(state)
    if concept:
        draft = _build_concept_question(concept, state)
        refined, warning = _refine_practice_item(draft, state, model_client)
        if warning and warning not in warnings:
            warnings.append(warning)
        items.append(refined)

    formula = _primary_formula(state)
    if formula:
        draft = _build_formula_application_question(formula, state)
        refined, warning = _refine_practice_item(draft, state, model_client)
        if warning and warning not in warnings:
            warnings.append(warning)
        items.append(refined)

    example, solution = _primary_calculation_pair(state)
    if example:
        draft = _build_calculation_question(example, solution, state)
        refined, warning = _refine_practice_item(draft, state, model_client)
        if warning and warning not in warnings:
            warnings.append(warning)
        items.append(refined)

    return items, warnings


def _build_concept_question(concept: ConceptRecord, state: StudyGraphState) -> PracticeItem:
    related_formula_ids = _related_formula_ids_for_concept(concept, state)
    prompt = (
        f"请用课程里的记号和术语解释“{concept.name}”在本章里到底在解决什么问题。"
        "回答时要说明它和哪些量、公式或题型有关。"
    )
    hint = (
        "先从本章主线切入，再回到原材料里的定义或描述；"
        "不要只背名词，要说清它为什么重要。"
    )
    expected_answer = (
        f"参考答案：应先说明“{concept.name}”的核心含义。"
        f"{(' 可进一步联系 ' + '、'.join(related_formula_ids) + ' 这些公式。') if related_formula_ids else ''}"
        f"{(' 原材料依据：' + concept.description) if concept.description else ' TODO: 需要回原材料补充更直接的定义句。'}"
    )
    return PracticeItem(
        practice_id="practice-concept-0",
        question_type="concept_question",
        concept_ids=[concept.concept_id],
        formula_ids=related_formula_ids,
        prompt=prompt,
        hint=hint,
        expected_answer=expected_answer,
        references=concept.references,
    )


def _build_formula_application_question(formula: FormulaArtifact, state: StudyGraphState) -> PracticeItem:
    concept_names = _linked_concept_names(formula, state)
    prompt = (
        f"题目：在什么情况下你应该想到使用 `{formula.expression}`？"
        "请结合题目中会出现的已知量、目标量和适用条件，用 2-4 句说明。"
    )
    hint = (
        f"先说这条公式连接了哪些量，再检查适用条件："
        f"{formula.conditions[0] if formula.conditions else 'TODO: 需要确认适用条件。'}"
    )
    expected_answer = (
        f"参考思路：当题目要求你处理与 `{formula.expression}` 对应的量关系时，"
        "先确认已知量是否齐全，再确认公式条件是否满足。"
        f"{(' 这通常和 ' + '、'.join(concept_names) + ' 相关。') if concept_names else ''}"
    )
    return PracticeItem(
        practice_id="practice-formula-0",
        question_type="formula_application",
        concept_ids=list(formula.concept_links),
        formula_ids=[formula.formula_id],
        prompt=prompt,
        hint=hint,
        expected_answer=expected_answer,
        references=formula.references,
    )


def _build_calculation_question(
    example: ExampleArtifact,
    solution: WorkedSolution | None,
    state: StudyGraphState,
) -> PracticeItem:
    formula_ids = list(example.formula_ids)
    prompt = example.problem_statement or example.prompt or "TODO: 需要补题目。"
    hint = (
        f"先判断这题在练什么：{example.study_value or 'TODO: 需要补充复习价值。'}"
        " 再按“列已知量 -> 选公式 -> 逐步代入”的顺序写。"
    )
    if solution and solution.detailed_steps:
        answer = "标准解法 / 关键步骤：" + " ".join(solution.detailed_steps[:4])
    else:
        answer = "标准解法 / 关键步骤：TODO: 需要结合 worked_solutions 补出关键步骤。"
    references = _collect_references([example.references, solution.references if solution else []])
    return PracticeItem(
        practice_id="practice-calculation-0",
        question_type="worked_calculation",
        concept_ids=_concept_ids_for_example(example, state),
        formula_ids=formula_ids,
        prompt=prompt,
        hint=hint,
        expected_answer=answer,
        references=references,
    )


def _refine_practice_item(
    item: PracticeItem,
    state: StudyGraphState,
    model_client,
) -> tuple[PracticeItem, str | None]:
    supporting_chunks = _retrieve_practice_support(item, state)
    if not supporting_chunks:
        return item, None

    result = model_client.generate_json(
        task_name=f"practice item '{item.practice_id}'",
        system_prompt=(
            "You are refining a grounded Chinese study practice question. "
            "Use only the provided local excerpts and current artifact metadata. "
            "Do not invent unrelated facts or unsupported topics. "
            "Return JSON with keys: prompt, hint, expected_answer."
        ),
        user_prompt=(
            f"Course: {state.course_name}\n"
            f"User goal: {state.user_goal}\n"
            f"Question type: {item.question_type}\n"
            f"Concept IDs: {item.concept_ids}\n"
            f"Formula IDs: {item.formula_ids}\n"
            f"Draft prompt: {item.prompt}\n"
            f"Draft hint: {item.hint}\n"
            f"Draft expected answer: {item.expected_answer}\n"
            f"Review-note mode: {state.review_notes.mode}\n"
            f"Review-note cues: {state.review_notes.study_questions[:3]}\n\n"
            "Retrieved local excerpts:\n"
            f"{_render_chunk_context(supporting_chunks)}\n\n"
            "Improve clarity for practice and review. "
            "Stay close to the same course notation and material."
        ),
    )
    if not result.payload:
        return item, result.warning

    updated = item.model_copy(
        update={
            "prompt": str(result.payload.get("prompt", item.prompt)).strip() or item.prompt,
            "hint": str(result.payload.get("hint", item.hint)).strip() or item.hint,
            "expected_answer": (
                str(result.payload.get("expected_answer", item.expected_answer)).strip()
                or item.expected_answer
            ),
        }
    )
    return updated, result.warning


def _retrieve_practice_support(item: PracticeItem, state: StudyGraphState):
    query_parts = [item.prompt, item.hint]
    for formula in state.formulas:
        if formula.formula_id in item.formula_ids:
            query_parts.append(formula.expression)
            query_parts.extend(formula.conditions[:1])
    for concept in state.concepts:
        if concept.concept_id in item.concept_ids:
            query_parts.append(concept.name)
    return retrieve_relevant_chunks(" ".join(part for part in query_parts if part), state, top_k=2)


def _primary_concept(state: StudyGraphState) -> ConceptRecord | None:
    return state.concepts[0] if state.concepts else None


def _primary_formula(state: StudyGraphState) -> FormulaArtifact | None:
    return state.formulas[0] if state.formulas else None


def _primary_calculation_pair(state: StudyGraphState) -> tuple[ExampleArtifact | None, WorkedSolution | None]:
    if not state.examples:
        return None, None
    example = state.examples[0]
    solution_lookup = {solution.example_id: solution for solution in state.worked_solutions}
    return example, solution_lookup.get(example.example_id)


def _linked_concept_names(formula: FormulaArtifact, state: StudyGraphState) -> list[str]:
    concept_lookup = {concept.concept_id: concept.name for concept in state.concepts}
    return [concept_lookup[concept_id] for concept_id in formula.concept_links if concept_id in concept_lookup]


def _related_formula_ids_for_concept(concept: ConceptRecord, state: StudyGraphState) -> list[str]:
    formula_ids = list(concept.related_formula_ids)
    for formula in state.formulas:
        if concept.concept_id in formula.concept_links and formula.formula_id not in formula_ids:
            formula_ids.append(formula.formula_id)
    return formula_ids


def _concept_ids_for_example(example: ExampleArtifact, state: StudyGraphState) -> list[str]:
    formula_lookup = {formula.formula_id: formula for formula in state.formulas}
    concept_ids: list[str] = []
    for formula_id in example.formula_ids:
        formula = formula_lookup.get(formula_id)
        if not formula:
            continue
        for concept_id in formula.concept_links:
            if concept_id not in concept_ids:
                concept_ids.append(concept_id)
    return concept_ids


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
