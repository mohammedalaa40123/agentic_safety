"""
AgentShield Defense — classifier + policy guard for agentic jailbreak resistance.

Design goals:
  1) Stable across target LLM families (Qwen/Llama/GenAI APIs)
  2) Block high-risk prompts before generation
  3) Predict and block risky tool calls before execution
  4) Work offline with heuristic fallback if HF model load fails

Recommended classifier model:
  - protectai/deberta-v3-base-prompt-injection-v2
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set

from .base import DefenseBase, DefenseResult

logger = logging.getLogger(__name__)


@dataclass
class AgentShieldPolicy:
    """Configurable policy knobs for prompt and tool-call risk gating."""

    model_id: str = "protectai/deberta-v3-base-prompt-injection-v2"
    prompt_block_threshold: float = 0.70
    tool_block_threshold: float = 0.65
    use_classifier: bool = True
    classifier_max_length: int = 512
    blocked_tools: Set[str] = field(default_factory=lambda: {"network"})
    strict_tools: Set[str] = field(default_factory=lambda: {"code_exec", "network"})
    allowed_domains: Set[str] = field(default_factory=set)
    blocked_domains: Set[str] = field(default_factory=lambda: {".onion", "pastebin.com", "exploit-db"})


class AgentShieldDefense(DefenseBase):
    """
    Agent-focused safety layer with two stages:
      - Prompt risk scoring
      - Tool-call risk scoring (before execution)
    """

    name = "agentshield"
    description = "Classifier + policy-based jailbreak and tool-call guard"
    defense_layer = "multi-layer"

    _RISKY_PATTERNS: Sequence[str] = (
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"developer\s+mode",
        r"jailbreak",
        r"authorization\s+override",
        r"bypass\s+(safety|policy|guardrail)",
        r"exfiltrat(e|ion)",
        r"(rm\s+-rf|shutil\.rmtree)",
        r"(subprocess\.|os\.system|eval\(|exec\()",
        r"(steal\s+credentials|credential\s+dump)",
        r"(port\s*scan|reverse\s+shell|payload)",
    )

    _BAD_LABEL_HINTS: Sequence[str] = (
        "injection",
        "jailbreak",
        "malicious",
        "attack",
        "unsafe",
        "harm",
    )

    _GOOD_LABEL_HINTS: Sequence[str] = (
        "legit",
        "benign",
        "safe",
        "normal",
        "clean",
    )

    def __init__(self, policy: Optional[AgentShieldPolicy] = None):
        self.policy = policy or AgentShieldPolicy()
        self._classifier = None
        self._classifier_failed = False

    def _lazy_load_classifier(self):
        if not self.policy.use_classifier:
            return None
        if self._classifier is not None:
            return self._classifier
        if self._classifier_failed:
            return None
        try:
            import torch  # noqa: F401 — must be available for transformers pipeline
            from transformers import pipeline

            self._classifier = pipeline(
                task="text-classification",
                model=self.policy.model_id,
                truncation=True,
            )
            logger.info("AgentShield classifier loaded: %s", self.policy.model_id)
            return self._classifier
        except (ImportError, NameError) as exc:
            logger.warning(
                "AgentShield: torch/transformers not available (%s). Using heuristics only.",
                exc,
            )
            self._classifier_failed = True
            return None
        except Exception as exc:
            logger.warning(
                "AgentShield classifier load failed (%s). Using heuristics only.",
                exc,
            )
            self._classifier_failed = True
            return None

    @classmethod
    def _heuristic_prompt_risk(cls, text: str) -> float:
        t = (text or "").lower()
        hits = sum(1 for pat in cls._RISKY_PATTERNS if re.search(pat, t, re.IGNORECASE))
        if hits == 0:
            return 0.0
        # Saturating score: 1 hit ~0.30, 2 hits ~0.50, 3+ approaches 1.0
        return min(1.0, 1.0 - (0.7 ** hits))

    def _classifier_prompt_risk(self, text: str) -> float:
        clf = self._lazy_load_classifier()
        if clf is None:
            return 0.0
        try:
            out = clf(
                text,
                top_k=None,
                truncation=True,
                max_length=self.policy.classifier_max_length,
            )
            if isinstance(out, list) and out and isinstance(out[0], list):
                out = out[0]
            bad = 0.0
            good = 0.0
            for row in out or []:
                label = str(row.get("label", "")).lower()
                score = float(row.get("score", 0.0))
                if any(h in label for h in self._BAD_LABEL_HINTS):
                    bad = max(bad, score)
                if any(h in label for h in self._GOOD_LABEL_HINTS):
                    good = max(good, score)
            # If labels are unknown, use top confidence as weak signal.
            if bad == 0.0 and out:
                top = max((float(r.get("score", 0.0)) for r in out), default=0.0)
                bad = 0.35 * top
            if good > 0.0:
                bad = max(0.0, bad - 0.25 * good)
            return min(1.0, max(0.0, bad))
        except Exception as exc:
            logger.debug("AgentShield classifier inference failed: %s", exc)
            return 0.0

    def _score_prompt_risk(self, text: str) -> Dict[str, float]:
        h = self._heuristic_prompt_risk(text)
        c = self._classifier_prompt_risk(text)
        # Heuristic has lower weight when classifier is available.
        total = 0.35 * h + 0.65 * c if c > 0 else h
        return {"heuristic": h, "classifier": c, "total": min(1.0, total)}

    def filter_prompt(self, prompt: str, **kwargs) -> DefenseResult:
        scores = self._score_prompt_risk(prompt)
        blocked = scores["total"] >= self.policy.prompt_block_threshold
        reason = (
            f"Prompt risk {scores['total']:.2f} >= threshold {self.policy.prompt_block_threshold:.2f}"
            if blocked
            else f"Prompt risk {scores['total']:.2f} < threshold {self.policy.prompt_block_threshold:.2f}"
        )
        return DefenseResult(
            blocked=blocked,
            defense_name=self.name,
            original_prompt=prompt,
            filtered_prompt=prompt if not blocked else "[BLOCKED BY AGENTSHIELD]",
            confidence=scores["total"],
            reason=reason,
            metadata={"scores": scores},
        )

    def _tool_policy_risk(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        reasons: List[str] = []
        risk = 0.0

        tname = (tool_name or "").strip().lower()
        if tname in self.policy.blocked_tools:
            reasons.append(f"Tool '{tname}' is blocked by policy")
            risk = max(risk, 1.0)

        if tname in self.policy.strict_tools:
            risk = max(risk, 0.45)
            reasons.append(f"Tool '{tname}' is high-risk and requires stricter threshold")

        if tname == "file_io":
            action = str(args.get("action", "")).lower()
            path = str(args.get("path", ""))
            if action == "write":
                risk = max(risk, 0.55)
                reasons.append("File write attempt")
            if re.search(r"(\.ssh|\.env|credentials|secret|/etc/)", path, re.IGNORECASE):
                risk = max(risk, 0.9)
                reasons.append("Sensitive file path pattern")

        if tname == "code_exec":
            code = str(args.get("code", ""))
            if re.search(r"(subprocess\.|os\.system|eval\(|exec\()", code, re.IGNORECASE):
                risk = max(risk, 0.95)
                reasons.append("Dangerous code execution primitive")
            if re.search(r"(socket|requests|httpx|wget|curl)", code, re.IGNORECASE):
                risk = max(risk, 0.75)
                reasons.append("Network-capable execution in code_exec")

        if tname in {"web_browse", "network"}:
            url = str(args.get("url", ""))
            host = str(args.get("host", ""))
            target = (url or host).lower()
            if target:
                for blocked in self.policy.blocked_domains:
                    if blocked and blocked.lower() in target:
                        risk = max(risk, 0.95)
                        reasons.append(f"Blocked domain pattern: {blocked}")
                if self.policy.allowed_domains:
                    if not any(d.lower() in target for d in self.policy.allowed_domains):
                        risk = max(risk, 0.75)
                        reasons.append("Domain not in allowlist")
            if tname == "network" and str(args.get("action", "")).lower() in {"port_scan", "connect"}:
                risk = max(risk, 0.9)
                reasons.append("Active network probing action")

        return {"risk": min(1.0, risk), "reasons": reasons}

    def check_tool_call(self, tool_name: str, args: Dict[str, Any]) -> DefenseResult:
        tool_name = str(tool_name or "")
        args = args or {}
        call_blob = json.dumps({"tool": tool_name, "args": args}, ensure_ascii=True)
        prompt_scores = self._score_prompt_risk(call_blob)
        policy_scores = self._tool_policy_risk(tool_name, args)

        # For tool calls, policy risk dominates, classifier gives additional evidence.
        total = min(1.0, 0.7 * policy_scores["risk"] + 0.3 * prompt_scores["total"])
        blocked = total >= self.policy.tool_block_threshold

        reasons = list(policy_scores["reasons"])
        if prompt_scores["total"] >= self.policy.tool_block_threshold:
            reasons.append("Classifier/heuristic sees injection-like tool payload")
        if not reasons:
            reasons.append("Tool call within configured risk budget")

        return DefenseResult(
            blocked=blocked,
            defense_name=self.name,
            original_prompt=f"tool_call:{tool_name}",
            confidence=total,
            reason=(
                f"Tool risk {total:.2f} >= threshold {self.policy.tool_block_threshold:.2f}; "
                + "; ".join(reasons)
                if blocked
                else f"Tool risk {total:.2f} < threshold {self.policy.tool_block_threshold:.2f}"
            ),
            metadata={
                "tool_name": tool_name,
                "args": args,
                "prompt_scores": prompt_scores,
                "policy_risk": policy_scores,
                "threshold": self.policy.tool_block_threshold,
            },
        )
