# Hybrid Attack Orchestration

!!! quote "Underlying Methods"
    The hybrid loop combines:

    - **PAIR** — Chao et al. (2023). *arXiv:2310.08419*. [arxiv.org/abs/2310.08419](https://arxiv.org/abs/2310.08419)
    - **Crescendo** — Russinovich et al. (2024). *arXiv:2404.01833*. [arxiv.org/abs/2404.01833](https://arxiv.org/abs/2404.01833)
    - **GCG** — Zou et al. (2023). *arXiv:2307.15043*. [arxiv.org/abs/2307.15043](https://arxiv.org/abs/2307.15043)

The **Hybrid Loop** (`attacks/hybrid_loop.py`) orchestrates multiple attack strategies in sequence, escalating from fast-and-cheap to slow-and-powerful.

## Orchestration Order

```yaml
attack_plan: [pair, crescendo, baseline]
```

1. **PAIR** is tried first — fast, low query cost.
2. If PAIR fails (judge score < threshold after max iterations), **Crescendo** is launched — multi-turn, higher cost.
3. If both fail, **baseline** direct prompting is used as a fallback.

The first successful attack short-circuits the chain.

## When to Use Hybrid

Use hybrid orchestration when:
- You want to measure which attack succeeds first per goal (for attack effectiveness comparison)
- You are running a full benchmark sweep and want maximum coverage

## Configuration

```yaml
--attack-plan pair crescendo baseline
```

Or in YAML config:

```yaml
attack_plan:
  - pair
  - crescendo
  - baseline
```

## Record Fields

Each `ExperimentRecord` produced by the hybrid loop includes:

- `attack_name`: the attack that produced the final result
- `iterations`: total iterations across all attempted strategies
- `queries`: total queries to the target model
- `fusion_strategy`: if prompt fusion was involved, the fusion variant used

→ [ExperimentRecord schema details](../evaluation/metrics.md)
