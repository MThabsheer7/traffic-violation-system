"""
Direction Violation Detector — Wrong Way.

Detects when a vehicle moves in the opposite direction of the expected
lane direction by analyzing centroid movement vectors.

Logic:
    1. Compute the vehicle's movement vector from its centroid history
    2. Calculate dot product with the expected lane direction vector
    3. If dot product is negative (opposing direction) for N consecutive frames
       → trigger WRONG_WAY
    4. Anti-flicker: requires sustained wrong-way movement to avoid false positives
"""

from __future__ import annotations

import logging
import time

import numpy as np

from backend.vision.tracker import TrackedObject
from backend.vision.violations.zone import ViolationEvent

logger = logging.getLogger(__name__)


class DirectionViolationDetector:
    """
    Detects wrong-way driving by comparing vehicle movement vectors
    against the expected lane direction.

    A vehicle triggers WRONG_WAY when it moves opposite to the expected
    direction for `direction_threshold` consecutive frames.
    """

    def __init__(
        self,
        lane_direction: list[float],
        direction_threshold: int = 10,
        min_displacement: float = 5.0,
        cooldown_seconds: float = 30.0,
    ):
        # Normalize the lane direction vector
        direction = np.array(lane_direction, dtype=np.float64)
        norm = np.linalg.norm(direction)
        if norm == 0:
            raise ValueError("Lane direction vector cannot be zero")
        self.lane_direction = direction / norm

        self.direction_threshold = direction_threshold
        self.min_displacement = min_displacement  # Min pixels to consider movement
        self.cooldown_seconds = cooldown_seconds

        # Track per-object: {object_id: consecutive_wrong_way_frames}
        self._wrong_way_counts: dict[int, int] = {}

        # Cooldown tracker: {object_id: last_alert_timestamp}
        self._last_alert_time: dict[int, float] = {}

    def _compute_movement_vector(self, obj: TrackedObject) -> np.ndarray | None:
        """
        Compute the movement vector from centroid history.

        Uses the oldest and newest centroids in history for a stable
        direction estimate (less noisy than frame-to-frame diffs).
        """
        history = obj.centroid_history
        if len(history) < 2:
            return None

        oldest = np.array(history[0], dtype=np.float64)
        newest = np.array(history[-1], dtype=np.float64)
        movement = newest - oldest

        # Ignore very small movements (stationary or jitter)
        if np.linalg.norm(movement) < self.min_displacement:
            return None

        return movement

    def check(self, tracked_objects: list[TrackedObject]) -> list[ViolationEvent]:
        """
        Check all tracked objects for wrong-way violations.

        Args:
            tracked_objects: Currently tracked vehicles from the tracker.

        Returns:
            List of new ViolationEvent instances (empty if no new violations).
        """
        violations: list[ViolationEvent] = []
        active_ids = {obj.object_id for obj in tracked_objects}
        now = time.time()

        for obj in tracked_objects:
            movement = self._compute_movement_vector(obj)
            if movement is None:
                continue

            # Dot product: positive = same direction, negative = wrong way
            dot_product = np.dot(movement, self.lane_direction)

            if dot_product < 0:
                # Vehicle is moving in the wrong direction
                self._wrong_way_counts[obj.object_id] = (
                    self._wrong_way_counts.get(obj.object_id, 0) + 1
                )

                # Check if sustained wrong-way movement exceeds threshold
                if self._wrong_way_counts[obj.object_id] >= self.direction_threshold:
                    # Check cooldown
                    last_alert = self._last_alert_time.get(obj.object_id, 0)
                    if now - last_alert > self.cooldown_seconds:
                        # Compute movement speed for metadata
                        speed = float(np.linalg.norm(movement))

                        violation = ViolationEvent(
                            violation_type="WRONG_WAY",
                            object_id=obj.object_id,
                            confidence=obj.confidence,
                            timestamp=now,
                            metadata={
                                "dot_product": float(dot_product),
                                "movement_vector": movement.tolist(),
                                "speed_px": speed,
                                "consecutive_frames": self._wrong_way_counts[obj.object_id],
                                "class": obj.class_name,
                                "bbox": list(obj.bbox),
                            },
                        )
                        violations.append(violation)
                        self._last_alert_time[obj.object_id] = now

                        logger.info(
                            "WRONG_WAY: object_id=%d, dot=%.2f, speed=%.1fpx, frames=%d",
                            obj.object_id,
                            dot_product,
                            speed,
                            self._wrong_way_counts[obj.object_id],
                        )
            else:
                # Vehicle is moving correctly — reset counter
                self._wrong_way_counts.pop(obj.object_id, None)

        # Cleanup stale entries
        stale_ids = set(self._wrong_way_counts.keys()) - active_ids
        for stale_id in stale_ids:
            self._wrong_way_counts.pop(stale_id, None)
            self._last_alert_time.pop(stale_id, None)

        return violations
