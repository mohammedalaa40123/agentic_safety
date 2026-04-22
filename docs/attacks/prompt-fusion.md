# Prompt Fusion Attack

!!! quote "Related Work"
    This strategy builds on prompt ensemble and candidate selection ideas from:

    - Zou, A., Wang, Z., Kolter, J. Z., & Fredrikson, M. (2023).
      **Universal and Transferable Adversarial Attacks on Aligned Language Models.**
      *arXiv:2307.15043*. [https://arxiv.org/abs/2307.15043](https://arxiv.org/abs/2307.15043)

    - Chao, P. et al. (2023). **Jailbreaking Black Box LLMs in Twenty Queries (PAIR).**
      *arXiv:2310.08419*. [https://arxiv.org/abs/2310.08419](https://arxiv.org/abs/2310.08419)

**Prompt Fusion** generates multiple jailbreak candidates and combines the most effective elements into a single composite prompt.

## How Prompt Fusion Works

1. An attacker model generates N independent jailbreak candidate prompts (default N=5).
2. Each candidate is tested against the target model and scored by the judge.
3. The top-scoring candidates are **fused** — their strongest elements are extracted and combined by the attacker model into one composite prompt.
4. The composite is submitted as the final attack attempt.

## Fusion Strategies

The `fusion_strategy` field in results records the approach used:

| Strategy | Description |
|----------|-------------|
| `pair_standalone` | Standard PAIR without fusion |
| `fusion_top_k` | Fuse top-K scored candidates |
| `fusion_ensemble` | All candidates merged via attacker LLM |

## Configuration

```yaml
attacks:
  - prompt_fusion

attack_config:
  prompt_fusion:
    n_candidates: 5
    top_k: 2
    fusion_model: ollama:gemma4:31b  # separate model for fusion step
```

## Notes

- Implemented in `attacks/prompt_fusion.py`
- Small-N runs show near-100% MIR but sample sizes are too small for reliable benchmark comparison
- Not included in the strict PAIR mini-benchmark; used for supplementary analysis
