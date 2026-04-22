# Defenses

This framework provides four defense implementations that operate at different points in the agentic pipeline:

## Defense Layers

```
Prompt → [JBShield / GradCuff] → Planner → Target LLM → [StepShield] → Tool Decision → [Progent]
```

| Defense | Layer | Mechanism |
|---------|-------|-----------|
| **JBShield** | Prompt | Mutation/divergence detection |
| **Gradient Cuff** | Prompt | Gradient signal anomaly (local models only) |
| **StepShield** | Response | Per-response harmfulness thresholding |
| **Progent** | Tool | Privilege policy and allowlist enforcement |

## Composability

Defenses are activated in deterministic registry order and are independently composable:

```bash
python run.py \
  --config configs/eval_qwen_pair_attack.yaml \
  --use-defenses jbshield gradient_cuff stepshield progent
```

Each active defense contributes to the **Defense Bypass Rate (DBR)** metric. A `defense_bypassed=True` record means the attack succeeded despite all active defenses.

## Implementation Location

- `defenses/jbshield.py`
- `defenses/gradient_cuff.py`
- `defenses/progent.py`
- `defenses/stepshield.py`
- `defenses/__init__.py` — registry and activation

→ [JBShield](jbshield.md)  
→ [Gradient Cuff](gradient-cuff.md)  
→ [Progent](progent.md)  
→ [StepShield](stepshield.md)
