"""Provider registry — maps provider names to classes and exposes helper functions."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Type

from .base import LLMProvider, ModelInfo
from .genai_studio import GenAIStudioProvider
from .gemini import GeminiProvider
from .openai_provider import OpenAIProvider
from .openrouter import OpenRouterProvider
from .anthropic_provider import AnthropicProvider
from .ollama import OllamaProvider

RCAC_BASE_URL = "https://genai.rcac.purdue.edu/api"

PROVIDER_CLASSES: Dict[str, Type[LLMProvider]] = {
    "genai": GenAIStudioProvider,
    "genaistudio": GenAIStudioProvider,
    "genai_rcac": GenAIStudioProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "openrouter": OpenRouterProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "ollama_cloud": OllamaProvider,
}


def _resolve_base_url(provider_name: str, base_url: str = "") -> str:
    if base_url:
        return base_url
    if provider_name == "genai_rcac":
        return RCAC_BASE_URL
    if provider_name == "ollama_cloud":
        return OllamaProvider.CLOUD_BASE_URL
    return ""


def get_provider(
    provider_name: str,
    model_id: str,
    api_key: str = "",
    base_url: str = "",
    calls_per_minute: int = 0,
) -> LLMProvider:
    """Instantiate a provider with explicit credentials.

    Args:
        provider_name: Key in PROVIDER_CLASSES (e.g. ``"genai_rcac"``, ``"ollama"``).
        model_id: Model identifier without the provider prefix.
        api_key: Explicit API key (falls back to env vars inside the provider).
        base_url: Override base URL (required for custom GenAI Studio / Ollama).
        calls_per_minute: Rate limit; 0 = unlimited.
    """
    name = provider_name.lower()
    cls = PROVIDER_CLASSES.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown provider '{provider_name}'. Available: {sorted(PROVIDER_CLASSES)}"
        )

    resolved_url = _resolve_base_url(name, base_url)

    if name in {"genai", "genaistudio", "genai_rcac"}:
        return cls(model_id, api_key=api_key, base_url=resolved_url, calls_per_minute=calls_per_minute)
    if name == "gemini":
        return cls(model_id, api_key=api_key, calls_per_minute=calls_per_minute)
    if name == "openai":
        return cls(model_id, api_key=api_key, calls_per_minute=calls_per_minute)
    if name == "openrouter":
        return cls(model_id, api_key=api_key, calls_per_minute=calls_per_minute)
    if name == "anthropic":
        return cls(model_id, api_key=api_key, calls_per_minute=calls_per_minute)
    if name in {"ollama", "ollama_cloud"}:
        return cls(model_id, base_url=resolved_url, api_key=api_key, calls_per_minute=calls_per_minute)

    raise ValueError(f"Unhandled provider routing for '{provider_name}'")


def validate_provider_key(provider_name: str, api_key: str = "", base_url: str = "") -> bool:
    """Return True if the credentials are valid for *provider_name*."""
    cls = PROVIDER_CLASSES.get(provider_name.lower())
    if cls is None:
        return False
    return cls.validate_key(api_key=api_key, base_url=_resolve_base_url(provider_name, base_url))


def list_provider_models(provider_name: str, api_key: str = "", base_url: str = "") -> List[ModelInfo]:
    """Return available models for *provider_name*."""
    cls = PROVIDER_CLASSES.get(provider_name.lower())
    if cls is None:
        return []
    return cls.list_models(api_key=api_key, base_url=_resolve_base_url(provider_name, base_url))


def get_provider_info() -> List[Dict[str, Any]]:
    """Metadata about each supported provider, consumed by the frontend /setup page."""
    return [
        {
            "id": "genai_rcac",
            "name": "GenAI Studio (Purdue RCAC)",
            "needs_key": True,
            "needs_base_url": False,
            "default_base_url": RCAC_BASE_URL,
            "key_env": "RCAC_GENAI_API_KEY",
            "description": "Purdue RCAC-hosted LLMs via GenAI Studio API",
        },
        {
            "id": "genai",
            "name": "GenAI Studio (Custom)",
            "needs_key": True,
            "needs_base_url": True,
            "default_base_url": "",
            "key_env": "GENAI_STUDIO_API_KEY",
            "description": "Self-hosted or other institution GenAI Studio deployment",
        },
        {
            "id": "openai",
            "name": "OpenAI",
            "needs_key": True,
            "needs_base_url": False,
            "default_base_url": "",
            "key_env": "OPENAI_API_KEY",
            "description": "GPT-4o, o3, and other OpenAI models",
        },
        {
            "id": "openrouter",
            "name": "OpenRouter",
            "needs_key": True,
            "needs_base_url": False,
            "default_base_url": "",
            "key_env": "OPENROUTER_API_KEY",
            "description": "200+ models via a single API key (Llama, Claude, Gemini, …)",
        },
        {
            "id": "gemini",
            "name": "Google Gemini",
            "needs_key": True,
            "needs_base_url": False,
            "default_base_url": "",
            "key_env": "GEMINI_API_KEY",
            "description": "Gemini 2.5 Flash/Pro and earlier models",
        },
        {
            "id": "anthropic",
            "name": "Anthropic",
            "needs_key": True,
            "needs_base_url": False,
            "default_base_url": "",
            "key_env": "ANTHROPIC_API_KEY",
            "description": "Claude Opus, Sonnet, and Haiku models",
        },
        {
            "id": "ollama",
            "name": "Ollama (Local)",
            "needs_key": False,
            "needs_base_url": True,
            "default_base_url": "http://localhost:11434",
            "key_env": "OLLAMA_API_KEY",
            "description": "Locally running Ollama server — any pulled model",
        },
        {
            "id": "ollama_cloud",
            "name": "Ollama Cloud (ollama.com)",
            "needs_key": True,
            "needs_base_url": False,
            "default_base_url": "https://api.ollama.com",
            "key_env": "OLLAMA_CLOUD_API_KEY",
            "description": "Ollama.com hosted models — requires an ollama.com API key",
        },
    ]
