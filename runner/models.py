import logging
import os
import time
from typing import Any, Dict

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
}


class SimpleGeminiTarget:
    def __init__(self, model_name: str):
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("Set GEMINI_API_KEY or GOOGLE_API_KEY for Gemini access")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def get_response(self, prompts):
        responses = []
        for prompt in prompts:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    time.sleep(4)
                    out = self.model.generate_content(prompt)
                    text = getattr(out, "text", None) or "".join(
                        [c.text for c in getattr(out, "candidates", []) if getattr(c, "text", None)]
                    )
                    responses.append(text or "")
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        logger.warning("Rate limited. Sleeping for 15s.")
                        time.sleep(15)
                    else:
                        responses.append(f"[Gemini error: {e}]")
                        break
        return responses


class HFTarget:
    def __init__(self, model_name: str):
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

    def get_response(self, prompts):
        responses = []
        for prompt in prompts:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            outputs = self.model.generate(**inputs.to(self.model.device), max_new_tokens=1024)
            response_text = self.tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
            responses.append(response_text)
        return responses

    def chat(self, messages_list, tools=None):
        responses = []
        for messages in messages_list:
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
            inputs = self.tokenizer(prompt, return_tensors="pt")
            outputs = self.model.generate(**inputs.to(self.model.device), max_new_tokens=max_n_tokens)
            response_text = self.tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
            responses.append(response_text)
        return responses


def build_models(cfg: ModelConfig):
    attack_name = MODEL_MAP.get(cfg.attack_model, cfg.attack_model)
    target_name = MODEL_MAP.get(cfg.target_model, cfg.target_model)
    judge_name = MODEL_MAP.get(cfg.judge_model, cfg.judge_model)

    logger.info(f"Loading attack model: {attack_name}")
    attack_lm = HFTarget(attack_name)

    if target_name == attack_name:
        target_lm = attack_lm
    else:
        logger.info(f"Loading target model: {target_name}")
        target_lm = HFTarget(target_name)

    if judge_name == attack_name:
        judge_lm = attack_lm
    elif judge_name == target_name:
        judge_lm = target_lm
    else:
        logger.info(f"Loading judge model: {judge_name}")
        judge_lm = HFTarget(judge_name) if "gemini" not in judge_name else SimpleGeminiTarget(judge_name)

    return attack_lm, target_lm, judge_lm
