"""Markdown export layer."""

from __future__ import annotations

from pathlib import Path

from study_review_graph.markdown_math import display_math, inline_math, symbol_math
from study_review_graph.state import ExampleArtifact, FormulaArtifact, SourceReference, StudyGraphState, WorkedSolution


def export_markdown_bundle(state: StudyGraphState) -> dict[str, str]:
    """Export a markdown bundle for study review outputs."""

    output_dir = Path(state.config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "content_map": str(output_dir / "content_map.md"),
        "formula_sheet": str(output_dir / "formula_sheet.md"),
        "worked_examples": str(output_dir / "worked_examples.md"),
        "overview": str(output_dir / "overview.md"),
        "formulas": str(output_dir / "formulas.md"),
        "worked_solutions": str(output_dir / "worked_solutions.md"),
        "review_notes": str(output_dir / "review_notes.md"),
        "quality_report": str(output_dir / "quality_report.md"),
    }

    content_map_markdown = _render_content_map(state)
    formula_sheet_markdown = _render_formula_sheet(state)

    Path(output_paths["content_map"]).write_text(content_map_markdown, encoding="utf-8")
    Path(output_paths["formula_sheet"]).write_text(formula_sheet_markdown, encoding="utf-8")
    Path(output_paths["worked_examples"]).write_text(
        _render_worked_examples(state),
        encoding="utf-8",
    )
    Path(output_paths["overview"]).write_text(_render_overview(state), encoding="utf-8")
    Path(output_paths["formulas"]).write_text(formula_sheet_markdown, encoding="utf-8")
    Path(output_paths["worked_solutions"]).write_text(
        _render_solutions(state),
        encoding="utf-8",
    )
    Path(output_paths["review_notes"]).write_text(_render_review_notes(state), encoding="utf-8")
    Path(output_paths["quality_report"]).write_text(
        _render_quality_report(state),
        encoding="utf-8",
    )

    return output_paths


def _render_overview(state: StudyGraphState) -> str:
    concept_lines = "\n".join(f"- {concept.name}" for concept in state.concepts) or "- None"
    return (
        f"# Study Review Overview\n\n"
        f"- Course: {state.course_name}\n"
        f"- Goal: {state.user_goal}\n"
        f"- Source documents: {len(state.normalized_docs)}\n"
        f"- Chunks: {len(state.chunks)}\n"
        f"- Primary outputs: `content_map.md`, `formula_sheet.md`, `worked_examples.md`, `worked_solutions.md`\n"
        f"- Formulas: {len(state.formulas)}\n"
        f"- Examples: {len(state.examples)}\n"
        f"- Worked solutions: {len(state.worked_solutions)}\n\n"
        f"## Concepts\n\n"
        f"{concept_lines}\n"
    )


def _render_content_map(state: StudyGraphState) -> str:
    if not state.concepts:
        return "# Content Map\n\nNo concepts were identified from the current materials.\n"

    formula_links = _build_formula_links_by_concept(state)
    sections = [
        "# Content Map",
        "",
        "这份内容图谱用于先抓住本章主线，再回到公式和例题。",
        "概念描述仍然以本地检索结果为依据，在 v0.1 中保持谨慎和可追踪。",
    ]
    for concept in state.concepts:
        linked_formula_lines = "\n".join(
            f"- {inline_math(formula.expression)} (`{formula.formula_id}`)"
            for formula in formula_links.get(concept.concept_id, [])
        ) or "- None linked yet"
        sections.append(
            "\n".join(
                [
                    f"## {concept.name}",
                    "",
                    concept.description,
                    "",
                    "### 为什么重要",
                    (
                        f"- 可以把这个概念当作复习主线，再去连接对应公式和例题。"
                    ),
                    "",
                    "### 关联公式",
                    linked_formula_lines,
                    "",
                    "### 来源",
                    _render_references(concept.references),
                ]
            )
        )
    return "\n\n".join(sections) + "\n"


def _render_formula_sheet(state: StudyGraphState) -> str:
    formulas = state.formulas
    if not formulas:
        return "# Formula Sheet\n\nNo formulas extracted from the current materials.\n"

    concept_lookup = {concept.concept_id: concept.name for concept in state.concepts}
    sections = [
        "# Formula Sheet",
        "",
        "这份公式表按复习资料的方式整理核心关系式、符号和适用条件。",
        "v0.1 仍然保留启发式提取和明确的 TODO 标记，不假装已经完全理解。",
    ]
    for formula in formulas:
        symbol_lines = "\n".join(
            f"- {symbol_math(symbol)}：{meaning}" for symbol, meaning in formula.symbol_explanations.items()
        ) or "- TODO"
        condition_lines = "\n".join(f"- {condition}" for condition in formula.conditions) or "- TODO"
        linked_concepts = "\n".join(
            f"- {concept_lookup.get(concept_id, concept_id)} (`{concept_id}`)"
            for concept_id in formula.concept_links
        ) or "- None linked yet"
        sections.append(
            "\n".join(
                [
                    f"## 公式 {formula.formula_id}",
                    "",
                    display_math(formula.expression),
                    "",
                    f"- 原始表达式：`{formula.expression}`",
                    f"- Formula ID: `{formula.formula_id}`",
                    "",
                    "### 关联概念",
                    linked_concepts,
                    "",
                    "### 符号解释",
                    symbol_lines,
                    "",
                    "### 条件 / 假设",
                    condition_lines,
                    "",
                    "### 说明与 TODO",
                    f"- {formula.notes or 'TODO: add more grounded interpretation notes.'}",
                    "",
                    "### 来源",
                    _render_references(formula.references),
                ]
            )
        )
    return "\n\n".join(sections) + "\n"


def _render_worked_examples(state: StudyGraphState) -> str:
    if not state.examples:
        return "# Worked Examples\n\nNo worked examples generated.\n"

    formula_lookup = {formula.formula_id: formula.expression for formula in state.formulas}
    sections = [
        "# 例题讲解",
        "",
        "这部分按“先知道这题在练什么，再看公式和已知量，再进入演算”的复习节奏组织。",
        "如果原材料没有给出完整数值例题，当前版本会诚实地用最小可算例题补全步骤。",
    ]
    for index, example in enumerate(state.examples, start=1):
        formula_lines = "\n".join(
            f"- {inline_math(formula_lookup.get(formula_id, formula_id))} (`{formula_id}`)"
            for formula_id in example.formula_ids
        ) or "- None"
        known_value_lines = "\n".join(
            f"- {symbol_math(symbol)} = {value}" for symbol, value in example.known_values.items()
        ) or "- None listed"
        sections.append(
            "\n".join(
                [
                    f"## 例题 {index}：{example.title}",
                    "",
                    f"- 例题 ID：`{example.example_id}`",
                    f"- 难度：{example.difficulty}",
                    (
                        f"- 目标符号：{symbol_math(example.target_symbol)}"
                        if example.target_symbol
                        else "- 目标符号：TODO"
                    ),
                    "",
                    "### 这题在练什么",
                    f"- {example.study_value or 'TODO: 需要补充这道题的复习价值。'}",
                    "",
                    "### 对应公式",
                    formula_lines,
                    "",
                    "### 题目",
                    example.problem_statement or example.prompt or "TODO",
                    "",
                    "### 已知条件",
                    known_value_lines,
                    "",
                    "### 与原材料的关系",
                    f"- {example.reasoning_context or 'TODO: add grounding notes.'}",
                    "",
                    "### 来源",
                    _render_references(example.references),
                ]
            )
        )
    return "\n\n".join(sections) + "\n"


def _render_solutions(state: StudyGraphState) -> str:
    solutions = state.worked_solutions
    if not solutions:
        return "# Worked Solutions\n\nNo worked solutions generated.\n"

    example_lookup = {example.example_id: example for example in state.examples}
    formula_lookup = {formula.formula_id: formula for formula in state.formulas}
    sections = [
        "# 例题详解",
        "",
        "这一部分按“题意直觉 -> 公式选择 -> 符号解释 -> 逐步代入 -> 结果理解 -> 易错点”的顺序讲解。",
    ]
    for solution in solutions:
        example = example_lookup.get(solution.example_id)
        formula = _primary_solution_formula(example, formula_lookup) if example else None
        symbol_lines = _render_symbol_explanations(formula)
        sections.append(
            "\n".join(
                [
                    f"## {solution.solution_id}",
                    "",
                    f"- 对应例题：`{solution.example_id}`",
                    f"- 题目标题：{example.title}" if example else "- 题目标题：TODO",
                    "",
                    "### 题意直觉",
                    (
                        f"- 这道题的目标是先看清要解决什么，再判断为什么要用这条公式。"
                        if example
                        else "- TODO"
                    ),
                    "",
                    "### 题目",
                    example.problem_statement if example and example.problem_statement else "TODO",
                    "",
                    "### 解题计划",
                    "\n".join(f"- {step}" for step in solution.plan_steps) or "- TODO",
                    "",
                    "### 公式选择",
                    (
                        display_math(formula.expression)
                        if formula
                        else "TODO: 需要补充本题对应的核心公式。"
                    ),
                    "",
                    "### 符号说明",
                    symbol_lines,
                    "",
                    "### 逐步代入 / 推导",
                    "\n".join(f"- {step}" for step in solution.detailed_steps) or "- TODO",
                    "",
                    "### 为什么这样做",
                    "\n".join(f"- {item}" for item in solution.rationale) or "- TODO",
                    "",
                    "### 易错点",
                    "\n".join(f"- {item}" for item in solution.common_mistakes) or "- TODO",
                    "",
                    "### 来源",
                    _render_references(solution.references),
                ]
            )
        )
    return "\n\n".join(sections) + "\n"


def _render_review_notes(state: StudyGraphState) -> str:
    notes = state.review_notes
    example_lookup = {example.example_id: example for example in state.examples}
    mistake_lines = _render_common_mistakes(state)
    example_lines = _render_review_examples(state, example_lookup)
    formula_lines = _render_review_formulas(state, notes)
    return "\n".join(
        [
            "# 复习笔记",
            "",
            "## 本章主线",
            "\n".join(f"- {line}" for line in notes.concise_summary) or "- None",
            "",
            "## 关键定义与公式",
            formula_lines,
            "",
            "## 算法 / 方法逐个讲解",
            "\n".join(f"- {line}" for line in notes.detailed_explanations) or "- TODO",
            "",
            "## 每个主要方法对应的例题 / worked example",
            example_lines,
            "",
            "## 易错点 / 混淆点",
            mistake_lines,
            "",
            "## 考前速记版",
            "\n".join(f"- {line}" for line in notes.study_questions) or "- None",
            "",
            "## 来源",
            _render_references(notes.references),
            "",
        ]
    )


def _render_quality_report(state: StudyGraphState) -> str:
    report = state.quality_report
    sections = [
        "# Quality Report",
        "",
        "## Groundedness Checks",
        _render_checks(report.groundedness_checks),
        "",
        "## Formula Coverage Checks",
        _render_checks(report.formula_coverage_checks),
        "",
        "## Explanation Completeness Checks",
        _render_checks(report.explanation_completeness_checks),
        "",
        "## Next Actions",
        "\n".join(f"- {item}" for item in report.next_actions) or "- None",
        "",
    ]
    return "\n".join(sections)


def _render_checks(checks) -> str:
    return "\n".join(f"- [{check.status}] {check.name}: {check.message}" for check in checks) or "- None"


def _render_references(references: list[SourceReference]) -> str:
    if not references:
        return "- None"
    return "\n".join(
        f"- {reference.source_path} ({reference.chunk_id or 'document'})"
        for reference in references
    )


def _render_symbol_explanations(formula: FormulaArtifact | None) -> str:
    if not formula or not formula.symbol_explanations:
        return "- TODO"
    return "\n".join(
        f"- {symbol_math(symbol)}：{meaning}"
        for symbol, meaning in formula.symbol_explanations.items()
    )


def _primary_solution_formula(
    example: ExampleArtifact | None,
    formula_lookup: dict[str, FormulaArtifact],
) -> FormulaArtifact | None:
    if not example:
        return None
    formula_ids = list(example.formula_ids)
    if example.formula_id and example.formula_id not in formula_ids:
        formula_ids.insert(0, example.formula_id)
    for formula_id in formula_ids:
        if formula_id in formula_lookup:
            return formula_lookup[formula_id]
    return None


def _render_review_formulas(state: StudyGraphState, notes) -> str:
    if state.formulas:
        sections: list[str] = []
        for formula in state.formulas[:4]:
            sections.extend(
                [
                    f"- 公式 {formula.formula_id}",
                    f"  {inline_math(formula.expression)}",
                    (
                        "  条件提醒："
                        + (formula.conditions[0] if formula.conditions else "TODO: 需要回原材料确认。")
                    ),
                ]
            )
        return "\n".join(sections)
    return "\n".join(f"- {line}" for line in notes.formula_highlights) or "- TODO"


def _render_review_examples(state: StudyGraphState, example_lookup: dict[str, ExampleArtifact]) -> str:
    if not state.examples:
        return "- TODO: 当前材料过少，例题部分还需要补充。"
    sections: list[str] = []
    solution_lookup = {solution.example_id: solution for solution in state.worked_solutions}
    for example in state.examples[:3]:
        sections.append(f"### {example.title}")
        sections.append(example.problem_statement or example.prompt or "TODO")
        solution = solution_lookup.get(example.example_id)
        if solution and solution.detailed_steps:
            sections.append("关键步骤：")
            sections.extend(f"- {step}" for step in solution.detailed_steps[:3])
        sections.append("")
    return "\n".join(sections).strip()


def _render_common_mistakes(state: StudyGraphState) -> str:
    mistakes: list[str] = []
    seen: set[str] = set()
    for solution in state.worked_solutions:
        for item in solution.common_mistakes:
            if item in seen:
                continue
            seen.add(item)
            mistakes.append(item)
    return "\n".join(f"- {item}" for item in mistakes) or "- TODO"


def _build_formula_links_by_concept(state: StudyGraphState) -> dict[str, list[FormulaArtifact]]:
    links: dict[str, list[FormulaArtifact]] = {}
    for formula in state.formulas:
        for concept_id in formula.concept_links:
            links.setdefault(concept_id, []).append(formula)
    return links
