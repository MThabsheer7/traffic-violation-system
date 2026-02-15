"""
Zone Violation Detector — Illegal Parking.

Detects when a vehicle remains stationary within a defined polygon zone
for longer than a configurable dwell-time threshold.

Logic:
    1. Check if vehicle centroid is inside the zone polygon
    2. Track how many consecutive frames the vehicle stays inside
    3. If frame count exceeds dwell_threshold → trigger ILLEGAL_PARKING
    4. Maintain per-object cooldown to avoid duplicate alerts
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import cv2
import numpy as np

from backend.vision.tracker import TrackedObject

logger = logging.getLogger(__name__)


@dataclass
class ViolationEvent:
    """Represents a detected traffic violation."""

    violation_type: str
    object_id: int
    confidence: float
    timestamp: float
    zone_id: str | None = None
    metadata: dict | None = None


class ZoneViolationDetector:
    """
    Detects illegal parking by monitoring vehicle dwell time in a defined zone.

    The zone is defined as a polygon (list of [x, y] vertices).
    A vehicle triggers ILLEGAL_PARKING when it stays inside the polygon
    for more than `dwell_threshold` consecutive frames.
    """

    def __init__(
        self,
        polygon: list[list[int]],
        dwell_threshold: int = 150,
        cooldown_seconds: float = 30.0,
        zone_id: str = "zone_1",
    ):
        self.polygon = np.array(polygon, dtype=np.int32)
        self.dwell_threshold = dwell_threshold
        self.cooldown_seconds = cooldown_seconds
        self.zone_id = zone_id

        # Track per-object: {object_id: frames_inside_zone}
        self._dwell_counts: dict[int, int] = {}

        # Cooldown tracker: {object_id: last_alert_timestamp}
        self._last_alert_time: dict[int, float] = {}

    def is_inside_zone(self, point: tuple[int, int]) -> bool:
        """Check if a point is inside the zone polygon."""
        result = cv2.pointPolygonTest(
            self.polygon.reshape(-1, 1, 2).astype(np.float32),
            (float(point[0]), float(point[1])),
            measureDist=False,
        )
        return result >= 0  # >= 0 means inside or on boundary

    def check(self, tracked_objects: list[TrackedObject]) -> list[ViolationEvent]:
        """
        Check all tracked objects for zone violations.

        Args:
            tracked_objects: Currently tracked vehicles from the tracker.

        Returns:
            List of new ViolationEvent instances (empty if no new violations).
        """
        violations: list[ViolationEvent] = []
        active_ids = {obj.object_id for obj in tracked_objects}
        now = time.time()

        for obj in tracked_objects:
            if self.is_inside_zone(obj.centroid):
                # Increment dwell counter
                self._dwell_counts[obj.object_id] = (
                    self._dwell_counts.get(obj.object_id, 0) + 1
                )

                # Check if threshold exceeded
                if self._dwell_counts[obj.object_id] >= self.dwell_threshold:
                    # Check cooldown — don't repeat alerts
                    last_alert = self._last_alert_time.get(obj.object_id, 0)
                    if now - last_alert > self.cooldown_seconds:
                        violation = ViolationEvent(
                            violation_type="ILLEGAL_PARKING",
                            object_id=obj.object_id,
                            confidence=obj.confidence,
                            timestamp=now,
                            zone_id=self.zone_id,
                            metadata={
                                "dwell_frames": self._dwell_counts[obj.object_id],
                                "class": obj.class_name,
                                "bbox": list(obj.bbox),
                            },
                        )
                        violations.append(violation)
                        self._last_alert_time[obj.object_id] = now

                        logger.info(
                            "ILLEGAL_PARKING: object_id=%d, dwell=%d frames, zone=%s",
                            obj.object_id,
                            self._dwell_counts[obj.object_id],
                            self.zone_id,
                        )
            else:
                # Object left the zone — reset its dwell counter
                self._dwell_counts.pop(obj.object_id, None)

        # Cleanup: remove stale entries for deregistered objects
        stale_ids = set(self._dwell_counts.keys()) - active_ids
        for stale_id in stale_ids:
            self._dwell_counts.pop(stale_id, None)
            self._last_alert_time.pop(stale_id, None)

        return violations

    def draw_zone(self, frame: np.ndarray, color: tuple = (0, 255, 100), alpha: float = 0.25) -> np.ndarray:
        """Draw the zone polygon overlay on the frame."""
        overlay = frame.copy()
        cv2.fillPoly(overlay, [self.polygon], color)
        cv2.polylines(frame, [self.polygon], isClosed=True, color=color, thickness=2)
        return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
