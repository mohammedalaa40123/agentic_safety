import logging
from typing import Any, Callable, Optional

from defenses.registry import DefenseRegistry

from .config import DefenseConfig

logger = logging.getLogger(__name__)


def build_defense_registry(cfg: DefenseConfig, target_fn: Optional[Callable[[str], str]] = None,
                           target_model: Any = None, target_tokenizer: Any = None) -> Optional[DefenseRegistry]:
    if not cfg.enabled:
        return None

    registry = DefenseRegistry()

    if "agentshield" in cfg.active:
        from defenses.agentshield import AgentShieldDefense, AgentShieldPolicy

        ash_cfg = cfg.agentshield or {}
        policy = AgentShieldPolicy(
            model_id=ash_cfg.get("model_id", "protectai/deberta-v3-base-prompt-injection-v2"),
            prompt_block_threshold=ash_cfg.get("prompt_block_threshold", 0.70),
            tool_block_threshold=ash_cfg.get("tool_block_threshold", 0.65),
            use_classifier=ash_cfg.get("use_classifier", True),
            classifier_max_length=ash_cfg.get("classifier_max_length", 512),
            blocked_tools=set(ash_cfg.get("blocked_tools", ["network"])),
            strict_tools=set(ash_cfg.get("strict_tools", ["code_exec", "network"])),
            allowed_domains=set(ash_cfg.get("allowed_domains", [])),
            blocked_domains=set(ash_cfg.get("blocked_domains", [".onion", "pastebin.com", "exploit-db"])),
        )
        registry.add(AgentShieldDefense(policy=policy))

    if "jbshield" in cfg.active:
        from defenses.jbshield import JBShieldDefense

        jbs_cfg = cfg.jbshield or {}
        registry.add(JBShieldDefense(
            threshold=jbs_cfg.get("threshold", jbs_cfg.get("divergence_threshold", jbs_cfg.get("refusal_threshold", 0.0))),
        ))

    if "gradient_cuff" in cfg.active:
        from defenses.gradient_cuff import GradientCuffDefense

        gc_cfg = cfg.gradient_cuff or {}
        registry.add(GradientCuffDefense(
            model_fn=target_fn,
            model=target_model,
            tokenizer=target_tokenizer,
            grad_norm_threshold=gc_cfg.get("grad_norm_threshold", gc_cfg.get("threshold", 50.0)),
        ))

    if "progent" in cfg.active:
        from defenses.progent import ProgentDefense, PrivilegePolicy

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
        from defenses.stepshield import StepShieldDefense

        ss_cfg = cfg.stepshield or {}
        registry.add(StepShieldDefense(
            harm_threshold=ss_cfg.get("harm_threshold", 0.7),
        ))

    if "contextguard" in cfg.active:
        from defenses.contextguard import ContextGuardDefense

        cg_cfg = cfg.contextguard or {}
        # Use the target_fn (judge/extractor LLM) passed into build_defense_registry
        extractor = target_fn if target_fn is not None else (lambda p: "")
        registry.add(ContextGuardDefense(
            extractor_fn=extractor,
            deny_patterns=cg_cfg.get("deny_patterns") or None,
            block_high_risk=cg_cfg.get("block_high_risk", True),
            model_name=cg_cfg.get("model_name", "contextguard-extractor"),
        ))

    return registry
