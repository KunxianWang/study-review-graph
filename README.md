# study-review-graph

`study-review-graph` is a CLI-first, open-source study and review pipeline for course materials. It ingests local study materials such as PDFs, markdown notes, and plain text notes, then produces grounded study artifacts. The current polished v0.1 foundation is centered on five showcase outputs: `content_map.md`, `formula_sheet.md`, `worked_examples.md`, `worked_solutions.md`, and `practice_set.md`.

The current version supports an OpenAI-compatible model endpoint, including Gemini served through an OpenAI-compatible base URL. LLM enhancement is intentionally limited to targeted nodes inside the concept/formula slice and the example/solution slice.
For learning artifacts, the repository also follows a local study-material skill under `.agents/skills/review-material-generator/`, which keeps review notes, worked examples, and worked solutions closer to a Chinese-first study-note structure without changing the underlying graph architecture.

The project exists to support deep understanding rather than shallow summarization. Instead of treating study material as a generic chat prompt, it organizes the work as a deterministic LangGraph workflow with shared state and structured intermediate artifacts. This makes the first version easier to inspect, test, and debug.

The repository now also includes a lightweight multi-agent study-session layer on top of that foundation. This agent layer does not replace the grounded pipeline; it routes user study requests to bounded specialists that reuse the existing artifacts.

## Why LangGraph + LangChain + RAG

- LangGraph provides a durable workflow model with explicit state transitions, which fits a multi-stage study pipeline better than a free-form agent chat loop.
- LangChain provides practical integrations for document loading, chunking, retrieval, and future model backends.
- RAG is used as the grounding layer across multiple stages, not only at the final review stage. The system is intended to retrieve relevant source material while building concepts, formulas, examples, explanations, and review notes.

## What v0.1 Actually Supports

Version `0.1.0` now includes two clearer functional slices with deterministic defaults:

- CLI-first workflow
- Local document ingestion for `.pdf`, `.md`, and `.txt`
- Normalization and chunking
- A simple retrieval layer with deterministic token-overlap scoring
- A presentable `content_map.md` built from headings, section titles, repeated source terms, and optionally LLM-enhanced grounded descriptions
- A presentable `formula_sheet.md` built from heuristic formula extraction plus optionally LLM-enhanced explanations and assumptions
- A presentable `worked_examples.md` built from extracted formulas, linked concepts, local references, and optionally LLM-refined study wording
- A presentable `worked_solutions.md` built from those worked examples, with plan steps, detailed steps, rationale, common mistakes, and optionally LLM-refined explanation wording
- Deterministic review note generation aligned to a local Chinese study-note skill, with selectable output modes
- Quality review placeholders for groundedness, formula coverage, and explanation completeness
- Markdown export with source traceability fields where possible
- A grounded `practice_set.md` built from current concepts, formulas, worked examples, worked solutions, and review notes
- A lightweight multi-agent orchestration layer for request routing across concept help, formula help, examples, practice, answer checking, and review guidance

This version is intentionally conservative. It is a runnable repository skeleton with two polished pipeline slices, not a finished pedagogical system. Targeted nodes can use an API-backed model when configured, but the repository still preserves a no-key heuristic fallback path.

The current polished slices are:

1. content and formula understanding via `content_map.md` and `formula_sheet.md`
2. example and solution learning support via `worked_examples.md` and `worked_solutions.md`
3. compact practice generation via `practice_set.md`
4. single-item answer checking via `answer_feedback.md`
5. lightweight study-session orchestration via `agent_session.md`

## Study Modes

`review_notes.md` now supports three skill-aligned study modes:

- `full_review`
  Default mode. Produces the full Chinese review-pack structure:
  `本章主线 -> 关键定义与公式 -> 算法 / 方法逐个讲解 -> 每个主要方法对应的例题 / worked example -> 易错点 / 混淆点 -> 考前速记版`
- `deep_dive`
  Focuses on one primary concept, formula, or method. If `--focus-topic` is provided, the pipeline uses that target when it can match current grounded artifacts. If no target is provided, it auto-selects the strongest current candidate and says so in the output.
- `exam_sprint`
  Produces a compressed, exam-oriented note:
  `必背定义 -> 核心公式 -> 高频考点 -> 一道典型题 -> 速记提醒`

These modes reuse the same grounded pipeline artifacts instead of creating a separate note-generation system.

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
  --user-goal "Build deep understanding of the concepts, formulas, and worked examples." ^
  --study-mode full_review
```

You can also run the module directly:

```bash
python -m study_review_graph run --env-file E:\PROJECT\AGENT\.env --input-dir examples/input --output-dir examples/output/run --study-mode full_review
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

Study-note mode flags:

- `--study-mode full_review`
- `--study-mode deep_dive`
- `--study-mode exam_sprint`
- `--focus-topic "Your concept or formula"` for `deep_dive`

Practice-set flag:

- `--include-practice-set/--skip-practice-set`
  Defaults to enabled. Normal runs now generate `practice_set.md` unless you explicitly skip it.

Answer-check command inputs:

- `check-answer`
- `--practice-id`
- `--answer` or `--answer-file`
- plus the same grounding options such as `--input-dir`, `--output-dir`, `--study-mode`, and `--env-file`

Agent-session command inputs:

- `study-session`
- `--request`
- `--input-dir`
- `--output-dir`
- `--study-mode`
- optional `--focus-topic`
- optional `--practice-id`
- optional `--answer` or `--answer-file`
- optional `--env-file`

## Generated Outputs

The primary showcase outputs are:

- `content_map.md`
- `formula_sheet.md`
- `worked_examples.md`
- `worked_solutions.md`
- `practice_set.md`

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

`worked_examples.md` contains:

- the example id
- a study-oriented title
- target formula id(s)
- a difficulty label
- a grounded problem statement
- known values when a direct formula example is available
- a short note about why the example is useful for study
- source references

`worked_solutions.md` contains:

- the solution id and linked example id
- plan steps
- detailed steps
- rationale
- common mistakes
- source references

`practice_set.md` contains:

- grounded concept questions
- grounded formula-application questions
- grounded worked-calculation questions
- a hint for each question
- a reference answer or solution sketch for each question
- review reminders based on current notes and common mistakes

The exporter also keeps these additional files:

- `overview.md`
- `formulas.md` (legacy compatibility mirror of `formula_sheet.md`)
- `review_notes.md`
- `quality_report.md`

The answer-check utility path also writes:

- `answer_feedback.md`
- `agent_session.md`

These outputs are scaffolded for grounded study workflows and include source references whenever the current stage can preserve them.
`review_notes.md` keeps the same filename, but its internal structure now changes with the selected study mode and follows the local skill templates in `.agents/skills/review-material-generator/`.
`practice_set.md` reuses the current grounded artifacts rather than generating from a disconnected quiz subsystem.
`answer_feedback.md` reuses the current practice item, linked formulas, linked concepts, worked examples, worked solutions, and review notes to produce a study-oriented feedback note.
`agent_session.md` records the detected intent, selected specialist agent, grounded response, references, and recommended next action for one study-session request.

## Current Limitations

- Concept names are still heuristic and tied to headings plus repeated source terms.
- Content-map descriptions can be LLM-enhanced, but only from retrieved local context.
- Formula extraction is heuristic and line-based.
- Symbol explanations and formula conditions can be LLM-enhanced from retrieved local context.
- Linked concepts still start from heuristic matching and may be improved by the model when local evidence is clear.
- Worked-example structure is deterministic first. The model only refines wording around the same formula-centered example.
- Worked-solution generation is still conservative. It can improve step wording with the model, but direct arithmetic is only attempted for simple solved-form formulas.
- Review-note section order is skill-guided, but the actual section content is still assembled from existing concepts, formulas, examples, and solutions rather than a broader pedagogical planner.
- Practice-item selection is deterministic first. The model can refine question wording, hints, and answer clarity, but it does not invent new unsupported topics.
- Answer checking is heuristic and study-oriented. It can detect broadly correct answers, partial answers, wrong-formula drift, and missing reasoning steps, but it is not a theorem prover or a mathematically complete grader.
- The study-session supervisor routes requests deterministically first. It is agentic in orchestration, but it still depends on the same grounded artifacts and tool wrappers rather than open-ended agent chat.
- `deep_dive` target selection is still heuristic when `--focus-topic` is omitted or cannot be matched cleanly.
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
9. `generate_practice_set`
10. `quality_review`
11. `export_outputs`

Two specialized subgraphs keep responsibilities sharp:

- `formula_subgraph`: formula extraction, symbol explanation, conditions, and links to concepts
- `solution_subgraph`: solution planning, explanation expansion, rationale, and common mistakes

`generate_review_notes` now branches by `study_mode` while still consuming the same shared state artifacts. The graph shape does not change.

## Example Commands

Default full review:

```bash
study-review-graph run --input-dir examples/input --output-dir examples/output/run --study-mode full_review
```

Deep dive with an explicit focus:

```bash
study-review-graph run --input-dir examples/input --output-dir examples/output/deep_dive_run --study-mode deep_dive --focus-topic "Kinetic Energy"
```

Exam sprint:

```bash
study-review-graph run --input-dir examples/input --output-dir examples/output/exam_sprint_run --study-mode exam_sprint
```

Full sample pipeline with practice generation enabled:

```bash
study-review-graph run --input-dir examples/input --output-dir examples/output/run --study-mode full_review --include-practice-set
```

Check one practice answer:

```bash
study-review-graph check-answer --input-dir examples/input --output-dir examples/output/check_answer_run --practice-id practice-formula-0 --answer "先看题目是不是在讨论净力、质量和加速度的关系，再确认质量可以视为常量，所以应该用 F = m * a。"
```

Run one study session through the agent layer:

```bash
study-review-graph study-session --input-dir examples/input --output-dir examples/output/study_session_run --request "请重点讲一下牛顿第二定律这个公式什么时候用" --study-mode deep_dive --focus-topic "Newton's Second Law"
```

See [docs/architecture.md](docs/architecture.md) for more detail.
See [docs/state_schema.md](docs/state_schema.md) for the current workflow state model.

## Contributing

Contributions are welcome. Please start with [CONTRIBUTING.md](CONTRIBUTING.md), review [AGENTS.md](AGENTS.md) if you are using Codex, and check the issue templates before opening new work.

## Status

This repository is intentionally at an early but structured stage. The workflow is runnable, testable, and debuggable, while several important capabilities remain explicit TODOs rather than hidden assumptions.
