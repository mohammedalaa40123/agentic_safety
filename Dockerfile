# ── Stage 1: Build frontend ────────────────────────────────────────────────────
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# bubblewrap provides network/pid/ipc isolation for code_exec without Docker daemon.
# --unshare-user/cgroup are skipped (unavailable in HF's container kernel),
# but net+pid+ipc+uts isolation is sufficient inside the container boundary.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl bubblewrap \
    && rm -rf /var/lib/apt/lists/*

# Copy Python project files
COPY pyproject.toml ./
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[server]"

# Copy built frontend into the expected location
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Non-root user for safety
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=7860

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "7860"]
