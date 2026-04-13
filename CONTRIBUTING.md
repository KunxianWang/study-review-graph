# Contributing

Thanks for contributing to `study-review-graph`.

## Development Principles

- Keep v0.1 simple, deterministic, and easy to debug.
- Preserve groundedness and source traceability.
- Prefer focused pull requests over broad rewrites.
- Document architecture-impacting changes in `docs/`.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install -e .[dev]
pytest
```

## Pull Request Expectations

- Add or update tests for behavior changes.
- Update docs when workflow structure changes.
- Keep TODO markers explicit when implementation is intentionally deferred.
- Avoid introducing unrelated refactors in the same PR.

## Reporting Issues

Please use the GitHub issue templates for bugs and feature requests. Include:

- what you tried
- the expected behavior
- the actual behavior
- relevant sample materials when possible

## Code Style

- Prefer clear names and small modules.
- Use type hints and docstrings.
- Keep generated artifacts structured.

## Questions

If a design choice affects grounding, retrieval, or source traceability, call it out clearly in the PR description.
