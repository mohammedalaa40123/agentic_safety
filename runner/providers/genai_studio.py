"""GenAI Studio provider (Purdue RCAC and custom deployments)."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

from .base import LLMProvider, ModelInfo, _RateLimiter

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://genai.rcac.purdue.edu/api"
DEFAULT_CHAT_ENDPOINT = f"{DEFAULT_BASE_URL}/chat/completions"


def _strip_genai_prefix(model_name: str) -> str:
    lowered = (model_name or "").lower()
    if lowered.startswith("genai:"):
        return model_name[len("genai:"):]
    if lowered.startswith("genaistudio:"):
        return model_name[len("genaistudio:"):]
    return model_name


def _parse_think_setting(raw_value: str | None) -> Any:
    if raw_value is None:
        return None
    text = str(raw_value).strip().lower()
    if text in {"", "none", "null", "unset"}:
        return None
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off"}:
        return False
    if text in {"low", "medium", "high"}:
        return text
    return False


def _parse_sse_chat_completion(raw_payload: str) -> Dict[str, Any] | None:
    role = "assistant"
    saw_chunk = False
    content_parts: List[str] = []
    tool_calls: List[Dict] = []

    for line in raw_payload.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        chunk_text = line[len("data:"):].strip()
        if not chunk_text or chunk_text == "[DONE]":
            continue
        try:
            chunk = json.loads(chunk_text)
        except json.JSONDecodeError:
            continue

        saw_chunk = True
        choices = chunk.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            continue
        delta = choices[0].get("delta") or {}
        if not isinstance(delta, dict):
            continue
        if isinstance(delta.get("role"), str):
            role = delta["role"]
        if isinstance(delta.get("content"), str):
            content_parts.append(delta["content"])
        for call in (delta.get("tool_calls") or []):
            if isinstance(call, dict):
                tool_calls.append(call)

    if not saw_chunk:
        return None
    message: Dict[str, Any] = {"role": role, "content": "".join(content_parts)}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"choices": [{"message": message}]}


class GenAIStudioProvider(LLMProvider):
    """OpenAI-compatible provider for GenAI Studio / Purdue RCAC."""

    def __init__(
        self,
        model_name: str,
        api_key: str = "",
        base_url: str = "",
        calls_per_minute: int = 0,
    ):
        self.model_name = _strip_genai_prefix(model_name)

        # Resolve chat endpoint
        if base_url:
            self.endpoint = base_url.rstrip("/") + "/chat/completions"
        else:
            self.endpoint = os.getenv("GENAI_STUDIO_API_URL", DEFAULT_CHAT_ENDPOINT)

        # Resolve API key
        self.api_key = api_key or (
            os.getenv("GENAI_STUDIO_API_KEY")
            or os.getenv("RCAC_GENAI_API_KEY")
            or os.getenv("ANVILGPT_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        )
        if not self.api_key:
            raise RuntimeError(
                "Set GENAI_STUDIO_API_KEY (or RCAC_GENAI_API_KEY / ANVILGPT_API_KEY / OPENAI_API_KEY)"
            )

        self.timeout_sec = int(os.getenv("GENAI_STUDIO_TIMEOUT_SEC", "180"))
        self.max_retries = max(1, int(os.getenv("GENAI_STUDIO_MAX_RETRIES", "4")))
        self.retry_base_sec = max(0.25, float(os.getenv("GENAI_STUDIO_RETRY_BASE_SEC", "1.0")))
        self.stream = str(os.getenv("GENAI_STUDIO_STREAM", "false")).strip().lower() in {
            "1", "true", "yes", "on",
        }
        self.think = _parse_think_setting(os.getenv("GENAI_STUDIO_THINK"))
        self.rate_limiter = _RateLimiter(calls_per_minute)

    # ── Internal HTTP helpers ──────────────────────────────────────────────────

    def _post_payload(self, payload: Dict[str, Any]) -> str:
        req = urlrequest.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=self.timeout_sec) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urlerror.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            raise RuntimeError(f"HTTP {e.code}: {body}") from e

    def _chat_once(self, messages, max_tokens: int, temperature: float, tools=None) -> str:
        self.rate_limiter.wait()
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": self.stream,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
        }
        if tools:
            payload["tools"] = tools
        if self.think is not None:
            payload["think"] = self.think

        try:
            raw = self._post_payload(payload)
        except RuntimeError as e:
            err_text = str(e).lower()
            if (
                "think" in payload
                and "http 400" in err_text
                and "think" in err_text
                and ("unknown" in err_text or "invalid" in err_text)
            ):
                logger.warning("Endpoint rejected think field; retrying without think.")
                payload.pop("think", None)
                raw = self._post_payload(payload)
            else:
                raise

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            parsed_stream = _parse_sse_chat_completion(raw)
            if parsed_stream is None:
                raise RuntimeError(
                    "Unexpected GenAI Studio payload format (neither JSON nor SSE chunks)"
                )
            data = parsed_stream

        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected GenAI Studio payload type: {type(data).__name__}")

        message: Dict[str, Any] = {}
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            first_choice = choices[0]
            msg_candidate = first_choice.get("message")
            if isinstance(msg_candidate, dict):
                message = msg_candidate
            elif isinstance(first_choice.get("text"), str):
                message = {"content": first_choice.get("text", "")}
        if not message and isinstance(data.get("message"), dict):
            message = data["message"]

        # Fallback: responses API-like shape
        if not message:
            output = data.get("output")
            if isinstance(output, list) and output and isinstance(output[0], dict):
                content_blocks = output[0].get("content") or []
                if isinstance(content_blocks, list):
                    out_parts = [
                        block.get("text", "")
                        for block in content_blocks
                        if isinstance(block, dict) and isinstance(block.get("text"), str)
                    ]
                    if out_parts:
                        message = {"content": "".join(out_parts)}

        content = message.get("content", "")
        if isinstance(content, list):
            content_text = "".join(
                item if isinstance(item, str)
                else str(item.get("text", "")) if isinstance(item, dict) and item.get("type") == "text"
                else ""
                for item in content
            )
        elif content is None:
            content_text = ""
        else:
            content_text = str(content)

        if not content_text.strip():
            logger.debug(f"Empty content from {self.model_name}; keys: {list(message.keys())}")
            for key in ("reasoning", "reasoning_content", "analysis"):
                val = message.get(key)
                if isinstance(val, str) and val.strip():
                    content_text = val
                    break

        # Serialize tool calls to XML-wrapped JSON (existing runner format)
        tool_call_blobs: List[str] = []
        for call in (message.get("tool_calls") or []):
            if not isinstance(call, dict):
                continue
            fn = call.get("function") or {}
            name = fn.get("name")
            arguments = fn.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except Exception:
                    pass
            if name:
                tool_call_blobs.append(
                    f"<tool_call>{json.dumps({'name': name, 'arguments': arguments})}</tool_call>"
                )

        function_call = message.get("function_call")
        if isinstance(function_call, dict):
            fn_name = function_call.get("name")
            fn_args = function_call.get("arguments", {})
            if isinstance(fn_args, str):
                try:
                    fn_args = json.loads(fn_args)
                except Exception:
                    pass
            if fn_name:
                tool_call_blobs.append(
                    f"<tool_call>{json.dumps({'name': fn_name, 'arguments': fn_args})}</tool_call>"
                )

        if tool_call_blobs:
            return (f"{content_text}\n" if content_text.strip() else "") + "\n".join(tool_call_blobs)
        return content_text

    def _chat_with_retry(self, messages, max_tokens: int, temperature: float, tools=None) -> str:
        for attempt in range(self.max_retries):
            try:
                return self._chat_once(messages, max_tokens=max_tokens, temperature=temperature, tools=tools)
            except Exception as e:
                err_text = str(e).lower()
                is_rate_limited = "http 429" in err_text
                is_retryable = (
                    is_rate_limited
                    or "timed out" in err_text
                    or "timeout" in err_text
                    or "unexpected genai studio payload type" in err_text
                    or "temporarily unavailable" in err_text
                )
                if is_retryable and attempt < self.max_retries - 1:
                    if attempt == 0:
                        time.sleep(min(self.retry_base_sec, 0.5))
                        continue
                    backoff = max(self.retry_base_sec * (2 ** attempt), self.rate_limiter.min_interval)
                    if is_rate_limited:
                        backoff = max(15.0, backoff)
                    logger.warning(
                        f"GenAI Studio transient error ({str(e)[:220]}). Sleeping {backoff:.1f}s."
                    )
                    time.sleep(backoff)
                    continue
                return f"[GenAI Studio error: {e}]"
        return "[GenAI Studio error: max retries exceeded]"

    # ── LLMProvider interface ──────────────────────────────────────────────────

    def chat_single(self, messages, tools=None, max_tokens=1024, temperature=0.7) -> str:
        return self._chat_with_retry(messages, max_tokens=max_tokens, temperature=temperature, tools=tools)

    @classmethod
    def validate_key(cls, api_key: str = "", base_url: str = "") -> bool:
        base = (base_url or DEFAULT_BASE_URL).rstrip("/")
        key = api_key or os.getenv("GENAI_STUDIO_API_KEY") or os.getenv("RCAC_GENAI_API_KEY") or ""
        if not key:
            return False
        try:
            req = urlrequest.Request(
                f"{base}/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            with urlrequest.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

    @classmethod
    def list_models(cls, api_key: str = "", base_url: str = "") -> List[ModelInfo]:
        base = (base_url or DEFAULT_BASE_URL).rstrip("/")
        key = api_key or os.getenv("GENAI_STUDIO_API_KEY") or os.getenv("RCAC_GENAI_API_KEY") or ""
        if not key:
            return []
        try:
            req = urlrequest.Request(
                f"{base}/models",
                headers={"Authorization": f"Bearer {key}"},
            )
            with urlrequest.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            return [
                ModelInfo(
                    id=m["id"],
                    name=m.get("name", m["id"]),
                    provider="genai",
                    description=m.get("description", ""),
                )
                for m in (data.get("data") or [])
            ]
        except Exception:
            return []


# Backward-compatible alias used in runner/models.py
GenAIStudioTarget = GenAIStudioProvider
