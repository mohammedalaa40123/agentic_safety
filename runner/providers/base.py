"""Shared base classes and utilities for all LLM providers."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    context_length: Optional[int] = None
    description: str = ""


class _RateLimiter:
    def __init__(self, calls_per_minute: int = 0):
        self.calls_per_minute = max(0, int(calls_per_minute or 0))
        self.min_interval = (60.0 / self.calls_per_minute) if self.calls_per_minute > 0 else 0.0
        self._last_call_time = 0.0

    def wait(self) -> None:
        if self.min_interval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call_time = time.monotonic()


class LLMProvider(ABC):
    """Abstract base for all LLM providers.

    Subclasses **must** implement ``chat_single()``.

    The legacy batch interfaces ``get_response()``, ``chat()``, and
    ``batched_generate()`` are provided as default implementations that call
    ``chat_single()`` so existing runner code works without changes.

    Class-level ``list_models()`` and ``validate_key()`` take explicit
    credentials so they can be called from the API server without creating
    a full instance (no side-effects, no env-var dependencies).
    """

    @abstractmethod
    def chat_single(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Return a single text response for *messages*."""
        ...

    @classmethod
    def validate_key(cls, api_key: str = "", base_url: str = "") -> bool:
        """Return True if the credentials appear valid. Override in subclasses."""
        return True

    @classmethod
    def list_models(cls, api_key: str = "", base_url: str = "") -> List[ModelInfo]:
        """Return models available for this provider. Override in subclasses."""
        return []

    # ── Legacy batch interface ─────────────────────────────────────────────────

    def get_response(self, prompts: List[str]) -> List[str]:
        return [self.chat_single([{"role": "user", "content": p}]) for p in prompts]

    def chat(
        self,
        messages_list: List[List[Dict[str, Any]]],
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> List[str]:
        return [
            self.chat_single(msgs, tools=tools, max_tokens=max_tokens, temperature=temperature)
            for msgs in messages_list
        ]

    def batched_generate(
        self,
        prompts: List[str],
        max_n_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> List[str]:
        return [
            self.chat_single(
                [{"role": "user", "content": p}],
                max_tokens=max_n_tokens,
                temperature=temperature,
            )
            for p in prompts
        ]
