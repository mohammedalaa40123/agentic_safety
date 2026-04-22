"""Background job management for evaluation runs.

Each job launches ``run.py`` as an asyncio subprocess, streams its output
through WebSocket connections, and tracks lifecycle state.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import yaml
from fastapi import WebSocket

from .config import PROJECT_ROOT, RESULTS_DIR

# Optional: persist results to a HF Dataset repo so they survive Space restarts.
# Set HF_RESULTS_DATASET=<owner>/<repo>  (e.g. "Mo-alaa/agentic-safety-results")
# and HF_TOKEN in your Space secrets to enable this.
try:
    from huggingface_hub import HfApi as _HfApi
    _hf_api = _HfApi()
except ImportError:
    _hf_api = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ── Job model ─────────────────────────────────────────────────────────────────

JobStatus = str  # "queued" | "running" | "completed" | "failed" | "cancelled"


def _to_str_list(cfg: Any) -> List[str]:
    """Normalise an attacks/defenses config value to a flat list of name strings.

    Handles three shapes:
    - ``"pair"``                       → ``["pair"]``
    - ``["pair", "crescendo"]``        → ``["pair", "crescendo"]``
    - ``[{"name": "pair", ...}, ...]`` → ``["pair"]``  (skips ``enabled=False``)
    """
    items = cfg if isinstance(cfg, list) else ([cfg] if cfg else [])
    result = []
    for item in items:
        if isinstance(item, dict):
            if item.get("enabled", True):
                result.append(str(item.get("name", "")))
        elif item:
            result.append(str(item))
    return result


def _build_job_name(models: Dict[str, Any], attacks_cfg: Any, defenses_cfg: Any) -> str:
    """Build a short human-readable label for a job card."""
    target = models.get("target_model", "") or ""
    t_short = target.split(":")[-1] if ":" in target else target

    atk_list = _to_str_list(attacks_cfg)
    def_list = _to_str_list(defenses_cfg)
    atk_str = "+".join(atk_list[:4]) + ("…" if len(atk_list) > 4 else "")
    name = f"{t_short} / {atk_str}" if atk_str else t_short
    if def_list:
        name += f" [{'+'.join(def_list)}]"
    return name


@dataclass
class Job:
    id: str
    status: JobStatus
    config_dict: Dict[str, Any]
    env_vars: Dict[str, str]  # provider API keys — never written to disk
    goal_indices: Optional[List[int]]
    dataset_path: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_path: Optional[str] = None
    error: Optional[str] = None
    log_lines: List[str] = field(default_factory=list)
    _process: Optional[asyncio.subprocess.Process] = field(default=None, repr=False)
    _ws_clients: Set[WebSocket] = field(default_factory=set, repr=False)
    _temp_config: Optional[str] = field(default=None, repr=False)

    def to_dict(self, queue_position: Optional[int] = None) -> Dict[str, Any]:
        models = self.config_dict.get("models", {})
        if not isinstance(models, dict):
            models = {}
        attacks_cfg = self.config_dict.get("attacks", [])
        defenses_cfg = self.config_dict.get("defenses", [])

        # Parse progress from last log lines — match goal-level [idx/total] first
        progress: Optional[Dict[str, Any]] = None
        for line in reversed(self.log_lines[-200:]):
            import re
            # Goal-level: "[2/5] Category=... Goal=..."
            m = re.search(r'\[(\d+)/(\d+)\]', line)
            if m:
                current, total = int(m.group(1)), int(m.group(2))
                label = re.sub(r'^\[\d+/\d+\]\s*', '', line).strip()[:120]
                progress = {
                    "current": current,
                    "total": total,
                    "pct": round(current / total * 100) if total > 0 else 0,
                    "label": label,
                }
                break

        # Duration seconds
        duration: Optional[float] = None
        if self.started_at:
            end = self.completed_at or datetime.now(timezone.utc)
            duration = (end - self.started_at).total_seconds()

        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_path": self.result_path,
            "error": self.error,
            "goal_count": len(self.goal_indices) if self.goal_indices is not None else None,
            "dataset": os.path.basename(self.dataset_path),
            # Enriched fields
            "target_model": models.get("target_model", ""),
            "attack_model": models.get("attack_model", ""),
            "judge_model":  models.get("judge_model",  ""),
            "attacks":  _to_str_list(attacks_cfg),
            "defenses": _to_str_list(defenses_cfg),
            "name": _build_job_name(models, attacks_cfg, defenses_cfg),
            "queue_position": queue_position,
            "progress": progress,
            "duration_seconds": round(duration, 1) if duration is not None else None,
            "log_tail": self.log_lines[-80:],
        }


# ── In-memory store ───────────────────────────────────────────────────────────

_jobs: Dict[str, Job] = {}


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def remove_job(job_id: str) -> bool:
    job = _jobs.get(job_id)
    if not job or job.status in {"queued", "running"}:
        return False
    del _jobs[job_id]
    return True


def list_jobs() -> List[Job]:
    return sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)


# ── Scope → indices resolution ────────────────────────────────────────────────

def resolve_goal_indices(scope: Dict[str, Any], total: int) -> Optional[List[int]]:
    """Convert a ``dataset_scope`` object to a flat list of indices.

    Returns None when the full dataset should be used (no filtering needed).
    """
    mode = (scope or {}).get("mode", "full")
    if mode == "full":
        return None
    if mode == "single":
        idx = int(scope["index"])
        return [idx] if idx < total else []
    if mode == "range":
        start = int(scope.get("start", 0))
        end = int(scope.get("end", total - 1))
        return list(range(max(0, start), min(end + 1, total)))
    if mode == "sample":
        k = int(scope.get("n", 10))
        seed = scope.get("seed")
        rng = random.Random(seed)
        population = list(range(total))
        return sorted(rng.sample(population, min(k, total)))
    return None


# ── Job lifecycle ─────────────────────────────────────────────────────────────

async def launch_job(
    config_dict: Dict[str, Any],
    env_vars: Dict[str, str],
    dataset_path: str,
    goal_indices: Optional[List[int]] = None,
) -> Job:
    import uuid

    job_id = str(uuid.uuid4())

    # Build a human-readable output dir name:
    #   smoke_tests/<target_short>_<attacks>_<YYYYMMDD_HHMMSS>_<uuid8>/
    _models = config_dict.get("models", {})
    if not isinstance(_models, dict):
        _models = {}
    _target_raw = str(_models.get("target_model", "unknown") or "unknown")
    # "genai:deepseek-r1:14b" → "deepseek-r1-14b"
    _target_short = _target_raw.replace(":", "-").replace("/", "-")
    if "-" in _target_short:
        # strip provider prefix (e.g. "genai-" → "")
        _parts = _target_short.split("-", 1)
        _known = {"genai", "genaistudio", "openai", "openrouter", "gemini", "anthropic", "ollama", "hf"}
        if _parts[0].lower() in _known:
            _target_short = _parts[1]

    _attacks_raw = config_dict.get("attacks", [])
    _atk_names: List[str] = []
    for _a in (_attacks_raw if isinstance(_attacks_raw, list) else []):
        if isinstance(_a, dict):
            if _a.get("enabled", True):
                _atk_names.append(str(_a.get("name", "")))
        elif isinstance(_a, str):
            _atk_names.append(_a)
    _atk_str = "_".join(_atk_names[:4]) if _atk_names else "run"

    _date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    _folder = f"{_target_short}_{_atk_str}_{_date_str}_{job_id[:8]}"

    # Force the output directory to be job-scoped so we can find the result file later
    config_dict = dict(config_dict)
    config_dict["output_dir"] = os.path.join(RESULTS_DIR, "smoke_tests3", _folder)

    job = Job(
        id=job_id,
        status="queued",
        config_dict=config_dict,
        env_vars=env_vars,
        goal_indices=goal_indices,
        dataset_path=dataset_path,
    )
    _jobs[job_id] = job
    asyncio.create_task(_run_job(job))
    return job


async def _run_job(job: Job) -> None:
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await _broadcast(job, {"type": "status", "status": "running"})

    # Write config to a named temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, dir=PROJECT_ROOT
    ) as f:
        yaml.dump(job.config_dict, f)
        job._temp_config = f.name

    os.makedirs(job.config_dict["output_dir"], exist_ok=True)

    cmd = [sys.executable, "run.py", "--config", job._temp_config]
    if job.goal_indices is not None:
        cmd += ["--goal-indices", ",".join(str(i) for i in job.goal_indices)]

    env = {**os.environ, **job.env_vars}

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
            cwd=PROJECT_ROOT,
        )
        job._process = proc

        assert proc.stdout is not None
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            job.log_lines.append(line)
            await _broadcast(job, {"type": "log", "line": line})

        await proc.wait()

        if job.status != "cancelled":
            job.status = "completed" if proc.returncode == 0 else "failed"
            if proc.returncode != 0:
                job.error = f"Process exited with code {proc.returncode}"

    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        logger.exception(f"Job {job.id} failed with exception")
    finally:
        job.completed_at = datetime.now(timezone.utc)
        _cleanup_temp(job)
        _find_result_file(job)
        await asyncio.get_event_loop().run_in_executor(None, _upload_result_to_hf, job)
        await _broadcast(job, {"type": "done", "status": job.status, "result_path": job.result_path})


def _cleanup_temp(job: Job) -> None:
    if job._temp_config and os.path.exists(job._temp_config):
        try:
            os.unlink(job._temp_config)
        except OSError:
            pass
    job._temp_config = None


def _upload_result_to_hf(job: Job) -> None:
    """Push the result JSON (and its sibling CSV if present) to a HF Dataset repo.

    Requires env vars:
      HF_RESULTS_DATASET  — e.g. "Mo-alaa/agentic-safety-results"
      HF_TOKEN            — write-access token for the dataset repo
    """
    dataset_repo = os.getenv("HF_RESULTS_DATASET", "").strip()
    hf_token = os.getenv("HF_TOKEN", "").strip()
    if not dataset_repo or not hf_token or _hf_api is None:
        return
    if not job.result_path or not os.path.isfile(job.result_path):
        return

    out_dir = os.path.dirname(job.result_path)
    folder_name = os.path.basename(out_dir)
    files_to_upload = [f for f in os.listdir(out_dir)
                       if f.endswith(".json") or f.endswith(".csv")]
    uploaded: list[str] = []
    for fname in files_to_upload:
        local_path = os.path.join(out_dir, fname)
        path_in_repo = f"results/{folder_name}/{fname}"
        try:
            _hf_api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=path_in_repo,
                repo_id=dataset_repo,
                repo_type="dataset",
                token=hf_token,
                commit_message=f"[auto] job {job.id[:8]} — {job.status}",
            )
            uploaded.append(path_in_repo)
        except Exception as exc:
            logger.warning("HF upload failed for %s: %s", local_path, exc)
    if uploaded:
        logger.info("Uploaded %d file(s) to HF dataset %s: %s", len(uploaded), dataset_repo, uploaded)


def _find_result_file(job: Job) -> None:
    out_dir = job.config_dict.get("output_dir", "")
    if not os.path.isdir(out_dir):
        return
    json_files = sorted(
        (f for f in os.listdir(out_dir) if f.endswith(".json")),
        reverse=True,
    )
    if json_files:
        job.result_path = os.path.join(out_dir, json_files[0])


async def _broadcast(job: Job, payload: Dict[str, Any]) -> None:
    msg = json.dumps(payload)
    for ws in list(job._ws_clients):
        try:
            await ws.send_text(msg)
        except Exception:
            job._ws_clients.discard(ws)


async def cancel_job(job_id: str) -> bool:
    job = _jobs.get(job_id)
    if not job or job.status not in {"queued", "running"}:
        return False
    job.status = "cancelled"
    if job._process:
        try:
            job._process.terminate()
        except ProcessLookupError:
            pass
    return True


async def cancel_all_on_shutdown() -> None:
    for job in list(_jobs.values()):
        if job.status in {"queued", "running"}:
            await cancel_job(job.id)
