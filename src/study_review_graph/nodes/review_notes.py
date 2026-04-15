"""Review-note generation node."""

from __future__ import annotations

from study_review_graph.state import ReviewNotes, SourceReference, StudyGraphState


def generate_review_notes_node(state: StudyGraphState) -> ReviewNotes:
    """Assemble Chinese-first review notes from prior grounded artifacts."""

    chapter_mainline = _build_chapter_mainline(state)
    key_formulas = _build_key_formula_highlights(state)
    method_explanations = _build_method_explanations(state)
    quick_review = _build_quick_review(state)
    references = _collect_references(state)

    return ReviewNotes(
        concise_summary=chapter_mainline,
        detailed_explanations=method_explanations,
        formula_highlights=key_formulas,
        study_questions=quick_review,
        references=references,
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


def _build_key_formula_highlights(state: StudyGraphState) -> list[str]:
    highlights: list[str] = []
    for formula in state.formulas[:5]:
        symbol_preview = "，".join(
            f"{symbol} 表示 {meaning}"
            for symbol, meaning in list(formula.symbol_explanations.items())[:3]
        ) or "TODO: 需要补充符号说明。"
        condition_text = formula.conditions[0] if formula.conditions else "TODO: 需要确认适用条件。"
        highlights.append(
            f"{formula.expression}：{symbol_preview} 适用提醒：{condition_text}"
        )
    if not highlights:
        highlights.append("TODO: 当前材料中还没有稳定提取到关键公式。")
    return highlights


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


def _collect_references(state: StudyGraphState) -> list[SourceReference]:
    references: list[SourceReference] = []
    seen: set[tuple[str, str | None]] = set()
    for reference_group in (
        [formula.references for formula in state.formulas[:4]]
        + [example.references for example in state.examples[:2]]
    ):
        for reference in reference_group:
            key = (reference.source_path, reference.chunk_id)
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
    return references
