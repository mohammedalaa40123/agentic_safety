"""Anthropic (Claude) provider."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from .base import LLMProvider, ModelInfo, _RateLimiter

logger = logging.getLogger(__name__)

# Hardcoded since Anthropic has no public list-models endpoint
ANTHROPIC_MODELS = [
    ModelInfo(id="claude-opus-4-5", name="Claude Opus 4.5", provider="anthropic", context_length=200000),
    ModelInfo(id="claude-sonnet-4-5", name="Claude Sonnet 4.5", provider="anthropic", context_length=200000),
    ModelInfo(id="claude-haiku-3-5", name="Claude Haiku 3.5", provider="anthropic", context_length=200000),
    ModelInfo(id="claude-opus-4", name="Claude Opus 4", provider="anthropic", context_length=200000),
    ModelInfo(id="claude-sonnet-4", name="Claude Sonnet 4", provider="anthropic", context_length=200000),
    ModelInfo(id="claude-3-5-haiku-latest", name="Claude 3.5 Haiku (latest)", provider="anthropic", context_length=200000),
    ModelInfo(id="claude-3-5-sonnet-latest", name="Claude 3.5 Sonnet (latest)", provider="anthropic", context_length=200000),
]


class AnthropicProvider(LLMProvider):
    def __init__(self, model_name: str, api_key: str = "", calls_per_minute: int = 0):
        import anthropic  # type: ignore[import-not-found]

        key = api_key or os.getenv("ANTHROPIC_API_KEY") or ""
        if not key:
            raise RuntimeError("Set ANTHROPIC_API_KEY or pass api_key to AnthropicProvider")
        self.model_name = model_name
        self._client = anthropic.Anthropic(api_key=key)
        self.rate_limiter = _RateLimiter(calls_per_minute)

    def chat_single(self, messages, tools=None, max_tokens=1024, temperature=0.7) -> str:
        self.rate_limiter.wait()
        try:
            # Anthropic separates system messages from the conversation
            system = ""
            conv: List[Dict] = []
            for msg in messages:
                if msg.get("role") == "system":
                    system = msg.get("content", "")
                else:
                    conv.append(msg)

            kwargs: Dict[str, Any] = {
                "model": self.model_name,
                "max_tokens": int(max_tokens),
                "messages": conv,
                "temperature": float(temperature),
            }
            if system:
                kwargs["system"] = system
            if tools:
                kwargs["tools"] = tools

            resp = self._client.messages.create(**kwargs)
            parts: List[str] = []
            for block in resp.content:
                if hasattr(block, "text"):
                    parts.append(block.text)
                elif getattr(block, "type", None) == "tool_use":
                    payload = {"name": block.name, "arguments": block.input}
                    parts.append(f"<tool_call>{json.dumps(payload)}</tool_call>")
            return "\n".join(parts)
        except Exception as e:
            return f"[Anthropic error: {e}]"

    @classmethod
    def validate_key(cls, api_key: str = "", base_url: str = "") -> bool:
        try:
            import anthropic  # type: ignore[import-not-found]

            client = anthropic.Anthropic(api_key=api_key)
            # Cheapest validation: send 1-token request
            client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception:
            return False

    @classmethod
    def list_models(cls, api_key: str = "", base_url: str = "") -> List[ModelInfo]:
        return list(ANTHROPIC_MODELS)
