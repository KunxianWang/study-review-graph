import os
import shutil
import tempfile
from pathlib import Path

from study_review_graph.cli import _load_runtime_environment


def test_explicit_env_file_overrides_stale_shell_variables(monkeypatch):
    temp_root = Path.cwd() / ".test_tmp"
    temp_root.mkdir(exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="cli-env-", dir=temp_root))
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
