"""Markdown export layer."""

from __future__ import annotations

from pathlib import Path

from study_review_graph.state import FormulaArtifact, SourceReference, StudyGraphState, WorkedSolution


def export_markdown_bundle(state: StudyGraphState) -> dict[str, str]:
    """Export a markdown bundle for study review outputs."""

    output_dir = Path(state.config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "content_map": str(output_dir / "content_map.md"),
        "formula_sheet": str(output_dir / "formula_sheet.md"),
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
    Path(output_paths["overview"]).write_text(_render_overview(state), encoding="utf-8")
    Path(output_paths["formulas"]).write_text(formula_sheet_markdown, encoding="utf-8")
    Path(output_paths["worked_solutions"]).write_text(
        _render_solutions(state.worked_solutions),
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
        f"- Primary outputs: `content_map.md`, `formula_sheet.md`\n"
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
        "This study artifact summarizes the main concepts inferred from the provided materials.",
        "Descriptions are grounded in retrieved source chunks and remain heuristic in v0.1.",
    ]
    for concept in state.concepts:
        linked_formula_lines = "\n".join(
            f"- `{formula.expression}` (`{formula.formula_id}`)"
            for formula in formula_links.get(concept.concept_id, [])
        ) or "- None linked yet"
        sections.append(
            "\n".join(
                [
                    f"## {concept.name}",
                    "",
                    concept.description,
                    "",
                    "### Why it matters",
                    (
                        f"- Treat this as a study anchor for understanding related formulas and examples."
                    ),
                    "",
                    "### Linked formulas",
                    linked_formula_lines,
                    "",
                    "### Sources",
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
        "This study artifact collects formulas found in the source materials.",
        "Extraction and interpretation are still heuristic in v0.1, so explicit TODO markers are kept where understanding is incomplete.",
    ]
    for formula in formulas:
        symbol_lines = "\n".join(
            f"- `{symbol}`: {meaning}" for symbol, meaning in formula.symbol_explanations.items()
        ) or "- TODO"
        condition_lines = "\n".join(f"- {condition}" for condition in formula.conditions) or "- TODO"
        linked_concepts = "\n".join(
            f"- {concept_lookup.get(concept_id, concept_id)} (`{concept_id}`)"
            for concept_id in formula.concept_links
        ) or "- None linked yet"
        sections.append(
            "\n".join(
                [
                    f"## {formula.expression}",
                    "",
                    f"- Formula ID: `{formula.formula_id}`",
                    "",
                    "### Linked concepts",
                    linked_concepts,
                    "",
                    "### Symbols",
                    symbol_lines,
                    "",
                    "### Conditions",
                    condition_lines,
                    "",
                    "### Notes and TODOs",
                    f"- {formula.notes or 'TODO: add more grounded interpretation notes.'}",
                    "",
                    "### References",
                    _render_references(formula.references),
                ]
            )
        )
    return "\n\n".join(sections) + "\n"


def _render_solutions(solutions: list[WorkedSolution]) -> str:
    if not solutions:
        return "# Worked Solutions\n\nNo worked solutions generated.\n"

    sections = ["# Worked Solutions\n"]
    for solution in solutions:
        sections.append(
            "\n".join(
                [
                    f"## {solution.solution_id}",
                    "",
                    "### Plan Steps",
                    "\n".join(f"- {step}" for step in solution.plan_steps) or "- TODO",
                    "",
                    "### Detailed Steps",
                    "\n".join(f"- {step}" for step in solution.detailed_steps) or "- TODO",
                    "",
                    "### Rationale",
                    "\n".join(f"- {item}" for item in solution.rationale) or "- TODO",
                    "",
                    "### Common Mistakes",
                    "\n".join(f"- {item}" for item in solution.common_mistakes) or "- TODO",
                    "",
                    "### References",
                    _render_references(solution.references),
                ]
            )
        )
    return "\n\n".join(sections) + "\n"


def _render_review_notes(state: StudyGraphState) -> str:
    notes = state.review_notes
    return "\n".join(
        [
            "# Review Notes",
            "",
            "## Concise Summary",
            "\n".join(f"- {line}" for line in notes.concise_summary) or "- None",
            "",
            "## Detailed Explanations",
            "\n".join(f"- {line}" for line in notes.detailed_explanations) or "- None",
            "",
            "## Formula Highlights",
            "\n".join(f"- {line}" for line in notes.formula_highlights) or "- None",
            "",
            "## Study Questions",
            "\n".join(f"- {line}" for line in notes.study_questions) or "- None",
            "",
            "## References",
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


def _build_formula_links_by_concept(state: StudyGraphState) -> dict[str, list[FormulaArtifact]]:
    links: dict[str, list[FormulaArtifact]] = {}
    for formula in state.formulas:
        for concept_id in formula.concept_links:
            links.setdefault(concept_id, []).append(formula)
    return links
