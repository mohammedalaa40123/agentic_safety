# Quickstart

## 1) Create and activate environment

```bash
cd /depot/davisjam/data/mohamed/agentic_safety
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## 2) Run a baseline smoke experiment

```bash
python run.py --config configs/eval_qwen_baseline.yaml --verbose
```

## 3) Run an agentic attack experiment

```bash
python run.py --config configs/eval_genai_pair_localjudge_100.yaml --verbose
```

## 4) Results output

Outputs are written under the configured output directory and include:

- Timestamped log file
- CSV records
- JSON summary and per-record details

## 5) Build docs locally

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

Site preview is available at http://127.0.0.1:8000.
