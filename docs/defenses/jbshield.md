# JBShield

!!! quote "Original Paper"
    Zhang, X., He, Y., Dong, X., & Wang, X. (2024).
    **JBShield: Defending Large Language Models from Jailbreak Attacks through Activated Concept Analysis and Manipulation.**
    *arXiv:2412.12549*. [https://arxiv.org/abs/2412.12549](https://arxiv.org/abs/2412.12549)

JBShield is a **prompt-layer defense** that detects jailbreak attempts by measuring divergence between the original and mutated versions of a candidate prompt.

## Mechanism

1. The incoming prompt is mutated N times (paraphrase, synonym replacement, minor structural changes).
2. The target model scores each mutation for intent alignment.
3. If the divergence between mutation scores exceeds a threshold, the prompt is flagged as adversarial.

**Intuition**: Legitimate prompts remain coherent under paraphrasing. Adversarially crafted prompts often lose their effect when slightly rephrased.

## Configuration

```yaml
defenses:
  jbshield:
    n_mutations: 5
    divergence_threshold: 0.4
```

## Limitations

- Computationally expensive: requires N+1 forward passes per prompt.
- PAIR-crafted prompts that are semantically robust may still bypass.

→ Back to [Defenses Overview](index.md)
