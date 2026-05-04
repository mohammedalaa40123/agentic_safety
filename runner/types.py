from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AttackOutcome:
    goal: str
    category: str
    attack_name: str
    success: bool
    task_success: bool
    queries: int
    iterations: int
    duration: float
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    fusion_strategy: Optional[str] = None
    jailbreak_prompt: Optional[str] = None
    jailbreak_response: Optional[str] = None
    correct_tool_calls: int = 0
    wrong_tool_calls: int = 0
    stages: List[Dict[str, Any]] = field(default_factory=list)
    defense_response: Optional[str] = None
    gcg_suffix: Optional[str] = None

    # --- Three-tier correctness (Phase 2: addresses reviewer W2) ---
    intent_compliance: Optional[bool] = None     # L1: judge-based intent
    tool_engagement: Optional[bool] = None       # L2: correct tool invoked
    execution_success: Optional[bool] = None     # L3: tool succeeded + harmful

    # --- Multi-judge evaluation (Phase 1: addresses reviewer W1) ---
    judge_scores: List[int] = field(default_factory=list)      # per-judge scores
    judge_agreement: Optional[float] = None                    # inter-judge κ
    majority_jailbroken: Optional[bool] = None                 # majority vote

