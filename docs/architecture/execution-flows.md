# Execution Flows

## Attack mode flow

```mermaid
sequenceDiagram
    participant U as User
    participant R as run.py
    participant A as runner.attacks
    participant T as target model
    participant J as judge model
    participant M as metrics.collector

    U->>R: run.py --config ...
    R->>A: build_attack_runners(...)
    loop each goal
        A->>T: generate target response
        A->>J: score response
        A->>M: record outcome
    end
    M-->>U: CSV/JSON summary
```

## Agentic mode flow

```mermaid
sequenceDiagram
    participant U as User
    participant R as run.py
    participant L as runner.agentic_loop
    participant T as target model
    participant S as AgenticSandbox
    participant X as tools
    participant M as metrics.collector

    U->>R: run.py --mode agentic
    R->>L: run_agentic_mode(...)
    loop until max_steps
        L->>T: chat with tool schema
        T-->>L: tool_call or final answer
        L->>S: execute_tool(name, args)
        S->>X: dispatch
        X-->>S: tool result
        S-->>L: observation
    end
    L->>M: record outcome and tool logs
    M-->>U: CSV/JSON summary
```

## Defense checkpoints

- Prompt-level filtering before model query.
- Response-level filtering after target generation.
- Optional tool-call checks in defense registry implementations.
