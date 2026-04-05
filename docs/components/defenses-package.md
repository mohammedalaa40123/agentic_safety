# defenses Package

The defenses package contains concrete defense mechanisms and a shared registry.

## Files and roles

| File | Purpose |
| --- | --- |
| defenses/base.py | Defense base classes and result dataclass definitions. |
| defenses/registry.py | Ordered defense pipeline for prompt and response checks. |
| defenses/jbshield.py | Mutation/divergence prompt defense. |
| defenses/gradient_cuff.py | Gradient-based defense for local differentiable models. |
| defenses/progent.py | Privilege and policy constraints for tools and domains. |
| defenses/stepshield.py | Step-level harmfulness detection and blocking. |
| defenses/__init__.py | Package exports. |

## Registry behavior

- Prompt checks run for input, gradient, and multi-layer defenses.
- Response checks run for output and multi-layer defenses.
- First blocking defense short-circuits the pipeline.
