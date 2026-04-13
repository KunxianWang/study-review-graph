"""Formula-focused subgraph for extraction and linking."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from study_review_graph.compat import END, START, StateGraph
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
        updated.append(
            formula.model_copy(
                update={
                    "symbol_explanations": explanations,
                    "conditions": conditions,
                }
            )
        )
    return updated


def link_formulas_to_concepts_node(state: StudyGraphState) -> list[FormulaArtifact]:
    """Link formulas to nearby concept names."""

    updated: list[FormulaArtifact] = []
    for formula in state.formulas:
        supporting_chunks = retrieve_relevant_chunks(formula.expression, state, top_k=2)
        linked = [
            concept.concept_id
            for concept in state.concepts
            if concept.name.lower() in formula.expression.lower()
            or any(
                concept.name.lower() in (reference.excerpt or "").lower()
                for reference in formula.references
            )
            or any(concept.name.lower() in chunk.text.lower() for chunk in supporting_chunks)
        ]
        note_lines = [formula.notes]
        if not linked:
            note_lines.append("TODO: no linked concept found from current heuristic matching.")
        if any("TODO:" in item for item in formula.conditions):
            note_lines.append("TODO: formula conditions remain incomplete.")
        updated.append(
            formula.model_copy(
                update={
                    "concept_links": linked,
                    "notes": " ".join(line for line in note_lines if line),
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
    for chunk in chunks:
        for sentence in _sentence_candidates(chunk.text):
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
