"""
Prompt Fusion Engine — fuses GCG gradient-optimized tokens with PAIR semantic prompts.

Extends the simple midpoint-insertion approach in hybrid_jailbreak/main.py with
multiple fusion strategies: midpoint, prefix, suffix, interleave, and keyword-anchor.
"""

from __future__ import annotations

import sys
import os
import random
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# GCG / torch are optional heavy dependencies — imported lazily inside __init__
# so the module can always be imported even when they are not installed.
_GCG_AVAILABLE = False
GCGAttackPrompt = None  # type: ignore[assignment]
GCGPromptManager = None  # type: ignore[assignment]
token_gradients = None  # type: ignore[assignment]



class FusionStrategy(str, Enum):
    """Where to insert GCG-optimized tokens into a PAIR prompt."""
    MIDPOINT = "midpoint"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    INTERLEAVE = "interleave"
    KEYWORD_ANCHOR = "keyword_anchor"


@dataclass
class FusionResult:
    """Output of a single fusion operation."""
    fused_prompt: str
    pair_prompt: str
    gcg_tokens: str
    strategy: FusionStrategy
    gcg_loss: float = float("inf")


@dataclass
class FusionConfig:
    """Configuration for the Prompt Fusion Engine."""
    strategies: List[FusionStrategy] = field(
        default_factory=lambda: [FusionStrategy.MIDPOINT]
    )
    gcg_batch_size: int = 512
    gcg_topk: int = 256
    n_gcg_tokens: int = 1
    keyword_anchors: List[str] = field(
        default_factory=lambda: [
            "interface manual", "tutorial", "task", "process",
            "format", "algorithm", "scenario",
        ]
    )


class PromptFusionEngine:
    """
    Fuses GCG gradient-optimized adversarial tokens with PAIR-generated
    semantic jailbreak prompts using configurable strategies.

    Usage:
        engine = PromptFusionEngine(config, tokenizer, conv_template, model)
        results = engine.fuse(pair_prompts, goal, target_str)
    """

    def __init__(
        self,
        config: FusionConfig,
        tokenizer,
        conv_template,
        model,
    ):
        global _GCG_AVAILABLE, GCGAttackPrompt, GCGPromptManager, token_gradients
        self.config = config
        self.tokenizer = tokenizer
        self.conv_template = conv_template
        self.model = model

        # Lazy-load GCG + torch from the optional hybrid_jailbreak directory
        if not _GCG_AVAILABLE:
            try:
                import torch  # noqa: F401
                _HYBRID_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "hybrid_jailbreak")
                _HYBRID_DIR = os.path.abspath(_HYBRID_DIR)
                if _HYBRID_DIR not in sys.path:
                    sys.path.insert(0, _HYBRID_DIR)
                from gcg import GCGAttackPrompt as _GAP, GCGPromptManager as _GPM, token_gradients as _TG  # type: ignore
                GCGAttackPrompt = _GAP
                GCGPromptManager = _GPM
                token_gradients = _TG
                _GCG_AVAILABLE = True
                logger.info("GCG (hybrid_jailbreak) loaded successfully.")
            except (ImportError, ModuleNotFoundError) as exc:
                logger.warning(f"GCG not available ({exc}); PromptFusionEngine will fall back to PAIR-only mode.")

        # Build GCG prompt manager once
        self._pm: Optional[object] = None
        self._gcg_ready = _GCG_AVAILABLE

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fuse(
        self,
        pair_prompts: List[str],
        goal: str,
        target_str: str,
    ) -> List[FusionResult]:
        """
        For each PAIR prompt, compute GCG gradients and fuse optimal tokens
        using every configured strategy.  Returns the best fusion per prompt
        (lowest GCG loss).  Falls back to PAIR-only when GCG is not available.
        """
        # ── GCG-unavailable fallback ──────────────────────────────────────────
        if not self._gcg_ready:
            return [
                FusionResult(
                    fused_prompt=p,
                    pair_prompt=p,
                    gcg_tokens="",
                    strategy=self.config.strategies[0] if self.config.strategies else FusionStrategy.MIDPOINT,
                    gcg_loss=float("inf"),
                )
                for p in pair_prompts
            ]

        results: List[FusionResult] = []

        for prompt_text in pair_prompts:
            # 1. Build a GCG attack prompt for this (goal, target) pair
            attack_prompt = GCGAttackPrompt(
                target=target_str,
                goal=goal,
                tokenizer=self.tokenizer,
                conv_template=self.conv_template,
            )

            # 2. Compute token-level gradients w.r.t. the attack loss
            grad = attack_prompt.grad(self.model)

            # 3. Sample optimal adversarial token replacements
            if self._pm is None:
                self._pm = GCGPromptManager(
                    targets=[target_str],
                    goals=[goal],
                    tokenizer=self.tokenizer,
                    conv_template=self.conv_template,
                    managers={"AP": GCGAttackPrompt},
                )
            control_toks = self._pm.sample_control(
                grad,
                batch_size=self.config.gcg_batch_size,
                topk=self.config.gcg_topk,
            )
            # Take the first candidate (lowest-loss in a quick eval)
            gcg_token_str = self.tokenizer.decode(
                control_toks[0], skip_special_tokens=True
            )

            # 4. Apply every configured fusion strategy
            best: Optional[FusionResult] = None
            for strategy in self.config.strategies:
                fused = self._apply_strategy(
                    strategy, prompt_text, gcg_token_str
                )
                result = FusionResult(
                    fused_prompt=fused,
                    pair_prompt=prompt_text,
                    gcg_tokens=gcg_token_str,
                    strategy=strategy,
                )
                # Pick the first strategy result as best (extend later
                # with loss-based ranking when batch eval is available)
                if best is None:
                    best = result
            results.append(best)

        return results

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _apply_strategy(
        self, strategy: FusionStrategy, prompt: str, gcg_tokens: str
    ) -> str:
        if strategy == FusionStrategy.MIDPOINT:
            return self._fuse_midpoint(prompt, gcg_tokens)
        elif strategy == FusionStrategy.PREFIX:
            return self._fuse_prefix(prompt, gcg_tokens)
        elif strategy == FusionStrategy.SUFFIX:
            return self._fuse_suffix(prompt, gcg_tokens)
        elif strategy == FusionStrategy.INTERLEAVE:
            return self._fuse_interleave(prompt, gcg_tokens)
        elif strategy == FusionStrategy.KEYWORD_ANCHOR:
            return self._fuse_keyword_anchor(prompt, gcg_tokens)
        else:
            raise ValueError(f"Unknown fusion strategy: {strategy}")

    @staticmethod
    def _fuse_midpoint(prompt: str, gcg_tokens: str) -> str:
        """Insert GCG tokens at the midpoint of the PAIR prompt."""
        mid = len(prompt) // 2
        return prompt[:mid] + f" {gcg_tokens} " + prompt[mid:]

    @staticmethod
    def _fuse_prefix(prompt: str, gcg_tokens: str) -> str:
        """Prepend GCG tokens before the PAIR prompt."""
        return f"{gcg_tokens} {prompt}"

    @staticmethod
    def _fuse_suffix(prompt: str, gcg_tokens: str) -> str:
        """Append GCG tokens after the PAIR prompt."""
        return f"{prompt} {gcg_tokens}"

    @staticmethod
    def _fuse_interleave(prompt: str, gcg_tokens: str) -> str:
        """
        Split prompt into sentences and interleave GCG tokens between them.
        """
        import re
        sentences = re.split(r"(?<=[.!?])\s+", prompt)
        if len(sentences) <= 1:
            # Fallback to midpoint
            return PromptFusionEngine._fuse_midpoint(prompt, gcg_tokens)
        # Insert GCG tokens after every other sentence
        parts = []
        for i, sent in enumerate(sentences):
            parts.append(sent)
            if i % 2 == 0 and i < len(sentences) - 1:
                parts.append(gcg_tokens)
        return " ".join(parts)

    def _fuse_keyword_anchor(self, prompt: str, gcg_tokens: str) -> str:
        """
        Insert GCG tokens after the first matching keyword anchor found
        in the PAIR prompt.  Falls back to midpoint if no keyword matches.
        """
        token_parts = gcg_tokens.split()
        new_prompt = prompt
        inserted = 0
        for kw in self.config.keyword_anchors:
            if inserted >= len(token_parts):
                break
            if kw in new_prompt:
                pos = new_prompt.index(kw) + len(kw)
                new_prompt = (
                    new_prompt[:pos]
                    + f" {{ {token_parts[inserted]} }} "
                    + new_prompt[pos:]
                )
                inserted += 1
        # Append any remaining token parts
        if inserted < len(token_parts):
            leftover = " ".join(f"{{ {t} }}" for t in token_parts[inserted:])
            new_prompt += " " + leftover
        return new_prompt
