# Gradient Cuff

Gradient Cuff is a **prompt-layer defense** for locally-hosted differentiable models that detects adversarial prompts by monitoring gradient signal anomalies.

## Mechanism

For a locally hosted model:
1. Compute the gradient of the loss with respect to the input token embeddings.
2. Measure the gradient norm against a calibrated threshold for benign inputs.
3. If the norm exceeds the threshold, flag the input as adversarial.

**Intuition**: Adversarially optimized prefixes (e.g., GCG suffixes) create characteristic high-gradient signals because they are specifically tuned to steer the loss surface.

## Applicability

!!! warning "Local models only"
    Gradient Cuff requires access to model gradients. It does not apply to API-backed models (OpenAI, Gemini, Anthropic, Genai/RCAC).

## Configuration

```yaml
defenses:
  gradient_cuff:
    gradient_threshold: 2.5
    norm_type: l2
```

→ Back to [Defenses Overview](index.md)
