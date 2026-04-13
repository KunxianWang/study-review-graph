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
- Purpose: concrete example prompts grounded in formulas or concepts

### `worked_solutions`

- Type: `list[WorkedSolution]`
- Purpose: step plans, detailed steps, rationale, and common mistakes for examples

### `review_notes`

- Type: `ReviewNotes`
- Purpose: concise summary, detailed explanation snippets, formula highlights, and study questions

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
- `enable_external_retrieval`
- `enable_gemini_review`

The last two flags are extension hooks only. They do not enable advanced functionality in v0.1 yet.

## Notes

- The schema is designed to evolve, but changes should remain additive where possible.
- If the state shape changes, update tests, exporters, and docs in the same change.
