# Changelog

All notable changes to this project will be documented in this file.

## v0.1.1 - 2026-04-14

`v0.1.1` is the first release that turns the earlier `v0.1.0` runnable skeleton into a more complete grounded study loop.

### Added

- Grounded showcase artifacts for content/formula understanding:
  - `content_map.md`
  - `formula_sheet.md`
- Grounded example and solution artifacts:
  - `worked_examples.md`
  - `worked_solutions.md`
- Skill-aligned Chinese review-note generation with three study modes:
  - `full_review`
  - `deep_dive`
  - `exam_sprint`
- Grounded `practice_set.md` generation built from current concepts, formulas, examples, solutions, and review notes.
- Single-item answer checking with `check-answer` and `answer_feedback.md`.
- Lightweight `study-session` orchestration with:
  - `SupervisorAgent`
  - `ConceptFormulaAgent`
  - `ExampleSolutionAgent`
  - `PracticeAgent`
  - `AnswerCriticAgent`
- OpenAI-compatible model client support, including Gemini behind an OpenAI-compatible base URL.
- Local study-material skill alignment under `.agents/skills/review-material-generator/`.

### Changed

- Promoted the repository from a pure scaffold into a deterministic-first study workflow with a practical study loop:
  - study artifacts
  - practice generation
  - answer checking
  - lightweight session routing
- Tightened concept filtering, formula linking, and formula-condition locality to improve grounded output quality.
- Clarified CLI usage around:
  - `run`
  - `check-answer`
  - `study-session`
- Kept the LangGraph workflow as the base system while adding a small orchestration layer on top.

### Fixed

- Fixed CLI environment loading so an explicit `--env-file` overrides stale shell variables.
- Accepted `MODEL_PROVIDER=openai` as an alias for the current OpenAI-compatible client path.
- Fixed a `run` command regression where `session_result.warnings` was referenced outside the `study-session` path.
- Improved `study-session` routing so example walkthrough requests beat generic practice routing and missing answer-check inputs return helpful Chinese-first guidance instead of raw crashes.

## v0.1.0

Initial runnable open-source skeleton:

- deterministic LangGraph workflow scaffold
- structured `StudyGraphState`
- CLI-first repository layout
- core nodes, subgraphs, exporters, tests, and open-source project files
