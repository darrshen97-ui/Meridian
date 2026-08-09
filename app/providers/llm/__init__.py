"""Active LLM provider selection. Local Ollama unless explicitly overridden."""
from __future__ import annotations

from app.core.config import get_settings
from app.providers.llm.anthropic import AnthropicProvider
from app.providers.llm.base import (  # noqa: F401
    LLMError,
    LLMProvider,
    LLMResponse,
    LLMUnavailable,
    endpoint_is_loopback,
)
from app.providers.llm.ollama import OllamaProvider
from app.services.app_settings import read_app_settings

_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        settings = get_settings()
        if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            _provider = AnthropicProvider(settings.anthropic_api_key)
        else:
            overrides = read_app_settings()
            model = overrides.get("ollama_model") or settings.ollama_model
            _provider = OllamaProvider(settings.ollama_base_url, model)
    return _provider


def reset_llm_provider() -> None:
    """Testing / settings-change hook."""
    global _provider
    _provider = None
