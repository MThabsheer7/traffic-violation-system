"""
Centroid-based Multi-Object Tracker.

Assigns persistent IDs to detected objects across frames using centroid
distance association (Hungarian algorithm via scipy). Maintains centroid
history for velocity/direction calculations needed by violation rules.
"""

from __future__ import annotations

import logging
from collections import OrderedDict, deque
from dataclasses import dataclass, field

import numpy as np
from scipy.spatial.distance import cdist

from backend.vision.detector import Detection

logger = logging.getLogger(__name__)

# ── Default configuration ────────────────────────────────────────────────────
DEFAULT_MAX_DISAPPEARED = 30  # Frames before deregistering an object
DEFAULT_MAX_DISTANCE = 80  # Max pixel distance for centroid association
DEFAULT_HISTORY_LENGTH = 30  # Number of past centroids to store per object


@dataclass
class TrackedObject:
    """A tracked object with persistent ID and centroid history."""

    object_id: int
    centroid: tuple[int, int]
    bbox: tuple[int, int, int, int]
    class_id: int
    class_name: str
    confidence: float
    disappeared: int = 0
    centroid_history: deque = field(default_factory=lambda: deque(maxlen=DEFAULT_HISTORY_LENGTH))
    frame_count: int = 0  # Total frames this object has been tracked

    def __post_init__(self):
        # Ensure the current centroid is added to history on creation
        if not self.centroid_history:
            self.centroid_history.append(self.centroid)


class CentroidTracker:
    """
    Tracks objects across frames by associating detections to existing
    tracked objects using centroid proximity.

    Algorithm:
        1. If no existing objects → register all new detections
        2. If no new detections → increment disappeared counter for all objects
        3. Otherwise → compute pairwise distance matrix between existing centroids
           and new detection centroids, then greedily assign using closest pairs
        4. Deregister objects that have disappeared for too many frames
    """

    def __init__(
        self,
        max_disappeared: int = DEFAULT_MAX_DISAPPEARED,
        max_distance: int = DEFAULT_MAX_DISTANCE,
    ):
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

        self._next_object_id = 0
        self.objects: OrderedDict[int, TrackedObject] = OrderedDict()

    @property
    def active_count(self) -> int:
        """Number of currently tracked objects."""
        return len(self.objects)

    def _register(self, detection: Detection) -> TrackedObject:
        """Register a new detection as a tracked object."""
        obj = TrackedObject(
            object_id=self._next_object_id,
            centroid=detection.center,
            bbox=detection.bbox,
            class_id=detection.class_id,
            class_name=detection.class_name,
            confidence=detection.confidence,
        )
        self.objects[self._next_object_id] = obj
        self._next_object_id += 1

        logger.debug("Registered new object ID=%d at %s", obj.object_id, obj.centroid)
        return obj

    def _deregister(self, object_id: int) -> None:
        """Remove a tracked object."""
        logger.debug("Deregistered object ID=%d", object_id)
        del self.objects[object_id]

    def update(self, detections: list[Detection]) -> list[TrackedObject]:
        """
        Update tracker with new frame detections.

        Args:
            detections: List of detections from the current frame.

        Returns:
            List of all currently tracked objects (with updated positions).
        """
        # ── Case 1: No detections → mark all existing as disappeared ─────
        if len(detections) == 0:
            for obj_id in list(self.objects.keys()):
                self.objects[obj_id].disappeared += 1
                if self.objects[obj_id].disappeared > self.max_disappeared:
                    self._deregister(obj_id)
            return list(self.objects.values())

        # ── Case 2: No existing objects → register all detections ────────
        if len(self.objects) == 0:
            for det in detections:
                self._register(det)
            return list(self.objects.values())

        # ── Case 3: Match existing objects to new detections ─────────────
        object_ids = list(self.objects.keys())
        existing_centroids = np.array(
            [self.objects[oid].centroid for oid in object_ids], dtype=np.float32
        )
        new_centroids = np.array(
            [det.center for det in detections], dtype=np.float32
        )

        # Pairwise distance matrix: (num_existing, num_new)
        distances = cdist(existing_centroids, new_centroids)

        # Greedy assignment: sort by distance, assign closest pairs
        rows = distances.min(axis=1).argsort()
        cols = distances.argmin(axis=1)[rows]

        used_rows: set[int] = set()
        used_cols: set[int] = set()

        for row, col in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue

            # Skip if distance exceeds threshold (likely a new object)
            if distances[row, col] > self.max_distance:
                continue

            # Update existing object with new detection data
            obj_id = object_ids[row]
            det = detections[col]
            obj = self.objects[obj_id]

            obj.centroid = det.center
            obj.bbox = det.bbox
            obj.confidence = det.confidence
            obj.disappeared = 0
            obj.frame_count += 1
            obj.centroid_history.append(det.center)

            used_rows.add(row)
            used_cols.add(col)

        # Handle unmatched existing objects (disappeared)
        for row in range(len(object_ids)):
            if row not in used_rows:
                obj_id = object_ids[row]
                self.objects[obj_id].disappeared += 1
                if self.objects[obj_id].disappeared > self.max_disappeared:
                    self._deregister(obj_id)

        # Handle unmatched new detections (register as new)
        for col in range(len(detections)):
            if col not in used_cols:
                self._register(detections[col])

        return list(self.objects.values())

    def reset(self) -> None:
        """Clear all tracked objects and reset ID counter."""
        self.objects.clear()
        self._next_object_id = 0
