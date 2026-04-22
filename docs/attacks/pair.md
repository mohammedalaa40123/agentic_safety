# PAIR Attack

**PAIR** (Prompt Automatic Iterative Refinement) uses one LLM as an automated attacker that iteratively refines jailbreak prompts against a target model, guided by a judge model that scores each attempt.

## How PAIR Works

```mermaid
sequenceDiagram
    participant A as Attacker LLM
    participant T as Target LLM
    participant J as Judge LLM

    loop Until success or max iterations
        A->>T: Send jailbreak candidate
        T->>A: Target response
        A->>J: (candidate, response)
        J-->>A: Score 1–10 + feedback
        A->>A: Refine candidate using feedback
    end
```

1. The attacker LLM generates an initial jailbreak prompt from the goal.
2. The target LLM responds.
3. The judge LLM scores the response (1 = clearly refused, 10 = fully compliant harmful).
4. If score ≥ threshold → attack success. Otherwise, the attacker refines based on judge feedback.
5. Repeat up to `max_iterations` (default: 5).

## Benchmark Results

In the strict PAIR mini-benchmark (4 core models, no defenses):

| Model | ASR | Avg QTJ |
|-------|-----|---------|
| Llama-3.3-70B | 83.7% | ~3.0 |
| DeepSeek-R1-70B | 83.2% | ~3.0 |
| DeepSeek-R1-14B | 75.4% | ~2.6 |
| DeepSeek-V3.2 | 66.0% | ~2.2 |

![ASR by Model](../assets/charts/asr_by_model.png)

## Configuration

```yaml
attacks:
  - pair

models:
  attack_model: genai:llama3.3:70b    # attacker LLM
  target_model: genai:deepseek-r1:14b # target LLM
  judge_model:  genai:llama3.3:70b    # judge LLM

attack_config:
  pair:
    max_iterations: 5
    judge_threshold: 8
```

## Implementation Notes

- Implemented in `attacks/pair.py`
- Judge prompt uses a structured scoring rubric (1–10) with explicit feedback extraction
- `fusion_strategy` field in output is set to `pair_standalone` for pure PAIR runs
- Attack records include `jailbreak_prompt` and `jailbreak_response` fields (truncated at 500 chars in JSON export)

## Caveats

- Results are sensitive to attacker/judge model choice — the benchmark uses a fixed judge to ensure comparability.
- PAIR can have high apparent ASR if the judge model is lenient; use consistent judge across all reported comparisons.
