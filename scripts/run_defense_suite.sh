#!/bin/bash
# Auto-generated: run all defense evaluation configs
# 4 defenses × 2 attacks × 3 models = 24 jobs
set -e

echo "=== eval_agentshield_pair_deepseek_r1_14b.yaml ==="
python run.py --config configs/defense_eval/eval_agentshield_pair_deepseek_r1_14b.yaml

echo "=== eval_agentshield_pair_llama3_3_70b.yaml ==="
python run.py --config configs/defense_eval/eval_agentshield_pair_llama3_3_70b.yaml

echo "=== eval_agentshield_pair_qwen3_14b.yaml ==="
python run.py --config configs/defense_eval/eval_agentshield_pair_qwen3_14b.yaml

echo "=== eval_agentshield_crescendo_deepseek_r1_14b.yaml ==="
python run.py --config configs/defense_eval/eval_agentshield_crescendo_deepseek_r1_14b.yaml

echo "=== eval_agentshield_crescendo_llama3_3_70b.yaml ==="
python run.py --config configs/defense_eval/eval_agentshield_crescendo_llama3_3_70b.yaml

echo "=== eval_agentshield_crescendo_qwen3_14b.yaml ==="
python run.py --config configs/defense_eval/eval_agentshield_crescendo_qwen3_14b.yaml

echo "=== eval_stepshield_pair_deepseek_r1_14b.yaml ==="
python run.py --config configs/defense_eval/eval_stepshield_pair_deepseek_r1_14b.yaml

echo "=== eval_stepshield_pair_llama3_3_70b.yaml ==="
python run.py --config configs/defense_eval/eval_stepshield_pair_llama3_3_70b.yaml

echo "=== eval_stepshield_pair_qwen3_14b.yaml ==="
python run.py --config configs/defense_eval/eval_stepshield_pair_qwen3_14b.yaml

echo "=== eval_stepshield_crescendo_deepseek_r1_14b.yaml ==="
python run.py --config configs/defense_eval/eval_stepshield_crescendo_deepseek_r1_14b.yaml

echo "=== eval_stepshield_crescendo_llama3_3_70b.yaml ==="
python run.py --config configs/defense_eval/eval_stepshield_crescendo_llama3_3_70b.yaml

echo "=== eval_stepshield_crescendo_qwen3_14b.yaml ==="
python run.py --config configs/defense_eval/eval_stepshield_crescendo_qwen3_14b.yaml

echo "=== eval_progent_pair_deepseek_r1_14b.yaml ==="
python run.py --config configs/defense_eval/eval_progent_pair_deepseek_r1_14b.yaml

echo "=== eval_progent_pair_llama3_3_70b.yaml ==="
python run.py --config configs/defense_eval/eval_progent_pair_llama3_3_70b.yaml

echo "=== eval_progent_pair_qwen3_14b.yaml ==="
python run.py --config configs/defense_eval/eval_progent_pair_qwen3_14b.yaml

echo "=== eval_progent_crescendo_deepseek_r1_14b.yaml ==="
python run.py --config configs/defense_eval/eval_progent_crescendo_deepseek_r1_14b.yaml

echo "=== eval_progent_crescendo_llama3_3_70b.yaml ==="
python run.py --config configs/defense_eval/eval_progent_crescendo_llama3_3_70b.yaml

echo "=== eval_progent_crescendo_qwen3_14b.yaml ==="
python run.py --config configs/defense_eval/eval_progent_crescendo_qwen3_14b.yaml

echo "=== eval_contextguard_pair_deepseek_r1_14b.yaml ==="
python run.py --config configs/defense_eval/eval_contextguard_pair_deepseek_r1_14b.yaml

echo "=== eval_contextguard_pair_llama3_3_70b.yaml ==="
python run.py --config configs/defense_eval/eval_contextguard_pair_llama3_3_70b.yaml

echo "=== eval_contextguard_pair_qwen3_14b.yaml ==="
python run.py --config configs/defense_eval/eval_contextguard_pair_qwen3_14b.yaml

echo "=== eval_contextguard_crescendo_deepseek_r1_14b.yaml ==="
python run.py --config configs/defense_eval/eval_contextguard_crescendo_deepseek_r1_14b.yaml

echo "=== eval_contextguard_crescendo_llama3_3_70b.yaml ==="
python run.py --config configs/defense_eval/eval_contextguard_crescendo_llama3_3_70b.yaml

echo "=== eval_contextguard_crescendo_qwen3_14b.yaml ==="
python run.py --config configs/defense_eval/eval_contextguard_crescendo_qwen3_14b.yaml

