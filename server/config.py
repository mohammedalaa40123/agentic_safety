"""Server-wide settings."""
from __future__ import annotations

import os

HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
PORT: int = int(os.getenv("SERVER_PORT", "8000"))

# Root of the agentic_safety project (parent of server/)
PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR: str = os.path.join(PROJECT_ROOT, "data")
RESULTS_DIR: str = os.path.join(PROJECT_ROOT, "results","agentic_experiments_v2_500")

# Dataset upload limits
MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))  # 10 MB
MAX_UPLOAD_ENTRIES: int = int(os.getenv("MAX_UPLOAD_ENTRIES", "1000"))
