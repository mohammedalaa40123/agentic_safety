# configs and data

## configs folder

The configs folder holds reproducible experiment presets.

Representative files:

- eval_genai_pair_localjudge_100.yaml
- eval_genaistudio_pair_apijudge_100.yaml
- eval_qwen_baseline.yaml
- eval_qwen_pair_attack.yaml
- eval_qwen_gcg_attack.yaml
- eval_qwen_crescendo_attack.yaml
- eval_qwen_stepshield.yaml
- eval_qwen_stepshield_pair.yaml
- eval_qwen_progent.yaml
- eval_qwen_pair_geminijudge.yaml
- agentic_5_safe.yaml
- generate_yamls.py

## data folder

The data folder includes mixed, safe-only, unsafe-only, and smoke datasets plus generation scripts.

Representative files:

- agentic_scenarios_asr_eval_v2.json
- agentic_scenarios_asr_eval_v2_safe.json
- agentic_scenarios_asr_eval_v2_unsafe.json
- agentic_scenarios_100_labeled.json
- advanced_jailbreak_samples_v2.json
- generate_100_scenarios.py
- generate_10_mixed.py

## jobs folder

The jobs folder contains scheduler submission scripts for cluster runs.
