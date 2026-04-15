"""Attack package exports.

Keep package import lightweight so consumers like ``from attacks.pair import ...``
do not pull optional heavy dependencies (for example torch from prompt_fusion)
at interpreter startup.
"""

__all__ = ["PromptFusionEngine", "CrescendoAttack", "HybridAttackLoop"]


def __getattr__(name):
	if name == "PromptFusionEngine":
		from .prompt_fusion import PromptFusionEngine as _PromptFusionEngine

		return _PromptFusionEngine
	if name == "CrescendoAttack":
		from .crescendo import CrescendoAttack as _CrescendoAttack

		return _CrescendoAttack
	if name == "HybridAttackLoop":
		from .hybrid_loop import HybridAttackLoop as _HybridAttackLoop

		return _HybridAttackLoop
	raise AttributeError(f"module 'attacks' has no attribute {name!r}")
