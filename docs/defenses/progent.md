# Progent

!!! quote "Original Paper"
    Jia, Z., Shi, P., Pan, L., Gong, N. Z., & Lyu, C. (2025).
    **Progent: Programmable Privilege Control for LLM Agents.**
    *arXiv:2504.11703*. [https://arxiv.org/abs/2504.11703](https://arxiv.org/abs/2504.11703)

Progent is a **tool-layer defense** that enforces privilege policy and access controls on tool invocations.

## Mechanism

Progent maintains a registry of:
- **Allowed tools** per execution context
- **Domain allowlists** for `web_browse` and `network` tools
- **Privilege levels** per tool (e.g., `file_io` restricted to `/tmp/` sandbox)

Before any tool call is dispatched to the sandbox, Progent checks:
1. Is this tool in the allowed set for this execution context?
2. If the call targets a path or URL, is it within the allowlisted scope?
3. Does the principal (agent) have sufficient privilege for this tool?

If any check fails, the tool call is blocked and logged as a `defense_bypassed=False` record.

## Configuration

```yaml
defenses:
  progent:
    allowed_tools:
      - file_io
      - code_exec
    file_io:
      allowed_paths:
        - /tmp/sandbox/
    network:
      allowed_domains:
        - "*.example.com"
```

## Integration with Sandbox

Progent is the last policy gate before the sandbox executes. Sandbox isolation provides additional OS-level containment, but Progent operates at the agent-policy layer.

→ [Sandbox isolation details](../deployment/sandboxing.md)  
→ Back to [Defenses Overview](index.md)
