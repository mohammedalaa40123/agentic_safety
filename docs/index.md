# Agentic Safety Evaluation Framework

!!! tip "Research-first documentation"
    This site foregrounds the **threat model**, **attack taxonomy**, **defense mechanisms**, and **benchmark results** before operational setup. If you just want to run an experiment, jump to [Quickstart](getting-started/quickstart.md).

## What This Framework Evaluates

Agentic LLMs are **qualitatively different** from single-turn chat models. They plan across many steps, call external tools, browse the web, execute code, and interact with other agents. A request that a chat model safely refuses in one turn may succeed after three carefully crafted turns with tool-use context.

This framework provides a repeatable evaluation harness that tests jailbreak attacks across the full agentic pipeline — from initial prompt to tool execution.

## Navigation

| Section | What you'll find |
|---------|-----------------|
| [🗺️ Threat Model](threat-model/index.md) | OWASP Agentic AI Top-10 taxonomy, full attack surface analysis |
| [⚔️ Attacks](attacks/index.md) | PAIR, Crescendo, Prompt Fusion, and Hybrid method documentation |
| [🛡️ Defenses](defenses/index.md) | JBShield, Gradient Cuff, Progent, StepShield — how each works |
| [📊 Evaluation](evaluation/index.md) | Benchmark methodology, metrics (ASR/TIR/DBR/QTJ), leaderboard |
| [🌐 Providers](providers/index.md) | Cloud, local, and HPC provider setup |
| [⚡ Getting Started](getting-started/quickstart.md) | Environment setup, install, and first run |
| [🏗️ Architecture](architecture/system-overview.md) | System wiring, execution flows, threat-defense model |
| [🚀 Deployment](deployment/github-pages.md) | GitHub Pages, Hugging Face Space, experiment scale-out |

## Mini-Benchmark Results at a Glance

> Strict PAIR attack · No defenses · 4-model core set · Consistent Llama-3.3-70B judge

![ASR by Model](assets/charts/asr_by_model.png)

| Model | ASR | QTJ |
|-------|-----|-----|
| Llama-3.3-70B | 83.7% | ~3.0 |
| DeepSeek-R1-70B | 83.2% | ~3.0 |
| DeepSeek-R1-14B | 75.4% | ~2.6 |
| DeepSeek-V3.2 | 66.0% | ~2.2 |

→ [Full evaluation methodology and per-category breakdown](evaluation/index.md)

## Core External Links

- 🤗 [Live Space](https://huggingface.co/spaces/Mo-alaa/agentic-safety-eval) — interactive frontend and results API
- 🤗 [Results Dataset](https://huggingface.co/datasets/Mo-alaa/agentic-safety-results) — raw experiment output
- 🐙 [GitHub Repository](https://github.com/mohammedalaa40123/agentic_safety) — source code
