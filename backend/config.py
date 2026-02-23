"""
Centralized configuration for the Traffic Violation System.
Loads from environment variables / .env file via pydantic-settings.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Project paths ────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
SNAPSHOTS_DIR = PROJECT_ROOT / "snapshots"


class Settings(BaseSettings):
    """Application-wide settings, loaded from .env or environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = f"sqlite:///{DATA_DIR / 'violations.db'}"

    # ── API ───────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    # ── Vision Engine ─────────────────────────────────────────────────────
    video_source: str = "0"  # webcam index, file path, or RTSP URL
    model_path: str = str(MODELS_DIR / "yolo26n_int8_openvino")

    # Zone polygon vertices as JSON string — list of [x, y] pairs
    zone_polygon: str = "[[100,400],[500,400],[500,700],[100,700]]"

    # Expected lane direction vector [dx, dy]
    lane_direction: str = "[1,0]"

    # Direction zone polygon — wrong-way checks only apply to vehicles inside this zone.
    # If empty string, wrong-way detection applies to ALL vehicles (legacy behavior).
    direction_zone_polygon: str = ""

    # Dwell time threshold in frames (150 = 5 seconds at 30 FPS)
    dwell_threshold: int = 150

    # Consecutive wrong-way frames required to trigger violation
    direction_threshold: int = 10

    # Which violations to enable: comma-separated list or "all"
    # Options: ILLEGAL_PARKING, WRONG_WAY
    enabled_violations: str = "all"

    # Snapshot settings
    snapshot_dir: str = str(SNAPSHOTS_DIR)

    # ── Helpers ───────────────────────────────────────────────────────────

    def get_zone_polygon(self) -> list[list[int]]:
        """Parse zone polygon from JSON string to list of coordinate pairs."""
        return json.loads(self.zone_polygon)

    def get_lane_direction(self) -> list[float]:
        """Parse lane direction from JSON string to [dx, dy] vector."""
        return json.loads(self.lane_direction)

    def get_direction_zone_polygon(self) -> list[list[int]] | None:
        """Parse direction zone polygon, or None if not configured."""
        if not self.direction_zone_polygon.strip():
            return None
        return json.loads(self.direction_zone_polygon)

    def get_video_source(self) -> int | str:
        """Return video source as int (webcam) or str (file/RTSP)."""
        try:
            return int(self.video_source)
        except ValueError:
            return self.video_source


# ── Singleton ─────────────────────────────────────────────────────────────

_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
