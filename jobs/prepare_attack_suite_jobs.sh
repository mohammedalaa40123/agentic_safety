#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/agentic_safety

python scripts/genai_make_attack_suite_jobs_nogcg.py \
  --goals data/agentic_scenarios_MIR_eval_v2.json \
  --chunk-size 100 \
  --model genai:llama3.1:latest \
  --rpm 20 \
  --config configs/eval_genaistudio_pair_apijudge_100.yaml \
  --pair-iters 3 \
  --crescendo-turns 4 \
  --crescendo-patience 2 \
  --out-root jobs/genai_attack_suite \
  --output-dir results/genai_attack_suite

echo "Prepared attack-suite jobs at jobs/genai_attack_suite"
echo "Run all sequentially: bash jobs/genai_attack_suite/run_all_suite_jobs.sh"
