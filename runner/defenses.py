import logging
from typing import Any, Callable, Optional

from defenses.registry import DefenseRegistry
from defenses.jbshield import JBShieldDefense
from defenses.gradient_cuff import GradientCuffDefense
from defenses.progent import ProgentDefense, PrivilegePolicy
from defenses.stepshield import StepShieldDefense

from .config import DefenseConfig

logger = logging.getLogger(__name__)


def build_defense_registry(cfg: DefenseConfig, target_fn: Optional[Callable[[str], str]] = None,
                           target_model: Any = None, target_tokenizer: Any = None) -> Optional[DefenseRegistry]:
    if not cfg.enabled:
        return None

    registry = DefenseRegistry()

    if "jbshield" in cfg.active:
        jbs_cfg = cfg.jbshield or {}
        registry.add(JBShieldDefense(
            n_mutations=jbs_cfg.get("n_mutations", 5),
            divergence_threshold=jbs_cfg.get("divergence_threshold", jbs_cfg.get("refusal_threshold", 0.6)),
            target_fn=target_fn,
        ))

    if "gradient_cuff" in cfg.active:
        gc_cfg = cfg.gradient_cuff or {}
        registry.add(GradientCuffDefense(
            model=target_model,
            tokenizer=target_tokenizer,
            threshold=gc_cfg.get("threshold", 10.0),
        ))

    if "progent" in cfg.active:
        prog_cfg = cfg.progent or {}
        policy = PrivilegePolicy(
            allowed_tools=set(prog_cfg.get("allowed_tools", ["file_io", "web_browse"])),
            blocked_tools=set(prog_cfg.get("blocked_tools", [])),
            max_tool_calls_per_turn=prog_cfg.get("rate_limit", prog_cfg.get("max_tool_calls_per_turn", 10)),
            allowed_domains=set(prog_cfg.get("domain_allowlist", prog_cfg.get("allowed_domains", []))),
            blocked_code_patterns=prog_cfg.get("block_code_patterns", prog_cfg.get("blocked_code_patterns", [
                r"import\s+subprocess", r"os\.system", r"eval\(", r"exec\(",
            ])),
        )
        registry.add(ProgentDefense(policy=policy))

    if "stepshield" in cfg.active:
        ss_cfg = cfg.stepshield or {}
        registry.add(StepShieldDefense(
            harm_threshold=ss_cfg.get("harm_threshold", 0.7),
        ))

    return registry
