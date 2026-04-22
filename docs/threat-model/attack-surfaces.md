# Attack Surfaces

## The Three-Layer Attack Surface

Agentic pipelines expose three distinct attack surfaces, each requiring different mitigations:

### 1. Input / Prompt Surface

The attacker shapes the **initial prompt or system context** to steer the planner.

- **Direct injection**: Malicious goal provided as a user message
- **Context smuggling**: Adversarial payload hidden in an upstream document or retrieved memory chunk
- **Role-hijacking**: Injected "system" or "assistant" turn fragments that override instructions

**Defenses active here**: JBShield (mutation/divergence detection), Gradient Cuff (gradient signal)

---

### 2. Model Response Surface

After the target model generates a response, the response itself may contain harmful content or unauthorized tool-call instructions before defenses execute.

- **Jailbreak response**: Direct harmful text output
- **Encoded harmful calls**: Tool invocations that appear benign but carry adversarial payloads
- **Incremental Crescendo**: Each response moves the model one step further into compliance

**Defenses active here**: StepShield (per-response harmfulness scoring)

---

### 3. Tool Execution Surface

Agentic models dispatch tool calls that interact with the real environment:

| Tool | Abuse Example |
|------|---------------|
| `file_io` | Read `/etc/shadow`, write backdoors |
| `code_exec` | Execute arbitrary shell or Python |
| `web_browse` | Exfiltrate data, download malware |
| `network` | Send data to attacker-controlled server |

**Defenses active here**: Progent policy controls, sandbox isolation, tool allowlists

---

## Attack Strategy vs Surface Coverage

| Attack | Prompt | Response | Tool |
|--------|--------|----------|------|
| PAIR | ✅ Primary | ✅ Judged | ✅ Via tool calls |
| Crescendo | ✅ Multi-turn | ✅ Each turn | ✅ Via progressions |
| Prompt Fusion | ✅ Fused payloads | ✅ | ⚠️ Indirect |
| GCG | ✅ Suffix-optimized | ✅ | ⚠️ Indirect |

→ [Attack details →](../attacks/index.md)
