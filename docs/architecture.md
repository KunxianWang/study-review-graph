# Architecture

## Goal

Build a deterministic study and review workflow that turns course materials into grounded learning artifacts for deep understanding.

The first polished v0.1 slice is centered on two primary outputs:

- `content_map.md`
- `formula_sheet.md`

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

Current v0.1 behavior:

- extraction is still heuristic
- symbol explanations come from local glossary-style lines when available
- conditions are pulled from nearby sentence cues when available, otherwise explicit TODO markers remain

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

The current polished slice uses this retrieval layer in two visible ways:

- grounding concept descriptions for `content_map.md`
- pulling nearby support for formula conditions and concept links in `formula_sheet.md`

## Primary Outputs

### `content_map.md`

This file is intended to be a readable study artifact rather than a debug dump. Each concept includes:

- concept name
- short grounded description
- linked formulas when available
- source references

### `formula_sheet.md`

This file is intended to be a readable formula study sheet. Each entry includes:

- formula expression
- formula id
- symbol explanations
- conditions and assumptions
- linked concepts when available
- source references
- explicit TODO markers where interpretation remains incomplete

## Extension Points

- external retrieval via Tavily
- model-backed formula parsing and explanation
- stronger evaluators for groundedness and completeness
- richer exporters
