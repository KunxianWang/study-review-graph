# State Schema

This document describes the current `StudyGraphState` used by the LangGraph workflow in v0.1.

## Design Goal

The state model is intentionally structured and explicit. Each major workflow stage reads and writes typed fields instead of passing around large unstructured text blobs.

## Top-Level Fields

### `course_name`

- Type: `str`
- Purpose: human-readable course or material label

### `user_goal`

- Type: `str`
- Purpose: primary study objective for the run

### `raw_docs`

- Type: `list[RawDocument]`
- Purpose: source materials loaded directly from disk before normalization

### `normalized_docs`

- Type: `list[NormalizedDocument]`
- Purpose: cleaned documents used for chunking and downstream extraction

### `chunks`

- Type: `list[ChunkRecord]`
- Purpose: retrieval-ready text chunks with source references

### `retrieval_cache`

- Type: `dict[str, list[str]]`
- Purpose: lightweight lookup cache for retrieval stages

### `concepts`

- Type: `list[ConceptRecord]`
- Purpose: lightweight concept map entries inferred from sections and chunk terms

### `formulas`

- Type: `list[FormulaArtifact]`
- Purpose: extracted formulas with symbol notes, conditions, concept links, and references

### `examples`

- Type: `list[ExampleArtifact]`
- Purpose: concrete worked examples grounded in formulas or concepts

### `worked_solutions`

- Type: `list[WorkedSolution]`
- Purpose: step plans, detailed steps, rationale, and common mistakes for examples

### `practice_items`

- Type: `list[PracticeItem]`
- Purpose: grounded practice questions, hints, and reference answers built from current concepts, formulas, and worked examples

### `review_notes`

- Type: `ReviewNotes`
- Purpose: mode-aware review-note content assembled from grounded concepts, formulas, examples, and worked solutions

### `output_paths`

- Type: `dict[str, str]`
- Purpose: exported markdown artifact locations

### `quality_report`

- Type: `QualityReport`
- Purpose: placeholder evaluator results and recommended follow-up actions

### `warnings`

- Type: `list[str]`
- Purpose: non-fatal pipeline issues

### `errors`

- Type: `list[str]`
- Purpose: fatal or important execution issues

### `config`

- Type: `RuntimeConfig`
- Purpose: runtime options such as directories, chunking, and future feature flags

## Nested Models

### `SourceReference`

Preserves source traceability through:

- `document_id`
- `source_path`
- `chunk_id`
- `page_number`
- `excerpt`

### `RuntimeConfig`

Current v0.1 config fields:

- `input_dir`
- `output_dir`
- `chunk_size`
- `chunk_overlap`
- `top_k`
- `study_mode`
- `focus_topic`
- `include_practice_set`
- `enable_external_retrieval`
- `enable_gemini_review`

The last two flags are extension hooks only. They do not enable advanced functionality in v0.1 yet.
`study_mode` currently accepts `full_review`, `deep_dive`, and `exam_sprint`. `focus_topic` is an optional deep-dive hint.
`include_practice_set` controls whether `practice_set.md` is populated during a run. It defaults to `True`.

### `ExampleArtifact`

Current v0.1 example fields include:

- `example_id`
- `title`
- `problem_statement`
- `formula_ids`
- `difficulty`
- `study_value`
- `known_values`
- `target_symbol`
- `prompt` (legacy compatibility mirror of `problem_statement`)
- `formula_id` (legacy compatibility field for a single primary formula)
- `reasoning_context`
- `references`

This model is intentionally explicit so the solution subgraph can stay grounded in the same formula-centered example rather than regenerating an unrelated prompt later.

### `WorkedSolution`

Current v0.1 solution fields include:

- `solution_id`
- `example_id`
- `plan_steps`
- `detailed_steps`
- `rationale`
- `common_mistakes`
- `references`

The model is designed for study guidance, not just final-answer storage.

### `ReviewNotes`

Current v0.1 review-note fields include:

- `mode`
- `focus_target`
- `focus_selection_note`
- `concise_summary`
- `detailed_explanations`
- `formula_highlights`
- `example_highlights`
- `common_mistakes`
- `study_questions`
- `references`

This model stays lightweight on purpose. The same object can back:

- full review-pack notes
- one-topic deep dives
- exam-sprint summaries

without changing the surrounding graph shape.

### `PracticeItem`

Current v0.1 practice-item fields include:

- `practice_id`
- `question_type`
- `concept_ids`
- `formula_ids`
- `prompt`
- `hint`
- `expected_answer`
- `references`

This model is intentionally compact. It supports the new practice workflow slice without introducing a separate tutor or planner subsystem.

### `AnswerFeedback`

Current v0.1 answer-feedback fields include:

- `practice_id`
- `question_type`
- `result_label`
- `question_prompt`
- `user_answer`
- `concept_ids`
- `formula_ids`
- `linked_examples`
- `linked_solutions`
- `key_issues`
- `correct_approach`
- `review_guidance`
- `references`

This model is used by the `check-answer` utility path. It is not currently stored back into `StudyGraphState`; instead, it is generated on demand from the current grounded artifacts.

## Notes

- The schema is designed to evolve, but changes should remain additive where possible.
- If the state shape changes, update tests, exporters, and docs in the same change.
