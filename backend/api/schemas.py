"""
Pydantic schemas for the Traffic Violation API.

Defines request/response models for alert CRUD and statistics endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ── Alert Schemas ─────────────────────────────────────────────────────────────


class AlertCreate(BaseModel):
    """Request body for creating a new violation alert."""

    violation_type: Literal["ILLEGAL_PARKING", "WRONG_WAY"]
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    object_id: int = Field(..., ge=0, description="Tracked object ID from the vision engine")
    snapshot_path: str | None = Field(None, description="Path to the snapshot image")
    zone_id: str | None = Field(None, description="Zone identifier where violation occurred")
    metadata: dict | None = Field(None, description="Additional metadata (e.g., vehicle class)")


class AlertResponse(BaseModel):
    """Response model for a single alert."""

    id: int
    violation_type: str
    confidence: float
    object_id: int
    snapshot_path: str | None
    zone_id: str | None
    metadata: dict | None
    timestamp: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _parse_metadata(cls, data):
        """Map metadata_json from ORM to metadata dict."""
        import json as _json

        # Handle ORM objects (have metadata_json attribute)
        if hasattr(data, "metadata_json"):
            raw = getattr(data, "metadata_json", None)
            # Build a dict representation, excluding SQLAlchemy's own metadata
            obj = {
                "id": data.id,
                "violation_type": data.violation_type,
                "confidence": data.confidence,
                "object_id": data.object_id,
                "snapshot_path": data.snapshot_path,
                "zone_id": data.zone_id,
                "metadata": _json.loads(raw) if raw else None,
                "timestamp": data.timestamp,
            }
            return obj
        return data


class AlertListResponse(BaseModel):
    """Paginated list of alerts."""

    alerts: list[AlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Statistics Schemas ────────────────────────────────────────────────────────


class HourlyDataPoint(BaseModel):
    """Single data point for hourly violation chart."""

    hour: str  # "00:00", "01:00", ...
    count: int
    illegal_parking: int = 0
    wrong_way: int = 0


class StatsResponse(BaseModel):
    """Aggregate statistics for the dashboard KPI cards."""

    total_violations: int
    violations_today: int
    by_type: dict[str, int]
    hourly_distribution: list[HourlyDataPoint]
    recent_trend: float = Field(
        0.0,
        description="Percentage change compared to previous period",
    )
