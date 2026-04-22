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

A modular evaluation harness for jailbreak attacks, agentic tool-use safety checks, and configurable defense benchmarking.

## Project links

- Documentation site: https://mohammedalaa40123.github.io/agentic_safety/
- Hugging Face Space: https://huggingface.co/spaces/Mo-alaa/agentic-safety-eval
- Results dataset: https://huggingface.co/datasets/Mo-alaa/agentic-safety-results
- Repository: https://github.com/mohammedalaa40123/agentic_safety

## Guide map

- Setup and requirements: Requirements, Environment variables, Recommended setup and checklist
- Running experiments: Quickstart CLI examples and Command reference
- Validation: Testing
- Deployment: Server backend and local deployment, Hugging Face Space deployment, Docs preview and GitHub Pages

## What this repo provides

- attack and baseline execution flows via `run.py`
- agentic sandbox evaluation with tool calls and step limits
- plug-and-play defense layers, including JBShield, Gradient Cuff, Progent, and StepShield
- Hugging Face and API-hosted model support
- FastAPI backend + deployed frontend support via Docker and Hugging Face Spaces
- MkDocs documentation with GitHub Pages deployment automation

## Requirements

- Python 3.10+
- `pip`, `venv`
- Optional GPU for local Hugging Face models

Install the package:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

Install server support:

```bash
pip install -e .[server]
```

Install docs dependencies:

```bash
pip install -r requirements-docs.txt
```

## Environment variables

Set provider keys as needed:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `GENAI_STUDIO_API_KEY`
- `ANTHROPIC_API_KEY`
- `OLLAMA_CLOUD_API_KEY`
- `WANDB_API_KEY`
- `HF_TOKEN` for Hugging Face Space deployment
- `AGENTIC_MODEL_CACHE_DIR` to override the model cache path

## Recommended setup and checklist

1. Clone the repo and enter its root folder.
2. Create and activate a virtual environment.
3. Install the package with `pip install -e .`.
4. If using the server/back end, install `pip install -e .[server]`.
5. Configure any provider API keys in your shell environment.
6. Run a local experiment and verify output files are produced.
7. Build or deploy docs with MkDocs.

## Quickstart CLI examples

Run a baseline evaluation:

```bash
python run.py --config configs/eval_qwen_baseline.yaml --verbose
```

Run an attack evaluation with sandboxing and defenses:

```bash
python run.py \
  --config configs/eval_qwen_pair_attack.yaml \
  --mode attack \
  --goals data/agentic_scenarios_10_mixed.json \
  --use-sandbox \
  --use-defenses jbshield gradient_cuff \
  --attack-plan pair crescendo baseline \
  --output-dir results/demo \
  --verbose
```

Run agentic mode with a sandbox:

```bash
python run.py --config configs/eval_qwen_pair_attack.yaml --mode agentic --use-sandbox --output-dir results/agentic-demo
```

Run a partial goals subset:

```bash
python run.py --config configs/baseline.yaml --goals data/agentic_scenarios_smoke5.json --goal-indices 0,2,5 --output-dir results/partial
```

## Command reference

Key `run.py` flags:

- `--config`: YAML config file path
- `--output-dir`: output directory override
- `--mode`: `attack`, `agentic`, or `baseline`
- `--goals`: JSON or CSV goals file
- `--attack-model`, `--target-model`, `--judge-model`: model overrides
- `--use-sandbox`: enable sandbox tool execution
- `--use-defenses`: list of defenses to turn on
- `--attack-plan`: ordered attack sequence
- `--baseline`: run baseline/direct mode
- `--goal-indices`: comma-separated list of goal indices
- `--verbose` / `-v`: enable debug logging

## Configuration overview

Configuration is loaded from YAML in `configs/` and parsed by `runner/config.py`.

Important sections:

- `experiment_name`
- `description`
- `mode`
- `output_dir`
- `goals_path`
- `models`
- `sandbox`
- `attacks`
- `defenses`
- `wandb`
- `logging`

For a complete config reference, see `docs/getting-started/configuration.md`.

## Testing

Run the unit and integration test suite:

```bash
pytest -q tests/
```

Run a local CLI smoke test:

```bash
python run.py --config configs/eval_qwen_baseline.yaml --goals data/agentic_scenarios_smoke5.json --output-dir results/smoke --verbose
```

## Server backend and local deployment

Start the FastAPI backend:

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 7860
```

The backend serves the built frontend if `frontend/dist` exists.

Build and run locally with Docker:

```bash
docker build -t agentic-safety .
docker run --rm -p 7860:7860 agentic-safety
```

## Hugging Face Space deployment

Deploy the repository to a private Hugging Face Docker Space:

```bash
export HF_TOKEN="<your_hf_token>"
python scripts/deploy_hf_space.py --repo <username>/agentic-safety-eval --token "$HF_TOKEN"
```

Set the required Space secrets after deployment:

- `GENAI_STUDIO_API_KEY`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `ANTHROPIC_API_KEY`
- `OLLAMA_CLOUD_API_KEY`
- `WANDB_API_KEY`

Optional but recommended for preloading Results in Space:

- `HF_RESULTS_DATASET=Mo-alaa/agentic-safety-results`

With this set, the backend automatically mirrors all files under `results/` from the dataset into local Space storage when `/api/results` endpoints are first accessed.

The Dockerfile exposes port `7860` and the Space will build from that container definition.

## Docs preview and GitHub Pages

Preview docs locally:

```bash
mkdocs serve
```

Build static docs:

```bash
mkdocs build --strict
```

Deploy docs to GitHub Pages:

```bash
mkdocs gh-deploy --clean
```

The repository also contains an automated docs deployment workflow at `.github/workflows/docs.yml`.

## Project layout

- `run.py`: CLI orchestrator
- `runner/`: config, models, sandbox, attack and defense wiring
- `attacks/`: attack algorithms and loops
- `defenses/`: defense implementations
- `tools/`: sandbox tool adapters
- `metrics/`: metric aggregation and results export
- `configs/`: YAML experiment presets
- `data/`: evaluation scenarios and datasets
- `server/`: FastAPI backend and job API
- `frontend/`: web UI source and build output
- `scripts/`: deployment and launcher helpers
- `docs/`: MkDocs documentation
- `.github/workflows/`: CI and docs automation
