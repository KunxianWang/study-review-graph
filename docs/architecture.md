# Architecture

## Goal

Build a deterministic study and review workflow that turns course materials into grounded learning artifacts for deep understanding.

The current polished v0.1 foundation is centered on four primary outputs:

- `content_map.md`
- `formula_sheet.md`
- `worked_examples.md`
- `worked_solutions.md`
- `practice_set.md`

These outputs can be enhanced with an OpenAI-compatible model endpoint, including Gemini behind an OpenAI-compatible base URL, while preserving a heuristic fallback path.
The wording and section structure of learning artifacts are also guided by a local repository skill at `.agents/skills/review-material-generator/`. This affects output style and pedagogical order, not the graph topology.

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
  -> generate_practice_set
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

Current v0.1 behavior:

- example-to-solution mapping stays deterministic and explicit
- worked examples remain tied to one main formula, plus a small amount of nearby concept context
- direct arithmetic is only attempted for simple solved-form formulas
- optional model calls refine explanation wording and study usefulness, but they do not replace the workflow structure

## State Model

The central state model is `StudyGraphState`. It carries:

- course metadata
- raw and normalized documents
- chunks and retrieval cache
- concepts, formulas, examples, worked solutions, review notes, practice items
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
- worked-example wording refinement
- worked-solution wording refinement
- practice-question wording, hint, and answer refinement

## Local Skill Guidance

The repository includes a local study-material skill that acts as an operating guide for learning artifacts. In the current implementation it mainly affects:

- `review_notes.md` section order and study-note framing
- `worked_examples.md` wording, study value, and Chinese-first presentation
- `worked_solutions.md` ordering around intuition, formula choice, substitution, interpretation, and mistakes
- `practice_set.md` question phrasing, hints, and answer sketches

The review-note node now maps that skill into three explicit output modes:

- `full_review`: full Chinese review pack
- `deep_dive`: one concept / formula / method in depth
- `exam_sprint`: compressed exam-oriented note

This guidance is deliberately applied inside the existing nodes and exporters instead of introducing a separate agent loop or a new orchestration layer.

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

### `worked_examples.md`

This file is intended to turn the concept/formula slice into concrete study practice. Each entry includes:

- example id
- title
- target formula id(s)
- difficulty
- problem statement
- known values when available
- study-value note
- source references

In v0.1, the example structure is deterministic and formula-centered. The model only refines clarity and phrasing around the same local evidence.

### `worked_solutions.md`

This file is intended to support learning, not just answer production. Each entry includes:

- solution id
- linked example id
- plan steps
- detailed steps
- rationale
- common mistakes
- source references

In v0.1, the solution scaffold stays deterministic. The model may improve wording and pedagogical clarity, but it should not invent unsupported derivations or exact conditions.

### `review_notes.md`

This file keeps a stable filename but now changes internal structure based on `RuntimeConfig.study_mode`.

- `full_review` keeps the full review-pack outline
- `deep_dive` chooses one focus target from current grounded artifacts, either from `focus_topic` or from a heuristic auto-selection
- `exam_sprint` compresses the same grounded artifacts into an exam-oriented cheat-sheet style note

The mode switch happens inside the review-note node and markdown exporter. The surrounding LangGraph workflow remains unchanged.

### `practice_set.md`

This file turns the current study artifacts into a compact practice workflow. It is built from:

- concepts for concept questions
- formulas for formula-application questions
- worked examples and worked solutions for calculation questions
- review notes for final reminders and mistake checks

In v0.1, item selection remains deterministic and close to existing grounded artifacts. Optional model calls only refine wording, hints, and answer clarity.

## Extension Points

- external retrieval via Tavily
- model-backed formula parsing and explanation
- stronger evaluators for groundedness and completeness
- richer exporters
