# =============================================================================
#  Filename: model_registry.py
#
#  Short Description: Thread-safe singleton registry that initializes LLM clients
#                     from project configuration.
#
#  Creation date: 2025-09-04
#  Author: Asif Qamar
# =============================================================================

from __future__ import annotations

import os
import threading
from typing import Any

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, validate_call
from langchain_openai import ChatOpenAI

from metamorphosis.exceptions import (
    ConfigurationError,
    raise_configuration_error,
)


class _LLMSettings(BaseModel):
    """Validated settings for a single LLM client."""

    model_config = ConfigDict(extra="forbid")

    model: str = Field(..., min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: PositiveInt | None = None
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    stop_sequences: list[str] | None = None
    timeout: PositiveInt | None = None


class ModelRegistry:
    """Singleton that provides configured LLM clients.

    The registry reads the project's configuration and constructs two
    `ChatOpenAI` clients: `summarizer_llm` and `copy_editor_llm`.
    """

    _instance: "ModelRegistry | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "ModelRegistry":  # type: ignore[override]
        if cls._instance is not None:
            return cls._instance
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialization when called multiple times
        if hasattr(self, "_initialized") and self._initialized:
            return

        logger.debug("Initializing ModelRegistry from configuration")

        # Fail-fast on API key
        if not os.getenv("OPENAI_API_KEY"):
            raise_configuration_error(
                "OPENAI_API_KEY environment variable is required",
                context={"env_vars_checked": ["OPENAI_API_KEY"]},
                operation="llm_api_key_validation",
            )

        cfg = self._load_text_modifier_section()

        summarizer_cfg = _LLMSettings(**cfg.get("summarizer", {}))
        copy_editor_cfg = _LLMSettings(**cfg.get("copy_editor", {}))

        self.summarizer_llm = self._build_chat_openai(summarizer_cfg)
        self.copy_editor_llm = self._build_chat_openai(copy_editor_cfg)

        self._initialized = True
        logger.debug("ModelRegistry initialized successfully")

    @staticmethod
    def _load_text_modifier_section() -> dict[str, Any]:
        """Return the `text_modifier_models` section from project config.

        Raises:
            ConfigurationError: If the section is missing or invalid.
        """
        # Import here to avoid import cycles
        from metamorphosis import config as project_config  # noqa: WPS433 (local import)

        try:
            section = project_config["text_modifier_models"]
        except KeyError as error:
            raise_configuration_error(
                "Missing 'text_modifier_models' in configuration",
                context={"config_keys": list(project_config.keys())},
                operation="config_section_resolution",
                original_error=error,
            )

        if not isinstance(section, dict) or not section:
            raise_configuration_error(
                "Invalid 'text_modifier_models' configuration section",
                context={"type": type(section).__name__},
                operation="config_section_validation",
            )
        return section

    @staticmethod
    @validate_call
    def _build_chat_openai(settings: _LLMSettings) -> ChatOpenAI:
        """Construct a `ChatOpenAI` client from validated settings."""
        params: dict[str, Any] = {"model": settings.model}

        if settings.temperature is not None:
            params["temperature"] = settings.temperature
        if settings.max_tokens is not None:
            params["max_tokens"] = settings.max_tokens
        if settings.top_p is not None:
            params["top_p"] = settings.top_p
        if settings.frequency_penalty is not None:
            params["frequency_penalty"] = settings.frequency_penalty
        if settings.presence_penalty is not None:
            params["presence_penalty"] = settings.presence_penalty
        if settings.stop_sequences is not None:
            params["stop"] = settings.stop_sequences
        if settings.timeout is not None:
            params["timeout"] = settings.timeout

        logger.debug("Creating ChatOpenAI with params: {}", params)
        return ChatOpenAI(**params)


__all__ = ["ModelRegistry"]


