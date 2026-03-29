"""
Base class for defense mechanisms.

Each defense wraps around the target LLM pipeline and can:
  - Filter/modify incoming prompts (input-level defense)
  - Filter/modify outgoing responses (output-level defense)
  - Analyze gradient signals (gradient-level defense)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DefenseResult:
    """Result of applying a defense to a prompt/response pair."""
    blocked: bool
    defense_name: str
    original_prompt: str
    filtered_prompt: Optional[str] = None
    original_response: Optional[str] = None
    filtered_response: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class DefenseBase(ABC):
    """Abstract base for all defense mechanisms."""

    name: str = "base_defense"
    description: str = "Base defense — not directly usable."
    defense_layer: str = "input"  # "input", "output", "gradient", "multi-layer"

    @abstractmethod
    def filter_prompt(self, prompt: str, **kwargs) -> DefenseResult:
        """
        Analyze an incoming prompt and decide whether to block it.

        Returns
        -------
        DefenseResult with blocked=True/False and optional filtered_prompt.
        """
        raise NotImplementedError

    def filter_response(
        self, prompt: str, response: str, **kwargs
    ) -> DefenseResult:
        """
        Analyze a (prompt, response) pair and decide whether to block.
        Default: pass through (override for output-level defenses).
        """
        return DefenseResult(
            blocked=False,
            defense_name=self.name,
            original_prompt=prompt,
            original_response=response,
            filtered_response=response,
        )

    def analyze_gradients(self, grad_info: Dict[str, Any]) -> DefenseResult:
        """
        Analyze gradient information for adversarial signal detection.
        Default: pass through (override for gradient-level defenses).
        """
        return DefenseResult(
            blocked=False,
            defense_name=self.name,
            original_prompt="",
            reason="Gradient analysis not implemented for this defense.",
        )
