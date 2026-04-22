"""Google Gemini provider."""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from .base import LLMProvider, ModelInfo, _RateLimiter

logger = logging.getLogger(__name__)

GEMINI_FALLBACK_MODELS = [
    # Gemini 3 (current generation)
    ModelInfo(id="gemini-3-flash-preview", name="Gemini 3 Flash (Preview)", provider="gemini"),
    ModelInfo(id="gemini-3.1-flash-lite-preview", name="Gemini 3.1 Flash Lite (Preview)", provider="gemini"),
    ModelInfo(id="gemini-3.1-pro-preview", name="Gemini 3.1 Pro (Preview)", provider="gemini"),
    # Gemini 2.5
    ModelInfo(id="gemini-2.5-flash", name="Gemini 2.5 Flash", provider="gemini"),
    ModelInfo(id="gemini-2.5-pro", name="Gemini 2.5 Pro", provider="gemini"),
    ModelInfo(id="gemini-2.5-flash-lite", name="Gemini 2.5 Flash Lite", provider="gemini"),
    # Gemini 2.0 (deprecated, will be shut down)
    ModelInfo(id="gemini-2.0-flash", name="Gemini 2.0 Flash (Deprecated)", provider="gemini"),
]


def _strip_gemini_prefix(model_name: str) -> str:
    lowered = (model_name or "").lower()
    if lowered.startswith("gemini:"):
        return model_name[len("gemini:"):]
    return model_name


class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str, api_key: str = "", calls_per_minute: int = 0):
        import google.generativeai as genai  # type: ignore[import-not-found]

        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        if not key:
            raise RuntimeError("Set GEMINI_API_KEY or GOOGLE_API_KEY for Gemini access")
        genai.configure(api_key=key)
        self.model = genai.GenerativeModel(_strip_gemini_prefix(model_name))
        self.rate_limiter = _RateLimiter(calls_per_minute)

    def chat_single(self, messages, tools=None, max_tokens=1024, temperature=0.7) -> str:
        # Flatten messages to a single prompt
        prompt = "\n".join(
            f"{m.get('role', 'user').upper()}: {m.get('content', '')}"
            for m in messages
        )
        for attempt in range(3):
            try:
                self.rate_limiter.wait()
                out = self.model.generate_content(prompt)
                return getattr(out, "text", None) or ""
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    backoff = max(15.0, self.rate_limiter.min_interval)
                    logger.warning(f"Gemini rate limited. Sleeping {backoff:.1f}s.")
                    time.sleep(backoff)
                else:
                    return f"[Gemini error: {e}]"
        return ""

    @classmethod
    def validate_key(cls, api_key: str = "", base_url: str = "") -> bool:
        try:
            import google.generativeai as genai  # type: ignore[import-not-found]

            genai.configure(api_key=api_key)
            next(iter(genai.list_models()), None)
            return True
        except Exception:
            return False

    @classmethod
    def list_models(cls, api_key: str = "", base_url: str = "") -> List[ModelInfo]:
        try:
            import google.generativeai as genai  # type: ignore[import-not-found]

            genai.configure(api_key=api_key)
            return [
                ModelInfo(
                    id=m.name.split("/")[-1],
                    name=m.display_name,
                    provider="gemini",
                )
                for m in genai.list_models()
                if "generateContent" in (m.supported_generation_methods or [])
            ]
        except Exception:
            return list(GEMINI_FALLBACK_MODELS)


# Backward-compatible alias
SimpleGeminiTarget = GeminiProvider
