from pathlib import Path

import pytest

from study_review_graph.model_client import reset_model_client_cache, reset_model_response_cache


def pytest_configure(config):
    workspace_tmp = Path.cwd() / ".pytest_runtime_tmp"
    workspace_tmp.mkdir(exist_ok=True)
    config.option.basetemp = str(workspace_tmp)


@pytest.fixture(autouse=True)
def isolate_runtime_env(monkeypatch):
    for name in (
        "MODEL_PROVIDER",
        "OPENAI_API_KEY",
        "OPENAI_API_BASE",
        "OPENAI_MODEL",
        "LANGSMITH_TRACING",
        "LANGSMITH_API_KEY",
        "LANGSMITH_PROJECT",
        "TAVILY_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    reset_model_client_cache()
    reset_model_response_cache()
    yield
    reset_model_client_cache()
    reset_model_response_cache()
