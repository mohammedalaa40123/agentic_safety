---
title: Agentic Safety Evaluator
emoji: 🛡️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
private: true
---

# Agentic Safety Evaluation Framework

A modular harness to run jailbreak attacks, baselines, and tool-augmented agent checks with optional defenses. The entrypoint is [run.py](run.py), backed by the small runner helpers in `runner/` (config, logging, models, attacks, defenses, sandbox, agentic loop).

## Prerequisites
- Python 3.10+
- GPU recommended for local Hugging Face models (PyTorch + transformers)
- Optional: Gemini API key (`GEMINI_API_KEY` or `GOOGLE_API_KEY`) if you map models to Gemini
- Optional: Weights & Biases if you wire it in (not enabled by default)

Install locally:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Project Layout
- [run.py](run.py): slim CLI orchestrator
- runner/: config + logging + models + sandbox + attacks + defenses + agentic loop
- attacks/: PAIR loop and other attack strategies
- defenses/: AgentShield, JBShield, Gradient Cuff, Progent, StepShield, registry
- tools/: sandbox, file I/O, code exec, web browse, network simulators
- metrics/: ASR/TIR/DBR/QTJ aggregation and exporters
- configs/: YAML presets (baseline, agentic, defense combos)
- data/: goal lists (JSON/CSV)

## Documentation (MkDocs)
Comprehensive documentation is available under `docs/` and configured via `mkdocs.yml`.

Build and preview locally:
```bash
pip install -r requirements-docs.txt
mkdocs serve
```

Build static site:
```bash
mkdocs build --strict
```

GitHub Pages deployment is automated by `.github/workflows/docs.yml`.

## Config (YAML)
See [runner/config.py](runner/config.py) for all fields. Key sections:
- `experiment_name`: label for logs/results
- `mode`: `attack` (default), `agentic`, or `baseline`
- `output_dir`: where CSV/JSON/logs are written
- `goals_path`: JSON/CSV goals file
- `models`: `attack_model`, `target_model`, `judge_model`, token limits, optional per-model rate limits (`attack_calls_per_minute`, `target_calls_per_minute`, `judge_calls_per_minute`)
- `sandbox`: `enabled`, `tools` (file_io, code_exec, web_browse, network), timeouts, max_steps
  - `code_exec_backend`: `auto` | `bwrap` | `none`
  - `code_exec_require_isolation`: fail closed if no isolation backend is available
- `attacks`: ordered list of attack specs `{name, enabled, stop_on_success, params}`; defaults to `pair`
- `baseline`: `{enabled}` to prepend a direct/baseline run
- `defenses`: `{enabled, active, agentshield, jbshield, gradient_cuff, progent, stepshield}`
- `wandb`, `logging`: optional toggles

## CLI (overrides config)
```bash
python run.py \
  --config configs/baseline.yaml \
  --attack-model vicuna \
  --target-model vicuna \
  --judge-model llama-guard \
  --goals data/agentic_scenarios_smoke5.json \
  --use-sandbox \
  --use-defenses jbshield gradient_cuff \
  --attack-plan pair baseline \
  --mode attack \
  --output-dir results/demo \
  --verbose
```
Flags:
- `--config` path to YAML
- `--mode` attack | agentic | baseline
- `--goals` JSON/CSV goals file
- `--attack-model`, `--target-model`, `--judge-model` overrides
- `--use-sandbox` enable sandbox/tool loop
- `--use-defenses <list>` activate defenses
- `--attack-plan <list>` ordered attacks (e.g., `pair crescendo baseline` — unknown names are skipped)
- `--baseline` force baseline mode and prepend a baseline runner
- `--output-dir` results directory
- `-v/--verbose` debug logging

## Modes
- Attack: executes the ordered attack plan (PAIR by default), stop-on-success per attack entry.
- Baseline: skips attack loops and just runs the baseline/direct runner (or any attack named `baseline`).
- Agentic: sandbox-only execution using the target model; malicious tool calls count as immediate jailbreak success.

## Outputs
- Results CSV/JSON in `output_dir` (timestamped filenames)
- Log file in `output_dir` with run header (mode, models, defenses, attacks, paths)
- Metrics include ASR/Task Success, TIR, DBR, QTJ, per-category breakdown in the JSON

## Tips
- Sandbox: set `sandbox.enabled: true` and choose tools; tool calls in malicious goals mark jailbreak success.
- Real command isolation: set `sandbox.code_exec_backend: bwrap` and `sandbox.code_exec_require_isolation: true` so code runs in a Linux namespace sandbox.
- Defenses: configure `defenses.enabled: true` and list `active` defenses; prompt/response filters can block and mark defense responses.
- AgentShield: enable `agentshield` in `defenses.active` to combine a prompt-injection classifier with tool-call risk blocking before execution.
- AgentShield preset: `configs/eval_qwen_agentshield_pair.yaml` includes `agentshield + progent` defaults for PAIR resistance.
- AgentShield calibration: `python scripts/calibrate_agentshield_threshold.py --data data/agentic_scenarios_asr_eval_v2.json` to tune prompt thresholds on your labeled data.
- Models: `runner/models.py` maps short names to HF IDs and uses a project-local Hugging Face cache at `models/` by default (override with `AGENTIC_MODEL_CACHE_DIR`).
- Purdue GenAI Studio API: use model names prefixed with `genai:` (for example `genai:llama3.1:latest`) and set `GENAI_STUDIO_API_KEY` (optional overrides: `GENAI_STUDIO_API_URL`, `GENAI_STUDIO_TIMEOUT_SEC`).
- Dataset split examples: `data/agentic_scenarios_asr_eval_v2.json` (mixed), `data/agentic_scenarios_asr_eval_v2_safe.json` (safe-only), `data/agentic_scenarios_asr_eval_v2_unsafe.json` (unsafe-only).
- Goals: JSON array of `{goal, target, category}` or CSV with `goal/prompt`, `target/target_str`, `category`.
- Performance: lower `attacks[*].params.n_iterations` or sandbox `max_steps` to speed up; prefer smaller models for quick smoke runs.
