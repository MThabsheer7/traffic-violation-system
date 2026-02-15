"""
Database engine and session management for the Traffic Violation System.

Uses SQLAlchemy async engine with aiosqlite for non-blocking DB access
within the FastAPI async context.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.models import Base
from backend.config import get_settings

logger = logging.getLogger(__name__)

# ── Engine & Session Factory ──────────────────────────────────────────────────

_engine = None
_session_factory = None


def _get_async_url(url: str) -> str:
    """Convert sqlite:/// URL to sqlite+aiosqlite:/// for async support."""
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


def get_engine():
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        async_url = _get_async_url(settings.database_url)
        _engine = create_async_engine(
            async_url,
            echo=False,
            connect_args={"check_same_thread": False},  # SQLite-specific
        )
        logger.info("Database engine created: %s", async_url)
    return _engine


def get_session_factory():
    """Get or create the async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


# ── Dependency ────────────────────────────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Lifecycle ─────────────────────────────────────────────────────────────────


async def init_db() -> None:
    """Create all tables if they don't exist."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")


async def close_db() -> None:
    """Dispose the engine connection pool."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed")
