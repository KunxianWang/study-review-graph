"""Quality review node and evaluator placeholders."""

from __future__ import annotations

from study_review_graph.state import QualityCheck, QualityReport, StudyGraphState


def quality_review_node(state: StudyGraphState) -> QualityReport:
    """Run deterministic placeholder checks for v0.1 quality control."""

    grounded = _groundedness_checks(state)
    coverage = _formula_coverage_checks(state)
    completeness = _explanation_completeness_checks(state)

    next_actions = []
    for check in grounded + coverage + completeness:
        if check.status != "pass":
            next_actions.append(check.message)

    return QualityReport(
        groundedness_checks=grounded,
        formula_coverage_checks=coverage,
        explanation_completeness_checks=completeness,
        next_actions=next_actions,
    )


def _groundedness_checks(state: StudyGraphState) -> list[QualityCheck]:
    artifact_count = len(state.formulas) + len(state.examples) + len(state.worked_solutions)
    referenced_count = sum(1 for formula in state.formulas if formula.references)
    referenced_count += sum(1 for example in state.examples if example.references)
    referenced_count += sum(1 for solution in state.worked_solutions if solution.references)

    status = "pass" if artifact_count == 0 or referenced_count == artifact_count else "warn"
    message = (
        "Groundedness placeholder passed with references attached to generated artifacts."
        if status == "pass"
        else "Some generated artifacts are missing source references. TODO: add stronger groundedness validation."
    )
    return [QualityCheck(name="groundedness_placeholder", status=status, message=message)]


def _formula_coverage_checks(state: StudyGraphState) -> list[QualityCheck]:
    source_mentions_formula_like_text = any("=" in doc.content for doc in state.normalized_docs)
    status = "pass"
    message = "Formula coverage placeholder passed."

    if source_mentions_formula_like_text and not state.formulas:
        status = "warn"
        message = "Source materials appear to contain formulas, but none were extracted."

    return [QualityCheck(name="formula_coverage_placeholder", status=status, message=message)]


def _explanation_completeness_checks(state: StudyGraphState) -> list[QualityCheck]:
    missing_explanations = [solution.solution_id for solution in state.worked_solutions if not solution.detailed_steps]
    status = "pass" if not missing_explanations else "warn"
    message = (
        "Explanation completeness placeholder passed."
        if status == "pass"
        else "Some worked solutions are missing detailed steps."
    )
    return [QualityCheck(name="explanation_completeness_placeholder", status=status, message=message)]
