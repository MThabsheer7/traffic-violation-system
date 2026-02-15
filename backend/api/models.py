"""
SQLAlchemy ORM models for the Traffic Violation System.

Defines the `Alert` table used to persist violation events.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class Alert(Base):
    """Violation alert record."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    violation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    object_id: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_alerts_timestamp", "timestamp"),
        Index("ix_alerts_violation_type", "violation_type"),
        Index("ix_alerts_type_timestamp", "violation_type", "timestamp"),
    )

    @property
    def metadata_dict(self) -> dict | None:
        """Deserialize metadata JSON string to dict."""
        if self.metadata_json:
            return json.loads(self.metadata_json)
        return None

    @metadata_dict.setter
    def metadata_dict(self, value: dict | None) -> None:
        """Serialize dict to JSON string for storage."""
        if value is not None:
            self.metadata_json = json.dumps(value)
        else:
            self.metadata_json = None

    def __repr__(self) -> str:
        return (
            f"<Alert(id={self.id}, type={self.violation_type}, "
            f"object_id={self.object_id}, time={self.timestamp})>"
        )
