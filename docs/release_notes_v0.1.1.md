# Release Notes: v0.1.1

## What This Release Supports

`v0.1.1` is the first release where the repository functions as a small but complete grounded study loop rather than only a runnable skeleton.

It now supports:

- grounded artifact generation from local course materials
- targeted LLM enhancement through an OpenAI-compatible endpoint
- Chinese-first review-note generation aligned with the local study-material skill
- three review-note modes:
  - `full_review`
  - `deep_dive`
  - `exam_sprint`
- grounded practice generation through `practice_set.md`
- single-item answer checking through `answer_feedback.md`
- lightweight study-session orchestration through `agent_session.md`

The deterministic LangGraph pipeline remains the foundation. The agent layer is only a thin routing layer over those grounded artifacts.

## Known Limitations

- concept extraction is still heuristic-first
- formula extraction is still heuristic and line-based
- retrieval is deterministic token overlap, not embeddings
- answer checking is study-oriented feedback, not mathematically complete grading
- the study-session layer is deterministic-first routing, not a fully autonomous tutor
- advanced evaluators remain placeholders

## Example Commands

Generate the main grounded artifact bundle:

```bash
study-review-graph run --input-dir examples/input --output-dir examples/output/run --study-mode full_review
```

Check one practice answer:

```bash
study-review-graph check-answer --input-dir examples/input --output-dir examples/output/check_answer_run --practice-id practice-formula-0 --answer "先看题目是不是在讨论净力、质量和加速度的关系，再确认质量可以视为常量，所以应该用 F = m * a。"
```

Run one lightweight study session:

```bash
study-review-graph study-session --input-dir examples/input --output-dir examples/output/study_session_run --request "请重点讲一下牛顿第二定律这个公式什么时候用" --study-mode deep_dive --focus-topic "Newton's Second Law"
```

## Recommended Next Roadmap Items

- improve retrieval quality without changing the current module boundaries
- strengthen concept and formula grounding further before adding broader agent behavior
- add better quality evaluators for groundedness and completeness
- improve release examples and reproducible sample outputs
- keep the session layer small while making routing and references more robust
