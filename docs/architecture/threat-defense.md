# Threat and Defense Model

```mermaid
flowchart TD
    INPUT[Goal prompt] --> PDEF[Prompt defenses]
    PDEF -->|blocked| BLOCK1[Prompt blocked]
    PDEF -->|pass| ATTACK[Attack or agentic planner]

    ATTACK --> TARGET[Target model]
    TARGET --> RESP[Model response]
    RESP --> RDEF[Response defenses]
    RDEF -->|blocked| BLOCK2[Response blocked]
    RDEF -->|pass| TOOL_DECISION{Tool call?}

    TOOL_DECISION -->|no| FINAL[Final response]
    TOOL_DECISION -->|yes| TDEF[Tool-call policy checks]
    TDEF -->|blocked| BLOCK3[Tool blocked]
    TDEF -->|pass| TOOL_EXEC[Sandbox tool execution]
    TOOL_EXEC --> FINAL
```

## Existing defense implementations

- JBShield: mutation/divergence-based prompt defense.
- Gradient Cuff: gradient-level signal defense for local differentiable models.
- Progent: privilege and policy controls, including tool and domain allowlists.
- StepShield: response-level harmfulness thresholding.

## Design principle

Defenses should fail safely and be composable in a deterministic registry order.
