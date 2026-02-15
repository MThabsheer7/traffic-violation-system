"""
FastAPI application entry point for the Traffic Violation System.

Configures:
    - Lifespan: DB init on startup, cleanup on shutdown
    - CORS: Allow frontend origin
    - Routers: API routes + WebSocket
    - Health check endpoint

Usage:
    uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.database import close_db, init_db
from backend.api.routes import router
from backend.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init DB on startup, cleanup on shutdown."""
    settings = get_settings()
    logger.info("Starting Traffic Violation API on port %d", settings.api_port)
    await init_db()
    yield
    await close_db()
    logger.info("Traffic Violation API shut down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Traffic Violation System API",
    description="Edge-First Smart Traffic Violation Detection — REST & WebSocket API",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(router)


# ── Static files (snapshots) ─────────────────────────────────────────────────

app.mount(
    "/snapshots",
    StaticFiles(directory=settings.snapshot_dir, check_dir=False),
    name="snapshots",
)


# ── Health check ──────────────────────────────────────────────────────────────


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint for Docker / load balancer."""
    return {
        "status": "healthy",
        "service": "traffic-violation-api",
        "version": "0.1.0",
    }
