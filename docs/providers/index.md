# Providers

## Supported Provider Backends

This framework supports five provider categories. The provider is configured via the `models` section of your YAML config.

| Provider | Type | Key requirement |
|----------|------|----------------|
| OpenAI | Cloud API | `OPENAI_API_KEY` |
| Gemini | Cloud API | `GEMINI_API_KEY` |
| Anthropic | Cloud API | `ANTHROPIC_API_KEY` |
| Genai Studio | Cloud API | `GENAI_STUDIO_API_KEY` |
| Ollama | Local / Cloud | `OLLAMA_CLOUD_API_KEY` (cloud) or local server |
| RCAC HPC | HPC cluster | `GENAI_STUDIO_API_KEY` + cluster endpoint |

## Provider String Format

Provider model strings follow the pattern `provider:model-name:tag`:

```yaml
models:
  attack_model: genai:llama3.3:70b       # Google Genai Studio
  target_model: genai_rcac:deepseek-r1:14b  # Purdue RCAC HPC
  judge_model:  ollama:nemotron-3-super   # Local Ollama
```

## Provider-Specific Guidance

→ [Cloud providers (OpenAI, Gemini, Anthropic)](cloud.md)  
→ [Local and Ollama](local.md)  
→ [RCAC HPC setup](rcac.md)
