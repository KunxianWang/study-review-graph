import os
import shutil
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

from study_review_graph import cli
from study_review_graph.cli import _load_runtime_environment, app
from study_review_graph.state import RuntimeConfig, StudyGraphState


def test_explicit_env_file_overrides_stale_shell_variables(monkeypatch):
    temp_root = Path.cwd() / ".runtime_test_dirs"
    temp_root.mkdir(exist_ok=True)
    temp_dir = temp_root / f"cli-env-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    env_file = temp_dir / ".env"
    try:
        env_file.write_text(
            "MODEL_PROVIDER=openai\n"
            "OPENAI_API_BASE=https://example.test/v1\n"
            "OPENAI_MODEL=test-model\n",
            encoding="utf-8",
        )

        monkeypatch.setenv("MODEL_PROVIDER", "stale-provider")
        monkeypatch.setenv("OPENAI_API_BASE", "https://stale.example/v1")
        monkeypatch.setenv("OPENAI_MODEL", "stale-model")

        _load_runtime_environment(env_file)

        assert os.environ["MODEL_PROVIDER"] == "openai"
        assert os.environ["OPENAI_API_BASE"] == "https://example.test/v1"
        assert os.environ["OPENAI_MODEL"] == "test-model"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_run_command_does_not_require_session_result(monkeypatch):
    runner = CliRunner()
    captured = {}
    temp_root = Path.cwd() / ".runtime_test_dirs"
    temp_root.mkdir(exist_ok=True)
    temp_dir = temp_root / f"cli-run-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    def fake_invoke_study_graph(state: StudyGraphState) -> StudyGraphState:
        captured["output_dir"] = state.config.output_dir
        return StudyGraphState(
            config=state.config,
            output_paths={"overview": str(Path(state.config.output_dir) / "overview.md")},
            warnings=["fallback path still usable"],
        )

    monkeypatch.setattr(cli, "invoke_study_graph", fake_invoke_study_graph)
    try:
        output_dir = temp_dir / "run-output"
        result = runner.invoke(
            app,
            [
                "run",
                "--input-dir",
                "examples/input",
                "--output-dir",
                str(output_dir),
            ],
        )

        assert result.exit_code == 0
        assert "overview" in result.stdout
        assert "fallback path still usable" in result.stdout
        assert captured["output_dir"] == str(output_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_study_session_command_still_routes_successfully(monkeypatch):
    runner = CliRunner()
    temp_root = Path.cwd() / ".runtime_test_dirs"
    temp_root.mkdir(exist_ok=True)
    temp_dir = temp_root / f"cli-session-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    def fake_invoke_study_graph(state: StudyGraphState) -> StudyGraphState:
        return StudyGraphState(
            config=RuntimeConfig(**state.config.model_dump()),
            output_paths={"overview": str(Path(state.config.output_dir) / "overview.md")},
        )

    def fake_run_study_session(state: StudyGraphState, request: str, focus_topic: str | None, practice_id, user_answer):
        from study_review_graph.agents.session import AgentSessionResult, RoutedRequest

        return (
            AgentSessionResult(
                detected_intent="concept_help",
                selected_agent="ConceptFormulaAgent",
                response_title="概念讲解",
                response_lines=["这是一个 grounded session 响应。"],
                recommended_next_action="继续看相关公式。",
            ),
            RoutedRequest(
                intent="concept_help",
                selected_agent="ConceptFormulaAgent",
                rationale=f"request={request}",
            ),
        )

    monkeypatch.setattr(cli, "invoke_study_graph", fake_invoke_study_graph)
    monkeypatch.setattr(cli, "run_study_session", fake_run_study_session)
    try:
        output_dir = temp_dir / "session-output"
        result = runner.invoke(
            app,
            [
                "study-session",
                "--input-dir",
                "examples/input",
                "--output-dir",
                str(output_dir),
                "--request",
                "请解释这个概念",
            ],
        )

        assert result.exit_code == 0
        assert "detected_intent: concept_help" in result.stdout
        assert "selected_agent: ConceptFormulaAgent" in result.stdout
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
