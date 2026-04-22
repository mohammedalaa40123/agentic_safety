# Running Experiments

## Typical command

```bash
source .venv/bin/activate
python run.py --config configs/eval_genai_pair_localjudge_100.yaml --verbose
```

## Common CLI experiment patterns

Run a simple baseline evaluation:

```bash
python run.py --config configs/eval_qwen_baseline.yaml --verbose
```

Run a targeted attack experiment:

```bash
python run.py \
  --config configs/eval_qwen_pair_attack.yaml \
  --mode attack \
  --goals data/agentic_scenarios_10_mixed.json \
  --use-sandbox \
  --use-defenses jbshield gradient_cuff \
  --attack-plan pair crescendo baseline \
  --output-dir results/demo \
  --verbose
```

Run a partial dataset subset:

```bash
python run.py --config configs/baseline.yaml --goals data/agentic_scenarios_smoke5.json --goal-indices 0,2,5 --output-dir results/smoke
```

Run agentic mode with sandbox tools:

```bash
python run.py --config configs/eval_qwen_pair_attack.yaml --mode agentic --use-sandbox --output-dir results/agentic
```

## Output artifacts

The configured `output_dir` normally contains:

- `*.log` run logs
- `results_*.csv` record tables
- `results_*.json` aggregated summary files

## CLI testing

Run the repository tests:

```bash
pytest -q tests/
```

Run a CLI smoke test:

```bash
python run.py --config configs/eval_qwen_baseline.yaml --goals data/agentic_scenarios_smoke5.json --output-dir results/smoke --verbose
```

## Metrics and troubleshooting

- `ASR`, `TIR`, `DBR`, `QTJ`: primary evaluation metrics
- If a model backend fails, verify the provider key and available token limits
- Slow experiments: reduce `attacks[*].params.n_iterations` or sandbox `max_steps`
- If a goal yields only an error response, the run may skip that record during metric aggregation
