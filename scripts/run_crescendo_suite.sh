#!/bin/bash
# Auto-generated: run all Crescendo CTF-50 evaluations
set -e

echo "=== Running eval_crescendo_ctf50_deepseek_r1_7b.yaml ==="
python run.py --config configs/eval_crescendo_ctf50_deepseek_r1_7b.yaml

echo "=== Running eval_crescendo_ctf50_llama3_1_latest.yaml ==="
python run.py --config configs/eval_crescendo_ctf50_llama3_1_latest.yaml

echo "=== Running eval_crescendo_ctf50_llama3_2_latest.yaml ==="
python run.py --config configs/eval_crescendo_ctf50_llama3_2_latest.yaml

echo "=== Running eval_crescendo_ctf50_llama3_3_70b.yaml ==="
python run.py --config configs/eval_crescendo_ctf50_llama3_3_70b.yaml

echo "=== Running eval_crescendo_ctf50_qwen3_1_7b.yaml ==="
python run.py --config configs/eval_crescendo_ctf50_qwen3_1_7b.yaml

echo "=== Running eval_crescendo_ctf50_qwen3_14b.yaml ==="
python run.py --config configs/eval_crescendo_ctf50_qwen3_14b.yaml

echo "=== Running eval_crescendo_ctf50_qwen3_30b.yaml ==="
python run.py --config configs/eval_crescendo_ctf50_qwen3_30b.yaml

