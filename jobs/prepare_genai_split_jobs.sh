#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/agentic_safety

python scripts/genai_split_and_make_jobs.py \
  --goals data/agentic_scenarios_asr_eval_v2.json \
  --chunk-size 100 \
  --models \
    genai:llama3.1:latest \
    genai:llama3.3:70b \
    genai:deepseek-r1:14b \
    genai:llama4:latest \
  --config configs/eval_genaistudio_pair_apijudge_100.yaml \
  --iterations 3 \
  --rpm 20 \
  --out-root jobs/genai_shards \
  --output-dir results/genai_shards

echo "Prepared shard scripts under jobs/genai_shards/scripts"
echo "Run sequentially: bash jobs/genai_shards/run_all_generated_jobs.sh"
