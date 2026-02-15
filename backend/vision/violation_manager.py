"""
Violation Manager — Orchestrator for all violation detection rules.

Sits between the tracker output and the API layer. For each frame:
    1. Receives tracked objects from the CentroidTracker
    2. Runs all registered violation checkers (zone, direction)
    3. Deduplicates violations and enforces cooldowns
    4. Captures snapshot frames for evidence
    5. Dispatches new violations to the backend API via HTTP POST
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import cv2
import httpx
import numpy as np

from backend.config import get_settings
from backend.vision.tracker import TrackedObject
from backend.vision.violations.direction import DirectionViolationDetector
from backend.vision.violations.zone import ViolationEvent, ZoneViolationDetector

logger = logging.getLogger(__name__)


class ViolationManager:
    """
    Orchestrates violation detection: runs all checkers, captures snapshots,
    and posts alerts to the FastAPI backend.
    """

    def __init__(
        self,
        api_base_url: str | None = None,
        snapshot_dir: str | None = None,
    ):
        settings = get_settings()
        self.api_base_url = api_base_url or f"http://localhost:{settings.api_port}"
        self.snapshot_dir = Path(snapshot_dir or settings.snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Initialize violation detectors from config
        self.zone_detector = ZoneViolationDetector(
            polygon=settings.get_zone_polygon(),
            dwell_threshold=settings.dwell_threshold,
        )
        self.direction_detector = DirectionViolationDetector(
            lane_direction=settings.get_lane_direction(),
            direction_threshold=settings.direction_threshold,
        )

        # Stats
        self._total_violations = 0
        self._violations_by_type: dict[str, int] = {}

    @property
    def total_violations(self) -> int:
        return self._total_violations

    @property
    def violations_by_type(self) -> dict[str, int]:
        return self._violations_by_type.copy()

    def check_violations(
        self,
        tracked_objects: list[TrackedObject],
        frame: np.ndarray,
    ) -> list[ViolationEvent]:
        """
        Run all violation checkers against current tracked objects.

        Args:
            tracked_objects: Vehicles currently being tracked.
            frame: Current BGR video frame (for snapshot capture).

        Returns:
            List of newly detected violations.
        """
        all_violations: list[ViolationEvent] = []

        # Run each violation detector
        zone_violations = self.zone_detector.check(tracked_objects)
        direction_violations = self.direction_detector.check(tracked_objects)

        all_violations.extend(zone_violations)
        all_violations.extend(direction_violations)

        # Process each new violation: snapshot + dispatch
        for violation in all_violations:
            self._total_violations += 1
            vtype = violation.violation_type
            self._violations_by_type[vtype] = self._violations_by_type.get(vtype, 0) + 1

            # Capture snapshot
            snapshot_path = self._capture_snapshot(frame, violation)

            # Dispatch to API (fire-and-forget)
            self._dispatch_alert(violation, snapshot_path)

        return all_violations

    def _capture_snapshot(self, frame: np.ndarray, violation: ViolationEvent) -> str:
        """Save a snapshot frame as evidence for the violation."""
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{violation.violation_type}_{violation.object_id}_{timestamp_str}.jpg"
        filepath = self.snapshot_dir / filename

        cv2.imwrite(str(filepath), frame)
        logger.debug("Snapshot saved: %s", filepath)

        return str(filepath)

    def _dispatch_alert(self, violation: ViolationEvent, snapshot_path: str) -> None:
        """Post the violation alert to the FastAPI backend (non-blocking)."""
        payload = {
            "violation_type": violation.violation_type,
            "confidence": violation.confidence,
            "object_id": violation.object_id,
            "snapshot_path": snapshot_path,
            "zone_id": violation.zone_id,
            "metadata": violation.metadata,
        }

        try:
            # Use a synchronous client since the vision pipeline runs in its own thread
            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    f"{self.api_base_url}/api/alerts",
                    json=payload,
                )
                if response.status_code == 200:
                    logger.info(
                        "Alert dispatched: %s (object_id=%d)",
                        violation.violation_type,
                        violation.object_id,
                    )
                else:
                    logger.warning(
                        "Alert dispatch failed: HTTP %d — %s",
                        response.status_code,
                        response.text,
                    )
        except httpx.RequestError as e:
            logger.warning("Alert dispatch failed (API unreachable): %s", e)

    def draw_overlays(self, frame: np.ndarray) -> np.ndarray:
        """Draw zone polygon and violation status overlays on the frame."""
        frame = self.zone_detector.draw_zone(frame)
        return frame
