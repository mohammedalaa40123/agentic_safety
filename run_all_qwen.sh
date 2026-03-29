#!/bin/bash
source /depot/davisjam/data/mohamed/agentic_safety/.venv/bin/activate
export HF_HOME=/depot/davisjam/data/mohamed/hf_cache

configs=(
  "eval_qwen_baseline.yaml"
  # "eval_qwen_stepshield.yaml" defense
  # "eval_qwen_progent.yaml" defense
  "eval_qwen_pair_attack.yaml"
  # "eval_qwen_stepshield_pair.yaml" attack + defense
  # "eval_qwen_pair_geminijudge.yaml"
  "eval_qwen_crescendo_attack.yaml"
  "eval_qwen_gcg_attack.yaml"
)

for conf in "${configs[@]}"; do
    echo "==========================================="
    echo "Running configuration: $conf"
    echo "==========================================="
    python run.py --config configs/$conf --verbose > "results/agentic_experiments/stdout_${conf}.log" 2>&1
    echo "Done with $conf. See results/agentic_experiments/stdout_${conf}.log"
done
