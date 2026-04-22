# Hugging Face Space Deployment

## Quick Links

- 🤗 [Live Space](https://huggingface.co/spaces/Mo-alaa/agentic-safety-eval) — interactive frontend + results API
- 🤗 [Results Dataset](https://huggingface.co/datasets/Mo-alaa/agentic-safety-results) — raw experiment output

## Prerequisites

- A Hugging Face account with write access
- `HF_TOKEN` set in your environment
- Dockerfile-based Space (this repo uses Docker)

## Deploy

```bash
export HF_TOKEN="<your_hf_token>"
python scripts/deploy_hf_space.py \
  --repo Mo-alaa/agentic-safety-eval \
  --token "$HF_TOKEN"
```

Add `--no-create` if the Space already exists and you are pushing an update.

## What Gets Deployed

- Full repository codebase (excluding large dev artifacts)
- FastAPI backend (`server/`) and built frontend assets (`frontend/dist`)
- Dockerfile — Space runs the container on port `7860`

## Required Space Secrets

Configure these in the Hugging Face Space settings after deployment:

| Secret | Purpose |
|--------|---------|
| `GENAI_STUDIO_API_KEY` | Primary inference API |
| `OPENAI_API_KEY` | OpenAI model access |
| `GEMINI_API_KEY` | Gemini model access |
| `ANTHROPIC_API_KEY` | Anthropic model access |
| `OLLAMA_CLOUD_API_KEY` | Ollama cloud endpoint |
| `WANDB_API_KEY` | Experiment tracking |
| `HF_RESULTS_DATASET` | Set to `Mo-alaa/agentic-safety-results` to auto-mirror results |
| `HF_TOKEN` | Readable token for private dataset access |

When `HF_RESULTS_DATASET` is set, the backend auto-mirrors all files under `results/` from the dataset into local Space storage on first access to `/api/results` routes.

## Local Validation

Test the server before deploying:

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 7860
```

Or with Docker:

```bash
docker build -t agentic-safety .
docker run --rm -p 7860:7860 agentic-safety
```

## API Routes

The deployed Space exposes:

- `/api/results` — list available result directories
- `/api/results/{id}` — fetch a specific result's summary and records
- `/api/jobs` — job management for experiment launches

→ [Results browsing via HF Dataset](https://huggingface.co/datasets/Mo-alaa/agentic-safety-results)
