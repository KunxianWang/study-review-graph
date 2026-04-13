from study_review_graph.model_client import (
    ModelCallResult,
    get_model_client,
    load_model_runtime_config,
    reset_model_client_cache,
    reset_model_response_cache,
)


def test_model_runtime_config_is_disabled_when_env_is_missing(monkeypatch):
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

    config = load_model_runtime_config()

    assert config.is_disabled
    assert config.configuration_warning() is None


def test_model_client_reports_safe_warning_for_partial_config(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder-key")
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    reset_model_client_cache()
    reset_model_response_cache()

    warning = get_model_client().availability_warning()

    assert warning is not None
    assert "Missing: OPENAI_API_BASE, OPENAI_MODEL" in warning

    reset_model_client_cache()
    reset_model_response_cache()


def test_model_provider_openai_is_accepted_alias(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "placeholder-model")
    reset_model_client_cache()
    reset_model_response_cache()

    config = load_model_runtime_config()

    assert config.provider == "openai"
    assert config.configuration_warning() is None

    reset_model_client_cache()
    reset_model_response_cache()
