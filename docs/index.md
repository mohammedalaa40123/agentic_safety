# Agentic Safety Evaluation Framework

This documentation covers the full repository structure and execution model for the agentic safety evaluation framework.

## What this project does

- Runs attack-centric and agentic safety evaluations with configurable attack plans.
- Supports local Hugging Face models and API-hosted models.
- Executes tool calls through a sandbox and records tool-use behavior.
- Applies optional defense layers on prompts, responses, and tool actions.
- Exports experiment metrics for ASR, TIR, DBR, QTJ, and per-category summaries.

## Documentation map

- Getting Started: onboarding, quickstart, and config fields.
- Architecture: end-to-end system and execution flow diagrams.
- Components: file-level purpose for runner, attacks, defenses, tools, metrics, configs, and data.
- Operations: reproducible experiment runs, sandbox isolation, docs publishing.
- Reference: complete directory and file inventory.

## Primary entrypoint

The main execution entrypoint is run.py, which orchestrates loading config, models, defenses, attacks, sandbox tools, and metrics collection.
