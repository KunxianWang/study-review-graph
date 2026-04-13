"""Main LangGraph workflow definition."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from study_review_graph.compat import END, START, StateGraph
from study_review_graph.ingestion import load_raw_documents, normalize_documents
from study_review_graph.nodes.content_map import build_content_map_node
from study_review_graph.nodes.examples import generate_examples_node
from study_review_graph.nodes.export import export_outputs_node
from study_review_graph.nodes.quality_review import quality_review_node
from study_review_graph.nodes.review_notes import generate_review_notes_node
from study_review_graph.retrieval import build_retrieval_cache, chunk_documents
from study_review_graph.state import StudyGraphState
from study_review_graph.subgraphs.formula_subgraph import run_formula_subgraph
from study_review_graph.subgraphs.solution_subgraph import run_solution_subgraph


def invoke_study_graph(initial_state: StudyGraphState) -> StudyGraphState:
    """Run the main study graph and return the final validated state."""

    result = build_study_graph().invoke(initial_state.model_dump(mode="python"))
    return StudyGraphState.model_validate(result)


@lru_cache(maxsize=1)
def build_study_graph():
    """Compile the main LangGraph workflow."""

    workflow = StateGraph(StudyGraphState)
    workflow.add_node("ingest_documents", _ingest_documents_graph_node)
    workflow.add_node("normalize_and_parse", _normalize_and_parse_graph_node)
    workflow.add_node("chunk_and_index", _chunk_and_index_graph_node)
    workflow.add_node("build_content_map", _build_content_map_graph_node)
    workflow.add_node("formula_subgraph", _formula_subgraph_graph_node)
    workflow.add_node("example_generation", _example_generation_graph_node)
    workflow.add_node("solution_subgraph", _solution_subgraph_graph_node)
    workflow.add_node("generate_review_notes", _generate_review_notes_graph_node)
    workflow.add_node("quality_review", _quality_review_graph_node)
    workflow.add_node("export_outputs", _export_outputs_graph_node)

    workflow.add_edge(START, "ingest_documents")
    workflow.add_edge("ingest_documents", "normalize_and_parse")
    workflow.add_edge("normalize_and_parse", "chunk_and_index")
    workflow.add_edge("chunk_and_index", "build_content_map")
    workflow.add_edge("build_content_map", "formula_subgraph")
    workflow.add_edge("formula_subgraph", "example_generation")
    workflow.add_edge("example_generation", "solution_subgraph")
    workflow.add_edge("solution_subgraph", "generate_review_notes")
    workflow.add_edge("generate_review_notes", "quality_review")
    workflow.add_edge("quality_review", "export_outputs")
    workflow.add_edge("export_outputs", END)
    return workflow.compile()


def _ingest_documents_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    input_dir = Path(state.config.input_dir)
    raw_docs = load_raw_documents(input_dir)
    warnings = list(state.warnings)
    if not raw_docs:
        warnings.append(f"No supported source files found in {input_dir}.")
    return {"raw_docs": [doc.model_dump(mode="python") for doc in raw_docs], "warnings": warnings}


def _normalize_and_parse_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    normalized_docs = normalize_documents(state.raw_docs)
    return {"normalized_docs": [doc.model_dump(mode="python") for doc in normalized_docs]}


def _chunk_and_index_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    chunks = chunk_documents(
        state.normalized_docs,
        chunk_size=state.config.chunk_size,
        chunk_overlap=state.config.chunk_overlap,
    )
    retrieval_cache = build_retrieval_cache(chunks)
    return {
        "chunks": [chunk.model_dump(mode="python") for chunk in chunks],
        "retrieval_cache": retrieval_cache,
    }


def _build_content_map_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    concepts, warnings = build_content_map_node(state)
    return {
        "concepts": [concept.model_dump(mode="python") for concept in concepts],
        "warnings": state.warnings + warnings,
    }


def _formula_subgraph_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    formulas = run_formula_subgraph(state)
    return {"formulas": [formula.model_dump(mode="python") for formula in formulas]}


def _example_generation_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    examples, warnings = generate_examples_node(state)
    return {
        "examples": [example.model_dump(mode="python") for example in examples],
        "warnings": state.warnings + warnings,
    }


def _solution_subgraph_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    worked_solutions = run_solution_subgraph(state)
    return {
        "worked_solutions": [
            solution.model_dump(mode="python") for solution in worked_solutions
        ]
    }


def _generate_review_notes_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    review_notes = generate_review_notes_node(state)
    return {"review_notes": review_notes.model_dump(mode="python")}


def _quality_review_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    quality_report = quality_review_node(state)
    return {"quality_report": quality_report.model_dump(mode="python")}


def _export_outputs_graph_node(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = StudyGraphState.model_validate(state_dict)
    output_paths = export_outputs_node(state)
    return {"output_paths": output_paths}
