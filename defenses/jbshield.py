"""
JBShield Defense — jailbreak detection via mutation-based testing.

Reference: Zhang et al. (2025), "JBShield: Defending Large Language Models
from Jailbreak Attacks through Activated Concept Analysis and Manipulation."

JBShield operates at the input level by:
  1. Generating mutations (paraphrases) of the input prompt
  2. Checking semantic consistency of model responses across mutations
  3. Flagging prompts where mutations cause large behavioral divergence
     (a hallmark of adversarial prompts that are fragile to rewording)
"""

from __future__ import annotations

import logging
import random
import re
from typing import Callable, List, Optional, Dict, Any

from .base import DefenseBase, DefenseResult

logger = logging.getLogger(__name__)


class JBShieldDefense(DefenseBase):
    """
    Mutation-based jailbreak detector.

    For each incoming prompt, generates N paraphrased variants and queries
    the target model on each.  If responses diverge significantly (some
    comply, some refuse), the original prompt is flagged as adversarial.
    """

    name = "jbshield"
    description = "Mutation-based jailbreak detection (JBShield)"
    defense_layer = "input"

    def __init__(
        self,
        n_mutations: int = 5,
        divergence_threshold: float = 0.6,
        target_fn: Optional[Callable[[str], str]] = None,
        mutation_fn: Optional[Callable[[str], str]] = None,
    ):
        """
        Parameters
        ----------
        n_mutations : int
            Number of paraphrased variants to generate.
        divergence_threshold : float
            If refusal rate across mutations > threshold, block the prompt.
        target_fn : callable
            (prompt) -> response  — queries the target model.
        mutation_fn : callable
            (prompt) -> mutated_prompt  — generates a paraphrased variant.
        """
        self.n_mutations = n_mutations
        self.divergence_threshold = divergence_threshold
        self.target_fn = target_fn
        self.mutation_fn = mutation_fn or self._default_mutation

    def filter_prompt(self, prompt: str, **kwargs) -> DefenseResult:
        """
        Generate mutations of the prompt, query the target on each,
        and check for behavioral divergence.
        """
        if self.target_fn is None:
            logger.warning("JBShield: no target_fn set, passing through.")
            return DefenseResult(
                blocked=False,
                defense_name=self.name,
                original_prompt=prompt,
                filtered_prompt=prompt,
            )

        mutations = [self.mutation_fn(prompt) for _ in range(self.n_mutations)]
        refusal_count = 0

        for mut in mutations:
            response = self.target_fn(mut)
            if self._is_refusal(response):
                refusal_count += 1

        refusal_rate = refusal_count / self.n_mutations
        # Also check the original
        original_response = self.target_fn(prompt)
        original_refused = self._is_refusal(original_response)

        # Divergence: original complies but mutations refuse (or vice versa)
        # High refusal rate on mutations + compliance on original = adversarial
        is_adversarial = (
            not original_refused and refusal_rate >= self.divergence_threshold
        )

        return DefenseResult(
            blocked=is_adversarial,
            defense_name=self.name,
            original_prompt=prompt,
            filtered_prompt=prompt if not is_adversarial else "[BLOCKED BY JBSHIELD]",
            confidence=refusal_rate,
            reason=(
                f"Mutation divergence: {refusal_rate:.0%} mutations refused "
                f"(threshold={self.divergence_threshold:.0%})"
                if is_adversarial
                else "Below divergence threshold"
            ),
            metadata={
                "n_mutations": self.n_mutations,
                "refusal_count": refusal_count,
                "refusal_rate": refusal_rate,
                "original_refused": original_refused,
            },
        )

    # ------------------------------------------------------------------
    # Mutation strategies
    # ------------------------------------------------------------------

    @staticmethod
    def _default_mutation(prompt: str) -> str:
        """
        Simple mutation: randomly shuffle sentence order, drop random
        words, and add filler phrases.  A production implementation would
        use an LLM paraphraser.
        """
        sentences = re.split(r"(?<=[.!?])\s+", prompt)
        if len(sentences) > 2:
            random.shuffle(sentences)
        # Drop ~10% of words
        words = " ".join(sentences).split()
        if len(words) > 10:
            n_drop = max(1, len(words) // 10)
            indices_to_drop = set(random.sample(range(len(words)), n_drop))
            words = [w for i, w in enumerate(words) if i not in indices_to_drop]
        return " ".join(words)

    @staticmethod
    def _is_refusal(response: str) -> bool:
        """Heuristic refusal detection."""
        refusal_phrases = [
            "i cannot", "i can't", "i'm unable", "i am unable",
            "sorry, but", "i must decline", "against my guidelines",
            "not appropriate", "cannot assist", "won't be able to",
        ]
        response_lower = response.lower()
        return any(phrase in response_lower for phrase in refusal_phrases)
