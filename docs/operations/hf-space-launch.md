# Deploy to Hugging Face Spaces

This project includes a dedicated deployment helper for private Hugging Face Docker Spaces.

## Quick links

- Hugging Face Space: https://huggingface.co/spaces/Mo-alaa/agentic-safety-eval
- Results dataset: https://huggingface.co/datasets/Mo-alaa/agentic-safety-results
- Repository docs: https://mohammedalaa40123.github.io/agentic_safety/

## Prerequisites

- A Hugging Face account
- A valid write token stored in `HF_TOKEN`
- Dockerfile support in the Space (the repo uses a Docker-based Space)

## Deployment script

The deployment helper is `scripts/deploy_hf_space.py`.

```bash
export HF_TOKEN="<your_hf_token>"
python scripts/deploy_hf_space.py --repo <username>/agentic-safety-eval --token "$HF_TOKEN"
```

Add `--no-create` if the Space already exists.

## What this deploys

- the repository code base
- backend server and frontend build assets
- Dockerfile-based runtime on port `7860`

The script keeps the Space lean by ignoring large files, development caches, and most dataset files.

## Required Space secrets

After deployment, configure the following secrets in the Space settings:

- `GENAI_STUDIO_API_KEY`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `ANTHROPIC_API_KEY`
- `OLLAMA_CLOUD_API_KEY`
- `WANDB_API_KEY`

For default Results population from the dataset, also set:

- `HF_RESULTS_DATASET=Mo-alaa/agentic-safety-results`
- `HF_TOKEN=<readable token for private dataset access>`

When enabled, the backend automatically mirrors all files under `results/` in the dataset into local Space storage on first access to `/api/results` routes.

## Local deployment validation

Test the server locally before deploying:

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 7860
```

If the frontend is built, the server will serve static assets from `frontend/dist`.

## Docker build and run

```bash
docker build -t agentic-safety .
docker run --rm -p 7860:7860 agentic-safety
```

## Notes

- Port `7860` is the exposed app port in the Dockerfile and matches the deployed Space port.
- The server API is available at `/api` and includes evaluation launch routes.
- The deployed Space uses the same Python package and frontend build as the local repository.
