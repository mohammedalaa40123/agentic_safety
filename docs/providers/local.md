# Local and Ollama Providers

## Running Ollama Locally

Install [Ollama](https://ollama.com/) and pull a model:

```bash
ollama pull llama3.3:70b
ollama serve   # starts local API at http://localhost:11434
```

Then reference in config:

```yaml
models:
  target_model: ollama:llama3.3:70b
  attack_model: ollama:qwen3-coder:480b
  judge_model:  ollama:nemotron-3-super
```

## Ollama Cloud Endpoint

For remote Ollama endpoints:

```bash
export OLLAMA_CLOUD_API_KEY="..."
```

```yaml
models:
  target_model: ollama:deepseek-v3.2:cloud
```

## Model Cache

Override the model cache directory:

```bash
export AGENTIC_MODEL_CACHE_DIR=/data/model_cache
```

## Performance Notes

- Local models require sufficient VRAM/RAM. DeepSeek-R1-70B requires ~40GB (fp16) or ~20GB (4-bit).
- CPU-only inference is very slow. Use MPS on Apple Silicon or CUDA on Linux with a GPU.
- For latency-sensitive benchmarking, prefer cloud API providers.

→ Back to [Providers Overview](index.md)
