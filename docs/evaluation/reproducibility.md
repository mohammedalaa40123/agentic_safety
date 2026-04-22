# Reproducibility

## Regenerating Charts and Benchmark Data

All charts embedded in these docs and in the README are generated from versioned result artifacts. To reproduce:

```bash
# Activate the project venv
source .venv/bin/activate

# Run the chart pipeline
python scripts/gen_benchmark_charts.py \
  --results-dir results/agentic_experiments_v2_500 \
  --out-dir docs/assets/charts
```

Output:

```
docs/assets/charts/
├── asr_by_model.png
├── asr_by_category.png
├── tool_quality.png
├── query_efficiency.png
├── query_distribution.png
└── benchmark_data.json      ← normalised chart data
```

## Benchmark Filter Rules

The script applies these filters programmatically:

```python
# From scripts/gen_benchmark_charts.py
BENCHMARK_ATTACK = "pair"
CORE_MODELS = {
    "Llama-3.3-70B":   "llama3.3:70b",
    "DeepSeek-R1-70B": "deepseek-r1:70b",
    "DeepSeek-R1-14B": "deepseek-r1:14b",
    "DeepSeek-V3.2":   "deepseek-v3.2",
}
# defense_name must be empty
# dedup: first occurrence per (goal, model) pair
```

## Data Source

Result JSON files live in `results/agentic_experiments_v2_500/`. Each sub-folder corresponds to one experiment run and contains one JSON file with `summary`, `by_category`, and `records` keys.

Older format files (plain list schema, no top-level `summary` key) are also handled by the pipeline.

## Verifying Metric Values

To cross-check a specific model's ASR:

```bash
python3 -c "
import json, glob
from pathlib import Path

# Load benchmark_data.json (normalised output)
data = json.loads(Path('docs/assets/charts/benchmark_data.json').read_text())
print('ASR by model:', data['asr_by_model'])
print('Per-model N:', data['benchmark']['per_model_n'])
"
```

## Adding New Runs

1. Place the new result directory under `results/agentic_experiments_v2_500/` (or update `--results-dir`).
2. Re-run `scripts/gen_benchmark_charts.py`.
3. Commit the updated chart PNGs and `benchmark_data.json`.

!!! tip "Reproducibility policy"
    The benchmark filter rules in `scripts/gen_benchmark_charts.py` are the canonical source of truth. If you change filtering logic, commit the updated script alongside the new charts so the change is traceable.
