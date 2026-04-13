"""Example generation module."""

from __future__ import annotations

from study_review_graph.model_client import get_model_client
from study_review_graph.retrieval import retrieve_relevant_chunks
from study_review_graph.state import ExampleArtifact, FormulaArtifact, SourceReference, StudyGraphState

DEFAULT_KNOWN_VALUES = {
    "a": "3 m/s^2",
    "d": "10 m",
    "e": "24 J",
    "e_k": "16 J",
    "f": "6 N",
    "g": "9.8 m/s^2",
    "m": "2 kg",
    "p": "8 kg*m/s",
    "t": "4 s",
    "v": "4 m/s",
    "x": "5 m",
}


def generate_examples_node(state: StudyGraphState) -> tuple[list[ExampleArtifact], list[str]]:
    """Create grounded worked examples from formulas with safe fallback behavior."""

    warnings: list[str] = []
    model_client = get_model_client()
    model_warning = model_client.availability_warning()
    if model_warning:
        warnings.append(model_warning)

    examples: list[ExampleArtifact] = []
    for index, formula in enumerate(state.formulas):
        draft = _build_formula_example(index=index, formula=formula, state=state)
        supporting_chunks = _retrieve_example_support(formula=formula, state=state)
        llm_payload, llm_warning = _generate_example_enrichment(
            draft=draft,
            formula=formula,
            state=state,
            supporting_chunks=supporting_chunks,
            model_client=model_client,
        )
        if llm_warning and llm_warning not in warnings:
            warnings.append(llm_warning)
        if llm_payload:
            draft = _merge_example_payload(draft, llm_payload)
        examples.append(draft)

    if not examples:
        examples = _build_concept_fallback_examples(state)

    return examples, warnings


def _build_formula_example(
    *,
    index: int,
    formula: FormulaArtifact,
    state: StudyGraphState,
) -> ExampleArtifact:
    target_symbol = _target_symbol(formula.expression)
    known_values = _build_known_values(formula, target_symbol)
    concept_names = _linked_concept_names(formula, state)
    title = _example_title(formula, concept_names, target_symbol)
    problem_statement = _problem_statement(formula, target_symbol, known_values, concept_names)
    study_value = _study_value(formula, concept_names, target_symbol)
    difficulty = "introductory" if len(known_values) <= 2 else "intermediate"
    references = _collect_references(
        [formula.references]
        + [_concept_references(concept_id, state) for concept_id in formula.concept_links]
    )
    reasoning_bits = [
        f"Centered on `{formula.expression}`.",
        f"Target symbol: `{target_symbol}`." if target_symbol else "TODO: confirm the target symbol.",
    ]
    if formula.conditions:
        reasoning_bits.append(f"Local condition cue: {formula.conditions[0]}")
    return ExampleArtifact(
        example_id=f"example-{index}",
        title=title,
        problem_statement=problem_statement,
        formula_ids=[formula.formula_id],
        difficulty=difficulty,
        study_value=study_value,
        known_values=known_values,
        target_symbol=target_symbol,
        prompt=problem_statement,
        formula_id=formula.formula_id,
        reasoning_context=" ".join(reasoning_bits),
        references=references,
    )


def _retrieve_example_support(*, formula: FormulaArtifact, state: StudyGraphState):
    concept_names = _linked_concept_names(formula, state)
    query_parts = [formula.expression, " ".join(concept_names)]
    if formula.conditions:
        query_parts.append(" ".join(formula.conditions[:1]))
    return retrieve_relevant_chunks(" ".join(part for part in query_parts if part), state, top_k=2)


def _generate_example_enrichment(
    *,
    draft: ExampleArtifact,
    formula: FormulaArtifact,
    state: StudyGraphState,
    supporting_chunks,
    model_client,
) -> tuple[dict | None, str | None]:
    if not supporting_chunks:
        return None, None

    result = model_client.generate_json(
        task_name=f"worked example '{draft.example_id}'",
        system_prompt=(
            "You are refining a grounded study example. "
            "Use only the provided local excerpts, formula metadata, and draft example. "
            "Do not invent unrelated topics or unsupported facts. "
            "Return JSON with keys: title, difficulty, problem_statement, study_value."
        ),
        user_prompt=(
            f"Course: {state.course_name}\n"
            f"User goal: {state.user_goal}\n"
            f"Formula expression: {formula.expression}\n"
            f"Linked concepts: {', '.join(_linked_concept_names(formula, state)) or 'None'}\n"
            f"Symbol explanations: {formula.symbol_explanations}\n"
            f"Formula conditions: {formula.conditions}\n"
            f"Draft title: {draft.title}\n"
            f"Draft problem statement: {draft.problem_statement}\n"
            f"Draft difficulty: {draft.difficulty}\n"
            f"Draft study value: {draft.study_value}\n"
            f"Known values: {draft.known_values}\n\n"
            "Retrieved local excerpts:\n"
            f"{_render_chunk_context(supporting_chunks)}\n\n"
            "Refine the example to make it clearer and more useful for study. "
            "Keep it tied to the same formula. "
            "If the local evidence is weak, preserve a cautious wording."
        ),
    )
    return result.payload, result.warning


def _merge_example_payload(example: ExampleArtifact, payload: dict) -> ExampleArtifact:
    updated = {
        "title": str(payload.get("title", example.title)).strip() or example.title,
        "difficulty": str(payload.get("difficulty", example.difficulty)).strip() or example.difficulty,
        "problem_statement": (
            str(payload.get("problem_statement", example.problem_statement)).strip()
            or example.problem_statement
        ),
        "study_value": str(payload.get("study_value", example.study_value)).strip() or example.study_value,
    }
    updated["prompt"] = updated["problem_statement"]
    return example.model_copy(update=updated)


def _build_concept_fallback_examples(state: StudyGraphState) -> list[ExampleArtifact]:
    examples: list[ExampleArtifact] = []
    for index, concept in enumerate(state.concepts[:3]):
        problem_statement = (
            f"Explain a concrete study scenario for '{concept.name}' using only the provided materials. "
            "Identify what is known, what should be interpreted, and which source idea supports the explanation."
        )
        examples.append(
            ExampleArtifact(
                example_id=f"example-concept-{index}",
                title=f"Concept application: {concept.name}",
                problem_statement=problem_statement,
                difficulty="introductory",
                study_value=(
                    f"Useful for practicing how '{concept.name}' appears in the local materials even when no formula was extracted."
                ),
                prompt=problem_statement,
                reasoning_context="Fallback concept-driven example because no formulas were extracted.",
                references=concept.references,
            )
        )
    return examples


def _target_symbol(expression: str) -> str | None:
    left, _separator, _right = expression.partition("=")
    symbol = left.strip()
    return symbol or None


def _build_known_values(formula: FormulaArtifact, target_symbol: str | None) -> dict[str, str]:
    values: dict[str, str] = {}
    for symbol in formula.symbol_explanations:
        if symbol == target_symbol:
            continue
        values[symbol] = DEFAULT_KNOWN_VALUES.get(symbol.lower(), "2 units")
    return values


def _linked_concept_names(formula: FormulaArtifact, state: StudyGraphState) -> list[str]:
    concept_lookup = {concept.concept_id: concept.name for concept in state.concepts}
    return [concept_lookup[concept_id] for concept_id in formula.concept_links if concept_id in concept_lookup]


def _concept_references(concept_id: str, state: StudyGraphState) -> list[SourceReference]:
    for concept in state.concepts:
        if concept.concept_id == concept_id:
            return concept.references
    return []


def _example_title(formula: FormulaArtifact, concept_names: list[str], target_symbol: str | None) -> str:
    if concept_names:
        return f"{concept_names[0]} worked example"
    if target_symbol:
        return f"Solve for {target_symbol} with {formula.expression}"
    return f"Worked example for {formula.expression}"


def _problem_statement(
    formula: FormulaArtifact,
    target_symbol: str | None,
    known_values: dict[str, str],
    concept_names: list[str],
) -> str:
    known_bits = [
        f"{_symbol_label(symbol, formula)} = {value}"
        for symbol, value in known_values.items()
    ]
    concept_prefix = f"In a study example about {concept_names[0]}, " if concept_names else ""
    if target_symbol and known_bits:
        return (
            f"{concept_prefix}use `{formula.expression}` to find {_symbol_label(target_symbol, formula)} "
            f"when {', '.join(known_bits)}."
        )
    return (
        f"{concept_prefix}use `{formula.expression}` to explain how the listed quantities relate "
        "in a concrete study example."
    )


def _study_value(formula: FormulaArtifact, concept_names: list[str], target_symbol: str | None) -> str:
    concept_text = concept_names[0] if concept_names else "the local study material"
    if target_symbol:
        return (
            f"Useful for practicing how {concept_text} turns the known quantities into {_symbol_label(target_symbol, formula)}."
        )
    return f"Useful for checking how {formula.expression} appears inside {concept_text}."


def _symbol_label(symbol: str, formula: FormulaArtifact) -> str:
    meaning = formula.symbol_explanations.get(symbol, "").strip()
    if meaning and "TODO:" not in meaning:
        return meaning
    return symbol


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
    lines = []
    for chunk in chunks:
        lines.append(f"- {chunk.source_path} [{chunk.chunk_id}]: {chunk.text[:500].strip()}")
    return "\n".join(lines)
