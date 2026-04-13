"""Minimal OpenAI-compatible model client for targeted workflow enhancements."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any


SUPPORTED_PROVIDERS = {"", "openai_compatible", "gemini", "gemini_openai_compatible"}


@dataclass(frozen=True)
class ModelRuntimeConfig:
    """Runtime configuration loaded from environment variables."""

    provider: str
    api_key: str | None
    api_base: str | None
    model_name: str | None
    langsmith_tracing: str | None
    langsmith_api_key: str | None
    langsmith_project: str | None
    tavily_api_key: str | None

    @property
    def is_disabled(self) -> bool:
        return not self.api_key and not self.api_base and not self.model_name

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_base and self.model_name)

    def configuration_warning(self) -> str | None:
        """Return a safe warning when configuration is partially invalid."""

        if self.is_disabled:
            return None

        missing = [
            name
            for name, value in (
                ("OPENAI_API_KEY", self.api_key),
                ("OPENAI_API_BASE", self.api_base),
                ("OPENAI_MODEL", self.model_name),
            )
            if not value
        ]
        if missing:
            return (
                "Model-backed enhancements are disabled because configuration is incomplete. "
                f"Missing: {', '.join(missing)}."
            )

        if self.provider not in SUPPORTED_PROVIDERS:
            return (
                "Model-backed enhancements are disabled because MODEL_PROVIDER is unsupported. "
                "Use an OpenAI-compatible provider setting."
            )

        return None


@dataclass
class ModelCallResult:
    """Result wrapper for model JSON generation."""

    payload: dict[str, Any] | None
    warning: str | None = None


class StudyModelClient:
    """Thin wrapper around an OpenAI-compatible chat-completions endpoint."""

    def __init__(self, runtime_config: ModelRuntimeConfig):
        self.runtime_config = runtime_config
        self._client: Any | None = None
        self._client_error: str | None = None

    def is_available(self) -> bool:
        """Return whether model-backed enhancement can be attempted."""

        if self.runtime_config.is_disabled:
            return False
        return self.runtime_config.configuration_warning() is None and self._get_client() is not None

    def availability_warning(self) -> str | None:
        """Return a safe warning if model-backed enhancement is not available."""

        if self.runtime_config.is_disabled:
            return None

        config_warning = self.runtime_config.configuration_warning()
        if config_warning:
            return config_warning

        if self._get_client() is None:
            return self._client_error or (
                "Model-backed enhancements are unavailable because the OpenAI client could not be initialized."
            )
        return None

    def generate_json(
        self,
        *,
        task_name: str,
        system_prompt: str,
        user_prompt: str,
    ) -> ModelCallResult:
        """Call the configured model and parse a JSON object response safely."""

        client = self._get_client()
        availability_warning = self.availability_warning()
        if client is None or availability_warning:
            return ModelCallResult(payload=None, warning=availability_warning)

        try:
            response = client.chat.completions.create(
                model=self.runtime_config.model_name,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            message = response.choices[0].message.content if response.choices else ""
            parsed = _parse_json_payload(message or "")
            if parsed is None:
                return ModelCallResult(
                    payload=None,
                    warning=(
                        f"Model-backed enhancement for {task_name} returned non-JSON content. "
                        "Falling back to heuristic behavior."
                    ),
                )
            return ModelCallResult(payload=parsed)
        except Exception as exc:  # pragma: no cover - exercised through mocks and error handling
            return ModelCallResult(
                payload=None,
                warning=(
                    f"Model-backed enhancement for {task_name} failed with {exc.__class__.__name__}. "
                    "Falling back to heuristic behavior."
                ),
            )

    def _get_client(self) -> Any | None:
        if self._client is not None:
            return self._client
        if self._client_error is not None:
            return None

        try:
            from openai import OpenAI
        except ModuleNotFoundError:
            self._client_error = (
                "Model-backed enhancements are unavailable because the 'openai' package is not installed."
            )
            return None

        try:
            self._client = OpenAI(
                api_key=self.runtime_config.api_key,
                base_url=self.runtime_config.api_base,
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._client_error = (
                f"Model-backed enhancements are unavailable because the OpenAI client failed to initialize "
                f"with {exc.__class__.__name__}."
            )
            return None
        return self._client


@lru_cache(maxsize=1)
def get_model_client() -> StudyModelClient:
    """Return a cached model client built from the current environment."""

    return StudyModelClient(load_model_runtime_config())


def reset_model_client_cache() -> None:
    """Clear the cached model client, primarily for tests."""

    get_model_client.cache_clear()


def load_model_runtime_config() -> ModelRuntimeConfig:
    """Load the supported runtime environment variables."""

    return ModelRuntimeConfig(
        provider=os.getenv("MODEL_PROVIDER", "").strip(),
        api_key=os.getenv("OPENAI_API_KEY"),
        api_base=os.getenv("OPENAI_API_BASE"),
        model_name=os.getenv("OPENAI_MODEL"),
        langsmith_tracing=os.getenv("LANGSMITH_TRACING"),
        langsmith_api_key=os.getenv("LANGSMITH_API_KEY"),
        langsmith_project=os.getenv("LANGSMITH_PROJECT"),
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
    )


def _parse_json_payload(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if not cleaned:
        return None

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fenced_match:
        cleaned = fenced_match.group(1)

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    object_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not object_match:
        return None

    try:
        parsed = json.loads(object_match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


@lru_cache(maxsize=128)
def get_cached_formula_enrichment(
    *,
    formula_id: str,
    expression: str,
    symbols_csv: str,
    concept_names_csv: str,
    chunk_context: str,
) -> ModelCallResult:
    """Cache repeated formula-enrichment requests across subgraph nodes."""

    return get_model_client().generate_json(
        task_name=f"formula '{formula_id}'",
        system_prompt=(
            "You are improving a grounded formula study sheet. "
            "Use only the provided local excerpts. "
            "Do not claim certainty beyond the evidence. "
            "Return JSON with keys: symbol_explanations, conditions, linked_concepts, note."
        ),
        user_prompt=(
            f"Formula ID: {formula_id}\n"
            f"Formula expression: {expression}\n"
            f"Known symbols: {symbols_csv or 'None'}\n"
            f"Available concept names: {concept_names_csv or 'None'}\n\n"
            "Retrieved local context:\n"
            f"{chunk_context}\n\n"
            "Requirements:\n"
            "- explain symbols only when the local evidence supports it\n"
            "- list conditions or assumptions supported by the local context\n"
            "- choose linked concepts only from the provided concept names\n"
            "- include TODO markers in note or conditions when evidence is incomplete\n"
        ),
    )


def reset_model_response_cache() -> None:
    """Clear cached model responses, primarily for tests."""

    get_cached_formula_enrichment.cache_clear()
