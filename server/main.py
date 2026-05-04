"""FastAPI application entry point."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes import providers, datasets, eval_, results


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .jobs import start_queue_runner
    await start_queue_runner()
    yield
    from .jobs import cancel_all_on_shutdown
    await cancel_all_on_shutdown()


app = FastAPI(
    title="Agentic Safety Evaluator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(providers.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(eval_.router, prefix="/api")
app.include_router(results.router, prefix="/api")

# Serve built frontend when running in production
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="static")
