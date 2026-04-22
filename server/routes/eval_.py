"""Evaluation launch + job monitoring routes.

POST /api/eval/launch              → start a new eval job
GET  /api/eval/jobs                → list all jobs
GET  /api/eval/{job_id}            → job details + last 200 log lines
DELETE /api/eval/{job_id}          → cancel a job
GET  /api/eval/{job_id}/results    → structured results (reads result JSON)
WS   /api/eval/{job_id}/stream     → live log streaming
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from server import jobs as job_store
from server.config import DATA_DIR

router = APIRouter(prefix="/eval", tags=["eval"])


# ── Request models ─────────────────────────────────────────────────────────────

class DatasetScope(BaseModel):
    mode: str = "full"           # full | single | range | sample
    index: Optional[int] = None  # mode=single
    start: Optional[int] = None  # mode=range
    end: Optional[int] = None    # mode=range
    n: Optional[int] = None      # mode=sample
    seed: Optional[int] = None   # mode=sample


class ProviderCredential(BaseModel):
    provider_id: str
    api_key: str = ""
    base_url: str = ""


class LaunchRequest(BaseModel):
    # Core model selection
    target_provider: str
    target_model: str
    attack_provider: str = ""
    attack_model: str = ""
    judge_provider: str = ""
    judge_model: str = ""
    # Dataset
    dataset: str = "agentic_scenarios_100_labeled.json"
    dataset_scope: DatasetScope = Field(default_factory=DatasetScope)
    # Attack / defense plan
    # Each entry is either a plain name (str) or {name, params} dict
    attacks: List[Any] = Field(default_factory=list)
    defenses: List[str] = Field(default_factory=list)
    # Per-defense tuning params, keyed by defense name
    defense_params: Dict[str, Any] = Field(default_factory=dict)
    # Rate limiting
    calls_per_minute: int = 0
    # W&B logging
    wandb_enabled: bool = False
    wandb_project: str = "agentic-safety"
    wandb_entity: str = ""
    wandb_run_name: str = ""
    # API credentials (never persisted)
    credentials: List[ProviderCredential] = Field(default_factory=list)
    # Pass-through extra config keys
    extra: Dict[str, Any] = Field(default_factory=dict)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_config(req: LaunchRequest, dataset_path: str) -> Dict[str, Any]:
    """Translate the launch request into a run.py-compatible YAML dict."""

    def _model_str(provider: str, model: str) -> str:
        if not provider or not model:
            return ""
        # Already prefixed with a known provider namespace
        known_prefixes = ("genai:", "genai_rcac:", "genaistudio:", "openai:", "openrouter:",
                          "gemini:", "anthropic:", "ollama:", "hf:")
        if any(model.lower().startswith(p) for p in known_prefixes):
            return model
        # ollama_cloud is just ollama: prefix at runtime
        if provider.lower() == "ollama_cloud":
            return f"ollama:{model}"
        return f"{provider}:{model}"

    target = _model_str(req.target_provider, req.target_model)
    attack = _model_str(req.attack_provider, req.attack_model) if req.attack_provider else ""
    judge  = _model_str(req.judge_provider, req.judge_model) if req.judge_provider else ""

    cpm = req.calls_per_minute or 0
    models_cfg: Dict[str, Any] = {"target_model": target}
    if attack:
        models_cfg["attack_model"] = attack
    if judge:
        models_cfg["judge_model"] = judge
    if cpm:
        models_cfg["attack_calls_per_minute"] = cpm
        models_cfg["target_calls_per_minute"] = cpm
        models_cfg["judge_calls_per_minute"] = cpm

    cfg: Dict[str, Any] = {
        "goals_path": dataset_path,
        "models": models_cfg,
        "sandbox": {
            "enabled": True,
            "sandbox_root": "/tmp/agentic_sandbox",
            "tools": ["file_io", "code_exec", "web_browse", "network"],
            "code_timeout": 10,
            "code_exec_backend": "auto",
            "code_exec_require_isolation": False,
            "web_timeout": 10,
            "net_sandbox": True,
            "web_sandbox": True,
            "max_steps": 5,
        },
    }
    if req.attacks:
        cfg["attacks"] = req.attacks
    if req.defenses:
        defense_cfg: Dict[str, Any] = {"enabled": True, "active": req.defenses}
        if req.defense_params:
            defense_cfg.update(req.defense_params)
        cfg["defenses"] = defense_cfg
    if req.wandb_enabled:
        cfg["wandb"] = {
            "enabled": True,
            "project": req.wandb_project or "agentic-safety",
            "entity": req.wandb_entity or None,
            "run_name": req.wandb_run_name or None,
        }
    cfg.update(req.extra)
    return cfg


def _build_env_vars(credentials: List[ProviderCredential]) -> Dict[str, str]:
    """Map provider credential objects to environment variable names."""
    ENV_MAP = {
        "genai_rcac": "RCAC_GENAI_API_KEY",
        "genai": "GENAI_STUDIO_API_KEY",
        "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        # ollama.com cloud API key — when set, OllamaTarget auto-routes to api.ollama.com
        "ollama": "OLLAMA_CLOUD_API_KEY",
        "ollama_cloud": "OLLAMA_CLOUD_API_KEY",
    }
    env: Dict[str, str] = {}
    for cred in credentials:
        pid = cred.provider_id.lower()
        if cred.api_key:
            if pid == "wandb":
                env["WANDB_API_KEY"] = cred.api_key
            elif pid in {"ollama_cloud"}:
                env["OLLAMA_CLOUD_API_KEY"] = cred.api_key
            else:
                var = ENV_MAP.get(pid, f"{pid.upper()}_API_KEY")
                env[var] = cred.api_key
        if cred.base_url and pid in {"genai", "genaistudio", "genai_rcac", "ollama"}:
            if pid == "ollama":
                # OllamaTarget reads OLLAMA_HOST (and OLLAMA_BASE_URL as fallback)
                env["OLLAMA_HOST"] = cred.base_url.rstrip("/")
                env["OLLAMA_BASE_URL"] = cred.base_url.rstrip("/")
            else:
                env["GENAI_STUDIO_API_URL"] = (
                    cred.base_url.rstrip("/") + "/chat/completions"
                )
    return env


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/launch")
async def launch_eval(req: LaunchRequest) -> Dict[str, Any]:
    # Resolve dataset
    dataset_path = os.path.join(DATA_DIR, req.dataset)
    if not os.path.exists(dataset_path):
        raise HTTPException(status_code=404, detail=f"Dataset '{req.dataset}' not found in data/")

    # Resolve goal indices
    with open(dataset_path) as f:
        dataset = json.load(f)
    total = len(dataset) if isinstance(dataset, list) else 0

    indices = job_store.resolve_goal_indices(req.dataset_scope.model_dump(), total)

    config_dict = _build_config(req, dataset_path)
    env_vars = _build_env_vars(req.credentials)

    job = await job_store.launch_job(
        config_dict=config_dict,
        env_vars=env_vars,
        dataset_path=dataset_path,
        goal_indices=indices,
    )
    return job.to_dict()


@router.get("/jobs")
def list_jobs():
    all_jobs = job_store.list_jobs()
    # Assign queue positions (1-indexed) only to queued jobs, in FIFO order
    queue_jobs = [j for j in reversed(all_jobs) if j.status == "queued"]
    queue_pos = {j.id: (i + 1) for i, j in enumerate(queue_jobs)}
    return [j.to_dict(queue_position=queue_pos.get(j.id)) for j in all_jobs]


@router.get("/{job_id}")
def get_job(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.delete("/{job_id}")
async def cancel_or_remove_job(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in {"queued", "running"}:
        await job_store.cancel_job(job_id)
        return {"cancelled": True}
    # Terminal state: remove from store entirely
    job_store.remove_job(job_id)
    return {"removed": True}


@router.get("/{job_id}/results")
def get_results(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.result_path or not os.path.exists(job.result_path):
        raise HTTPException(status_code=404, detail="Results not yet available")
    with open(job.result_path) as f:
        return json.load(f)


@router.websocket("/{job_id}/stream")
async def stream_logs(websocket: WebSocket, job_id: str):
    await websocket.accept()
    job = job_store.get_job(job_id)
    if not job:
        await websocket.send_text(json.dumps({"type": "error", "message": "Job not found"}))
        await websocket.close()
        return

    # Replay buffered logs for late joiners
    for line in job.log_lines:
        try:
            await websocket.send_text(json.dumps({"type": "log", "line": line}))
        except Exception:
            return

    if job.status in {"completed", "failed", "cancelled"}:
        await websocket.send_text(json.dumps({"type": "done", "status": job.status}))
        await websocket.close()
        return

    job._ws_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; client can send pings
    except WebSocketDisconnect:
        pass
    finally:
        job._ws_clients.discard(websocket)
