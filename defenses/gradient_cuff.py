"""
Gradient Cuff Defense — two-step adversarial prompt detection.

Reference: Hu et al. (2024), "Gradient Cuff: Detecting Jailbreak Attacks
on Large Language Models by Exploring Refusal Loss Landscapes."
arXiv:2403.00867

Two-step detection algorithm (Algorithm 1 from paper):

  Step 1 — Sampling-based refusal check:
    Query the model N times with the same prompt and collect responses y_1..y_N.
    Define JB(y) = 1 if y contains any refusal keyword, else 0.
    Compute  f_θ(x) = 1 - (1/N) Σ JB(y_i)   (non-refusal rate).
    If f_θ(x) < 0.5 → BLOCK  (model mostly refuses → prompt is adversarial).

  Step 2 — Zeroth-order gradient norm check:
    Estimate ‖g_θ(x)‖ where g_θ is the gradient of f_θ w.r.t. e(x):
      g_θ(x) = Σ_{i=1}^{P} [ (f_θ(e(x) ⊕ μ·u_i) - f_θ(x)) / μ ] · u_i
    u_i ~ N(0, I_d),  e(x) ⊕ v = add same d-dim vector v to every token row.
    If ‖g_θ(x)‖₂ > threshold t → BLOCK.

Paper parameters: μ=0.02, N=10, P=10.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from .base import DefenseBase, DefenseResult

logger = logging.getLogger(__name__)

# Refusal keywords — Appendix A.3 of the Gradient Cuff paper
_REFUSAL_KEYWORDS: List[str] = [
    "I'm sorry",
    "Sorry",
    "I am sorry",
    "I apologize",
    "I cannot",
    "I can't",
    "I am unable to",
    "I am not able to",
    "I'm unable to",
    "I'm not able to",
]


def _is_refusal(response: str) -> bool:
    """Return True if *response* contains any refusal keyword (paper definition)."""
    return any(kw in response for kw in _REFUSAL_KEYWORDS)


class GradientCuffDefense(DefenseBase):
    """
    Two-step adversarial prompt detector (Hu et al., 2024).

    Step 1 only needs a model_fn callable (works with ollama / any LLM API).
    Step 2 additionally requires a local HF model + tokenizer for embedding
    perturbation — the truly white-box component of the paper.
    """

    name = "gradient_cuff"
    description = "Two-step gradient-based jailbreak detection (Gradient Cuff, Hu et al. 2024)"
    defense_layer = "gradient"

    def __init__(
        self,
        model_fn: Optional[Callable[[str], str]] = None,
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,
        grad_norm_threshold: float = 50.0,
        n_samples: int = 10,
        n_perturbations: int = 10,
        mu: float = 0.02,
    ):
        """
        Parameters
        ----------
        model_fn : callable, optional
            (prompt: str) -> str — queries the target model (e.g. ollama).
            Required for Step 1.
        model : transformers LM, optional
            HF causal LM with embedding access.  Required for Step 2.
        tokenizer : transformers tokenizer, optional
            Required together with *model* for Step 2.
        grad_norm_threshold : float
            Step 2 blocks when estimated gradient norm exceeds this value.
        n_samples : int
            N — number of responses sampled per f_θ evaluation (paper: 10).
        n_perturbations : int
            P — number of random perturbation directions (paper: 10).
        mu : float
            μ — perturbation scale (paper: 0.02).
        """
        self.model_fn = model_fn
        self.model = model
        self.tokenizer = tokenizer
        self.grad_norm_threshold = grad_norm_threshold
        self.n_samples = n_samples
        self.n_perturbations = n_perturbations
        self.mu = mu

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def filter_prompt(self, prompt: str, **kwargs) -> DefenseResult:
        """Run the two-step Gradient Cuff detection algorithm."""
        if self.model_fn is None and self.model is None:
            logger.warning("GradientCuff: no model_fn or model provided, passing through.")
            return DefenseResult(
                blocked=False,
                defense_name=self.name,
                original_prompt=prompt,
                filtered_prompt=prompt,
            )

        # ── Step 1: Sampling-based refusal check ──────────────────────────
        try:
            f_theta = self._compute_refusal_loss(prompt)
        except Exception as exc:
            logger.exception("GradientCuff Step 1 error: %s", exc)
            f_theta = None

        if f_theta is not None and f_theta < 0.5:
            return DefenseResult(
                blocked=True,
                defense_name=self.name,
                original_prompt=prompt,
                filtered_prompt="[BLOCKED BY GRADIENT CUFF — Step 1]",
                confidence=1.0 - f_theta,
                reason=f"f_theta={f_theta:.3f} < 0.5 (model mostly refuses — adversarial pattern)",
                metadata={"step": 1, "f_theta": f_theta},
            )

        # ── Step 2: Zeroth-order gradient norm check ──────────────────────
        if self.model is None or self.tokenizer is None:
            return DefenseResult(
                blocked=False,
                defense_name=self.name,
                original_prompt=prompt,
                filtered_prompt=prompt,
                reason=f"Step 1 passed (f_theta={f_theta}); Step 2 skipped (no HF model).",
                metadata={"step": 1, "f_theta": f_theta},
            )

        try:
            grad_norm = self._estimate_grad_norm(prompt, f_theta_x=f_theta)
        except Exception as exc:
            logger.exception("GradientCuff Step 2 error: %s", exc)
            grad_norm = None

        is_adversarial = grad_norm is not None and grad_norm > self.grad_norm_threshold

        return DefenseResult(
            blocked=is_adversarial,
            defense_name=self.name,
            original_prompt=prompt,
            filtered_prompt=(
                "[BLOCKED BY GRADIENT CUFF — Step 2]" if is_adversarial else prompt
            ),
            confidence=(
                min(grad_norm / self.grad_norm_threshold, 1.0) if grad_norm else 0.0
            ),
            reason=(
                f"grad_norm={grad_norm:.2f} > threshold {self.grad_norm_threshold}"
                if is_adversarial
                else f"grad_norm={grad_norm}; within bounds"
            ),
            metadata={
                "step": 2,
                "f_theta": f_theta,
                "grad_norm": grad_norm,
                "threshold": self.grad_norm_threshold,
            },
        )

    def analyze_gradients(self, grad_info: Dict[str, Any]) -> DefenseResult:
        """Analyze pre-computed gradient information (legacy compatibility)."""
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
    # Step 1: Sampling-based refusal loss
    # ------------------------------------------------------------------

    def _compute_refusal_loss(self, prompt: str, n: Optional[int] = None) -> float:
        """
        Compute f_θ(x) = 1 - (1/N) Σ JB(y_i).

        Returns the NON-REFUSAL rate (0 → model always refuses, 1 → never).
        Values below 0.5 are the adversarial signal: the model has learned
        to refuse this specific prompt, suggesting it was optimised to elicit
        such behaviour.
        """
        n = n if n is not None else self.n_samples
        query_fn = self._get_query_fn()

        n_refusal = 0
        for _ in range(n):
            response = query_fn(prompt)
            if _is_refusal(response):
                n_refusal += 1
        return 1.0 - n_refusal / n

    def _get_query_fn(self) -> Callable[[str], str]:
        """Return the best available prompt → response callable."""
        if self.model_fn is not None:
            return self.model_fn
        if self.model is not None and self.tokenizer is not None:
            return self._hf_generate
        raise RuntimeError("GradientCuff requires at least model_fn or (model + tokenizer)")

    def _hf_generate(self, prompt: str) -> str:
        """Greedy decode from HF model — used when no model_fn is provided."""
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt").to(
            next(self.model.parameters()).device
        )
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=64,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        new_tokens = out[0, inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True)

    # ------------------------------------------------------------------
    # Step 2: Zeroth-order gradient norm estimation
    # ------------------------------------------------------------------

    def _estimate_grad_norm(
        self, prompt: str, f_theta_x: Optional[float] = None
    ) -> float:
        """
        Estimate ‖g_θ(x)‖₂ via zeroth-order approximation.

        g_θ(x) = Σ_{i=1}^{P} [ (f_θ(e(x) ⊕ μ·u_i) - f_θ(x)) / μ ] · u_i

        e(x) ⊕ v  means adding the SAME d-dimensional vector v to every row
        of the prompt's token embedding matrix (shape T×d → (T,d) + (1,d)).
        """
        import torch

        device = next(self.model.parameters()).device
        embed_layer = self.model.get_input_embeddings()

        input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids.to(device)
        with torch.no_grad():
            base_embeds = embed_layer(input_ids)  # (1, T, d)

        d = base_embeds.shape[-1]

        if f_theta_x is None:
            f_theta_x = self._compute_refusal_loss_from_embeds(base_embeds, input_ids)

        g = torch.zeros(d, device=device)
        for _ in range(self.n_perturbations):
            u = torch.randn(d, device=device)
            # Add the same vector to every token embedding row: (1,T,d) + (1,1,d)
            perturbed = base_embeds + self.mu * u.unsqueeze(0).unsqueeze(0)
            f_perturbed = self._compute_refusal_loss_from_embeds(perturbed, input_ids)
            g = g + ((f_perturbed - f_theta_x) / self.mu) * u

        return g.norm(p=2).item()

    def _compute_refusal_loss_from_embeds(
        self, embeds: "torch.Tensor", input_ids: "torch.Tensor"
    ) -> float:
        """
        Single-sample f_θ measurement from perturbed embeddings.

        Generates one response from the given embedding tensor and checks
        for refusal keywords.  Returns 0.0 (refusal) or 1.0 (no refusal).
        """
        with torch.no_grad():
            out = self.model.generate(
                inputs_embeds=embeds,
                max_new_tokens=64,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        response_ids = out[0, input_ids.shape[1]:]
        response = self.tokenizer.decode(response_ids, skip_special_tokens=True)
        return 0.0 if _is_refusal(response) else 1.0
