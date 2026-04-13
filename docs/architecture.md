# Architecture

## Goal

Build a deterministic study and review workflow that turns course materials into grounded learning artifacts for deep understanding.

## Design Principles

- shared workflow state over ad hoc agent memory
- structured artifacts over free-form text blobs
- retrieval as a reusable grounding layer
- explicit subgraph boundaries
- simple defaults in v0.1

## Main Workflow

```text
ingest_documents
  -> normalize_and_parse
  -> chunk_and_index
  -> build_content_map
  -> formula_subgraph
  -> example_generation
  -> solution_subgraph
  -> generate_review_notes
  -> quality_review
  -> export_outputs
```

## Subgraphs

### Formula Subgraph

Responsibilities:

- identify candidate formulas
- attach symbol explanations
- record conditions and assumptions
- link formulas back to concepts and source references

This subgraph should not generate worked examples or narrative review notes.

### Solution Subgraph

Responsibilities:

- create step plans for solving examples
- expand plans into worked explanations
- attach rationale and common mistakes

This subgraph should not own formula discovery.

## State Model

The central state model is `StudyGraphState`. It carries:

- course metadata
- raw and normalized documents
- chunks and retrieval cache
- concepts, formulas, examples, worked solutions, review notes
- output paths
- quality report
- warnings and errors
- runtime config

## Retrieval Strategy in v0.1

The first version uses deterministic chunk scoring based on token overlap. This keeps the system easy to run locally and easy to inspect in tests.

Future versions can replace this with embedding-backed retrieval while preserving the same module boundary.

## Extension Points

- external retrieval via Tavily
- model-backed formula parsing and explanation
- stronger evaluators for groundedness and completeness
- richer exporters
