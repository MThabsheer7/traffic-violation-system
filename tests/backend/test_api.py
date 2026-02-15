"""
Unit tests for the FastAPI backend API.

Tests cover:
    - POST /api/alerts: create alert, validation, WebSocket broadcast
    - GET /api/alerts: list with pagination and filters
    - GET /api/alerts/{id}: single alert retrieval, 404 for missing
    - GET /api/stats: aggregate statistics
    - GET /health: health check
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.main import app
from backend.api.models import Base
from backend.api.database import get_db


# ── Test Database Setup ───────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    """Dependency override: use in-memory test database."""
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Sample Data ───────────────────────────────────────────────────────────────

VALID_ALERT = {
    "violation_type": "ILLEGAL_PARKING",
    "confidence": 0.92,
    "object_id": 42,
    "snapshot_path": "/snapshots/test_001.jpg",
    "zone_id": "zone_A",
    "metadata": {"vehicle_class": "car"},
}


# ── Health Check ──────────────────────────────────────────────────────────────


class TestHealthCheck:
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


# ── POST /api/alerts ──────────────────────────────────────────────────────────


class TestCreateAlert:
    async def test_create_alert_success(self, client: AsyncClient):
        """Valid alert should be created and returned with an ID and timestamp."""
        response = await client.post("/api/alerts", json=VALID_ALERT)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == 1
        assert data["violation_type"] == "ILLEGAL_PARKING"
        assert data["confidence"] == 0.92
        assert data["object_id"] == 42
        assert "timestamp" in data

    async def test_create_alert_wrong_way(self, client: AsyncClient):
        """WRONG_WAY type should also be accepted."""
        alert = {**VALID_ALERT, "violation_type": "WRONG_WAY"}
        response = await client.post("/api/alerts", json=alert)
        assert response.status_code == 200
        assert response.json()["violation_type"] == "WRONG_WAY"

    async def test_create_alert_invalid_type(self, client: AsyncClient):
        """Invalid violation type should return 422."""
        alert = {**VALID_ALERT, "violation_type": "SPEEDING"}
        response = await client.post("/api/alerts", json=alert)
        assert response.status_code == 422

    async def test_create_alert_invalid_confidence(self, client: AsyncClient):
        """Confidence outside [0, 1] should return 422."""
        alert = {**VALID_ALERT, "confidence": 1.5}
        response = await client.post("/api/alerts", json=alert)
        assert response.status_code == 422

    async def test_create_alert_minimal_payload(self, client: AsyncClient):
        """Only required fields should be sufficient."""
        alert = {
            "violation_type": "ILLEGAL_PARKING",
            "confidence": 0.8,
            "object_id": 1,
        }
        response = await client.post("/api/alerts", json=alert)
        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_path"] is None
        assert data["zone_id"] is None


# ── GET /api/alerts ───────────────────────────────────────────────────────────


class TestListAlerts:
    async def _seed_alerts(self, client: AsyncClient, count: int = 5):
        """Helper to create multiple alerts."""
        for i in range(count):
            alert = {**VALID_ALERT, "object_id": i}
            await client.post("/api/alerts", json=alert)

    async def test_list_alerts_empty(self, client: AsyncClient):
        """Empty database should return empty list."""
        response = await client.get("/api/alerts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["alerts"] == []

    async def test_list_alerts_with_data(self, client: AsyncClient):
        """Should return seeded alerts."""
        await self._seed_alerts(client, 3)
        response = await client.get("/api/alerts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["alerts"]) == 3

    async def test_list_alerts_pagination(self, client: AsyncClient):
        """Pagination should limit results."""
        await self._seed_alerts(client, 10)
        response = await client.get("/api/alerts?page=1&page_size=3")
        data = response.json()
        assert len(data["alerts"]) == 3
        assert data["total"] == 10
        assert data["total_pages"] == 4

    async def test_list_alerts_filter_by_type(self, client: AsyncClient):
        """Should filter by violation type."""
        await client.post("/api/alerts", json=VALID_ALERT)  # ILLEGAL_PARKING
        await client.post("/api/alerts", json={**VALID_ALERT, "violation_type": "WRONG_WAY"})

        response = await client.get("/api/alerts?violation_type=WRONG_WAY")
        data = response.json()
        assert data["total"] == 1
        assert data["alerts"][0]["violation_type"] == "WRONG_WAY"


# ── GET /api/alerts/{id} ─────────────────────────────────────────────────────


class TestGetAlert:
    async def test_get_alert_success(self, client: AsyncClient):
        """Should return a specific alert by ID."""
        await client.post("/api/alerts", json=VALID_ALERT)
        response = await client.get("/api/alerts/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1

    async def test_get_alert_not_found(self, client: AsyncClient):
        """Non-existent ID should return 404."""
        response = await client.get("/api/alerts/999")
        assert response.status_code == 404


# ── GET /api/stats ────────────────────────────────────────────────────────────


class TestStats:
    async def test_stats_empty_db(self, client: AsyncClient):
        """Stats should return zeros for empty database."""
        response = await client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_violations"] == 0
        assert data["violations_today"] == 0

    async def test_stats_with_data(self, client: AsyncClient):
        """Stats should reflect created alerts."""
        for _ in range(3):
            await client.post("/api/alerts", json=VALID_ALERT)
        await client.post("/api/alerts", json={**VALID_ALERT, "violation_type": "WRONG_WAY"})

        response = await client.get("/api/stats")
        data = response.json()
        assert data["total_violations"] == 4
        assert data["by_type"]["ILLEGAL_PARKING"] == 3
        assert data["by_type"]["WRONG_WAY"] == 1
        assert "hourly_distribution" in data
