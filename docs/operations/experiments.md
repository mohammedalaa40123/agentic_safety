# Running Experiments

## Typical command

```bash
cd /depot/davisjam/data/mohamed/agentic_safety
source .venv/bin/activate
python run.py --config configs/eval_genai_pair_localjudge_100.yaml --verbose
```

## Useful overrides

```bash
python run.py \
  --config configs/eval_qwen_pair_attack.yaml \
  --goals data/agentic_scenarios_asr_eval_v2_unsafe.json \
  --mode attack \
  --use-sandbox \
  --attack-plan pair crescendo baseline \
  --output-dir results/adhoc_run \
  --verbose
```

## Output artifacts

- output_dir/*.log
- output_dir/results_*.csv
- output_dir/results_*.json

## Common troubleshooting

- Missing API key: set GENAI_STUDIO_API_KEY or GEMINI_API_KEY based on backend.
- Slow runs: lower n_iterations and max_steps, or use smaller models.
- Judge failures: increase judge_max_n_tokens for structured judge outputs.
