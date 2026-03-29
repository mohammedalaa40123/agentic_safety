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
