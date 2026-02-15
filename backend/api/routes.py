"""
API routes for the Traffic Violation System.

Endpoints:
    POST   /api/alerts        — Create a new violation alert (from vision engine)
    GET    /api/alerts        — List alerts with pagination and filters
    GET    /api/alerts/{id}   — Get a single alert by ID
    GET    /api/stats         — Dashboard aggregate statistics
    GET    /api/stats/hourly  — Violations grouped by hour (for chart)
    WS     /api/ws/alerts     — Live alert feed via WebSocket
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.database import get_db
from backend.api.models import Alert
from backend.api.schemas import AlertCreate, AlertListResponse, AlertResponse, HourlyDataPoint, StatsResponse
from backend.api.ws import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["alerts"])


# ── POST /api/alerts ──────────────────────────────────────────────────────────


@router.post("/alerts", response_model=AlertResponse)
async def create_alert(
    alert: AlertCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new violation alert.

    Called by the vision engine when a violation is detected.
    Also broadcasts the alert to connected WebSocket clients.
    """
    db_alert = Alert(
        violation_type=alert.violation_type,
        confidence=alert.confidence,
        object_id=alert.object_id,
        snapshot_path=alert.snapshot_path,
        zone_id=alert.zone_id,
        metadata_json=json.dumps(alert.metadata) if alert.metadata else None,
    )
    db.add(db_alert)
    await db.flush()
    await db.refresh(db_alert)

    logger.info(
        "Alert created: id=%d type=%s object_id=%d",
        db_alert.id,
        db_alert.violation_type,
        db_alert.object_id,
    )

    # Broadcast to connected dashboards
    alert_data = AlertResponse.model_validate(db_alert).model_dump(mode="json")
    await ws_manager.broadcast(alert_data)

    return db_alert


# ── GET /api/alerts ───────────────────────────────────────────────────────────


@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    violation_type: str | None = Query(None, description="Filter by type"),
    date_from: datetime | None = Query(None, description="Filter from date"),
    date_to: datetime | None = Query(None, description="Filter to date"),
    db: AsyncSession = Depends(get_db),
):
    """List violation alerts with pagination and optional filters."""
    query = select(Alert)

    # Apply filters
    if violation_type:
        query = query.where(Alert.violation_type == violation_type)
    if date_from:
        query = query.where(Alert.timestamp >= date_from)
    if date_to:
        query = query.where(Alert.timestamp <= date_to)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.order_by(Alert.timestamp.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    alerts = result.scalars().all()

    total_pages = max(1, (total + page_size - 1) // page_size)

    return AlertListResponse(
        alerts=[AlertResponse.model_validate(a) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ── GET /api/alerts/{id} ─────────────────────────────────────────────────────


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single alert by ID."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert


# ── GET /api/stats ────────────────────────────────────────────────────────────


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate statistics for the dashboard KPI cards."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)

    # Total violations
    total_result = await db.execute(select(func.count(Alert.id)))
    total_violations = total_result.scalar() or 0

    # Today's violations
    today_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.timestamp >= today_start)
    )
    violations_today = today_result.scalar() or 0

    # Yesterday's violations (for trend)
    yesterday_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.timestamp >= yesterday_start,
            Alert.timestamp < today_start,
        )
    )
    violations_yesterday = yesterday_result.scalar() or 0

    # By type
    type_result = await db.execute(
        select(Alert.violation_type, func.count(Alert.id)).group_by(Alert.violation_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    # Hourly distribution (last 24 hours)
    hourly = await _get_hourly_distribution(db, now)

    # Trend calculation
    trend = 0.0
    if violations_yesterday > 0:
        trend = ((violations_today - violations_yesterday) / violations_yesterday) * 100

    return StatsResponse(
        total_violations=total_violations,
        violations_today=violations_today,
        by_type=by_type,
        hourly_distribution=hourly,
        recent_trend=round(trend, 1),
    )


async def _get_hourly_distribution(
    db: AsyncSession,
    now: datetime,
) -> list[HourlyDataPoint]:
    """Get violation counts grouped by hour for the last 24 hours."""
    start = now - timedelta(hours=24)

    result = await db.execute(
        select(Alert.violation_type, Alert.timestamp).where(Alert.timestamp >= start)
    )
    rows = result.all()

    # Bucket by hour
    hourly: dict[str, dict[str, int]] = {}
    for hour in range(24):
        h = (start + timedelta(hours=hour)).strftime("%H:00")
        hourly[h] = {"count": 0, "illegal_parking": 0, "wrong_way": 0}

    for violation_type, timestamp in rows:
        h = timestamp.strftime("%H:00")
        if h in hourly:
            hourly[h]["count"] += 1
            if violation_type == "ILLEGAL_PARKING":
                hourly[h]["illegal_parking"] += 1
            elif violation_type == "WRONG_WAY":
                hourly[h]["wrong_way"] += 1

    return [
        HourlyDataPoint(
            hour=hour,
            count=data["count"],
            illegal_parking=data["illegal_parking"],
            wrong_way=data["wrong_way"],
        )
        for hour, data in hourly.items()
    ]


# ── WS /api/ws/alerts ────────────────────────────────────────────────────────


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket endpoint for live alert push to dashboards."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive — just receive and discard pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
