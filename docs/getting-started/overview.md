# Project Overview

## Repository goals

This repository is designed for evaluating jailbreak behavior in both traditional single-turn prompting and agentic tool-calling workflows.

## Key capabilities

- Multi-mode execution: attack, baseline, and agentic modes.
- Pluggable attacks: PAIR, GCG, Crescendo, baseline, prompt fusion, and hybrid variants.
- Pluggable defenses: JBShield, Gradient Cuff, Progent, and StepShield.
- Tool sandbox: file I/O, code execution, web browse, and network simulation.
- Metrics pipeline: aggregate and export ASR, TIR, DBR, QTJ, plus detailed records.

## High-level package layout

- run.py: command-line orchestrator.
- runner/: builders and mode wiring.
- attacks/: attack algorithms and loops.
- defenses/: defense implementations and registry.
- tools/: sandbox and tool implementations.
- metrics/: metric definitions and aggregation.
- configs/: YAML presets for experiment variants.
- data/: scenario datasets and generation scripts.
- jobs/: cluster submission scripts.
- results/: run artifacts and logs.
- models/: local Hugging Face model cache.
