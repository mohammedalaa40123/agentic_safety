"""
Progent Defense — policy-guided agentic safety guardrails.

Reference: Progent (2025), "Programmable Privilege Control for LLM Agents."

Progent operates at the action/tool level by:
  1. Defining a privilege policy (which tools/actions are allowed)
  2. Intercepting tool calls before execution
  3. Blocking calls that violate the policy
  4. Optionally escalating to a human-in-the-loop for ambiguous cases
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .base import DefenseBase, DefenseResult

logger = logging.getLogger(__name__)


@dataclass
class PrivilegePolicy:
    """
    Defines what an agentic LLM is allowed to do.
    """
    allowed_tools: Set[str] = field(default_factory=lambda: {"file_io", "web_browse"})
    blocked_tools: Set[str] = field(default_factory=lambda: {"network"})
    max_tool_calls_per_turn: int = 3
    file_read_only: bool = True
    allowed_domains: Set[str] = field(
        default_factory=lambda: {"example.com", "wikipedia.org"}
    )
    blocked_code_patterns: List[str] = field(
        default_factory=lambda: [
            r"subprocess\.", r"os\.system", r"socket\.",
            r"shutil\.rmtree", r"rm\s+-rf",
        ]
    )


class ProgentDefense(DefenseBase):
    """
    Policy-guided privilege control for agentic LLMs.

    Intercepts tool invocations and blocks those that violate
    the configured privilege policy.
    """

    name = "progent"
    description = "Policy-guided agentic guardrails (Progent)"
    defense_layer = "multi-layer"

    def __init__(self, policy: Optional[PrivilegePolicy] = None):
        self.policy = policy or PrivilegePolicy()
        self._call_count = 0

    def filter_prompt(self, prompt: str, **kwargs) -> DefenseResult:
        """
        Input-level check: scan prompt for indications of policy violations.
        """
        violations = []
        for pattern in self.policy.blocked_code_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                violations.append(f"Blocked code pattern: {pattern}")

        is_blocked = len(violations) > 0
        return DefenseResult(
            blocked=is_blocked,
            defense_name=self.name,
            original_prompt=prompt,
            filtered_prompt=prompt if not is_blocked else "[BLOCKED BY PROGENT]",
            reason="; ".join(violations) if violations else "No policy violations",
            metadata={"violations": violations},
        )

    def check_tool_call(
        self, tool_name: str, args: Dict[str, Any]
    ) -> DefenseResult:
        """
        Check whether a tool invocation is permitted under the policy.

        Parameters
        ----------
        tool_name : str
        args : dict — tool arguments

        Returns
        -------
        DefenseResult with blocked=True if the call violates policy.
        """
        self._call_count += 1
        violations = []

        # Check tool allowlist/blocklist
        if tool_name in self.policy.blocked_tools:
            violations.append(f"Tool '{tool_name}' is blocked by policy")
        if self.policy.allowed_tools and tool_name not in self.policy.allowed_tools:
            violations.append(f"Tool '{tool_name}' not in allowed set")

        # Rate limiting
        if self._call_count > self.policy.max_tool_calls_per_turn:
            violations.append(
                f"Tool call limit exceeded ({self._call_count}/"
                f"{self.policy.max_tool_calls_per_turn})"
            )

        # File write restriction
        if tool_name == "file_io" and self.policy.file_read_only:
            if args.get("action") == "write":
                violations.append("File write blocked (read-only policy)")

        # Domain restriction for web browsing
        if tool_name == "web_browse":
            url = args.get("url", "")
            domain_ok = any(d in url for d in self.policy.allowed_domains)
            if not domain_ok:
                violations.append(f"Domain not in allowlist: {url}")

        # Code execution pattern check
        if tool_name == "code_exec":
            code = args.get("code", "")
            for pattern in self.policy.blocked_code_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    violations.append(f"Blocked code pattern: {pattern}")

        is_blocked = len(violations) > 0
        return DefenseResult(
            blocked=is_blocked,
            defense_name=self.name,
            original_prompt=f"tool_call:{tool_name}",
            reason="; ".join(violations) if violations else "Tool call permitted",
            confidence=1.0 if is_blocked else 0.0,
            metadata={
                "tool_name": tool_name,
                "args": args,
                "violations": violations,
                "call_count": self._call_count,
            },
        )

    def reset_turn(self) -> None:
        """Reset per-turn counters (call at start of each new user turn)."""
        self._call_count = 0
