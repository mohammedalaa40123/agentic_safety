"""Results file browser routes.

GET /api/results              → list all result files across results/
GET /api/results/summary      → lightweight summary per file (model, attack, MIR, count)
GET /api/results/{rel_path}   → get a specific result JSON or CSV file
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from server.config import RESULTS_DIR

try:
    from huggingface_hub import HfApi, hf_hub_download
except ImportError:  # pragma: no cover
    HfApi = None  # type: ignore[assignment]
    hf_hub_download = None  # type: ignore[assignment]

router = APIRouter(prefix="/results", tags=["results"])

_SYNC_LOCK = threading.Lock()
_LAST_SYNC_TS = 0.0
_SYNC_RETRY_SEC = int(os.getenv("HF_RESULTS_SYNC_RETRY_SEC", "120"))
_SYNC_DONE = False


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _results_dataset_repo() -> str:
    # Defaults to your shared dataset so HF Space can show prior runs out of the box.
    return os.getenv("HF_RESULTS_DATASET", "Mo-alaa/agentic-safety-results").strip()


def _hf_token() -> Optional[str]:
    token = os.getenv("HF_TOKEN", "").strip()
    if token:
        return token
    token = os.getenv("HUGGING_FACE_HUB_TOKEN", "").strip()
    return token or None


def _download_all_results_from_hf(force: bool = False) -> Dict[str, Any]:
    """Mirror all dataset files under ``results/`` into local ``RESULTS_DIR``.

    This keeps the Results page populated on HF Space cold starts, where local
    ephemeral storage may begin empty.
    """
    global _LAST_SYNC_TS, _SYNC_DONE

    if not force and not _env_flag("HF_RESULTS_AUTO_SYNC", True):
        return {"status": "skipped", "reason": "HF_RESULTS_AUTO_SYNC disabled"}

    repo_id = _results_dataset_repo()
    if not repo_id:
        return {"status": "skipped", "reason": "HF_RESULTS_DATASET not set"}
    if HfApi is None or hf_hub_download is None:
        return {"status": "skipped", "reason": "huggingface_hub unavailable"}

    now = time.time()
    if not force and _SYNC_DONE:
        return {"status": "ok", "repo": repo_id, "downloaded": 0, "updated": 0, "reused": 0, "failed": 0}
    if not force and (now - _LAST_SYNC_TS) < _SYNC_RETRY_SEC:
        return {"status": "skipped", "reason": "cooldown"}

    with _SYNC_LOCK:
        now = time.time()
        if not force and _SYNC_DONE:
            return {"status": "ok", "repo": repo_id, "downloaded": 0, "updated": 0, "reused": 0, "failed": 0}
        if not force and (now - _LAST_SYNC_TS) < _SYNC_RETRY_SEC:
            return {"status": "skipped", "reason": "cooldown"}
        _LAST_SYNC_TS = now

        token = _hf_token()
        api = HfApi(token=token)

        try:
            repo_files = api.list_repo_files(repo_id=repo_id, repo_type="dataset", token=token)
        except Exception as exc:
            return {"status": "error", "repo": repo_id, "error": str(exc)}

        result_files = [
            p for p in repo_files
            if p.startswith("results/") and (p.endswith(".json") or p.endswith(".csv"))
        ]
        result_files.sort()

        downloaded = 0
        updated = 0
        reused = 0
        failed = 0

        os.makedirs(RESULTS_DIR, exist_ok=True)

        for path_in_repo in result_files:
            rel = path_in_repo[len("results/"):]
            if not rel:
                continue
            target_path = os.path.join(RESULTS_DIR, rel)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            try:
                src_path = hf_hub_download(
                    repo_id=repo_id,
                    repo_type="dataset",
                    filename=path_in_repo,
                    token=token,
                )
                downloaded += 1
                src_size = os.path.getsize(src_path)
                if os.path.exists(target_path) and os.path.getsize(target_path) == src_size:
                    reused += 1
                    continue
                shutil.copy2(src_path, target_path)
                updated += 1
            except Exception:
                failed += 1

        _SYNC_DONE = failed == 0
        return {
            "status": "ok" if failed == 0 else "partial",
            "repo": repo_id,
            "downloaded": downloaded,
            "updated": updated,
            "reused": reused,
            "failed": failed,
        }


def _ensure_hf_results_mirrored() -> None:
    _download_all_results_from_hf(force=False)

def _try_parse_json_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in '{[':
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _try_parse_scalar(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    lowered = text.lower()
    if lowered == 'true':
        return True
    if lowered == 'false':
        return False
    if lowered == 'null':
        return None
    if re.fullmatch(r'-?\d+', text):
        try:
            return int(text)
        except ValueError:
            return value
    if re.fullmatch(r'-?\d+\.\d+', text):
        try:
            return float(text)
        except ValueError:
            return value
    return value


def _try_parse_value(value: Any) -> Any:
    parsed = _try_parse_json_string(value)
    if isinstance(parsed, str):
        parsed = _try_parse_scalar(parsed)
    return parsed


def _normalize_result_data(data: Any) -> Any:
    if isinstance(data, list):
        return [_normalize_result_data(item) for item in data]
    if isinstance(data, dict):
        return {key: _normalize_result_data(_try_parse_value(val)) for key, val in data.items()}
    return _try_parse_value(data)


@router.get("")
def list_results() -> List[Dict[str, Any]]:
    _ensure_hf_results_mirrored()
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = []
    for root, _, files in os.walk(RESULTS_DIR):
        for fname in sorted(files):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, RESULTS_DIR)
            out.append(
                {
                    "path": rel,
                    "size_bytes": os.path.getsize(fpath),
                    "modified": os.path.getmtime(fpath),
                }
            )
    return sorted(out, key=lambda x: x["modified"], reverse=True)


def _coerce_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() == "true"
    return bool(v)


def _extract_records(data: Any) -> List[Dict[str, Any]]:
    """Extract a flat list of experiment records from either format:

    - **List format** (legacy per-model exports): ``[{...}, {...}, ...]``
    - **Dict format** (new run.py output): ``{"records": [...], "summary": {...}, ...}``
    """
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        recs = data.get("records", [])
        if isinstance(recs, list):
            return [r for r in recs if isinstance(r, dict)]
    return []


@router.get("/summary")
def results_summary() -> List[Dict[str, Any]]:
    """Return lightweight per-file metadata (model, attack, defense, MIR, count) without full records."""
    _ensure_hf_results_mirrored()
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out: List[Dict[str, Any]] = []
    for root, _, files in os.walk(RESULTS_DIR):
        for fname in sorted(files):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, RESULTS_DIR)
            try:
                with open(fpath, encoding="utf-8") as f:
                    data = json.load(f)
                records = _extract_records(data)
                if not records:
                    continue
                first: Dict[str, Any] = records[0]
                record_count = len(records)
                succeeded = sum(1 for r in records if _coerce_bool(r.get("attack_success", False)))
                MIR = succeeded / record_count if record_count > 0 else 0.0
                out.append({
                    "path": rel,
                    "size_bytes": os.path.getsize(fpath),
                    "modified": os.path.getmtime(fpath),
                    "target_model": first.get("target_model", ""),
                    "attack_name": first.get("attack_name", ""),
                    "attack_model": first.get("attack_model", ""),
                    "judge_model": first.get("judge_model", ""),
                    "defense_name": first.get("defense_name", "") or "none",
                    "record_count": record_count,
                    "succeeded": succeeded,
                    "MIR": round(MIR, 4),
                })
            except Exception:
                continue
    return sorted(out, key=lambda x: x["modified"], reverse=True)


@router.get("/leaderboard")
def results_leaderboard() -> List[Dict[str, Any]]:
    """Aggregate all result files into per-(target_model, attack, defense) leaderboard rows.

    Each row includes: MIR, Task_Success, TIR, DBR, QTJ, avg_duration, avg_queries,
    total_tool_calls, avg_correct_tool_calls, avg_wrong_tool_calls, plus model/attack/defense info.
    """
    _ensure_hf_results_mirrored()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # key → aggregated stats
    groups: Dict[str, Dict[str, Any]] = {}

    for root, _, files in os.walk(RESULTS_DIR):
        for fname in sorted(files):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    data = json.load(f)
                records = _extract_records(data)
                if not records:
                    continue
                first = records[0]

                # Determine file-level defaults (attack_model, judge_model come from first record)
                file_attack_model = str(first.get("attack_model", "") or "")
                file_judge_model  = str(first.get("judge_model",  "") or "")

                # Group EACH record by its own (target_model, attack_name, defense_name) so that
                # multi-attack result files don't collapse everything under the first attack.
                for rec in records:
                    target_model = str(rec.get("target_model", "") or "unknown")
                    attack_name  = str(rec.get("attack_name",  "") or "baseline")
                    defense_name = str(rec.get("defense_name", "") or "none") or "none"

                    key = f"{target_model}||{attack_name}||{defense_name}"
                    if key not in groups:
                        groups[key] = {
                            "target_model": target_model,
                            "attack_name": attack_name,
                            "defense_name": defense_name,
                            "attack_model": str(rec.get("attack_model", "") or file_attack_model),
                            "judge_model":  str(rec.get("judge_model",  "") or file_judge_model),
                            "files": [],
                            "_recs": [],
                        }
                    rel = os.path.relpath(fpath, RESULTS_DIR)
                    if rel not in groups[key]["files"]:
                        groups[key]["files"].append(rel)
                    groups[key]["_recs"].append(rec)

            except Exception:
                continue

    rows: List[Dict[str, Any]] = []
    for key, grp in groups.items():
        recs = grp.pop("_recs")
        n = len(recs)
        if n == 0:
            continue

        def _f(r: Dict[str, Any], k: str, default: float = 0.0) -> float:
            v = r.get(k, default)
            try:
                return float(v) if v is not None else default
            except (TypeError, ValueError):
                return default

        n_attacked    = sum(1 for r in recs if _coerce_bool(r.get("attack_success", False)))
        n_task_ok     = sum(1 for r in recs if _coerce_bool(r.get("task_success", False)))
        n_malicious   = sum(1 for r in recs if _coerce_bool(r.get("is_malicious", False)))
        n_def_bypass  = sum(1 for r in recs if _coerce_bool(r.get("defense_bypassed", False)))

        total_tool_calls = sum(_f(r, "tool_calls_total") for r in recs)
        total_correct    = sum(_f(r, "tool_calls_correct") for r in recs)
        total_wrong      = sum(_f(r, "tool_calls_wrong") for r in recs)
        total_harmful    = sum(_f(r, "tool_calls_harmful") for r in recs)
        total_queries    = sum(_f(r, "queries") for r in recs)
        total_duration   = sum(_f(r, "duration") for r in recs)

        # Queries to jailbreak — average over jailbroken records only
        jb_queries = [_f(r, "queries") for r in recs if _coerce_bool(r.get("attack_success", False))]

        # DBR: fraction of malicious records where defense was bypassed
        n_malicious_with_defense = sum(
            1 for r in recs
            if _coerce_bool(r.get("is_malicious", False)) and grp["defense_name"] != "none"
        )

        row = {
            **{k: v for k, v in grp.items() if k != "files"},
            "source_files": grp["files"],
            "total_experiments": n,
            "MIR":        round(n_attacked / n, 4) if n else 0.0,
            "Task_Success": round(n_task_ok / n, 4) if n else 0.0,
            "TIR":        round(total_tool_calls / n, 4) if n else 0.0,
            "DBR":        round(n_def_bypass / n_malicious_with_defense, 4)
                          if n_malicious_with_defense else 0.0,
            "QTJ":        round(sum(jb_queries) / len(jb_queries), 4) if jb_queries else None,
            "avg_duration": round(total_duration / n, 4) if n else 0.0,
            "avg_queries":  round(total_queries / n, 4)  if n else 0.0,
            "total_tool_calls":        int(total_tool_calls),
            "avg_correct_tool_calls":  round(total_correct  / n, 4) if n else 0.0,
            "avg_wrong_tool_calls":    round(total_wrong     / n, 4) if n else 0.0,
            "avg_harmful_tool_calls":  round(total_harmful   / n, 4) if n else 0.0,
            "n_malicious": n_malicious,
        }
        rows.append(row)

    # Sort: descending MIR
    rows.sort(key=lambda r: r["MIR"], reverse=True)
    return rows


@router.post("/sync")
def sync_results_from_hf() -> Dict[str, Any]:
    """Force-refresh local results from HF dataset storage."""
    return _download_all_results_from_hf(force=True)


@router.delete("/{rel_path:path}")
def delete_result(rel_path: str) -> Dict[str, str]:
    """Delete a result JSON (and its sibling CSV if present)."""
    safe_root = os.path.realpath(RESULTS_DIR)
    full_path = os.path.realpath(os.path.join(RESULTS_DIR, rel_path))
    if not full_path.startswith(safe_root + os.sep):
        raise HTTPException(status_code=400, detail="Path traversal rejected")
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Result file not found")

    os.remove(full_path)

    # Also remove sibling CSV if it exists
    csv_path = os.path.splitext(full_path)[0] + ".csv"
    if os.path.exists(csv_path):
        os.remove(csv_path)

    # Remove parent directory if now empty
    parent = os.path.dirname(full_path)
    try:
        if os.path.isdir(parent) and not os.listdir(parent):
            os.rmdir(parent)
    except OSError:
        pass

    return {"deleted": rel_path}


@router.get("/{rel_path:path}")
def get_result(rel_path: str) -> Any:
    # Prevent path traversal
    safe_root = os.path.realpath(RESULTS_DIR)
    full_path = os.path.realpath(os.path.join(RESULTS_DIR, rel_path))
    if not full_path.startswith(safe_root + os.sep):
        raise HTTPException(status_code=400, detail="Path traversal rejected")
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Result file not found")

    if full_path.lower().endswith('.json'):
        with open(full_path) as f:
            return _normalize_result_data(json.load(f))

    # if full_path.lower().endswith('.csv'):
    #     with open(full_path, newline='') as f:
    #         reader = csv.DictReader(f)
    #         return _normalize_result_data([row for row in reader])

    raise HTTPException(status_code=415, detail="Unsupported result file type")
