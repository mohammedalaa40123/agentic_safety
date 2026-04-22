"""Dataset management routes.

GET    /api/datasets                    → list dataset files
GET    /api/datasets/{name}             → preview (first N entries)
GET    /api/datasets/{name}/sample/{i}  → single entry by index
POST   /api/datasets/upload             → upload a new JSON dataset
DELETE /api/datasets/{name}             → delete a dataset
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from server.config import DATA_DIR, MAX_UPLOAD_BYTES, MAX_UPLOAD_ENTRIES

router = APIRouter(prefix="/datasets", tags=["datasets"])

_VALID_NAME = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}\.json$")


def _safe_path(name: str) -> str:
    if not _VALID_NAME.match(name):
        raise HTTPException(status_code=400, detail=f"Invalid dataset name: {name!r}")
    path = os.path.realpath(os.path.join(DATA_DIR, name))
    if not path.startswith(os.path.realpath(DATA_DIR) + os.sep):
        raise HTTPException(status_code=400, detail="Path traversal rejected")
    return path


@router.get("")
def list_datasets() -> List[Dict[str, Any]]:
    os.makedirs(DATA_DIR, exist_ok=True)
    out = []
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(DATA_DIR, fname)
        try:
            size = os.path.getsize(fpath)
            with open(fpath) as f:
                data = json.load(f)
            count = len(data) if isinstance(data, list) else None
        except Exception:
            count = None
            size = 0
        out.append({"name": fname, "count": count, "size_bytes": size})
    return out


@router.get("/{name}")
def preview_dataset(name: str, limit: int = 5) -> Dict[str, Any]:
    path = _safe_path(name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Dataset not found")
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise HTTPException(status_code=422, detail="Dataset must be a JSON array")
    return {"name": name, "count": len(data), "preview": data[: max(1, limit)]}


@router.get("/{name}/sample/{index}")
def get_entry(name: str, index: int) -> Dict[str, Any]:
    path = _safe_path(name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Dataset not found")
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise HTTPException(status_code=422, detail="Dataset must be a JSON array")
    if index < 0 or index >= len(data):
        raise HTTPException(status_code=404, detail=f"Index {index} out of range (0–{len(data)-1})")
    return {"index": index, "entry": data[index]}


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(default=""),
) -> Dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_BYTES} bytes")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")

    if not isinstance(data, list):
        raise HTTPException(status_code=422, detail="Dataset must be a JSON array")

    if len(data) > MAX_UPLOAD_ENTRIES:
        raise HTTPException(status_code=422, detail=f"Dataset has {len(data)} entries; limit is {MAX_UPLOAD_ENTRIES}")

    # Validate that each entry has at least a 'goal' field
    for i, entry in enumerate(data):
        if not isinstance(entry, dict) or "goal" not in entry:
            raise HTTPException(status_code=422, detail=f"Entry {i} is missing required field 'goal'")

    target_name = name.strip() or (file.filename or "upload.json")
    if not target_name.endswith(".json"):
        target_name += ".json"

    path = _safe_path(target_name)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    return {"name": target_name, "count": len(data), "size_bytes": len(raw)}


@router.delete("/{name}")
def delete_dataset(name: str) -> Dict[str, Any]:
    path = _safe_path(name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Dataset not found")
    os.remove(path)
    return {"deleted": name}
