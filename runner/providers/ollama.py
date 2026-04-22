"""Ollama provider — native /api/chat and OpenAI-compatible /v1/chat/completions."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

from .base import LLMProvider, ModelInfo, _RateLimiter

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    DEFAULT_BASE_URL = "http://localhost:11434"
    # Docs: https://docs.ollama.com/api/introduction
    # Local base: http://localhost:11434  → /api/chat  (native format)
    # Cloud base: https://ollama.com/api  → /api/chat  (native format)
    CLOUD_BASE_URL   = "https://ollama.com/api"

    def __init__(self, model_name: str, base_url: str = "", api_key: str = "",
                 calls_per_minute: int = 0):
        self.model_name = model_name
        _cloud_key = api_key or os.getenv("OLLAMA_CLOUD_API_KEY", "")
        self.base_url = (
            base_url
            or os.getenv("OLLAMA_HOST")
            or os.getenv("OLLAMA_BASE_URL")
            or (self.CLOUD_BASE_URL if _cloud_key else self.DEFAULT_BASE_URL)
        ).rstrip("/")
        self.api_key = _cloud_key
        # Native Ollama API uses /api/chat; OpenAI-compat uses /v1/chat/completions.
        # Detect by whether the base already ends in /api (cloud or explicit).
        if self.base_url.endswith("/api"):
            self.chat_endpoint = f"{self.base_url}/chat"
            self._native_api = True
        else:
            self.chat_endpoint = f"{self.base_url}/v1/chat/completions"
            self._native_api = False
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT_SEC", "120"))
        self.rate_limiter = _RateLimiter(calls_per_minute)

    def chat_single(self, messages, tools=None, max_tokens=1024, temperature=0.7) -> str:
        self.rate_limiter.wait()
        if self._native_api:
            # Native Ollama API: token/temp go inside "options"
            payload: Dict[str, Any] = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": int(max_tokens),
                    "temperature": float(temperature),
                },
            }
        else:
            # OpenAI-compatible endpoint
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "max_tokens": int(max_tokens),
                "temperature": float(temperature),
            }
        if tools:
            payload["tools"] = tools

        req = urlrequest.Request(
            self.chat_endpoint,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
        except urlerror.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            return f"[Ollama error: HTTP {e.code}: {body}]"
        except Exception as e:
            return f"[Ollama error: {e}]"

        # Parse response: native format has top-level "message"; OpenAI format has "choices"
        msg: Dict[str, Any] = {}
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get("message") or {}
        if not msg and isinstance(data.get("message"), dict):
            msg = data["message"]
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []

        if tool_calls:
            blobs: List[str] = []
            for call in tool_calls:
                fn = call.get("function") or {}
                name = fn.get("name")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        pass
                if name:
                    blobs.append(
                        f"<tool_call>{json.dumps({'name': name, 'arguments': args})}</tool_call>"
                    )
            return (f"{content}\n" if content else "") + "\n".join(blobs)

        return content

    def pull_model(self, model_name: str) -> bool:
        """Trigger `ollama pull` via the native API. Returns True if accepted."""
        try:
            payload = json.dumps({"name": model_name}).encode()
            req = urlrequest.Request(
                f"{self.base_url}/api/pull",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlrequest.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    @classmethod
    def validate_key(cls, api_key: str = "", base_url: str = "") -> bool:
        """Ping /api/version to confirm the server is reachable."""
        _cloud_key = api_key or os.getenv("OLLAMA_CLOUD_API_KEY", "")
        base = (base_url or (cls.CLOUD_BASE_URL if _cloud_key else cls.DEFAULT_BASE_URL)).rstrip("/")
        version_url = f"{base}/version" if base.endswith("/api") else f"{base}/api/version"
        headers = {}
        if _cloud_key:
            headers["Authorization"] = f"Bearer {_cloud_key}"
        try:
            req = urlrequest.Request(version_url, headers=headers)
            with urlrequest.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    @classmethod
    def list_models(cls, api_key: str = "", base_url: str = "") -> List[ModelInfo]:
        """Return all locally pulled models via GET /api/tags."""
        base = (base_url or cls.DEFAULT_BASE_URL).rstrip("/")
        try:
            with urlrequest.urlopen(f"{base}/api/tags", timeout=5) as resp:
                data = json.loads(resp.read())
        except Exception:
            return []
        return [
            ModelInfo(
                id=m["name"],
                name=m["name"],
                provider="ollama",
                description=(m.get("details") or {}).get("family", ""),
            )
            for m in (data.get("models") or [])
        ]
