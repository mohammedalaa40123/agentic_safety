"""
StepShield Defense — step-level safety verification for multi-step agents.

Reference: StepShield (2026), "Step-Level Safety Verification for
Multi-Step Reasoning in LLM Agents."

StepShield operates at the output level by:
  1. Breaking the agent's response into individual reasoning steps
  2. Scoring each step for safety using a lightweight classifier
  3. Blocking the response if any single step exceeds the harm threshold
  4. Providing fine-grained step-level safety attribution
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base import DefenseBase, DefenseResult

logger = logging.getLogger(__name__)


@dataclass
class StepVerdict:
    """Safety verdict for a single reasoning step."""
    step_index: int
    step_text: str
    is_safe: bool
    harm_score: float = 0.0
    category: str = ""


class StepShieldDefense(DefenseBase):
    """
    Step-level safety verifier for multi-step agent responses.

    Segments the agent's response into discrete reasoning steps and
    evaluates each independently with a safety classifier.
    """

    name = "stepshield"
    description = "Step-level safety verification (StepShield)"
    defense_layer = "output"

    def __init__(
        self,
        step_classifier: Optional[Callable[[str], float]] = None,
        harm_threshold: float = 0.7,
        step_delimiters: Optional[List[str]] = None,
    ):
        """
        Parameters
        ----------
        step_classifier : callable
            (step_text) -> harm_score in [0, 1].
            If None, uses a keyword-based heuristic classifier.
        harm_threshold : float
            Steps with harm_score >= threshold are flagged.
        step_delimiters : list[str]
            Regex patterns for splitting responses into steps.
        """
        self.step_classifier = step_classifier or self._keyword_classifier
        self.harm_threshold = harm_threshold
        self.step_delimiters = step_delimiters or [
            r"\n\d+[\.\)]\s",       # "1. " or "1) "
            r"\nStep\s+\d+",        # "Step 1"
            r"\n[-•]\s",            # bullet points
            r"\n(?=First|Second|Third|Next|Then|Finally)",
        ]

    def filter_prompt(self, prompt: str, **kwargs) -> DefenseResult:
        """Input-level: pass through (StepShield is output-level)."""
        return DefenseResult(
            blocked=False,
            defense_name=self.name,
            original_prompt=prompt,
            filtered_prompt=prompt,
        )

    def filter_response(
        self, prompt: str, response: str, **kwargs
    ) -> DefenseResult:
        """
        Segment the response into steps and verify each.
        """
        steps = self._segment_steps(response)
        verdicts: List[StepVerdict] = []
        blocked = False

        for idx, step_text in enumerate(steps):
            harm_score = self.step_classifier(step_text)
            is_safe = harm_score < self.harm_threshold
            verdict = StepVerdict(
                step_index=idx,
                step_text=step_text[:200],
                is_safe=is_safe,
                harm_score=harm_score,
            )
            verdicts.append(verdict)
            if not is_safe:
                blocked = True

        # Build filtered response (redact harmful steps)
        if blocked:
            filtered_parts = []
            for v in verdicts:
                if v.is_safe:
                    filtered_parts.append(v.step_text)
                else:
                    filtered_parts.append(
                        f"[STEP {v.step_index + 1} REDACTED BY STEPSHIELD: "
                        f"harm_score={v.harm_score:.2f}]"
                    )
            filtered_response = "\n".join(filtered_parts)
        else:
            filtered_response = response

        max_harm = max((v.harm_score for v in verdicts), default=0.0)
        n_harmful = sum(1 for v in verdicts if not v.is_safe)

        return DefenseResult(
            blocked=blocked,
            defense_name=self.name,
            original_prompt=prompt,
            original_response=response,
            filtered_response=filtered_response,
            confidence=max_harm,
            reason=(
                f"{n_harmful}/{len(verdicts)} steps flagged as harmful"
                if blocked
                else "All steps safe"
            ),
            metadata={
                "n_steps": len(verdicts),
                "n_harmful_steps": n_harmful,
                "max_harm_score": max_harm,
                "step_verdicts": [
                    {"idx": v.step_index, "safe": v.is_safe, "score": v.harm_score}
                    for v in verdicts
                ],
            },
        )

    # ------------------------------------------------------------------
    # Step segmentation
    # ------------------------------------------------------------------

    def _segment_steps(self, response: str) -> List[str]:
        """Split response into reasoning steps using configured delimiters."""
        # Combine all delimiter patterns
        combined = "|".join(f"({d})" for d in self.step_delimiters)
        parts = re.split(combined, response)
        # Filter out None and empty strings from split groups
        steps = [p.strip() for p in parts if p and p.strip()]
        # If no delimiters matched, treat sentences as steps
        if len(steps) <= 1:
            steps = re.split(r"(?<=[.!?])\s+", response)
        return [s for s in steps if len(s) > 10]  # skip tiny fragments

    # ------------------------------------------------------------------
    # Default keyword-based classifier
    # ------------------------------------------------------------------

    _HARM_KEYWORDS = {
        "high": [
            "detonate", "explosive", "weapon", "kill", "murder",
            "hack into", "steal credentials", "ransomware", "malware",
            "synthesize", "poison", "trafficking",
        ],
        "medium": [
            "bypass security", "exploit", "vulnerability",
            "unauthorized access", "social engineering",
            "phishing", "impersonate", "forge",
        ],
        "low": [
            "manipulate", "deceive", "mislead", "circumvent",
            "obfuscate", "evade detection",
        ],
    }

    @classmethod
    def _keyword_classifier(cls, text: str) -> float:
        """Simple keyword-based harm scorer."""
        text_lower = text.lower()
        score = 0.0
        for kw in cls._HARM_KEYWORDS["high"]:
            if kw in text_lower:
                score = max(score, 0.9)
        for kw in cls._HARM_KEYWORDS["medium"]:
            if kw in text_lower:
                score = max(score, 0.6)
        for kw in cls._HARM_KEYWORDS["low"]:
            if kw in text_lower:
                score = max(score, 0.3)
        return score
