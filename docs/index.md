# Agentic Safety Evaluation Framework

Welcome to the Agentic Safety Evaluation Framework documentation.

## Project links

- Documentation site: https://mohammedalaa40123.github.io/agentic_safety/
- Hugging Face Space: https://huggingface.co/spaces/Mo-alaa/agentic-safety-eval
- Results dataset: https://huggingface.co/datasets/Mo-alaa/agentic-safety-results
- Repository: https://github.com/mohammedalaa40123/agentic_safety

This repository provides a repeatable evaluation platform for testing jailbreak attacks, agentic tool-use behavior, and defense effectiveness.

## What this documentation contains

- Getting Started: environment setup, package install, CLI workflow, and configuration reference.
- Architecture: how the system is wired, how attack flows execute, and defense decision points.
- Components: package-level responsibility for `run.py`, `runner/`, `attacks/`, `defenses/`, `tools/`, `metrics/`, `configs/`, and `data/`.
- Operations: real experiment commands, sandbox settings, GitHub Pages docs deployment, and Hugging Face Space launch.
- Reference: repository directory and file inventory for quick lookup.

## Core entrypoints

- `run.py`: local experiment orchestrator and CLI entrypoint.
- `runner/config.py`: YAML loader and CLI override handler.
- `server/main.py`: FastAPI app entrypoint for server-backed execution and API launch.
- `scripts/deploy_hf_space.py`: deploy the repo as a Docker-based Hugging Face Space.

## Start here

1. Read `docs/getting-started/overview.md` for project goals and layout.
2. Follow `docs/getting-started/quickstart.md` for a full setup walkthrough.
3. Use `docs/getting-started/configuration.md` to customize experiments.
4. Run `mkdocs serve` to preview docs locally.
