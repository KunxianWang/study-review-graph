"""Review-note generation node with skill-aligned output modes."""

from __future__ import annotations

from dataclasses import dataclass

from study_review_graph.state import (
    ConceptRecord,
    ExampleArtifact,
    FormulaArtifact,
    ReviewNotes,
    SourceReference,
    StudyGraphState,
    WorkedSolution,
)


@dataclass
class FocusSelection:
    """Resolved focus target for deep-dive review mode."""

    label: str
    formula: FormulaArtifact | None = None
    concept: ConceptRecord | None = None
    example: ExampleArtifact | None = None
    solution: WorkedSolution | None = None
    selection_note: str | None = None


def generate_review_notes_node(state: StudyGraphState) -> ReviewNotes:
    """Assemble skill-aligned review notes from prior grounded artifacts."""

    if state.config.study_mode == "deep_dive":
        return _build_deep_dive_notes(state)
    if state.config.study_mode == "exam_sprint":
        return _build_exam_sprint_notes(state)
    return _build_full_review_notes(state)


def _build_full_review_notes(state: StudyGraphState) -> ReviewNotes:
    return ReviewNotes(
        mode="full_review",
        concise_summary=_build_chapter_mainline(state),
        formula_highlights=_build_full_review_formulas(state),
        detailed_explanations=_build_method_explanations(state),
        example_highlights=_build_full_review_examples(state),
        common_mistakes=_collect_common_mistakes(state),
        study_questions=_build_quick_review(state),
        references=_collect_references(state),
    )


def _build_deep_dive_notes(state: StudyGraphState) -> ReviewNotes:
    selection = _select_focus_target(state)
    return ReviewNotes(
        mode="deep_dive",
        focus_target=selection.label,
        focus_selection_note=selection.selection_note,
        concise_summary=_build_focus_problem_lines(selection),
        detailed_explanations=_build_focus_core_ideas(selection),
        formula_highlights=_build_focus_formula_lines(selection),
        example_highlights=_build_focus_example_lines(selection),
        common_mistakes=_build_focus_mistakes(selection),
        study_questions=_build_focus_process_lines(selection),
        references=_collect_focus_references(selection),
    )


def _build_exam_sprint_notes(state: StudyGraphState) -> ReviewNotes:
    return ReviewNotes(
        mode="exam_sprint",
        concise_summary=_build_exam_definitions(state),
        formula_highlights=_build_exam_formula_lines(state),
        detailed_explanations=_build_exam_points(state),
        example_highlights=_build_exam_example_lines(state),
        study_questions=_build_exam_reminders(state),
        common_mistakes=_collect_common_mistakes(state),
        references=_collect_references(state),
    )


def _build_chapter_mainline(state: StudyGraphState) -> list[str]:
    lines: list[str] = []
    if state.concepts:
        concept_names = "、".join(concept.name for concept in state.concepts[:4])
        lines.append(f"本章主要围绕 {concept_names} 这些核心概念展开。")
    if state.formulas:
        formula_names = "、".join(formula.expression for formula in state.formulas[:3])
        lines.append(f"从解题主线看，最重要的关系式包括 {formula_names}。")
    if state.examples:
        lines.append("学习顺序建议是先理解概念和适用条件，再看例题如何把公式落到具体计算。")
    if not lines:
        lines.append("TODO: 当前材料过少，尚无法稳定总结本章主线。")
    return lines


def _build_full_review_formulas(state: StudyGraphState) -> list[str]:
    lines: list[str] = []
    for formula in state.formulas[:5]:
        lines.append(f"### 公式 {formula.formula_id}")
        lines.append(formula.expression)
        if formula.symbol_explanations:
            for symbol, meaning in list(formula.symbol_explanations.items())[:4]:
                lines.append(f"- {symbol} 表示 {meaning}")
        else:
            lines.append("- TODO: 需要补充符号说明。")
        lines.append(
            f"- 条件提醒：{formula.conditions[0] if formula.conditions else 'TODO: 需要确认适用条件。'}"
        )
        lines.append("")
    if not lines:
        lines.append("TODO: 当前材料中还没有稳定提取到关键公式。")
    return _trim_trailing_blank(lines)


def _build_method_explanations(state: StudyGraphState) -> list[str]:
    explanations: list[str] = []
    concept_lookup = {concept.concept_id: concept.name for concept in state.concepts}
    for formula in state.formulas[:5]:
        linked_concepts = [
            concept_lookup[concept_id]
            for concept_id in formula.concept_links
            if concept_id in concept_lookup
        ]
        concept_text = linked_concepts[0] if linked_concepts else "该方法"
        condition_text = formula.conditions[0] if formula.conditions else "TODO: 适用条件尚需结合原文确认。"
        explanations.append(
            f"{concept_text} 的核心关系是 {formula.expression}。"
            f"理解时先抓住它在解决什么量之间的关系，再检查是否满足“{condition_text}”。"
        )
    if not explanations:
        for concept in state.concepts[:3]:
            explanations.append(
                f"{concept.name}：先理解它在本章主线中的作用，再回到原材料确认定义和符号。"
            )
    if not explanations:
        explanations.append("TODO: 当前材料还不足以逐个讲清主要方法。")
    return explanations


def _build_full_review_examples(state: StudyGraphState) -> list[str]:
    if not state.examples:
        return ["TODO: 当前材料过少，例题部分还需要补充。"]

    solution_lookup = {solution.example_id: solution for solution in state.worked_solutions}
    lines: list[str] = []
    for example in state.examples[:3]:
        lines.append(f"### {example.title}")
        lines.append(example.problem_statement or example.prompt or "TODO")
        if example.study_value:
            lines.append(f"- 为什么值得做：{example.study_value}")
        solution = solution_lookup.get(example.example_id)
        if solution and solution.detailed_steps:
            lines.append("关键步骤：")
            lines.extend(f"- {step}" for step in solution.detailed_steps[:3])
        else:
            lines.append("TODO: 还需要补出这题的关键步骤。")
        lines.append("")
    return _trim_trailing_blank(lines)


def _build_quick_review(state: StudyGraphState) -> list[str]:
    review_lines: list[str] = []
    for formula in state.formulas[:3]:
        review_lines.append(
            f"看到 {formula.expression} 时，先检查题目在求什么、已知量够不够、适用条件是否满足。"
        )
    for concept in state.concepts[:2]:
        review_lines.append(f"考前至少要能用自己的话解释“{concept.name}”在本章里为什么重要。")
    if not review_lines:
        review_lines.append("TODO: 当前材料过少，考前速记版只能在补充内容后生成。")
    return review_lines


def _select_focus_target(state: StudyGraphState) -> FocusSelection:
    requested_focus = (state.config.focus_topic or "").strip()
    if requested_focus:
        matched = _match_focus_target(requested_focus, state)
        if matched:
            return matched

    auto_selected = _auto_select_focus_target(state)
    if requested_focus:
        auto_selected.selection_note = (
            f"未找到与 “{requested_focus}” 完全匹配的主题，本次自动改为聚焦 “{auto_selected.label}”。"
        )
    else:
        auto_selected.selection_note = f"未指定 focus_topic，本次自动选择 “{auto_selected.label}” 作为 deep_dive 主题。"
    return auto_selected


def _match_focus_target(query: str, state: StudyGraphState) -> FocusSelection | None:
    normalized_query = _normalize_text(query)
    formula_lookup = {formula.formula_id: formula for formula in state.formulas}
    concept_lookup = {concept.concept_id: concept for concept in state.concepts}
    example_lookup = {example.example_id: example for example in state.examples}
    solution_lookup = {solution.example_id: solution for solution in state.worked_solutions}

    for formula in state.formulas:
        search_space = [
            formula.formula_id,
            formula.expression,
            *formula.concept_links,
            *formula.symbol_explanations.values(),
        ]
        if any(normalized_query in _normalize_text(item) for item in search_space if item):
            concept = _best_linked_concept(formula, concept_lookup)
            example = _example_for_formula(formula, state)
            return FocusSelection(
                label=concept.name if concept else formula.expression,
                formula=formula,
                concept=concept,
                example=example,
                solution=solution_lookup.get(example.example_id) if example else None,
            )

    for concept in state.concepts:
        if normalized_query in _normalize_text(concept.name):
            formula = _formula_for_concept(concept, formula_lookup, state)
            example = _example_for_formula(formula, state) if formula else _example_for_concept(concept, state)
            return FocusSelection(
                label=concept.name,
                concept=concept,
                formula=formula,
                example=example,
                solution=solution_lookup.get(example.example_id) if example else None,
            )

    for example in state.examples:
        if normalized_query in _normalize_text(example.title) or normalized_query in _normalize_text(example.example_id):
            formula = _formula_for_example(example, formula_lookup)
            concept = _best_linked_concept(formula, concept_lookup) if formula else None
            return FocusSelection(
                label=example.title,
                formula=formula,
                concept=concept,
                example=example,
                solution=solution_lookup.get(example.example_id),
            )

    return None


def _auto_select_focus_target(state: StudyGraphState) -> FocusSelection:
    formula_lookup = {formula.formula_id: formula for formula in state.formulas}
    concept_lookup = {concept.concept_id: concept for concept in state.concepts}
    solution_lookup = {solution.example_id: solution for solution in state.worked_solutions}

    if state.formulas:
        formula = max(
            state.formulas,
            key=lambda item: (
                len(item.references),
                len(item.concept_links),
                len(item.symbol_explanations),
                -len(item.expression),
            ),
        )
        concept = _best_linked_concept(formula, concept_lookup)
        example = _example_for_formula(formula, state)
        return FocusSelection(
            label=concept.name if concept else formula.expression,
            formula=formula,
            concept=concept,
            example=example,
            solution=solution_lookup.get(example.example_id) if example else None,
        )

    if state.concepts:
        concept = state.concepts[0]
        example = _example_for_concept(concept, state)
        formula = _formula_for_concept(concept, formula_lookup, state)
        return FocusSelection(
            label=concept.name,
            concept=concept,
            formula=formula,
            example=example,
            solution=solution_lookup.get(example.example_id) if example else None,
        )

    return FocusSelection(label="当前材料中的主要方法")


def _build_focus_problem_lines(selection: FocusSelection) -> list[str]:
    lines: list[str] = []
    if selection.concept and selection.concept.description:
        lines.append(f"这次聚焦 “{selection.label}”，它在本章里主要在解决：{selection.concept.description}")
    elif selection.formula:
        left_side = selection.formula.expression.split("=")[0].strip()
        lines.append(f"这次聚焦 “{selection.label}”，核心是搞清楚什么时候应该想到 {selection.formula.expression}，以及它如何帮助我们求 {left_side}。")
    else:
        lines.append(f"这次聚焦 “{selection.label}”，目标是先讲清它到底在解决什么问题。")
    if selection.formula and selection.formula.conditions:
        lines.append(f"原材料里的第一条条件提醒是：{selection.formula.conditions[0]}")
    else:
        lines.append("TODO: 适用条件还需要回原材料进一步确认。")
    return lines


def _build_focus_core_ideas(selection: FocusSelection) -> list[str]:
    lines: list[str] = []
    if selection.concept:
        lines.append(f"先把 {selection.concept.name} 放回课程语境里理解，再去看它连接了哪些量、条件和题型。")
    if selection.formula:
        lines.append(
            f"核心思想不是死记 {selection.formula.expression}，而是先判断题目里的量之间是否正好满足这条关系。"
        )
    if selection.example and selection.example.study_value:
        lines.append(f"从复习角度看，这个主题最值得练的是：{selection.example.study_value}")
    if not lines:
        lines.append("TODO: 当前材料过少，尚无法稳定提炼这个主题的核心思想。")
    return lines


def _build_focus_formula_lines(selection: FocusSelection) -> list[str]:
    if not selection.formula:
        return ["TODO: 当前没有稳定提取到可深挖的核心公式。"]

    lines = [
        f"### 核心公式",
        selection.formula.expression,
    ]
    if selection.formula.symbol_explanations:
        lines.append("### 符号解释")
        lines.extend(
            f"- {symbol} 表示 {meaning}"
            for symbol, meaning in selection.formula.symbol_explanations.items()
        )
    else:
        lines.append("TODO: 需要补充符号说明。")
    if selection.formula.conditions:
        lines.append("### 条件 / 假设")
        lines.extend(f"- {condition}" for condition in selection.formula.conditions[:2])
    else:
        lines.append("TODO: 需要确认适用条件。")
    return lines


def _build_focus_process_lines(selection: FocusSelection) -> list[str]:
    if selection.solution and selection.solution.plan_steps:
        return list(selection.solution.plan_steps)
    if selection.example and selection.formula:
        return [
            "先看清题目在求什么，不要一上来就代数字。",
            f"再确认为什么应该用 {selection.formula.expression}。",
            "最后逐步列已知量、代入、解释结果。",
        ]
    return ["TODO: 还需要补足这个主题的计算 / 推导流程。"]


def _build_focus_example_lines(selection: FocusSelection) -> list[str]:
    if not selection.example:
        return ["TODO: 当前还没有稳定匹配到一个完整例子。"]

    lines = [
        f"### {selection.example.title}",
        selection.example.problem_statement or selection.example.prompt or "TODO",
    ]
    if selection.solution and selection.solution.detailed_steps:
        lines.append("关键步骤：")
        lines.extend(f"- {step}" for step in selection.solution.detailed_steps[:4])
    else:
        lines.append("TODO: 还需要补上这个例子的完整关键步骤。")
    return lines


def _build_focus_mistakes(selection: FocusSelection) -> list[str]:
    if selection.solution and selection.solution.common_mistakes:
        return list(selection.solution.common_mistakes)
    if selection.formula:
        return [
            "只背公式，不先判断题目是否真的满足这条公式的适用条件。",
            "把目标量也当成已知量一起代入，导致解题顺序混乱。",
        ]
    return ["TODO: 当前还缺少足够证据来稳定总结这个主题的易错点。"]


def _build_exam_definitions(state: StudyGraphState) -> list[str]:
    lines: list[str] = []
    for concept in state.concepts[:3]:
        definition = concept.description or "TODO: 需要回原材料确认定义。"
        lines.append(f"{concept.name}：{definition}")
    if not lines:
        lines.append("TODO: 当前材料中还没有足够稳定的必背定义。")
    return lines


def _build_exam_formula_lines(state: StudyGraphState) -> list[str]:
    lines: list[str] = []
    for formula in state.formulas[:4]:
        lines.append(f"{formula.expression}；条件提醒：{formula.conditions[0] if formula.conditions else 'TODO'}")
    if not lines:
        lines.append("TODO: 当前没有稳定提取到核心公式。")
    return lines


def _build_exam_points(state: StudyGraphState) -> list[str]:
    lines: list[str] = []
    for formula in state.formulas[:3]:
        lines.append(
            f"高频考点：看到 {formula.expression} 时，要先判断已知量是否足够、条件是否满足。"
        )
    for concept in state.concepts[:2]:
        lines.append(f"高频考点：能区分“{concept.name}”在概念解释题和计算题里的不同作用。")
    if not lines:
        lines.append("TODO: 当前材料过少，还不能稳定压缩出高频考点。")
    return lines[:5]


def _build_exam_example_lines(state: StudyGraphState) -> list[str]:
    if not state.examples:
        return ["TODO: 当前还没有可直接复习的一道典型题。"]

    example = state.examples[0]
    lines = [example.title, example.problem_statement or example.prompt or "TODO"]
    solution_lookup = {solution.example_id: solution for solution in state.worked_solutions}
    solution = solution_lookup.get(example.example_id)
    if solution and solution.detailed_steps:
        lines.append("最关键的两步：")
        lines.extend(f"- {step}" for step in solution.detailed_steps[:2])
    return lines


def _build_exam_reminders(state: StudyGraphState) -> list[str]:
    reminders: list[str] = []
    for formula in state.formulas[:3]:
        reminders.append(
            f"题目里一旦出现和 {formula.expression} 对应的量，就先回忆这条公式和它的条件。"
        )
    reminders.extend(_collect_common_mistakes(state)[:2])
    if not reminders:
        reminders.append("TODO: 当前材料过少，还不能稳定生成速记提醒。")
    return reminders


def _formula_for_example(
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


def _example_for_formula(formula: FormulaArtifact | None, state: StudyGraphState) -> ExampleArtifact | None:
    if not formula:
        return None
    for example in state.examples:
        if formula.formula_id in example.formula_ids or example.formula_id == formula.formula_id:
            return example
    return None


def _example_for_concept(concept: ConceptRecord, state: StudyGraphState) -> ExampleArtifact | None:
    for example in state.examples:
        if concept.name in example.title or concept.name in example.problem_statement:
            return example
    return None


def _formula_for_concept(
    concept: ConceptRecord,
    formula_lookup: dict[str, FormulaArtifact],
    state: StudyGraphState,
) -> FormulaArtifact | None:
    for formula in state.formulas:
        if concept.concept_id in formula.concept_links:
            return formula
    for formula_id in concept.related_formula_ids:
        if formula_id in formula_lookup:
            return formula_lookup[formula_id]
    return None


def _best_linked_concept(
    formula: FormulaArtifact | None,
    concept_lookup: dict[str, ConceptRecord],
) -> ConceptRecord | None:
    if not formula:
        return None
    for concept_id in formula.concept_links:
        if concept_id in concept_lookup:
            return concept_lookup[concept_id]
    return None


def _collect_common_mistakes(state: StudyGraphState) -> list[str]:
    mistakes: list[str] = []
    seen: set[str] = set()
    for solution in state.worked_solutions:
        for item in solution.common_mistakes:
            if item in seen:
                continue
            seen.add(item)
            mistakes.append(item)
    if not mistakes:
        mistakes.append("TODO: 当前还缺少足够的例题证据来稳定总结易错点。")
    return mistakes


def _collect_references(state: StudyGraphState) -> list[SourceReference]:
    references: list[SourceReference] = []
    seen: set[tuple[str, str | None]] = set()
    for reference_group in (
        [formula.references for formula in state.formulas[:4]]
        + [example.references for example in state.examples[:3]]
    ):
        for reference in reference_group:
            key = (reference.source_path, reference.chunk_id)
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
    return references


def _collect_focus_references(selection: FocusSelection) -> list[SourceReference]:
    references: list[SourceReference] = []
    seen: set[tuple[str, str | None]] = set()
    for reference_group in (
        selection.concept.references if selection.concept else [],
        selection.formula.references if selection.formula else [],
        selection.example.references if selection.example else [],
        selection.solution.references if selection.solution else [],
    ):
        for reference in reference_group:
            key = (reference.source_path, reference.chunk_id)
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
    return references


def _normalize_text(text: str) -> str:
    return "".join(ch.lower() for ch in text if ch.isalnum())


def _trim_trailing_blank(lines: list[str]) -> list[str]:
    trimmed = list(lines)
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    return trimmed
