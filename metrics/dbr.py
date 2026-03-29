"""
DBR — Defense Bypass Rate metric.

    DBR = #attacks_bypassing_defense / #total_attacks_with_defense

Measures the fraction of attacks that successfully jailbreak the target
even when a defense mechanism is active (Phase 3).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DBRMetric:
    """Running computation of Defense Bypass Rate."""

    _bypassed: int = 0
    _attacked: int = 0

    def update(self, attacked: bool, bypassed: bool) -> None:
        if attacked:
            self._attacked += 1
            if bypassed:
                self._bypassed += 1

    def compute(self) -> float:
        if self._attacked == 0:
            return 0.0
        return self._bypassed / self._attacked

    def reset(self) -> None:
        self._bypassed = 0
        self._attacked = 0

    def __repr__(self) -> str:
        return f"DBR({self._bypassed}/{self._attacked} = {self.compute():.2%})"
