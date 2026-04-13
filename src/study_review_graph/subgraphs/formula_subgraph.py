"""Formula-focused subgraph for extraction and linking."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from study_review_graph.compat import END, START, StateGraph
from study_review_graph.model_client import get_cached_formula_enrichment, get_model_client
from study_review_graph.retrieval import retrieve_relevant_chunks
from study_review_graph.state import FormulaArtifact, StudyGraphState

FORMULA_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*\s*=\s*.+)")
CONDITION_CUES = ("when", "assuming", "valid", "under", "if", "use this")


def extract_formulas_node(state: StudyGraphState) -> list[FormulaArtifact]:
    """Extract simple formula candidates from document content."""

    formulas: list[FormulaArtifact] = []
    seen: set[str] = set()
    for chunk in state.chunks:
        for line in chunk.text.splitlines():
            candidate = line.strip()
            match = FORMULA_PATTERN.match(candidate)
            if not match:
                continue
            expression = match.group(1).strip()
            if expression in seen:
                continue
            seen.add(expression)
            formulas.append(
                FormulaArtifact(
                    formula_id=f"formula-{len(formulas)}",
                    expression=expression,
                    references=chunk.references,
                    notes=(
                        "TODO: heuristic extraction only. Confirm the exact derivation and scope "
                        "from the source material."
                    ),
                )
            )
    return formulas


def explain_formula_symbols_node(state: StudyGraphState) -> list[FormulaArtifact]:
    """Attach lightweight symbol explanations and conditions."""

    updated: list[FormulaArtifact] = []
    symbol_glossary = _build_symbol_glossary(state)
    model_client = get_model_client()
    for formula in state.formulas:
        symbols = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula.expression)))
        explanations = {
            symbol: symbol_glossary.get(
                symbol.lower(),
                "TODO: infer a grounded explanation for this symbol from nearby source context.",
            )
            for symbol in symbols
        }
        supporting_chunks = retrieve_relevant_chunks(formula.expression, state, top_k=2)
        conditions = _extract_conditions(formula.expression, supporting_chunks)
        llm_payload, llm_warning = _generate_formula_enrichment(
            formula=formula,
            symbols=symbols,
            supporting_chunks=supporting_chunks,
            concept_names=[concept.name for concept in state.concepts],
            model_client=model_client,
        )
        if llm_payload:
            explanations = _merge_symbol_explanations(explanations, llm_payload)
            conditions = _merge_conditions(conditions, llm_payload)
        note = formula.notes
        llm_note = _extract_note(llm_payload) if llm_payload else None
        if llm_note:
            note = f"{note} {llm_note}".strip()
        if llm_warning:
            note = f"{note} {llm_warning}".strip()
        updated.append(
            formula.model_copy(
                update={
                    "symbol_explanations": explanations,
                    "conditions": conditions,
                    "notes": note,
                }
            )
        )
    return updated


def link_formulas_to_concepts_node(state: StudyGraphState) -> list[FormulaArtifact]:
    """Link formulas to nearby concept names."""

    updated: list[FormulaArtifact] = []
    model_client = get_model_client()
    availability_warning = model_client.availability_warning()
    for formula in state.formulas:
        supporting_chunks = retrieve_relevant_chunks(formula.expression, state, top_k=2)
        scored_concepts = _score_contextual_concepts(
            state=state,
            supporting_chunks=supporting_chunks,
            formula=formula,
        )
        linked = [concept_id for concept_id, _score in scored_concepts[:2]]
        llm_payload, llm_warning = _generate_formula_enrichment(
            formula=formula,
            symbols=sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula.expression))),
            supporting_chunks=supporting_chunks,
            concept_names=[concept.name for concept in state.concepts],
            model_client=model_client,
        )
        if llm_payload:
            linked = _merge_concept_links(
                existing_links=linked,
                suggested_concepts=llm_payload.get("linked_concepts", []),
                state=state,
                allowed_concept_ids={concept_id for concept_id, _score in scored_concepts[:4]},
            )
        note_lines = [formula.notes]
        if availability_warning:
            note_lines.append(availability_warning)
        if llm_warning:
            note_lines.append(llm_warning)
        if not linked:
            note_lines.append("TODO: no linked concept found from current heuristic matching.")
        if any("TODO:" in item for item in formula.conditions):
            note_lines.append("TODO: formula conditions remain incomplete.")
        unique_note_lines = list(dict.fromkeys(line for line in note_lines if line))
        updated.append(
            formula.model_copy(
                update={
                    "concept_links": linked,
                    "notes": " ".join(unique_note_lines),
                }
            )
        )
    return updated


def run_formula_subgraph(state: StudyGraphState) -> list[FormulaArtifact]:
    """Invoke the formula subgraph and return the updated formula list."""

    result = _compiled_formula_subgraph().invoke(state.model_dump(mode="python"))
    validated = StudyGraphState.model_validate(result)
    return validated.formulas


@lru_cache(maxsize=1)
def _compiled_formula_subgraph():
    workflow = StateGraph(StudyGraphState)
    workflow.add_node("extract_formulas", _extract_formulas_graph_node)
    workflow.add_node("explain_formula_symbols", _explain_formula_symbols_graph_node)
    workflow.add_node("link_formulas_to_concepts", _link_formulas_to_concepts_graph_node)
    workflow.add_edge(START, "extract_formulas")
    workflow.add_edge("extract_formulas", "explain_formula_symbols")
    workflow.add_edge("explain_formula_symbols", "link_formulas_to_concepts")
    workflow.add_edge("link_formulas_to_concepts", END)
    return workflow.compile()


def _extract_formulas_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    return {"formulas": [formula.model_dump(mode="python") for formula in extract_formulas_node(state)]}


def _explain_formula_symbols_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    return {
        "formulas": [
            formula.model_dump(mode="python") for formula in explain_formula_symbols_node(state)
        ]
    }


def _link_formulas_to_concepts_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    return {
        "formulas": [
            formula.model_dump(mode="python") for formula in link_formulas_to_concepts_node(state)
        ]
    }


def _build_symbol_glossary(state: StudyGraphState) -> dict[str, str]:
    glossary: dict[str, str] = {}
    for doc in state.normalized_docs:
        for line in doc.content.splitlines():
            stripped = line.strip().lstrip("-").strip()
            if ":" not in stripped:
                continue
            key, value = [part.strip() for part in stripped.split(":", 1)]
            if key:
                glossary[key.lower()] = value
    return glossary


def _extract_conditions(expression: str, chunks) -> list[str]:
    conditions: list[str] = []
    seen = set()
    for local_context in _extract_formula_support_contexts(expression, chunks):
        for sentence in _sentence_candidates(local_context):
            lowered = sentence.lower()
            if expression.lower() in lowered:
                continue
            if any(cue in lowered for cue in CONDITION_CUES):
                if sentence not in seen:
                    seen.add(sentence)
                    conditions.append(sentence)
    if not conditions:
        conditions.append(
            "TODO: confirm the exact assumptions and valid-use conditions from nearby source text."
        )
    return conditions


def _sentence_candidates(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
        if sentence.strip()
    ]


def _generate_formula_enrichment(
    *,
    formula: FormulaArtifact,
    symbols: list[str],
    supporting_chunks,
    concept_names: list[str],
    model_client,
) -> tuple[dict[str, Any] | None, str | None]:
    if not supporting_chunks:
        return None, None

    if model_client.availability_warning():
        return None, model_client.availability_warning()

    result = get_cached_formula_enrichment(
        formula_id=formula.formula_id,
        expression=formula.expression,
        symbols_csv=", ".join(symbols),
        concept_names_csv=", ".join(concept_names),
        chunk_context=_render_chunk_context(
            _extract_formula_support_contexts(formula.expression, supporting_chunks)
        ),
    )
    return result.payload, result.warning


def _merge_symbol_explanations(
    explanations: dict[str, str],
    llm_payload: dict[str, Any],
) -> dict[str, str]:
    merged = dict(explanations)
    llm_symbols = llm_payload.get("symbol_explanations", {})
    if not isinstance(llm_symbols, dict):
        return merged
    for symbol, meaning in llm_symbols.items():
        if symbol in merged and str(meaning).strip():
            merged[symbol] = str(meaning).strip()
    return merged


def _merge_conditions(existing_conditions: list[str], llm_payload: dict[str, Any]) -> list[str]:
    conditions = [condition.strip() for condition in existing_conditions if condition.strip()]
    llm_conditions = llm_payload.get("conditions", [])
    if isinstance(llm_conditions, list):
        for condition in llm_conditions:
            cleaned = str(condition).strip()
            if cleaned and cleaned not in conditions:
                conditions.append(cleaned)
    return conditions or [
        "TODO: confirm the exact assumptions and valid-use conditions from nearby source text."
    ]


def _merge_concept_links(
    *,
    existing_links: list[str],
    suggested_concepts: Any,
    state: StudyGraphState,
    allowed_concept_ids: set[str],
) -> list[str]:
    links = list(existing_links)
    if not isinstance(suggested_concepts, list):
        return links

    concept_lookup = {concept.name.lower(): concept.concept_id for concept in state.concepts}
    for concept_name in suggested_concepts:
        concept_id = concept_lookup.get(str(concept_name).strip().lower())
        if concept_id and concept_id in allowed_concept_ids and concept_id not in links:
            links.append(concept_id)
        if len(links) >= 2:
            break
    return links


def _extract_note(llm_payload: dict[str, Any]) -> str | None:
    note = str(llm_payload.get("note", "")).strip()
    return note or None


def _render_chunk_context(chunks) -> str:
    lines = []
    for index, chunk_text in enumerate(chunks):
        if hasattr(chunk_text, "source_path"):
            lines.append(
                f"- {chunk_text.source_path} [{chunk_text.chunk_id}]: {chunk_text.text[:500].strip()}"
            )
        else:
            lines.append(f"- local-context-{index}: {str(chunk_text)[:500].strip()}")
    return "\n".join(lines)


def _extract_local_formula_contexts(expression: str, chunks) -> list[str]:
    local_contexts: list[str] = []
    for chunk in chunks:
        lines = [line.strip() for line in chunk.text.splitlines() if line.strip()]
        contexts = _slice_formula_contexts(expression, lines, trailing_window=2)
        local_contexts.extend(contexts or [chunk.text])
    return local_contexts or [chunk.text for chunk in chunks]


def _extract_formula_support_contexts(expression: str, chunks) -> list[str]:
    support_contexts: list[str] = []
    for chunk in chunks:
        lines = [line.strip() for line in chunk.text.splitlines() if line.strip()]
        contexts = _slice_formula_contexts(expression, lines, trailing_window=6)
        support_contexts.extend(contexts or [chunk.text])
    return support_contexts or [chunk.text for chunk in chunks]


def _slice_formula_contexts(expression: str, lines: list[str], *, trailing_window: int) -> list[str]:
    if not lines:
        return []

    formula_indices = [index for index, line in enumerate(lines) if FORMULA_PATTERN.match(line)]
    target_indices = [index for index in formula_indices if lines[index] == expression]
    if not target_indices:
        return []

    sliced_contexts: list[str] = []
    for target_index in target_indices:
        previous_formula = max((idx for idx in formula_indices if idx < target_index), default=-1)
        next_formula = min((idx for idx in formula_indices if idx > target_index), default=len(lines))
        if previous_formula >= 0:
            start = max(previous_formula + 2, target_index - 1)
            heading_index = target_index - 2
            if heading_index >= 0 and lines[heading_index].startswith("#"):
                start = max(previous_formula + 2, heading_index)
        else:
            start = max(0, target_index - 3)
        end = min(next_formula, target_index + trailing_window)
        sliced_contexts.append("\n".join(lines[start:end]))
    return sliced_contexts


def _select_contextual_concepts(
    *,
    state: StudyGraphState,
    supporting_chunks,
    formula: FormulaArtifact,
) -> list[str]:
    return [concept_id for concept_id, _score in _score_contextual_concepts(
        state=state,
        supporting_chunks=supporting_chunks,
        formula=formula,
    )[:2]]


def _score_contextual_concepts(
    *,
    state: StudyGraphState,
    supporting_chunks,
    formula: FormulaArtifact,
) -> list[tuple[str, int]]:
    scored: list[tuple[str, int]] = []
    local_text = "\n".join(_extract_local_formula_contexts(formula.expression, supporting_chunks)).lower()
    local_tokens = set(re.findall(r"[A-Za-z][A-Za-z'-]*", local_text))
    expression_tokens = set(re.findall(r"[A-Za-z][A-Za-z'-]*", formula.expression.lower()))

    for concept in state.concepts:
        concept_name_lower = concept.name.lower()
        concept_tokens = set(re.findall(r"[A-Za-z][A-Za-z'-]*", concept_name_lower))
        if not concept_tokens:
            continue

        score = 0
        if concept_name_lower in local_text:
            score += 5
        score += 2 * len(concept_tokens.intersection(local_tokens))
        score += len(concept_tokens.intersection(expression_tokens))
        if any(reference.chunk_id in {chunk.chunk_id for chunk in supporting_chunks} for reference in concept.references):
            score += 1
        if score >= 3:
            scored.append((concept.concept_id, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored
