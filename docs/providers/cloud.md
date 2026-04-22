# Cloud Providers: OpenAI, Gemini, Anthropic

## Configuration

Set provider API keys in your shell environment before running:

```bash
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GENAI_STUDIO_API_KEY="..."
```

Then reference models in your YAML config:

```yaml
models:
  target_model: openai:gpt-4o
  attack_model: gemini:gemini-2.0-flash
  judge_model:  anthropic:claude-3-5-sonnet-20241022
```

## Rate Limits and Retry

Cloud providers impose rate limits. The framework includes retry logic with exponential backoff in `runner/models.py`. Adjust `max_retries` and `retry_backoff` in config if needed:

```yaml
runner:
  max_retries: 5
  retry_backoff: 2.0
```

## Genai Studio (Google)

The `genai:` prefix targets Google's Generative AI Studio endpoint. The `GENAI_STUDIO_API_KEY` environment variable is required:

```yaml
models:
  target_model: genai:gemma-3-27b-it
  attack_model: genai:llama3.3:70b
```

→ Back to [Providers Overview](index.md)
