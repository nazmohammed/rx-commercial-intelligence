"""FastAPI entrypoint for the RX Commercial Intelligence web app.

Run locally:
    uvicorn src.api.main:app --reload --port 8000

In Container Apps, this is the backend sidecar listening on localhost:8000.
The frontend nginx sidecar reverse-proxies /api/* to here.
"""

from __future__ import annotations

import os

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import chat as chat_routes

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="RX Commercial Intelligence API",
        description="HTTP front-door for the Coordinator → Foundry agents pipeline.",
        version="0.1.0",
    )

    # CORS only matters during local dev (frontend on Vite dev server hits
    # uvicorn directly). In Container Apps both run on the same origin via
    # the nginx sidecar, so CORS is a no-op.
    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(chat_routes.router)

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
