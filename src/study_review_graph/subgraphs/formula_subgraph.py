"""Formula-focused subgraph for extraction and linking."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from study_review_graph.compat import END, START, StateGraph
from study_review_graph.state import FormulaArtifact, StudyGraphState

FORMULA_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*\s*=\s*.+)")


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
                    notes="TODO: replace heuristic extraction with model-assisted parsing.",
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
        conditions = ["TODO: verify formula-specific assumptions from retrieved supporting chunks."]
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
        linked = [
            concept.concept_id
            for concept in state.concepts
            if concept.name.lower() in formula.expression.lower()
            or any(
                concept.name.lower() in (reference.excerpt or "").lower()
                for reference in formula.references
            )
        ]
        updated.append(formula.model_copy(update={"concept_links": linked}))
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
