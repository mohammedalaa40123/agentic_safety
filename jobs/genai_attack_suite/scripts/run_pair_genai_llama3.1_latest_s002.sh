#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${GENAI_STUDIO_API_KEY:-}" ]]; then
  echo "GENAI_STUDIO_API_KEY is not set" >&2
  exit 1
fi

cd /workspaces/agentic_safety
mkdir -p results/genai_attack_suite
export GENAI_STUDIO_TIMEOUT_SEC=${GENAI_STUDIO_TIMEOUT_SEC:-45}
python run.py --config jobs/genai_attack_suite/configs/config_pair_genai_llama3.1_latest_s002.yaml --verbose
