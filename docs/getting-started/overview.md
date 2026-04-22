# Project Overview

## Repository goals

This repository is a structured evaluation framework for agentic jailbreaks and defenses. It is designed to:

- generate and execute jailbreak-style attack scenarios
- test defense layers across prompt, response, and tool-action paths
- log and export reproducible metrics for analysis
- operate with both local Hugging Face models and API-hosted backends
- provide a deployable API and web frontend for hosted evaluation

## Key capabilities

- Multi-mode execution: `attack`, `baseline`, and `agentic`
- Plug-and-play attack strategies: PAIR, GCG, Crescendo, baseline, prompt fusion, and hybrid variants
- Defense modules: JBShield, Gradient Cuff, Progent, StepShield, plus registry-based activation
- Sandbox tools: `file_io`, `code_exec`, `web_browse`, `network`
- Metrics pipeline: ASR, TIR, DBR, QTJ, plus detailed per-run and per-goal logs

## High-level package layout

- `run.py`: CLI orchestrator and experiment entrypoint
- `runner/`: config loading, model build, sandbox integration, attack/defense wiring, metrics collection
- `attacks/`: attack implementations and runner logic
- `defenses/`: defense implementations and registry
- `tools/`: sandbox tool adapters and isolation helpers
- `metrics/`: metrics definitions, aggregation, and export
- `configs/`: reusable YAML scenario presets and defaults
- `data/`: evaluation goals, scenarios, and generation scripts
- `server/`: FastAPI backend, job API, and static asset serving
- `frontend/`: web UI source and built distribution
- `scripts/`: deploy helpers and batch launcher utilities
- `.github/workflows/`: CI and docs deployment automation

## Recommended first steps

1. Create a Python virtual environment.
2. Install the package.
3. Configure API keys for your chosen backend.
4. Run a sample experiment.
5. Preview the docs locally with MkDocs.
