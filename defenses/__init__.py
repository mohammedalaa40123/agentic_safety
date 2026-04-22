__all__ = [
    "DefenseBase",
    "AgentShieldDefense",
    "JBShieldDefense",
    "GradientCuffDefense",
    "ProgentDefense",
    "StepShieldDefense",
    "ContextGuardDefense",
    "DefenseRegistry",
]


def __getattr__(name):
    if name == "DefenseBase":
        from .base import DefenseBase as _DefenseBase

        return _DefenseBase
    if name == "AgentShieldDefense":
        from .agentshield import AgentShieldDefense as _AgentShieldDefense

        return _AgentShieldDefense
    if name == "JBShieldDefense":
        from .jbshield import JBShieldDefense as _JBShieldDefense

        return _JBShieldDefense
    if name == "GradientCuffDefense":
        from .gradient_cuff import GradientCuffDefense as _GradientCuffDefense

        return _GradientCuffDefense
    if name == "ProgentDefense":
        from .progent import ProgentDefense as _ProgentDefense

        return _ProgentDefense
    if name == "StepShieldDefense":
        from .stepshield import StepShieldDefense as _StepShieldDefense

        return _StepShieldDefense
    if name == "ContextGuardDefense":
        from .contextguard import ContextGuardDefense as _ContextGuardDefense

        return _ContextGuardDefense
    if name == "DefenseRegistry":
        from .registry import DefenseRegistry as _DefenseRegistry

        return _DefenseRegistry
    raise AttributeError(f"module 'defenses' has no attribute {name!r}")
