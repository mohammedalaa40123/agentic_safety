"""OpenRouter provider — 200+ models behind a single API key."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

from .base import LLMProvider, ModelInfo, _RateLimiter

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(LLMProvider):
    def __init__(self, model_name: str, api_key: str = "", calls_per_minute: int = 0):
        key = api_key or os.getenv("OPENROUTER_API_KEY") or ""
        if not key:
            raise RuntimeError("Set OPENROUTER_API_KEY or pass api_key to OpenRouterProvider")
        self.model_name = model_name
        self.api_key = key
        self.rate_limiter = _RateLimiter(calls_per_minute)

    def chat_single(self, messages, tools=None, max_tokens=1024, temperature=0.7) -> str:
        self.rate_limiter.wait()
        try:
            from openai import OpenAI  # type: ignore[import-not-found]

            client = OpenAI(
                api_key=self.api_key,
                base_url=OPENROUTER_BASE_URL,
                default_headers={
                    "HTTP-Referer": "https://github.com/agentic-safety",
                    "X-Title": "Agentic Safety Evaluator",
                },
            )
            kwargs: Dict[str, Any] = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": int(max_tokens),
                "temperature": float(temperature),
            }
            if tools:
                kwargs["tools"] = tools
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenRouter error: {e}]"

    @classmethod
    def validate_key(cls, api_key: str = "", base_url: str = "") -> bool:
        try:
            req = urlrequest.Request(
                f"{OPENROUTER_BASE_URL}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            with urlrequest.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

    @classmethod
    def list_models(cls, api_key: str = "", base_url: str = "") -> List[ModelInfo]:
        try:
            req = urlrequest.Request(
                f"{OPENROUTER_BASE_URL}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            with urlrequest.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            return [
                ModelInfo(
                    id=m["id"],
                    name=m.get("name", m["id"]),
                    provider="openrouter",
                    context_length=m.get("context_length"),
                    description=m.get("description", ""),
                )
                for m in (data.get("data") or [])
            ]
        except Exception:
            return []
