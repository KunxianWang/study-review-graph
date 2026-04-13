"""Review-note generation node."""

from __future__ import annotations

from study_review_graph.state import ReviewNotes, StudyGraphState


def generate_review_notes_node(state: StudyGraphState) -> ReviewNotes:
    """Assemble concise and detailed study notes from prior artifacts."""

    concise_summary = [
        f"Course focus: {state.course_name}",
        f"Primary learning goal: {state.user_goal}",
    ]
    concise_summary.extend(f"Key concept: {concept.name}" for concept in state.concepts[:5])

    formula_highlights = [
        f"{formula.expression} | conditions: {', '.join(formula.conditions) or 'TODO'}"
        for formula in state.formulas[:5]
    ]

    detailed_explanations = []
    for solution in state.worked_solutions[:5]:
        if solution.detailed_steps:
            detailed_explanations.append(
                f"{solution.example_id}: {' '.join(solution.detailed_steps)}"
            )

    study_questions = []
    for formula in state.formulas[:3]:
        study_questions.append(
            f"When is {formula.expression} valid, and what assumptions must be checked first?"
        )
    for concept in state.concepts[:2]:
        study_questions.append(
            f"How would you explain the concept '{concept.name}' without relying on memorized phrasing?"
        )

    references = []
    for formula in state.formulas[:3]:
        references.extend(formula.references)

    return ReviewNotes(
        concise_summary=concise_summary,
        detailed_explanations=detailed_explanations,
        formula_highlights=formula_highlights,
        study_questions=study_questions,
        references=references,
    )
