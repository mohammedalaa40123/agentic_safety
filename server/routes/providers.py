"""Provider API routes.

GET  /api/providers                → list provider metadata
POST /api/providers/{id}/validate  → validate credentials
GET  /api/providers/{id}/models    → list available models
POST /api/providers/ollama/pull    → pull a model from Ollama registry
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException

from runner.providers.registry import (
    get_provider_info,
    list_provider_models,
    validate_provider_key,
)
from runner.providers.ollama import OllamaProvider

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
def list_providers():
    return get_provider_info()


@router.post("/{provider_id}/validate")
def validate_key(
    provider_id: str,
    body: Dict[str, Any] = Body(default={}),
):
    api_key = body.get("api_key", "")
    base_url = body.get("base_url", "")
    ok = validate_provider_key(provider_id, api_key=api_key, base_url=base_url)
    return {"valid": ok}


@router.get("/{provider_id}/models")
def get_models(provider_id: str, api_key: str = "", base_url: str = ""):
    models = list_provider_models(provider_id, api_key=api_key, base_url=base_url)
    return [
        {"id": m.id, "name": m.name, "provider": m.provider, "context_length": m.context_length}
        for m in models
    ]


@router.post("/ollama/pull")
def pull_model(body: Dict[str, Any] = Body(...)):
    """Ask a running Ollama server to pull a model by name."""
    model_name = body.get("model")
    base_url = body.get("base_url", "")
    if not model_name:
        raise HTTPException(status_code=422, detail="'model' is required")
    provider = OllamaProvider("__pull__", base_url=base_url)
    ok = provider.pull_model(model_name)
    return {"accepted": ok}
