#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${GENAI_STUDIO_API_KEY:-}" ]]; then
  echo "GENAI_STUDIO_API_KEY is not set" >&2
  exit 1
fi

cd /workspaces/agentic_safety
# Sequential execution preserves rate limits and reduces provider throttling.
bash jobs/genai_attack_suite/scripts/run_pair_genai_llama3.1_latest_s001.sh
bash jobs/genai_attack_suite/scripts/run_pair_genai_llama3.1_latest_s002.sh
bash jobs/genai_attack_suite/scripts/run_crescendo_genai_llama3.1_latest_s001.sh
bash jobs/genai_attack_suite/scripts/run_crescendo_genai_llama3.1_latest_s002.sh
bash jobs/genai_attack_suite/scripts/run_prompt_fusion_genai_llama3.1_latest_s001.sh
bash jobs/genai_attack_suite/scripts/run_prompt_fusion_genai_llama3.1_latest_s002.sh
bash jobs/genai_attack_suite/scripts/run_baseline_genai_llama3.1_latest_s001.sh
bash jobs/genai_attack_suite/scripts/run_baseline_genai_llama3.1_latest_s002.sh
