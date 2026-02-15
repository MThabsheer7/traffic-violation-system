"""
Unit tests for the CentroidTracker.

Tests cover:
    - Registration of new objects
    - ID persistence across frames
    - Object deregistration after disappearance
    - Centroid history tracking
    - Multi-object association
"""

from __future__ import annotations

import pytest

from backend.vision.detector import Detection
from backend.vision.tracker import CentroidTracker


class TestCentroidTracker:
    """Tests for CentroidTracker object tracking logic."""

    def test_register_new_objects(self, tracker: CentroidTracker, sample_detections):
        """New detections should be registered with unique IDs starting from 0."""
        tracked = tracker.update(sample_detections)

        assert len(tracked) == 2
        ids = {obj.object_id for obj in tracked}
        assert ids == {0, 1}

    def test_persistent_ids_across_frames(self, tracker: CentroidTracker):
        """Same object in consecutive frames should keep the same ID."""
        # Frame 1: car at (150, 250)
        det_frame1 = [
            Detection(bbox=(100, 200, 200, 300), class_id=2, class_name="car", confidence=0.9)
        ]
        tracked1 = tracker.update(det_frame1)
        obj_id = tracked1[0].object_id

        # Frame 2: car moves slightly to (160, 255)
        det_frame2 = [
            Detection(bbox=(110, 205, 210, 305), class_id=2, class_name="car", confidence=0.9)
        ]
        tracked2 = tracker.update(det_frame2)

        assert len(tracked2) == 1
        assert tracked2[0].object_id == obj_id  # Same ID preserved

    def test_deregister_after_max_disappeared(self, tracker: CentroidTracker):
        """Objects should be removed after exceeding max_disappeared frames."""
        # Register an object
        det = [Detection(bbox=(100, 200, 200, 300), class_id=2, class_name="car", confidence=0.9)]
        tracker.update(det)
        assert tracker.active_count == 1

        # Send empty detections for max_disappeared + 1 frames
        for _ in range(tracker.max_disappeared + 1):
            tracker.update([])

        assert tracker.active_count == 0

    def test_object_not_deregistered_before_threshold(self, tracker: CentroidTracker):
        """Objects should survive brief disappearances below the threshold."""
        det = [Detection(bbox=(100, 200, 200, 300), class_id=2, class_name="car", confidence=0.9)]
        tracker.update(det)

        # Disappear for fewer frames than threshold
        for _ in range(tracker.max_disappeared - 2):
            tracker.update([])

        assert tracker.active_count == 1  # Still tracked

    def test_centroid_history_updated(self, tracker: CentroidTracker):
        """Centroid history should accumulate positions across frames."""
        positions = [(150, 250), (160, 255), (170, 260), (180, 265)]

        for i, (cx, cy) in enumerate(positions):
            x1, y1 = cx - 50, cy - 50
            x2, y2 = cx + 50, cy + 50
            det = [Detection(bbox=(x1, y1, x2, y2), class_id=2, class_name="car", confidence=0.9)]
            tracked = tracker.update(det)

        obj = tracked[0]
        # Should have centroid from registration + updates
        assert len(obj.centroid_history) >= len(positions)

    def test_multiple_objects_tracked_independently(self, tracker: CentroidTracker):
        """Multiple objects should be tracked with separate IDs."""
        dets = [
            Detection(bbox=(100, 100, 200, 200), class_id=2, class_name="car", confidence=0.9),
            Detection(bbox=(500, 500, 600, 600), class_id=7, class_name="truck", confidence=0.8),
        ]
        tracked = tracker.update(dets)

        assert len(tracked) == 2
        assert tracked[0].object_id != tracked[1].object_id

    def test_new_object_gets_new_id(self, tracker: CentroidTracker):
        """A new object appearing should get a new ID, not reuse an old one."""
        # Frame 1: one car
        det1 = [Detection(bbox=(100, 100, 200, 200), class_id=2, class_name="car", confidence=0.9)]
        tracked1 = tracker.update(det1)
        first_id = tracked1[0].object_id

        # Frame 2: original car + new car far away
        det2 = [
            Detection(bbox=(105, 105, 205, 205), class_id=2, class_name="car", confidence=0.9),
            Detection(bbox=(800, 800, 900, 900), class_id=2, class_name="car", confidence=0.85),
        ]
        tracked2 = tracker.update(det2)

        assert len(tracked2) == 2
        ids = {obj.object_id for obj in tracked2}
        assert first_id in ids  # Original preserved
        new_ids = ids - {first_id}
        assert len(new_ids) == 1
        assert new_ids.pop() > first_id  # New ID is higher

    def test_reset_clears_all_state(self, tracker: CentroidTracker, sample_detections):
        """Reset should clear all tracked objects and reset ID counter."""
        tracker.update(sample_detections)
        assert tracker.active_count > 0

        tracker.reset()
        assert tracker.active_count == 0

        # New objects should start from ID 0 again
        tracked = tracker.update(sample_detections)
        assert tracked[0].object_id == 0
