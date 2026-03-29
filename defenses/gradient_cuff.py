"""
Gradient Cuff Defense — detects adversarial prompts via gradient analysis.

Reference: Hu et al. (2024), "Gradient Cuff: Detecting Jailbreak Attacks
on Large Language Models by Exploring Refusal Loss Landscapes."

Gradient Cuff operates at the gradient level by:
  1. Computing the refusal loss gradient norm for the input prompt
  2. Comparing it against a calibrated threshold
  3. Adversarial prompts (especially GCG-optimized) exhibit anomalously
     high gradient norms because they sit on steep loss landscape regions
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

import torch

from .base import DefenseBase, DefenseResult

logger = logging.getLogger(__name__)


class GradientCuffDefense(DefenseBase):
    """
    Gradient-based adversarial prompt detector.

    Computes the L2 norm of the refusal loss gradient w.r.t. input
    embeddings.  Adversarial prompts that were optimized via GCG
    tend to produce anomalously high gradient norms compared to
    benign prompts.
    """

    name = "gradient_cuff"
    description = "Gradient-based jailbreak detection (Gradient Cuff)"
    defense_layer = "gradient"

    def __init__(
        self,
        model=None,
        tokenizer=None,
        refusal_target: str = "I cannot assist with that request.",
        grad_norm_threshold: float = 50.0,
    ):
        """
        Parameters
        ----------
        model : transformers model
            The target LLM (must support gradient computation).
        tokenizer : transformers tokenizer
        refusal_target : str
            The expected refusal string for computing refusal loss.
        grad_norm_threshold : float
            Prompts with gradient norm above this threshold are flagged.
        """
        self.model = model
        self.tokenizer = tokenizer
        self.refusal_target = refusal_target
        self.grad_norm_threshold = grad_norm_threshold

    def filter_prompt(self, prompt: str, **kwargs) -> DefenseResult:
        """
        Compute the refusal-loss gradient norm and flag if anomalous.
        """
        if self.model is None or self.tokenizer is None:
            logger.warning("GradientCuff: model/tokenizer not set, passing through.")
            return DefenseResult(
                blocked=False,
                defense_name=self.name,
                original_prompt=prompt,
                filtered_prompt=prompt,
            )

        try:
            grad_norm = self._compute_refusal_grad_norm(prompt)
        except Exception as e:
            logger.exception(f"GradientCuff error: {e}")
            return DefenseResult(
                blocked=False,
                defense_name=self.name,
                original_prompt=prompt,
                filtered_prompt=prompt,
                reason=f"Error computing gradient: {e}",
            )

        is_adversarial = grad_norm > self.grad_norm_threshold

        return DefenseResult(
            blocked=is_adversarial,
            defense_name=self.name,
            original_prompt=prompt,
            filtered_prompt=prompt if not is_adversarial else "[BLOCKED BY GRADIENT CUFF]",
            confidence=min(grad_norm / self.grad_norm_threshold, 1.0),
            reason=(
                f"Gradient norm {grad_norm:.2f} > threshold {self.grad_norm_threshold:.2f}"
                if is_adversarial
                else f"Gradient norm {grad_norm:.2f} within bounds"
            ),
            metadata={"grad_norm": grad_norm, "threshold": self.grad_norm_threshold},
        )

    def analyze_gradients(self, grad_info: Dict[str, Any]) -> DefenseResult:
        """Analyze pre-computed gradient information."""
        grad_norm = grad_info.get("grad_norm", 0.0)
        prompt = grad_info.get("prompt", "")
        is_adversarial = grad_norm > self.grad_norm_threshold

        return DefenseResult(
            blocked=is_adversarial,
            defense_name=self.name,
            original_prompt=prompt,
            confidence=min(grad_norm / self.grad_norm_threshold, 1.0),
            reason=f"Gradient norm: {grad_norm:.2f}",
            metadata=grad_info,
        )

    # ------------------------------------------------------------------
    # Gradient computation
    # ------------------------------------------------------------------

    def _compute_refusal_grad_norm(self, prompt: str) -> float:
        """
        Compute L2 norm of the gradient of the refusal loss w.r.t.
        the input embedding of *prompt*.
        """
        device = self.model.device if hasattr(self.model, "device") else "cuda"

        # Tokenize prompt + refusal target
        prompt_ids = self.tokenizer(prompt, return_tensors="pt").input_ids.to(device)
        target_ids = self.tokenizer(
            self.refusal_target, return_tensors="pt", add_special_tokens=False
        ).input_ids.to(device)

        # Concatenate for teacher-forced generation
        full_ids = torch.cat([prompt_ids, target_ids], dim=1)

        # Get embedding matrix
        if hasattr(self.model, "model"):
            embed_layer = self.model.model.embed_tokens
        elif hasattr(self.model, "get_input_embeddings"):
            embed_layer = self.model.get_input_embeddings()
        else:
            raise RuntimeError("Cannot find embedding layer in model")

        # Compute embeddings with gradient tracking for the prompt portion
        embeds = embed_layer(full_ids).detach()
        prompt_len = prompt_ids.shape[1]
        prompt_embeds = embeds[:, :prompt_len, :].clone().requires_grad_(True)
        target_embeds = embeds[:, prompt_len:, :].detach()

        full_embeds = torch.cat([prompt_embeds, target_embeds], dim=1)

        # Forward pass
        outputs = self.model(inputs_embeds=full_embeds)
        logits = outputs.logits

        # Compute cross-entropy loss on the refusal target tokens
        shift_logits = logits[:, prompt_len - 1:-1, :]
        shift_labels = target_ids

        loss = torch.nn.functional.cross_entropy(
            shift_logits.reshape(-1, shift_logits.shape[-1]),
            shift_labels.reshape(-1),
        )

        loss.backward()

        grad_norm = prompt_embeds.grad.norm(p=2).item()
        return grad_norm
