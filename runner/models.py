import json
import logging
import os
import time
from typing import Any, Dict
from urllib import error as urlerror
from urllib import request as urlrequest

from .config import ModelConfig

logger = logging.getLogger(__name__)


MODEL_MAP = {
    "vicuna": "vicuna",
    "llama2": "llama-2",
    "llama3": "llama-3",
    "llama-guard": "llama-guard",
    "qwen25-7b": "qwen25-7b",
    "qwen35-7b": "qwen35-7b",
    "mistral-nemo": "mistral-nemo",
    "gemini": "gemini",
    "gemini-flash": "gemini-2.5-flash",
    "gemini-2.5-flash": "gemini-2.5-flash",
    "gemini-pro": "gemini-pro",
    "gpt-4o-mini": "gpt-4o-mini",
    "genai": "genai:llama3.3:70b",
    "genaistudio": "genai:llama3.3:70b",
    "genai-llama3.1": "genai:llama3.1:latest",
    "genai-llama3.3": "genai:llama3.3:70b",
    # Local aliases for currently available Ollama cloud-backed IDs.
    "minimax-m2": "genai:minimax-m2.7:cloud",
    "genai:minimax-m2": "genai:minimax-m2.7:cloud",
    "genaistudio:minimax-m2": "genai:minimax-m2.7:cloud",
    "glm-5.1": "genai:glm-5.1:cloud",
    "genai:glm-5.1": "genai:glm-5.1:cloud",
    "genaistudio:glm-5.1": "genai:glm-5.1:cloud",
}


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


def _strip_genai_prefix(model_name: str) -> str:
    lowered = (model_name or "").lower()
    for prefix in ("genai_rcac:", "genaistudio:", "genai:"):
        if lowered.startswith(prefix):
            return model_name[len(prefix):]
    return model_name


def _strip_gemini_prefix(model_name: str) -> str:
    lowered = (model_name or "").lower()
    if lowered.startswith("gemini:"):
        return model_name[len("gemini:"):]
    return model_name


def _strip_ollama_prefix(model_name: str) -> str:
    lowered = (model_name or "").lower()
    if lowered.startswith("ollama:"):
        return model_name[len("ollama:"):]
    return model_name


def _parse_think_setting(raw_value: str | None) -> Any:
    """
    Parse think setting for Ollama-compatible requests.
    Supported values:
      - booleans: true/false/1/0/yes/no/on/off
      - GPT-OSS levels: low/medium/high
      - empty/none/null => do not send think field
    """
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
    """
    Parse OpenAI-compatible SSE chat chunks into a non-streaming-like payload.
    """
    role = "assistant"
    saw_chunk = False
    content_parts = []
    tool_calls = []

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
            role = delta.get("role", role)

        if isinstance(delta.get("content"), str):
            content_parts.append(delta.get("content", ""))

        delta_tool_calls = delta.get("tool_calls") or []
        if isinstance(delta_tool_calls, list):
            for call in delta_tool_calls:
                if isinstance(call, dict):
                    tool_calls.append(call)

    if not saw_chunk:
        return None

    message: Dict[str, Any] = {
        "role": role,
        "content": "".join(content_parts),
    }
    if tool_calls:
        message["tool_calls"] = tool_calls

    return {"choices": [{"message": message}]}


class GenAIStudioTarget:
    def __init__(self, model_name: str, calls_per_minute: int = 0):
        self.model_name = _strip_genai_prefix(model_name)
        self.endpoint = os.getenv(
            "GENAI_STUDIO_API_URL",
            "https://genai.rcac.purdue.edu/api/chat/completions",
        )
        self.api_key = (
            os.getenv("GENAI_STUDIO_API_KEY")
            or os.getenv("RCAC_GENAI_API_KEY")
            or os.getenv("ANVILGPT_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        if not self.api_key:
            raise RuntimeError(
                "Set GENAI_STUDIO_API_KEY (or RCAC_GENAI_API_KEY / ANVILGPT_API_KEY / OPENAI_API_KEY)"
            )
        self.timeout_sec = int(os.getenv("GENAI_STUDIO_TIMEOUT_SEC", "180"))
        self.max_retries = max(1, int(os.getenv("GENAI_STUDIO_MAX_RETRIES", "4")))
        self.retry_base_sec = max(0.25, float(os.getenv("GENAI_STUDIO_RETRY_BASE_SEC", "1.0")))
        self.stream = str(os.getenv("GENAI_STUDIO_STREAM", "false")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        # Only send think field when explicitly configured via env var.
        # Many models (e.g. Gemma4) don't support it and return empty.
        self.think = _parse_think_setting(os.getenv("GENAI_STUDIO_THINK"))
        self.rate_limiter = _RateLimiter(calls_per_minute)

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

    def _chat_once(self, messages, max_tokens: int, temperature: float, tools=None):
        self.rate_limiter.wait()
        payload = {
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
            # Some OpenAI-compatible endpoints may reject unknown fields.
            # If so, retry once without `think`.
            err_text = str(e).lower()
            if "think" in payload and "http 400" in err_text and "think" in err_text and ("unknown" in err_text or "invalid" in err_text):
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
                raise RuntimeError("Unexpected GenAI Studio payload format (neither JSON nor SSE chunks)")
            data = parsed_stream

        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected GenAI Studio payload type: {type(data).__name__}")

        # OpenAI-compatible payload: prefer choices[0].message but tolerate alternate shapes.
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
            message = data.get("message")

        # Fallback for responses API-like shapes: output[0].content[*].text
        if not message:
            output = data.get("output")
            if isinstance(output, list) and output and isinstance(output[0], dict):
                content_blocks = output[0].get("content") or []
                if isinstance(content_blocks, list):
                    out_parts = []
                    for block in content_blocks:
                        if isinstance(block, dict) and isinstance(block.get("text"), str):
                            out_parts.append(block.get("text", ""))
                    if out_parts:
                        message = {"content": "".join(out_parts)}

        # Normalize message content across providers:
        # - string content
        # - list-of-parts content (text blocks)
        # - null content (common when tool_calls are emitted)
        content = message.get("content", "")
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            content_text = "".join(parts)
        elif content is None:
            content_text = ""
        elif isinstance(content, str):
            content_text = content
        else:
            content_text = str(content)

        # Some reasoning-capable models may emit empty content while populating
        # auxiliary fields such as `reasoning` / `reasoning_content`.
        if not content_text.strip():
            logger.debug(f"Empty content from {self.model_name}; raw message keys: {list(message.keys())}")
            reasoning_text = (
                message.get("reasoning")
                or message.get("reasoning_content")
                or message.get("analysis")
                or ""
            )
            if isinstance(reasoning_text, str) and reasoning_text.strip():
                content_text = reasoning_text

        # Convert native tool_calls to the loop's expected XML-wrapped JSON format.
        tool_call_blobs = []
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
                payload = {"name": name, "arguments": arguments}
                tool_call_blobs.append(f"<tool_call>{json.dumps(payload)}</tool_call>")

        # Support legacy/function_call shape.
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
                payload = {"name": fn_name, "arguments": fn_args}
                tool_call_blobs.append(f"<tool_call>{json.dumps(payload)}</tool_call>")

        if tool_call_blobs:
            if content_text.strip():
                return f"{content_text}\n" + "\n".join(tool_call_blobs)
            return "\n".join(tool_call_blobs)

        return content_text

    def _chat_with_retry(self, messages, max_tokens: int, temperature: float, tools=None):
        max_retries = self.max_retries
        for attempt in range(max_retries):
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
                if is_retryable and attempt < max_retries - 1:
                    # First transient miss is commonly a cold-start hiccup; retry quickly and quietly.
                    if attempt == 0:
                        time.sleep(min(self.retry_base_sec, 0.5))
                        continue

                    backoff = max(self.retry_base_sec * (2 ** attempt), self.rate_limiter.min_interval)
                    if is_rate_limited:
                        backoff = max(15.0, backoff)
                    err_preview = str(e).replace("\n", " ")[:220]
                    logger.warning(
                        f"GenAI Studio transient error ({err_preview}). Sleeping for {backoff:.1f}s before retry."
                    )
                    time.sleep(backoff)
                    continue
                return f"[GenAI Studio error: {e}]"

    def get_response(self, prompts):
        responses = []
        for prompt in prompts:
            responses.append(
                self._chat_with_retry(
                    [{"role": "user", "content": prompt}],
                    max_tokens=1024,
                    temperature=0.7,
                )
            )
        return responses

    def chat(self, messages_list, tools=None, max_tokens: int = 1024, temperature: float = 0.7):
        responses = []
        for messages in messages_list:
            responses.append(
                self._chat_with_retry(
                    messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    tools=tools,
                )
            )
        return responses

    def batched_generate(self, prompts, max_n_tokens=1024, temperature=0.7):
        responses = []
        for prompt in prompts:
            responses.append(
                self._chat_with_retry(
                    [{"role": "user", "content": prompt}],
                    max_tokens=max_n_tokens,
                    temperature=temperature,
                )
            )
        return responses


class OllamaTarget:
    """Ollama client — native /api/chat (local & cloud) or OpenAI-compat /v1/chat/completions.

    Endpoint resolution:
      1. OLLAMA_API_URL env var — full URL override
      2. OLLAMA_CLOUD_API_KEY set → https://ollama.com/api/chat  (native, cloud)
      3. OLLAMA_HOST / OLLAMA_BASE_URL env var → custom base
      4. Default: http://localhost:11434/api/chat  (native, local)
    """

    def __init__(self, model_name: str, calls_per_minute: int = 0):
        self.model_name = _strip_ollama_prefix(model_name)

        # Ollama cloud (api.ollama.com) is activated by setting OLLAMA_CLOUD_API_KEY.
        # Endpoint resolution order:
        #  1. OLLAMA_API_URL  — full URL override
        #  2. OLLAMA_CLOUD_API_KEY set → https://api.ollama.com
        #  3. OLLAMA_HOST / OLLAMA_BASE_URL env var → custom base
        #  4. Default: http://localhost:11434
        cloud_key = os.getenv("OLLAMA_CLOUD_API_KEY", "")
        # Docs: local base = http://localhost:11434, cloud base = https://ollama.com/api
        raw_host = (
            os.getenv("OLLAMA_HOST")
            or os.getenv("OLLAMA_BASE_URL")
            or ("https://ollama.com/api" if cloud_key else "http://localhost:11434")
        ).rstrip("/")
        # Ensure the host has a scheme; bare IP/hostname (e.g. "0.0.0.0") → http://host:11434
        if not raw_host.startswith("http://") and not raw_host.startswith("https://"):
            raw_host = f"http://{raw_host}"
        # For localhost only, append default port if missing
        scheme_stripped = raw_host.split("://", 1)[1]
        if ":" not in scheme_stripped.split("/")[0] and "localhost" in scheme_stripped:
            raw_host = f"{raw_host}:11434"
        # Native Ollama API: base ends in /api → /api/chat
        # OpenAI-compat: bare host → /v1/chat/completions
        if os.getenv("OLLAMA_API_URL"):
            self.endpoint = os.getenv("OLLAMA_API_URL")
            self._native_api = False  # assume OpenAI-compat when explicitly set
        elif raw_host.endswith("/api"):
            self.endpoint = f"{raw_host}/chat"
            self._native_api = True
        else:
            self.endpoint = f"{raw_host}/v1/chat/completions"
            self._native_api = False
        # Prefer cloud key when set; fall back to OLLAMA_API_KEY; omit header for local
        self.api_key = cloud_key or os.getenv("OLLAMA_API_KEY", "")
        self.timeout_sec = int(os.getenv("OLLAMA_TIMEOUT_SEC", "180"))
        self.max_retries = max(1, int(os.getenv("OLLAMA_MAX_RETRIES", "3")))
        self.retry_base_sec = max(0.25, float(os.getenv("OLLAMA_RETRY_BASE_SEC", "1.0")))
        self.think = _parse_think_setting(os.getenv("OLLAMA_THINK"))
        self.rate_limiter = _RateLimiter(calls_per_minute)

    def _post_payload(self, payload: Dict[str, Any]) -> str:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urlrequest.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=self.timeout_sec) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urlerror.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            raise RuntimeError(f"HTTP {e.code}: {body}") from e

    def _chat_once(self, messages, max_tokens: int, temperature: float, tools=None):
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
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "max_tokens": int(max_tokens),
                "temperature": float(temperature),
            }
        if tools:
            payload["tools"] = tools
        if self.think is not None:
            payload["think"] = self.think

        raw = self._post_payload(payload)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            parsed_stream = _parse_sse_chat_completion(raw)
            if parsed_stream is None:
                raise RuntimeError("Unexpected Ollama payload format (neither JSON nor SSE chunks)")
            data = parsed_stream

        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected Ollama payload type: {type(data).__name__}")

        message: Dict[str, Any] = {}
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            msg_candidate = choices[0].get("message")
            if isinstance(msg_candidate, dict):
                message = msg_candidate
        if not message and isinstance(data.get("message"), dict):
            message = data["message"]

        content = message.get("content", "")
        if isinstance(content, list):
            content_text = "".join(
                item if isinstance(item, str)
                else str(item.get("text", ""))
                for item in content
                if isinstance(item, (str, dict))
            )
        elif content is None:
            content_text = ""
        else:
            content_text = str(content)

        if not content_text.strip():
            for key in ("reasoning", "reasoning_content", "thinking"):
                val = message.get(key)
                if isinstance(val, str) and val.strip():
                    content_text = val
                    break

        # Convert tool_calls to XML-wrapped JSON (same format as GenAIStudioTarget).
        tool_call_blobs = []
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
                tc_payload = {"name": name, "arguments": arguments}
                tool_call_blobs.append(f"<tool_call>{json.dumps(tc_payload)}</tool_call>")

        if tool_call_blobs:
            return (f"{content_text}\n" if content_text.strip() else "") + "\n".join(tool_call_blobs)

        return content_text

    def _chat_with_retry(self, messages, max_tokens: int, temperature: float, tools=None):
        for attempt in range(self.max_retries):
            try:
                return self._chat_once(messages, max_tokens=max_tokens, temperature=temperature, tools=tools)
            except Exception as e:
                err_text = str(e).lower()
                is_retryable = (
                    "http 429" in err_text
                    or "http 500" in err_text
                    or "http 502" in err_text
                    or "http 503" in err_text
                    or "timed out" in err_text
                    or "timeout" in err_text
                    or "temporarily unavailable" in err_text
                    or "connection refused" in err_text
                )
                if is_retryable and attempt < self.max_retries - 1:
                    backoff = self.retry_base_sec * (2 ** attempt)
                    if "http 429" in err_text:
                        backoff = max(15.0, backoff)
                    logger.warning(
                        f"Ollama transient error ({str(e)[:180]}). Retrying in {backoff:.1f}s."
                    )
                    time.sleep(backoff)
                    continue
                return f"[Ollama error: {e}]"

    def get_response(self, prompts):
        return [
            self._chat_with_retry([{"role": "user", "content": p}], max_tokens=1024, temperature=0.7)
            for p in prompts
        ]

    def chat(self, messages_list, tools=None, max_tokens: int = 1024, temperature: float = 0.7):
        return [
            self._chat_with_retry(messages, max_tokens=max_tokens, temperature=temperature, tools=tools)
            for messages in messages_list
        ]

    def batched_generate(self, prompts, max_n_tokens=1024, temperature=0.7):
        return [
            self._chat_with_retry([{"role": "user", "content": p}], max_tokens=max_n_tokens, temperature=temperature)
            for p in prompts
        ]


class SimpleGeminiTarget:
    def __init__(self, model_name: str, calls_per_minute: int = 0):
        import google.generativeai as genai  # type: ignore[import-not-found]

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("Set GEMINI_API_KEY or GOOGLE_API_KEY for Gemini access")
        genai.configure(api_key=api_key)
        clean_name = _strip_gemini_prefix(model_name)
        self.model = genai.GenerativeModel(clean_name)
        self.rate_limiter = _RateLimiter(calls_per_minute)

    def get_response(self, prompts):
        responses = []
        for prompt in prompts:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.rate_limiter.wait()
                    out = self.model.generate_content(prompt)
                    text = getattr(out, "text", None) or "".join(
                        [c.text for c in getattr(out, "candidates", []) if getattr(c, "text", None)]
                    )
                    responses.append(text or "")
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        backoff = max(15.0, self.rate_limiter.min_interval)
                        logger.warning(f"Rate limited. Sleeping for {backoff:.1f}s.")
                        time.sleep(backoff)
                    else:
                        responses.append(f"[Gemini error: {e}]")
                        break
        return responses


class HFTarget:
    def __init__(self, model_name: str, calls_per_minute: int = 0):
        try:
            import torch
        except ImportError as exc:
            raise ImportError(
                f"HFTarget requires PyTorch but it is not installed in this environment. "
                f"Install with: pip install torch\nOriginal error: {exc}"
            ) from exc
        from transformers import AutoModelForCausalLM, AutoTokenizer

        path_map = {
            "qwen25-7b": "/depot/davisjam/data/mohamed/agentic_safety/models/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28",
            "qwen35-7b": "/depot/davisjam/data/mohamed/agentic_safety/models/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28",
            "llama2": "meta-llama/Llama-2-7b-chat-hf",
            "llama3": "meta-llama/Meta-Llama-3-8B-Instruct",
            "vicuna": "lmsys/vicuna-7b-v1.5",
        }
        model_path = path_map.get(model_name, model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.bfloat16, device_map="auto")
        self.rate_limiter = _RateLimiter(calls_per_minute)

    def get_response(self, prompts):
        responses = []
        for prompt in prompts:
            self.rate_limiter.wait()
            inputs = self.tokenizer(prompt, return_tensors="pt")
            outputs = self.model.generate(**inputs.to(self.model.device), max_new_tokens=1024)
            response_text = self.tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
            responses.append(response_text)
        return responses

    def chat(self, messages_list, tools=None):
        responses = []
        for messages in messages_list:
            self.rate_limiter.wait()
            if tools:
                inputs = self.tokenizer.apply_chat_template(messages, tools=tools, add_generation_prompt=True, return_dict=True, return_tensors="pt")
            else:
                inputs = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_dict=True, return_tensors="pt")
            outputs = self.model.generate(**inputs.to(self.model.device), max_new_tokens=1024)
            response_text = self.tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
            responses.append(response_text)
        return responses

    def batched_generate(self, prompts, max_n_tokens=1024, temperature=0.7):
        responses = []
        for prompt in prompts:
            self.rate_limiter.wait()
            inputs = self.tokenizer(prompt, return_tensors="pt")
            outputs = self.model.generate(**inputs.to(self.model.device), max_new_tokens=max_n_tokens)
            response_text = self.tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
            responses.append(response_text)
        return responses


def _is_gemini_model(model_name: str) -> bool:
    return "gemini" in (model_name or "").lower()


def _is_ollama_model(model_name: str) -> bool:
    return (model_name or "").strip().lower().startswith("ollama:")


def _is_genai_studio_model(model_name: str) -> bool:
    lowered = (model_name or "").strip().lower()
    return (
        lowered.startswith("genai:")
        or lowered.startswith("genaistudio:")
        or lowered.startswith("genai_rcac:")
    )


def _is_openrouter_model(model_name: str) -> bool:
    return (model_name or "").strip().lower().startswith("openrouter:")


def _strip_openrouter_prefix(model_name: str) -> str:
    lowered = (model_name or "").lower()
    if lowered.startswith("openrouter:"):
        return model_name[len("openrouter:"):]
    return model_name


class SimpleOpenRouterTarget:
    """Thin adapter so OpenRouterProvider works like HFTarget/OllamaTarget."""

    def __init__(self, model_name: str, calls_per_minute: int = 0):
        from .providers.openrouter import OpenRouterProvider
        self._provider = OpenRouterProvider(
            model_name=model_name,
            calls_per_minute=calls_per_minute,
        )

    def get_response(self, prompts):
        responses = []
        for prompt in prompts:
            messages = [{"role": "user", "content": prompt}]
            responses.append(self._provider.chat_single(messages))
        return responses

    def chat(self, conversations):
        responses = []
        for msgs in conversations:
            responses.append(self._provider.chat_single(msgs))
        return responses


def _is_no_judge(model_name: str) -> bool:
    return (model_name or "").strip().lower() in {"", "none", "null", "no-judge", "no_judge"}


def _build_single_model(model_name: str, calls_per_minute: int):
    if _is_ollama_model(model_name):
        clean_name = _strip_ollama_prefix(model_name)
        logger.info(f"Using Ollama API model: {clean_name}")
        return OllamaTarget(model_name, calls_per_minute=calls_per_minute)
    if _is_genai_studio_model(model_name):
        clean_name = _strip_genai_prefix(model_name)
        logger.info(f"Using GenAI Studio API model: {clean_name}")
        return GenAIStudioTarget(model_name, calls_per_minute=calls_per_minute)
    if _is_gemini_model(model_name):
        clean_name = _strip_gemini_prefix(model_name)
        logger.info(f"Using Gemini API model: {clean_name}")
        return SimpleGeminiTarget(clean_name, calls_per_minute=calls_per_minute)
    if _is_openrouter_model(model_name):
        clean_name = _strip_openrouter_prefix(model_name)
        logger.info(f"Using OpenRouter API model: {clean_name}")
        return SimpleOpenRouterTarget(clean_name, calls_per_minute=calls_per_minute)
    return HFTarget(model_name, calls_per_minute=calls_per_minute)


def build_models(cfg: ModelConfig):
    attack_name = MODEL_MAP.get(cfg.attack_model, cfg.attack_model)
    target_name = MODEL_MAP.get(cfg.target_model, cfg.target_model)
    judge_name = MODEL_MAP.get(cfg.judge_model, cfg.judge_model)

    logger.info(f"Loading attack model: {attack_name}")
    attack_lm = _build_single_model(attack_name, cfg.attack_calls_per_minute)

    def _is_api_model(name: str) -> bool:
        return _is_gemini_model(name) or _is_genai_studio_model(name) or _is_ollama_model(name) or _is_openrouter_model(name)

    if (
        target_name == attack_name
        and not _is_api_model(target_name)
        and cfg.target_calls_per_minute == cfg.attack_calls_per_minute
    ):
        target_lm = attack_lm
    else:
        logger.info(f"Loading target model: {target_name}")
        target_lm = _build_single_model(target_name, cfg.target_calls_per_minute)

    if _is_no_judge(judge_name):
        logger.info("Judge model disabled.")
        judge_lm = None
    elif (
        judge_name == attack_name
        and not _is_api_model(judge_name)
        and cfg.judge_calls_per_minute == cfg.attack_calls_per_minute
    ):
        judge_lm = attack_lm
    elif (
        judge_name == target_name
        and not _is_api_model(judge_name)
        and cfg.judge_calls_per_minute == cfg.target_calls_per_minute
    ):
        judge_lm = target_lm
    else:
        logger.info(f"Loading judge model: {judge_name}")
        judge_lm = _build_single_model(judge_name, cfg.judge_calls_per_minute)

    return attack_lm, target_lm, judge_lm
