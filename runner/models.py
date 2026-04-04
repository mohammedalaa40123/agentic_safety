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
    "genai": "genai:llama3.1:latest",
    "genaistudio": "genai:llama3.1:latest",
    "genai-llama3.1": "genai:llama3.1:latest",
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
    if lowered.startswith("genai:"):
        return model_name[len("genai:"):]
    if lowered.startswith("genaistudio:"):
        return model_name[len("genaistudio:"):]
    return model_name


class GenAIStudioTarget:
    def __init__(self, model_name: str, calls_per_minute: int = 0):
        self.model_name = _strip_genai_prefix(model_name)
        self.endpoint = os.getenv("GENAI_STUDIO_API_URL", "https://genai.rcac.purdue.edu/api/chat/completions")
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
        self.rate_limiter = _RateLimiter(calls_per_minute)

    def _chat_once(self, messages, max_tokens: int, temperature: float, tools=None):
        self.rate_limiter.wait()
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
                raw = resp.read().decode("utf-8", errors="replace")
        except urlerror.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            raise RuntimeError(f"HTTP {e.code}: {body}") from e

        data = json.loads(raw)
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
        max_retries = 3
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
                    backoff = max(2.0 * (attempt + 1), self.rate_limiter.min_interval)
                    if is_rate_limited:
                        backoff = max(15.0, backoff)
                    logger.warning(f"GenAI Studio transient error. Sleeping for {backoff:.1f}s before retry.")
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

    def chat(self, messages_list, tools=None):
        responses = []
        for messages in messages_list:
            responses.append(self._chat_with_retry(messages, max_tokens=1024, temperature=0.7, tools=tools))
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


class SimpleGeminiTarget:
    def __init__(self, model_name: str, calls_per_minute: int = 0):
        import google.generativeai as genai  # type: ignore[import-not-found]

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("Set GEMINI_API_KEY or GOOGLE_API_KEY for Gemini access")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
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
        import torch
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


def _is_genai_studio_model(model_name: str) -> bool:
    lowered = (model_name or "").strip().lower()
    return lowered.startswith("genai:") or lowered.startswith("genaistudio:")


def _is_no_judge(model_name: str) -> bool:
    return (model_name or "").strip().lower() in {"", "none", "null", "no-judge", "no_judge"}


def _build_single_model(model_name: str, calls_per_minute: int):
    if _is_genai_studio_model(model_name):
        clean_name = _strip_genai_prefix(model_name)
        logger.info(f"Using GenAI Studio API model: {clean_name}")
        return GenAIStudioTarget(model_name, calls_per_minute=calls_per_minute)
    if _is_gemini_model(model_name):
        logger.info(f"Using Gemini API model: {model_name}")
        return SimpleGeminiTarget(model_name, calls_per_minute=calls_per_minute)
    return HFTarget(model_name, calls_per_minute=calls_per_minute)


def build_models(cfg: ModelConfig):
    attack_name = MODEL_MAP.get(cfg.attack_model, cfg.attack_model)
    target_name = MODEL_MAP.get(cfg.target_model, cfg.target_model)
    judge_name = MODEL_MAP.get(cfg.judge_model, cfg.judge_model)

    logger.info(f"Loading attack model: {attack_name}")
    attack_lm = _build_single_model(attack_name, cfg.attack_calls_per_minute)

    if (
        target_name == attack_name
        and not _is_gemini_model(target_name)
        and not _is_genai_studio_model(target_name)
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
        and not _is_gemini_model(judge_name)
        and not _is_genai_studio_model(judge_name)
        and cfg.judge_calls_per_minute == cfg.attack_calls_per_minute
    ):
        judge_lm = attack_lm
    elif (
        judge_name == target_name
        and not _is_gemini_model(judge_name)
        and not _is_genai_studio_model(judge_name)
        and cfg.judge_calls_per_minute == cfg.target_calls_per_minute
    ):
        judge_lm = target_lm
    else:
        logger.info(f"Loading judge model: {judge_name}")
        judge_lm = _build_single_model(judge_name, cfg.judge_calls_per_minute)

    return attack_lm, target_lm, judge_lm
