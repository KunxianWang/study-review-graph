# Example Output

Generated markdown artifacts can be written to this directory during local runs.

This repository does not depend on committed runtime outputs for the `v0.1.1` release. Instead, use the commands below to reproduce the current outputs locally.

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

Recommended commands:

```bash
study-review-graph run --input-dir examples/input --output-dir examples/output/run --study-mode full_review
```

```bash
study-review-graph check-answer --input-dir examples/input --output-dir examples/output/check_answer_run --practice-id practice-formula-0 --answer "先看题目是不是在讨论净力、质量和加速度的关系，再确认质量可以视为常量，所以应该用 F = m * a。"
```

```bash
study-review-graph study-session --input-dir examples/input --output-dir examples/output/study_session_run --request "请重点讲一下牛顿第二定律这个公式什么时候用" --study-mode deep_dive --focus-topic "Newton's Second Law"
```
