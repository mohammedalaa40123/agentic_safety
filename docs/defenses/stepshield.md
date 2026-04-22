# StepShield

!!! quote "Related Work"
    StepShield applies per-step response harmfulness scoring, conceptually related to:

    - Yuan, Z. et al. (2024).
      **ShieldLM: Empowering LLMs as Aligned, Customizable and Explainable Safety Detectors.**
      *arXiv:2402.16444*. [https://arxiv.org/abs/2402.16444](https://arxiv.org/abs/2402.16444)

    - Inan, H. et al. (2023).
      **Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations.**
      *arXiv:2312.06674*. [https://arxiv.org/abs/2312.06674](https://arxiv.org/abs/2312.06674)

StepShield is a **response-layer defense** that evaluates each model response against a harmfulness threshold before allowing it to proceed to tool dispatch.

## Mechanism

After the target model generates a response (but before any tool call is executed):

1. The response is scored by a lightweight harmfulness classifier or a judge model.
2. If the harmfulness score exceeds `threshold`, the response is blocked.
3. A blocked response prevents tool execution for that step.

**Intuition**: Multi-turn attacks rely on incremental compliance. StepShield catches each harmful step individually rather than waiting for the end of a trajectory.

## Configuration

```yaml
defenses:
  stepshield:
    threshold: 0.7           # harmfulness score cutoff (0–1)
    scorer: judge_model      # use the configured judge, or a local classifier
```

## Effect on Crescendo

StepShield is particularly effective against Crescendo because each escalation turn's response is evaluated before the next turn proceeds, preventing gradual compliance drift.

→ Back to [Defenses Overview](index.md)
