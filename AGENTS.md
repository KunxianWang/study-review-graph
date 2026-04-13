# AGENTS.md

This repository builds a deterministic study and review pipeline for course materials. It is not a generic chatbot, free-form tutor, or multi-agent chat sandbox.

## Scope

- Focus on CLI-first workflow code, structured artifacts, tests, and docs.
- Do not add a frontend unless explicitly requested.
- Do not introduce advanced evaluator logic unless explicitly requested.
- Keep v0.1 implementation honest: placeholders are acceptable, fake completeness is not.

## Core Priorities

- Prioritize groundedness, correctness, and pedagogical clarity.
- Preserve source traceability whenever possible.
- Prefer deterministic workflow logic over agentic improvisation.
- Keep module boundaries strict and responsibilities narrow.
- Keep changes scoped and local; avoid opportunistic refactors.
- Use structured intermediate objects instead of giant text blobs.
- Update tests and docs when changing workflow structure or architecture.

## Architecture Guardrails

- The orchestration layer should stay in LangGraph with shared state.
- RAG should support multiple stages, not only the final output stage.
- Only introduce a subgraph when it clearly improves modularity.
- Avoid collapsing formula logic, worked-solution logic, and review-note logic into one node.
- Preserve the current package split unless there is a clear maintenance reason to change it.

## Editing Rules

- Favor simple, inspectable defaults in v0.1.
- Mark deferred implementation details with TODO comments.
- Keep exports and reports explicit rather than hidden in side effects.
- Preserve backwards-compatible CLI behavior unless a change is necessary.
- Prefer small deterministic helpers over implicit framework magic.
- When changing state shape, update `docs/state_schema.md`, tests, and any exporters that depend on it.
- When changing workflow nodes, update `README.md` and `docs/architecture.md` if behavior changes.
