# study-review-graph

`study-review-graph` is a CLI-first, open-source study and review pipeline for course materials. It ingests local study materials such as PDFs, markdown notes, and plain text notes, then produces grounded study artifacts. The first polished v0.1 slice is centered on two showcase outputs: `content_map.md` and `formula_sheet.md`.

The current version supports an OpenAI-compatible model endpoint, including Gemini served through an OpenAI-compatible base URL. LLM enhancement is intentionally limited to the concept-map and formula-sheet slice.

The project exists to support deep understanding rather than shallow summarization. Instead of treating study material as a generic chat prompt, it organizes the work as a deterministic LangGraph workflow with shared state and structured intermediate artifacts. This makes the first version easier to inspect, test, and debug.

## Why LangGraph + LangChain + RAG

- LangGraph provides a durable workflow model with explicit state transitions, which fits a multi-stage study pipeline better than a free-form agent chat loop.
- LangChain provides practical integrations for document loading, chunking, retrieval, and future model backends.
- RAG is used as the grounding layer across multiple stages, not only at the final review stage. The system is intended to retrieve relevant source material while building concepts, formulas, examples, explanations, and review notes.

## What v0.1 Actually Supports

Version `0.1.0` now includes a clearer functional slice with deterministic defaults:

- CLI-first workflow
- Local document ingestion for `.pdf`, `.md`, and `.txt`
- Normalization and chunking
- A simple retrieval layer with deterministic token-overlap scoring
- A presentable `content_map.md` built from headings, section titles, repeated source terms, and optionally LLM-enhanced grounded descriptions
- A presentable `formula_sheet.md` built from heuristic formula extraction plus optionally LLM-enhanced explanations and assumptions
- Deterministic example generation and worked-solution scaffolding
- Deterministic review note generation
- Quality review placeholders for groundedness, formula coverage, and explanation completeness
- Markdown export with source traceability fields where possible

This version is intentionally conservative. It is a runnable repository skeleton with one polished pipeline slice, not a finished pedagogical system. Targeted nodes can use an API-backed model when configured, but the repository still preserves a no-key heuristic fallback path.

## Planned Later

- Model-backed concept extraction and explanation expansion
- Embedding-backed vector retrieval
- Tavily-based external retrieval for supplemental context
- Gemini-based review passes
- Stronger formula parsing and symbolic reasoning
- Richer export formats
- Optional UI layers after the CLI workflow is stable

## Repository Layout

```text
study-review-graph/
|-- README.md
|-- AGENTS.md
|-- LICENSE
|-- CONTRIBUTING.md
|-- CODE_OF_CONDUCT.md
|-- SECURITY.md
|-- pyproject.toml
|-- requirements.txt
|-- .env.example
|-- docs/
|-- examples/
|-- src/study_review_graph/
|-- tests/
`-- .github/
```

## Installation

Python `3.11+` is recommended.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install -e .[dev]
```

If you prefer a requirements file:

```bash
pip install -r requirements.txt
```

`requirements.txt` intentionally delegates to the editable project install so the dependency list stays aligned with `pyproject.toml`.

## Quick Start

Sample input material is provided under `examples/input/`.

If your runtime variables are already exported in the shell, run:

```bash
study-review-graph run ^
  --input-dir examples/input ^
  --output-dir examples/output/run ^
  --course-name "Intro Mechanics" ^
  --user-goal "Build deep understanding of the concepts, formulas, and worked examples."
```

If you want to load variables from a local `.env` file at runtime, use:

```bash
study-review-graph run ^
  --env-file E:\PROJECT\AGENT\.env ^
  --input-dir examples/input ^
  --output-dir examples/output/run ^
  --course-name "Intro Mechanics" ^
  --user-goal "Build deep understanding of the concepts, formulas, and worked examples."
```

You can also run the module directly:

```bash
python -m study_review_graph run --env-file E:\PROJECT\AGENT\.env --input-dir examples/input --output-dir examples/output/run
```

When `--env-file` is provided explicitly, values in that file take precedence over stale shell environment variables. This helps avoid confusing runtime mismatches such as an old `MODEL_PROVIDER` still being present in the shell.

The supported runtime variables are:

- `OPENAI_API_KEY`
- `OPENAI_API_BASE`
- `OPENAI_MODEL`
- `MODEL_PROVIDER`
- `LANGSMITH_TRACING`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`
- `TAVILY_API_KEY`

Accepted `MODEL_PROVIDER` values for the current OpenAI-compatible client path are:

- `openai`
- `openai_compatible`
- `gemini`
- `gemini_openai_compatible`

## Generated Outputs

The primary showcase outputs are:

- `content_map.md`
- `formula_sheet.md`

`content_map.md` contains:

- a curated list of inferred study concepts
- a short grounded description for each concept
- linked formulas when available
- source references for traceability

`formula_sheet.md` contains:

- the extracted formula expression
- the formula id
- symbol explanations
- conditions and assumptions
- linked concepts when available
- source references
- explicit TODO markers where understanding is still incomplete

The exporter also keeps these additional files:

- `overview.md`
- `formulas.md` (legacy compatibility mirror of `formula_sheet.md`)
- `worked_solutions.md`
- `review_notes.md`
- `quality_report.md`

These outputs are scaffolded for grounded study workflows and include source references whenever the current stage can preserve them.

## Current Limitations

- Concept names are still heuristic and tied to headings plus repeated source terms.
- Content-map descriptions can be LLM-enhanced, but only from retrieved local context.
- Formula extraction is heuristic and line-based.
- Symbol explanations and formula conditions can be LLM-enhanced from retrieved local context.
- Linked concepts still start from heuristic matching and may be improved by the model when local evidence is clear.
- Quality review uses placeholder checks rather than advanced evaluators.
- Retrieval is deterministic token overlap, not embeddings.
- PDF support requires the optional runtime dependencies to be installed.

## Fallback Behavior

- If model configuration is absent, the pipeline keeps using the heuristic path.
- If model configuration is incomplete, the repository surfaces warnings and falls back safely.
- If an API call fails, the affected nodes fall back to heuristic behavior instead of crashing the whole run.
- CI and tests do not require live API access.

## Architecture Overview

The main LangGraph workflow is organized around these nodes:

1. `ingest_documents`
2. `normalize_and_parse`
3. `chunk_and_index`
4. `build_content_map`
5. `formula_subgraph`
6. `example_generation`
7. `solution_subgraph`
8. `generate_review_notes`
9. `quality_review`
10. `export_outputs`

Two specialized subgraphs keep responsibilities sharp:

- `formula_subgraph`: formula extraction, symbol explanation, conditions, and links to concepts
- `solution_subgraph`: solution planning, explanation expansion, rationale, and common mistakes

See [docs/architecture.md](docs/architecture.md) for more detail.
See [docs/state_schema.md](docs/state_schema.md) for the current workflow state model.

## Contributing

Contributions are welcome. Please start with [CONTRIBUTING.md](CONTRIBUTING.md), review [AGENTS.md](AGENTS.md) if you are using Codex, and check the issue templates before opening new work.

## Status

This repository is intentionally at an early but structured stage. The workflow is runnable, testable, and debuggable, while several important capabilities remain explicit TODOs rather than hidden assumptions.
