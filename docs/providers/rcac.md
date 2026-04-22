# RCAC HPC Provider

The `genai_rcac:` prefix targets the Purdue RCAC (Research Computing) HPC cluster's Genai inference endpoint. This is used for large-scale benchmark runs (e.g., the `agentic_experiments_v2_500` dataset).

## Setup

```bash
export GENAI_STUDIO_API_KEY="<your_rcac_api_key>"
```

```yaml
models:
  target_model: genai_rcac:deepseek-r1:14b
  attack_model: genai_rcac:llama3.2:latest
  judge_model:  genai_rcac:llama3.3:70b
```

## Available Models (RCAC)

| Model string | Notes |
|-------------|-------|
| `genai_rcac:deepseek-r1:14b` | 14B parameter reasoning model |
| `genai_rcac:deepseek-r1:70b` | 70B parameter reasoning model |
| `genai_rcac:llama3.3:70b` | Llama 3.3 70B — primary judge model |
| `genai_rcac:llama3.2:latest` | Llama 3.2 latest |
| `genai_rcac:gpt-oss:120b` | GPT OSS 120B (limited availability) |

## Running Parallel Jobs

For large benchmark runs, use the job launcher in `jobs/` or submit SLURM jobs directly. See `scripts/` for batch launcher helpers.

→ Back to [Providers Overview](index.md)
