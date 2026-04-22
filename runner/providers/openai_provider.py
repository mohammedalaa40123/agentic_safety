"""OpenAI provider (GPT-4o, o3, etc.)."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from .base import LLMProvider, ModelInfo, _RateLimiter

logger = logging.getLogger(__name__)

# Models to surface in the UI (filter out fine-tuning noise)
_INTERESTING_PREFIXES = ("gpt-", "o1", "o3", "o4", "text-", "dall-")


class OpenAIProvider(LLMProvider):
    def __init__(self, model_name: str, api_key: str = "", calls_per_minute: int = 0):
        from openai import OpenAI  # type: ignore[import-not-found]

        key = api_key or os.getenv("OPENAI_API_KEY") or ""
        if not key:
            raise RuntimeError("Set OPENAI_API_KEY or pass api_key to OpenAIProvider")
        self.model_name = model_name
        self._client = OpenAI(api_key=key)
        self.rate_limiter = _RateLimiter(calls_per_minute)

    def chat_single(self, messages, tools=None, max_tokens=1024, temperature=0.7) -> str:
        self.rate_limiter.wait()
        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
        }
        if tools:
            kwargs["tools"] = tools
        try:
            resp = self._client.chat.completions.create(**kwargs)
            msg = resp.choices[0].message
            content = msg.content or ""
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                blobs = []
                for call in tool_calls:
                    fn = call.function
                    args = fn.arguments
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            pass
                    blobs.append(
                        f"<tool_call>{json.dumps({'name': fn.name, 'arguments': args})}</tool_call>"
                    )
                return (f"{content}\n" if content else "") + "\n".join(blobs)
            return content
        except Exception as e:
            return f"[OpenAI error: {e}]"

    @classmethod
    def validate_key(cls, api_key: str = "", base_url: str = "") -> bool:
        try:
            from openai import OpenAI  # type: ignore[import-not-found]

            client = OpenAI(api_key=api_key)
            client.models.list()
            return True
        except Exception:
            return False

    @classmethod
    def list_models(cls, api_key: str = "", base_url: str = "") -> List[ModelInfo]:
        try:
            from openai import OpenAI  # type: ignore[import-not-found]

            client = OpenAI(api_key=api_key)
            models = client.models.list()
            return [
                ModelInfo(id=m.id, name=m.id, provider="openai")
                for m in models.data
                if any(m.id.startswith(p) for p in _INTERESTING_PREFIXES)
            ]
        except Exception:
            return []
