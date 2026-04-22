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

<div align="center">

# 🛡️ Agentic Safety Evaluation Framework

**A reproducible jailbreak-attack benchmarking harness for agentic LLMs.**  
Evaluates PAIR, Crescendo, and Prompt-Fusion attacks across multi-step tool-use pipelines with pluggable defenses and structured metrics.

[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-0969DA?style=flat-square&logo=github)](https://mohammedalaa40123.github.io/agentic_safety/)
[![HF Space](https://img.shields.io/badge/🤗%20Space-Live%20Demo-orange?style=flat-square)](https://huggingface.co/spaces/Mo-alaa/agentic-safety-eval)
[![Dataset](https://img.shields.io/badge/🤗%20Dataset-Results-yellow?style=flat-square)](https://huggingface.co/datasets/Mo-alaa/agentic-safety-results)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=flat-square&logo=github)](https://github.com/mohammedalaa40123/agentic_safety)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## What This Is

Most LLM safety evaluations target single-turn chat. **Agentic systems are fundamentally different** — they plan, call tools, browse the web, and execute code across many steps. A jailbreak that fails in one turn may succeed in three.

This framework provides:

- 🎯 **Attack evaluation**: PAIR, Crescendo, Prompt-Fusion, and hybrid attack loops against agentic LLM pipelines
- 🛡️ **Defense testing**: JBShield, Gradient Cuff, Progent, and StepShield across prompt/response/tool paths
- 📊 **Structured metrics**: ASR, TIR, DBR, and QTJ — defined once, measured consistently
- 🔁 **Reproducibility**: YAML-configured experiments, seeded runs, structured JSON output
- 🌐 **Scale**: Cloud and compute-cluster provider support (OpenAI, Gemini, Anthropic, Ollama, Genai/RCAC)

---

## Mini-Benchmark Snapshot

> **Scope**: Strict PAIR attack · No defenses · 4 core target models · Consistent judge (Llama-3.3-70B)  
> **Data**: 999 deduplicated goal/model pairs from `agentic_experiments_v2_500`  
> **Caveats**: PAIR-only (no Crescendo/Fusion comparison); judge-model bias risk present; no defense-at-scale matrix included.

### Attack Success Rate by Model

![ASR by Model](docs/assets/charts/asr_by_model.png)

| Model | ASR (PAIR) | Avg QTJ | Notes |
|-------|-----------|---------|-------|
| Llama-3.3-70B | **83.7%** | ~3.0 | Most susceptible under PAIR |
| DeepSeek-R1-70B | **83.2%** | ~3.0 | Strong reasoning; still highly susceptible |
| DeepSeek-R1-14B | **75.4%** | ~2.6 | Fewer parameters, lower but significant ASR |
| DeepSeek-V3.2 | **66.0%** | ~2.2 | Most resistant in core set |

> **QTJ** = Queries-to-Jailbreak: lower means easier to break on average.

### ASR by OWASP Agentic AI Top-10 Category

![ASR by OWASP Category](docs/assets/charts/asr_by_category.png)

### Tool-Call Quality (Correct vs Wrong)

![Tool Quality](docs/assets/charts/tool_quality.png)

### Query Efficiency vs ASR

![Query Efficiency](docs/assets/charts/query_efficiency.png)

_Low QTJ + high ASR = efficient jailbreak. The scatter shows that DeepSeek-V3.2 requires fewer queries but also has meaningfully lower ASR, suggesting some implicit resistance._

### Query Count Distribution

![Query Distribution](docs/assets/charts/query_distribution.png)

**→ [Full benchmark methodology and metrics definitions](https://mohammedalaa40123.github.io/agentic_safety/evaluation/)**  
**→ [Browse raw results on Hugging Face](https://huggingface.co/datasets/Mo-alaa/agentic-safety-results)**

---

## Threat Model in Brief

Agentic LLMs operate in a multi-surface threat environment:

```
Prompt → [Prompt Defense] → Attack/Planner → Target LLM → [Response Defense]
                                                               ↓
                                                      Tool-call Decision
                                                               ↓
                                               [Tool Policy Check] → Sandbox Exec
```

Attack surfaces: **prompt injection**, **multi-turn manipulation**, **tool misuse**, **memory poisoning**, and **agent impersonation** — all covered by the OWASP Agentic AI Top-10 taxonomy used in this benchmark.

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/mohammedalaa40123/agentic_safety
cd agentic_safety
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Set provider keys
export GENAI_STUDIO_API_KEY="..."
export OPENAI_API_KEY="..."        # optional
export ANTHROPIC_API_KEY="..."    # optional

# 3. Run a PAIR attack experiment
python run.py \
  --config configs/eval_qwen_pair_attack.yaml \
  --mode attack \
  --goals data/agentic_scenarios_10_mixed.json \
  --use-sandbox \
  --attack-plan pair \
  --output-dir results/demo \
  --verbose

# 4. Regenerate benchmark charts
python scripts/gen_benchmark_charts.py
```

→ **[Full setup and configuration guide →](https://mohammedalaa40123.github.io/agentic_safety/getting-started/quickstart/)**

---

## Key Metrics

| Metric | Name | Definition |
|--------|------|-----------|
| **ASR** | Attack Success Rate | Fraction of malicious goals where attack_success = true |
| **TIR** | Tool Invocation Rate | Harmful tool calls / total tool calls |
| **DBR** | Defense Bypass Rate | Bypassed attacks / total defended attacks |
| **QTJ** | Queries to Jailbreak | Avg query count over successful jailbreaks only |

All metrics are defined in `metrics/` and computed identically across runs.

---

## Attack and Defense Coverage

**Attacks**: PAIR · Crescendo · Prompt Fusion · GCG · Hybrid orchestration  
**Defenses**: JBShield · Gradient Cuff · Progent · StepShield  
**Providers**: OpenAI · Gemini · Anthropic · Ollama · Genai/RCAC HPC  
**Eval taxonomy**: [OWASP Agentic AI Top-10](https://genai.owasp.org/) (AAI-01 through AAI-10)

---

## Reproducibility

Charts and benchmark data are generated from versioned result artifacts:

```bash
python scripts/gen_benchmark_charts.py \
  --results-dir results/agentic_experiments_v2_500 \
  --out-dir docs/assets/charts
```

Filter rules applied:
- Attack = `pair` only
- No defense (`defense_name` is empty)
- Core 4 target models only (see `scripts/gen_benchmark_charts.py: CORE_MODELS`)
- First-occurrence deduplication per goal/model pair

---

## Documentation

| Section | Location |
|---------|----------|
| 🔬 Threat Model & Attacks | [docs/threat-model](https://mohammedalaa40123.github.io/agentic_safety/threat-model/) |
| 🛡️ Defenses | [docs/defenses](https://mohammedalaa40123.github.io/agentic_safety/defenses/) |
| 📊 Evaluation & Results | [docs/evaluation](https://mohammedalaa40123.github.io/agentic_safety/evaluation/) |
| ⚡ Quickstart | [docs/getting-started](https://mohammedalaa40123.github.io/agentic_safety/getting-started/quickstart/) |
| 🔧 Configuration | [docs/configuration](https://mohammedalaa40123.github.io/agentic_safety/getting-started/configuration/) |
| 🏗️ Architecture | [docs/architecture](https://mohammedalaa40123.github.io/agentic_safety/architecture/) |
| 🚀 Deployment | [docs/deployment](https://mohammedalaa40123.github.io/agentic_safety/deployment/) |

---

## Project Layout

```
agentic_safety/
├── run.py                    # CLI orchestrator
├── runner/                   # Config, model build, attack/defense wiring
├── attacks/                  # PAIR, GCG, Crescendo, Prompt-Fusion, Hybrid
├── defenses/                 # JBShield, Gradient Cuff, Progent, StepShield
├── tools/                    # Sandbox tool adapters
├── metrics/                  # ASR / TIR / DBR / QTJ + MetricsCollector
├── configs/                  # YAML experiment presets
├── data/                     # Goal scenarios and datasets
├── server/                   # FastAPI backend + job API
├── frontend/                 # Web UI source
├── scripts/                  # gen_benchmark_charts.py, deploy helpers
├── docs/                     # MkDocs documentation source
│   └── assets/charts/        # Generated chart PNGs + benchmark_data.json
└── results/                  # Experiment output (gitignored)
```

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `GENAI_STUDIO_API_KEY` | Google Genai Studio / RCAC |
| `OPENAI_API_KEY` | OpenAI API |
| `GEMINI_API_KEY` | Gemini API |
| `ANTHROPIC_API_KEY` | Anthropic/Claude API |
| `OLLAMA_CLOUD_API_KEY` | Ollama cloud endpoint |
| `WANDB_API_KEY` | Weights & Biases logging |
| `HF_TOKEN` | Hugging Face Space deployment |
| `HF_RESULTS_DATASET` | Auto-mirror results from HF dataset on startup |
