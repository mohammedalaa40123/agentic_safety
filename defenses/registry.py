"""
Defense Registry — manages multiple defense layers and runs them as a pipeline.

Supports:
  - Registering/removing defenses by name
  - Running all input-level defenses on a prompt
  - Running all output-level defenses on a response
  - Aggregating results across the defense stack
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base import DefenseBase, DefenseResult

logger = logging.getLogger(__name__)


class DefenseRegistry:
    """
    Pipeline manager for multiple defense mechanisms.

    Usage:
        registry = DefenseRegistry()
        registry.add(JBShieldDefense(...))
        registry.add(GradientCuffDefense(...))
        registry.add(ProgentDefense(...))
        registry.add(StepShieldDefense(...))

        # Input filtering
        result = registry.filter_prompt(prompt)
        if result.blocked:
            print(f"Blocked by {result.defense_name}: {result.reason}")

        # Output filtering
        result = registry.filter_response(prompt, response)
    """

    def __init__(self):
        self._defenses: Dict[str, DefenseBase] = {}

    def add(self, defense: DefenseBase) -> None:
        self._defenses[defense.name] = defense
        logger.info(f"Registered defense: {defense.name} ({defense.defense_layer})")

    def remove(self, name: str) -> None:
        self._defenses.pop(name, None)

    def list_defenses(self) -> List[str]:
        return list(self._defenses.keys())

    @property
    def defenses(self) -> Dict[str, "DefenseBase"]:
        """Read-only view of all registered defenses."""
        return dict(self._defenses)

    def filter_prompt(self, prompt: str, **kwargs) -> DefenseResult:
        """
        Run all input-level and gradient-level defenses on the prompt.
        Returns the first blocking result, or a pass-through if none block.
        """
        for name, defense in self._defenses.items():
            if defense.defense_layer in ("input", "gradient", "multi-layer", "representation"):
                result = defense.filter_prompt(prompt, **kwargs)
                if result.blocked:
                    logger.info(f"Prompt blocked by {name}: {result.reason}")
                    return result
        return DefenseResult(
            blocked=False,
            defense_name="registry",
            original_prompt=prompt,
            filtered_prompt=prompt,
            reason="All defenses passed",
        )

    def filter_response(
        self, prompt: str, response: str, **kwargs
    ) -> DefenseResult:
        """
        Run all output-level defenses on the (prompt, response) pair.
        Returns the first blocking result, or a pass-through if none block.
        """
        for name, defense in self._defenses.items():
            if defense.defense_layer in ("output", "multi-layer"):
                result = defense.filter_response(prompt, response, **kwargs)
                if result.blocked:
                    logger.info(f"Response blocked by {name}: {result.reason}")
                    return result
        return DefenseResult(
            blocked=False,
            defense_name="registry",
            original_prompt=prompt,
            original_response=response,
            filtered_response=response,
            reason="All defenses passed",
        )

    def check_tool_call(
        self, tool_name: str, args: Dict[str, Any]
    ) -> DefenseResult:
        """
        Check a tool invocation against any Progent-style defenses.
        """
        for name, defense in self._defenses.items():
            if hasattr(defense, "check_tool_call"):
                result = defense.check_tool_call(tool_name, args)
                if result.blocked:
                    logger.info(
                        f"Tool call {tool_name} blocked by {name}: {result.reason}"
                    )
                    return result
        return DefenseResult(
            blocked=False,
            defense_name="registry",
            original_prompt=f"tool_call:{tool_name}",
            reason="Tool call permitted by all defenses",
        )

    def run_all(
        self, prompt: str, response: Optional[str] = None, **kwargs
    ) -> List[DefenseResult]:
        """
        Run ALL defenses (not short-circuit) and return all results.
        Useful for comprehensive analysis/reporting.
        """
        results = []
        for name, defense in self._defenses.items():
            if defense.defense_layer in ("input", "gradient", "multi-layer", "representation"):
                results.append(defense.filter_prompt(prompt, **kwargs))
            if response and defense.defense_layer in ("output", "multi-layer"):
                results.append(
                    defense.filter_response(prompt, response, **kwargs)
                )
        return results
