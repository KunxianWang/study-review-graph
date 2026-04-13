# Architecture

## Goal

Build a deterministic study and review workflow that turns course materials into grounded learning artifacts for deep understanding.

The first polished v0.1 slice is centered on two primary outputs:

- `content_map.md`
- `formula_sheet.md`

These outputs can be enhanced with an OpenAI-compatible model endpoint, including Gemini behind an OpenAI-compatible base URL, while preserving a heuristic fallback path.

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
- symbol explanations start from local glossary-style lines and may be refined by a targeted model call
- conditions start from nearby sentence cues and may be refined by a targeted model call
- concept linking remains heuristic-first, with optional model-assisted suggestions constrained to known concept names

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

## Targeted Model Integration

The repository now includes a small model client layer for OpenAI-compatible endpoints.

Design constraints:

- environment-driven runtime configuration
- no mandatory model access for tests or local fallback runs
- model enhancement is limited to a few targeted nodes
- the graph remains a deterministic pipeline, not a free-form agent system

Current LLM-enhanced nodes:

- content-map description generation
- formula-sheet symbol explanation refinement
- formula-sheet condition refinement
- formula-sheet concept-link suggestion

## Primary Outputs

### `content_map.md`

This file is intended to be a readable study artifact rather than a debug dump. Each concept includes:

- concept name
- short grounded description
- linked formulas when available
- source references

In v0.1, concept names remain source-tied and heuristic. Only the description field may be LLM-enhanced.

### `formula_sheet.md`

This file is intended to be a readable formula study sheet. Each entry includes:

- formula expression
- formula id
- symbol explanations
- conditions and assumptions
- linked concepts when available
- source references
- explicit TODO markers where interpretation remains incomplete

In v0.1, formula extraction remains heuristic. The model only enhances interpretation around the extracted formula.

## Extension Points

- external retrieval via Tavily
- model-backed formula parsing and explanation
- stronger evaluators for groundedness and completeness
- richer exporters
