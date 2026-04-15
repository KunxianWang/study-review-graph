# study-review-graph

`study-review-graph` is a CLI-first study and review workflow for course materials. It ingests local PDFs and notes, builds grounded study artifacts, generates practice, checks one answer at a time, and exposes a lightweight study-session layer over those existing artifacts.

`v0.1.1` is the first release that goes beyond the earlier `v0.1.0` runnable skeleton. The current release keeps the deterministic LangGraph pipeline as the base system and adds a more complete study loop on top of it:

- grounded study artifacts
- targeted LLM enhancement through an OpenAI-compatible endpoint
- Chinese-first study-note alignment via the local skill under `.agents/skills/review-material-generator/`
- study modes for review notes
- practice generation
- answer checking
- lightweight session routing

This repository is not a generic chatbot or an autonomous tutor. The agent layer is intentionally small: it routes requests to bounded specialists that reuse the same grounded pipeline outputs.

## Why LangGraph + LangChain + RAG

- LangGraph keeps the workflow explicit and inspectable through shared state.
- LangChain provides practical document, retrieval, and model integration boundaries.
- RAG is used as a grounding layer across multiple stages instead of only at the final output.

## Release Scope

`v0.1.0` should be treated as the baseline runnable skeleton.

`v0.1.1` is the first more complete study loop built on that base. It currently supports:

- local document ingestion for `.pdf`, `.md`, and `.txt`
- normalization and chunking
- deterministic token-overlap retrieval
- `content_map.md`
- `formula_sheet.md`
- `worked_examples.md`
- `worked_solutions.md`
- `review_notes.md` with three study modes
- `practice_set.md`
- `answer_feedback.md`
- `agent_session.md`

## Deterministic vs LLM-Enhanced

The repository is deterministic first.

Deterministic core:

- document ingestion and normalization
- chunking and retrieval
- graph orchestration
- base concept selection
- base formula extraction
- example / solution scaffolding
- practice-item scaffolding
- answer-check structure
- study-session routing

Targeted LLM enhancement when configured:

- concept description wording
- formula symbol and condition explanation refinement
- example wording refinement
- worked-solution wording refinement
- practice question / hint / answer wording refinement
- answer-feedback wording refinement through the existing feedback path

If no model is configured, the repository stays usable and falls back to heuristic behavior.

## Main Commands

### `run`

Build the grounded study artifact bundle.

```bash
study-review-graph run --input-dir examples/input --output-dir examples/output/run --study-mode full_review
```

### `check-answer`

Check one answer against the current grounded practice set.

```bash
study-review-graph check-answer --input-dir examples/input --output-dir examples/output/check_answer_run --practice-id practice-formula-0 --answer "先看题目是不是在讨论净力、质量和加速度的关系，再确认质量可以视为常量，所以应该用 F = m * a。"
```

### `study-session`

Route one study request through the lightweight agent layer.

```bash
study-review-graph study-session --input-dir examples/input --output-dir examples/output/study_session_run --request "请重点讲一下牛顿第二定律这个公式什么时候用" --study-mode deep_dive --focus-topic "Newton's Second Law"
```

## Study Modes

`review_notes.md` supports three skill-aligned modes:

- `full_review`
  Default Chinese review-pack structure:
  `本章主线 -> 关键定义与公式 -> 算法 / 方法逐个讲解 -> 每个主要方法对应的例题 / worked example -> 易错点 / 混淆点 -> 考前速记版`
- `deep_dive`
  Focus on one concept, formula, or method. If `--focus-topic` is missing, the current implementation auto-selects a focus target from existing grounded artifacts.
- `exam_sprint`
  A compressed exam-oriented note:
  `必背定义 -> 核心公式 -> 高频考点 -> 一道典型题 -> 速记提醒`

## Installation

Python `3.11+` is recommended.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install -e .[dev]
```

Or:

```bash
pip install -r requirements.txt
```

## Runtime Configuration

Supported environment variables:

- `OPENAI_API_KEY`
- `OPENAI_API_BASE`
- `OPENAI_MODEL`
- `MODEL_PROVIDER`
- `LANGSMITH_TRACING`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`
- `TAVILY_API_KEY`

Accepted `MODEL_PROVIDER` values for the current OpenAI-compatible path:

- `openai`
- `openai_compatible`
- `gemini`
- `gemini_openai_compatible`

If you explicitly pass `--env-file`, that file overrides stale shell variables so the requested runtime config wins.

Example:

```bash
study-review-graph run ^
  --env-file E:\PROJECT\AGENT\.env ^
  --input-dir examples/input ^
  --output-dir examples/output/run ^
  --course-name "Intro Mechanics" ^
  --user-goal "Build deep understanding of the concepts, formulas, and worked examples." ^
  --study-mode full_review
```

`.env` must remain local and uncommitted. Use `.env.example` for placeholders only.

## Generated Outputs

Primary grounded outputs:

- `content_map.md`
- `formula_sheet.md`
- `worked_examples.md`
- `worked_solutions.md`
- `review_notes.md`
- `practice_set.md`

Utility outputs:

- `answer_feedback.md`
- `agent_session.md`
- `overview.md`
- `quality_report.md`
- `formulas.md` as a legacy compatibility mirror of `formula_sheet.md`

What they contain:

- `content_map.md`
  grounded concepts, short descriptions, and source references
- `formula_sheet.md`
  extracted formulas, ids, symbols, conditions, concept links, references, and explicit TODOs where interpretation is incomplete
- `worked_examples.md`
  grounded study examples tied to formulas and concepts
- `worked_solutions.md`
  step-by-step solution guidance, rationale, and common mistakes
- `review_notes.md`
  skill-aligned review notes whose structure depends on `study_mode`
- `practice_set.md`
  concept questions, formula-application questions, worked-calculation questions, hints, and answer sketches
- `answer_feedback.md`
  grounded feedback for one practice item
- `agent_session.md`
  detected intent, selected specialist agent, grounded response, references, and recommended next action

## Agent Layer

The repository includes a lightweight study-session layer with:

- `SupervisorAgent`
- `ConceptFormulaAgent`
- `ExampleSolutionAgent`
- `PracticeAgent`
- `AnswerCriticAgent`

This layer does not replace the grounded pipeline. It rebuilds the current grounded state, routes one request, and reuses the existing artifacts and utility paths.

Current routed intent categories:

- `concept_help`
- `formula_help`
- `example_help`
- `practice_request`
- `answer_check`
- `review_guidance`

## Current Limitations

- concept discovery is still heuristic-first
- formula extraction is still heuristic and line-based
- retrieval is deterministic token overlap, not embeddings
- answer checking is practical study feedback, not mathematically complete grading
- the study-session layer is deterministic-first routing, not a fully autonomous tutor
- advanced evaluators are still placeholders
- `deep_dive` auto-selection is still heuristic when no explicit focus is given

## Reproducible Example Commands

Default full review:

```bash
study-review-graph run --input-dir examples/input --output-dir examples/output/run --study-mode full_review
```

Deep dive:

```bash
study-review-graph run --input-dir examples/input --output-dir examples/output/deep_dive_run --study-mode deep_dive --focus-topic "Kinetic Energy"
```

Exam sprint:

```bash
study-review-graph run --input-dir examples/input --output-dir examples/output/exam_sprint_run --study-mode exam_sprint
```

Check one answer:

```bash
study-review-graph check-answer --input-dir examples/input --output-dir examples/output/check_answer_run --practice-id practice-formula-0 --answer "先看题目是不是在讨论净力、质量和加速度的关系，再确认质量可以视为常量，所以应该用 F = m * a。"
```

Run one study session:

```bash
study-review-graph study-session --input-dir examples/input --output-dir examples/output/study_session_run --request "讲一下这道题" --focus-topic "Newton's Second Law"
```

## More Docs

- [Architecture](docs/architecture.md)
- [State Schema](docs/state_schema.md)
- [Release Notes v0.1.1](docs/release_notes_v0.1.1.md)
- [Changelog](CHANGELOG.md)

## Contributing

Please start with [CONTRIBUTING.md](CONTRIBUTING.md). If you are using Codex in this repository, also read [AGENTS.md](AGENTS.md).

## Status

This repository is still early-stage. The current release is meant to be runnable, inspectable, and honest about where heuristic logic remains.
