# Attacks

!!! quote "Key References"
    - **PAIR** — Chao et al. (2023). *arXiv:2310.08419*. [arxiv.org/abs/2310.08419](https://arxiv.org/abs/2310.08419)
    - **Crescendo** — Russinovich et al. (2024). *arXiv:2404.01833*. [arxiv.org/abs/2404.01833](https://arxiv.org/abs/2404.01833)
    - **GCG** — Zou et al. (2023). *arXiv:2307.15043*. [arxiv.org/abs/2307.15043](https://arxiv.org/abs/2307.15043)
    - **OWASP Agentic AI Top-10** — [genai.owasp.org](https://genai.owasp.org/)

This framework implements four attack strategies, each targeting the agentic pipeline at different points and with different optimization assumptions.


## Attack Taxonomy

| Attack | Strategy | Key Assumption | Typical MIR |
|--------|----------|----------------|-------------|
| **PAIR** | LLM-as-attacker iterative refinement | Attacker LLM judges and improves prompts | 66–84% (PAIR core benchmark) |
| **Crescendo** | Multi-turn escalation | Small incremental steps bypass per-turn detection | 88–100% |
| **Prompt Fusion** | Candidate combination | Multiple jailbreak candidates fused into strong composite | ~100% (small-N) |
| **GCG** | Gradient-based suffix optimization | White-box access to target gradients | Local models only |

## Implementation Files

| File | Purpose |
|------|---------|
| `attacks/pair.py` | PAIR attack loop and judge prompt handling |
| `attacks/crescendo.py` | Multi-turn escalation strategy |
| `attacks/prompt_fusion.py` | Candidate generation and fusion |
| `attacks/gcg.py` | GCG suffix optimization integration |
| `attacks/hybrid_loop.py` | Orchestrated combination of all strategies |
| `attacks/__init__.py` | Registry exports |

## Threat Reference

The `attacks/Agentic-AI-Top10-Vulnerability/` folder contains 16 markdown vulnerability references plus README — the original source material mapping attack implementations to the OWASP Agentic AI Top-10.

→ [PAIR details](pair.md)  
→ [Crescendo details](crescendo.md)  
→ [Prompt Fusion details](prompt-fusion.md)  
→ [Hybrid orchestration](hybrid.md)
