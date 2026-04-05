# System Overview

```mermaid
flowchart LR
    CLI[CLI args] --> CONFIG[runner/config.py]
    CONFIG --> MODE{mode}

    MODE -->|attack or baseline| ATTACKS[runner/attacks.py]
    MODE -->|agentic| LOOP[runner/agentic_loop.py]

    ATTACKS --> MODELS[runner/models.py]
    LOOP --> MODELS

    ATTACKS --> SANDBOX[runner/sandbox.py]
    LOOP --> SANDBOX
    SANDBOX --> TOOLS[tools/*]

    ATTACKS --> DEFENSES[runner/defenses.py]
    DEFENSES --> DEF_REG[defenses/registry.py]

    ATTACKS --> METRICS[metrics/collector.py]
    LOOP --> METRICS

    METRICS --> OUTPUTS[(CSV JSON Logs)]
```

## Architectural intent

- Keep orchestration thin in run.py.
- Delegate each concern to a runner module.
- Keep attacks, defenses, and tools independently extensible.
- Standardize outputs through a shared AttackOutcome and metrics collector.
