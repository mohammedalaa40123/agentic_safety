# Quickstart

## 0) Prerequisites

- **OS**: macOS or Linux (required for sandbox isolation)
- **Python**: 3.10+
- **Isolation (Optional)**: `bubblewrap` (bwrap) or Docker, required for tool-execution sandboxing.

## 1) Clone and setup environment

```bash
# Clone the repository
git clone https://github.com/mohammedalaa40123/agentic_safety.git
cd agentic_safety

# Create and activate the Python environment
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

Install server support if you plan to run the FastAPI backend:

```bash
pip install -e .[server]
```

Install documentation dependencies:

```bash
pip install -r requirements-docs.txt
```

## 2) Set provider API keys

Export the keys required by your chosen model backend:

```bash
export OPENAI_API_KEY="..."            # OpenAI models
export ANTHROPIC_API_KEY="..."         # Claude models
export GEMINI_API_KEY="..."            # Google Gemini (standard API)
export GENAI_STUDIO_API_KEY="..."      # Google Vertex AI / GenAI Studio (RCAC)
export OLLAMA_CLOUD_API_KEY="..."      # Hosted Ollama endpoint (e.g., https://ollama.com/api)
export WANDB_API_KEY="..."             # Optional: only if wandb.enabled: true
```

## 3) Run a baseline smoke experiment

```bash
python run.py --config configs/eval_qwen_baseline.yaml --verbose
```

## 4) Run a sandboxed attack experiment

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

## 5) Run a server-backed evaluation

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 7860
```

If you have built the frontend, the backend will serve the `frontend/dist` bundle.

## 6) Verify outputs

The configured `output_dir` contains:

- `*.log` run logs
- `results_*.csv` experiment records
- `results_*.json` summary and detail exports

## 7) Run tests

```bash
pytest -q tests/
```

## 8) Preview docs locally

```bash
mkdocs serve
```

Then open http://127.0.0.1:8000.
