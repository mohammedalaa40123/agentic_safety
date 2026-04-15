#!/bin/bash
source /depot/davisjam/data/mohamed/agentic_safety/.venv/bin/activate

export GENAI_STUDIO_API_KEY="sk-6d974b477afc48c88de95978d2f662ef"

MODELS=(
    "genai:llama3.3:70b"
    "genai:llama3.2:latest"
    "genai:llama3.1:latest"
    "genai:deepseek-r1:70b"
    "genai:deepseek-r1:14b"
    "genai:deepseek-r1:7b"
    "genai:qwen3:30b"
    "genai:qwen3:14b"
    "genai:qwen3:1.7b"
)

for MODEL in "${MODELS[@]}"; do
    echo "========================================================"
    echo "Running PAIR attack against target: $MODEL"
    echo "========================================================"
    python run.py \
        --config configs/eval_pair_500_v2.yaml \
        --target-model "$MODEL" \
        --output-dir "results/agentic_experiments_v2_500/${MODEL//:/_}"
done
echo "All evaluations completed!"
