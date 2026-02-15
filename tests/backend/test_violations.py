"""
Unit tests for violation detection logic (zone + direction).

Tests cover:
    Zone Violation (Illegal Parking):
        - Point inside/outside polygon detection
        - Dwell time threshold trigger
        - Cooldown prevents duplicate alerts
        - Stale object cleanup

    Direction Violation (Wrong Way):
        - Same-direction movement (no violation)
        - Opposite-direction movement (triggers violation)
        - Insufficient displacement ignored
        - Anti-flicker: requires sustained wrong-way frames
        - Cooldown prevents duplicate alerts
"""

from __future__ import annotations

import time
from collections import deque

import pytest

from backend.vision.tracker import TrackedObject
from backend.vision.violations.direction import DirectionViolationDetector
from backend.vision.violations.zone import ZoneViolationDetector

# ═══════════════════════════════════════════════════════════════════════════
# Zone Violation Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestZoneViolationDetector:
    """Tests for illegal parking detection via zone dwell-time."""

    @pytest.fixture
    def zone_detector(self) -> ZoneViolationDetector:
        """Zone detector with a simple rectangular polygon and low threshold for testing."""
        polygon = [[100, 100], [500, 100], [500, 500], [100, 500]]
        return ZoneViolationDetector(
            polygon=polygon,
            dwell_threshold=5,  # Low threshold for fast tests
            cooldown_seconds=0.1,  # Short cooldown for tests
        )

    def _make_tracked_object(
        self, object_id: int, cx: int, cy: int
    ) -> TrackedObject:
        """Helper to create a TrackedObject at a given centroid."""
        return TrackedObject(
            object_id=object_id,
            centroid=(cx, cy),
            bbox=(cx - 50, cy - 50, cx + 50, cy + 50),
            class_id=2,
            class_name="car",
            confidence=0.9,
        )

    def test_point_inside_zone(self, zone_detector):
        """A point clearly inside the polygon should return True."""
        assert zone_detector.is_inside_zone((300, 300)) is True

    def test_point_outside_zone(self, zone_detector):
        """A point clearly outside the polygon should return False."""
        assert zone_detector.is_inside_zone((50, 50)) is False

    def test_point_on_boundary(self, zone_detector):
        """A point on the polygon boundary should be considered inside."""
        assert zone_detector.is_inside_zone((100, 100)) is True

    def test_no_violation_below_threshold(self, zone_detector):
        """Object inside zone for fewer frames than threshold should NOT trigger."""
        obj = self._make_tracked_object(1, 300, 300)  # Inside zone

        for _ in range(zone_detector.dwell_threshold - 1):
            violations = zone_detector.check([obj])

        assert len(violations) == 0

    def test_violation_at_threshold(self, zone_detector):
        """Object inside zone for exactly threshold frames SHOULD trigger."""
        obj = self._make_tracked_object(1, 300, 300)  # Inside zone

        violations = []
        for _ in range(zone_detector.dwell_threshold):
            violations = zone_detector.check([obj])

        assert len(violations) == 1
        assert violations[0].violation_type == "ILLEGAL_PARKING"
        assert violations[0].object_id == 1

    def test_no_violation_outside_zone(self, zone_detector):
        """Object outside zone should never trigger, regardless of duration."""
        obj = self._make_tracked_object(1, 50, 50)  # Outside zone

        for _ in range(zone_detector.dwell_threshold * 2):
            violations = zone_detector.check([obj])

        assert len(violations) == 0

    def test_dwell_resets_when_leaving_zone(self, zone_detector):
        """Dwell counter should reset when an object leaves the zone."""
        obj_inside = self._make_tracked_object(1, 300, 300)
        obj_outside = self._make_tracked_object(1, 50, 50)

        # Inside for threshold - 1 frames
        for _ in range(zone_detector.dwell_threshold - 1):
            zone_detector.check([obj_inside])

        # Leave the zone
        zone_detector.check([obj_outside])

        # Re-enter — counter should restart from zero
        for _ in range(zone_detector.dwell_threshold - 1):
            violations = zone_detector.check([obj_inside])

        assert len(violations) == 0  # Not enough frames yet

    def test_cooldown_prevents_duplicate_alerts(self, zone_detector):
        """After triggering, same object should not re-trigger within cooldown."""
        obj = self._make_tracked_object(1, 300, 300)

        # First trigger
        for _ in range(zone_detector.dwell_threshold):
            zone_detector.check([obj])

        # Subsequent checks within cooldown should not trigger again
        violations = zone_detector.check([obj])
        assert len(violations) == 0

    def test_cooldown_allows_retrigger_after_expiry(self, zone_detector):
        """After cooldown expires, same object should be able to trigger again."""
        obj = self._make_tracked_object(1, 300, 300)

        # First trigger
        for _ in range(zone_detector.dwell_threshold):
            zone_detector.check([obj])

        # Wait for cooldown to expire
        time.sleep(zone_detector.cooldown_seconds + 0.05)

        # Should trigger again
        violations = zone_detector.check([obj])
        assert len(violations) == 1

    def test_multiple_objects_tracked_independently(self, zone_detector):
        """Each object should have its own independent dwell counter."""
        obj_a = self._make_tracked_object(1, 300, 300)  # Inside
        obj_b = self._make_tracked_object(2, 200, 200)  # Also inside

        # Run obj_a for threshold, obj_b for threshold - 2
        for i in range(zone_detector.dwell_threshold):
            if i < zone_detector.dwell_threshold - 2:
                violations = zone_detector.check([obj_a, obj_b])
            else:
                violations = zone_detector.check([obj_a])  # Only obj_a

        # Only obj_a should have triggered
        assert any(v.object_id == 1 for v in violations)


# ═══════════════════════════════════════════════════════════════════════════
# Direction Violation Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestDirectionViolationDetector:
    """Tests for wrong-way detection via movement vector analysis."""

    @pytest.fixture
    def direction_detector(self) -> DirectionViolationDetector:
        """Direction detector expecting left-to-right movement [1, 0]."""
        return DirectionViolationDetector(
            lane_direction=[1.0, 0.0],
            direction_threshold=3,  # Low threshold for fast tests
            min_displacement=5.0,
            cooldown_seconds=0.1,
        )

    def _make_tracked_with_history(
        self, object_id: int, centroids: list[tuple[int, int]]
    ) -> TrackedObject:
        """Create a TrackedObject with a pre-populated centroid history."""
        latest = centroids[-1]
        obj = TrackedObject(
            object_id=object_id,
            centroid=latest,
            bbox=(latest[0] - 50, latest[1] - 50, latest[0] + 50, latest[1] + 50),
            class_id=2,
            class_name="car",
            confidence=0.9,
        )
        obj.centroid_history = deque(centroids, maxlen=30)
        return obj

    def test_no_violation_same_direction(self, direction_detector):
        """Movement in the expected lane direction should NOT trigger."""
        # Moving left-to-right (positive x)
        obj = self._make_tracked_with_history(1, [(100, 300), (120, 300), (140, 300)])

        for _ in range(direction_detector.direction_threshold + 1):
            violations = direction_detector.check([obj])

        assert len(violations) == 0

    def test_violation_opposite_direction(self, direction_detector):
        """Movement opposite to lane direction SHOULD trigger."""
        # Moving right-to-left (negative x) — wrong way
        obj = self._make_tracked_with_history(1, [(300, 300), (280, 300), (260, 300)])

        violations = []
        for _ in range(direction_detector.direction_threshold):
            violations = direction_detector.check([obj])

        assert len(violations) == 1
        assert violations[0].violation_type == "WRONG_WAY"
        assert violations[0].object_id == 1

    def test_no_violation_insufficient_displacement(self, direction_detector):
        """Very small movements (jitter) should be ignored."""
        # Moving only 2 pixels — below min_displacement
        obj = self._make_tracked_with_history(1, [(300, 300), (298, 300)])

        for _ in range(direction_detector.direction_threshold + 5):
            violations = direction_detector.check([obj])

        assert len(violations) == 0

    def test_anti_flicker_requires_sustained_movement(self, direction_detector):
        """Wrong-way counter should reset when object moves correctly again."""
        # Start wrong-way
        obj_wrong = self._make_tracked_with_history(1, [(300, 300), (280, 300), (260, 300)])

        for _ in range(direction_detector.direction_threshold - 1):
            direction_detector.check([obj_wrong])

        # Correct direction resets the counter
        obj_correct = self._make_tracked_with_history(1, [(260, 300), (280, 300), (300, 300)])
        direction_detector.check([obj_correct])

        # Resume wrong-way — should need full threshold again
        for _ in range(direction_detector.direction_threshold - 1):
            violations = direction_detector.check([obj_wrong])

        assert len(violations) == 0  # Not enough consecutive wrong-way frames

    def test_cooldown_prevents_duplicate_alerts(self, direction_detector):
        """After triggering, same object should not re-trigger within cooldown."""
        obj = self._make_tracked_with_history(1, [(300, 300), (280, 300), (260, 300)])

        # First trigger
        for _ in range(direction_detector.direction_threshold):
            direction_detector.check([obj])

        # Immediate re-check should not trigger
        violations = direction_detector.check([obj])
        assert len(violations) == 0

    def test_diagonal_wrong_way(self):
        """Vehicle moving diagonally opposite should also trigger."""
        # Lane direction is [1, 1] (diagonal)
        detector = DirectionViolationDetector(
            lane_direction=[1.0, 1.0],
            direction_threshold=3,
            min_displacement=5.0,
            cooldown_seconds=0.1,
        )

        # Moving [-1, -1] — opposite diagonal
        obj = self._make_tracked_with_history(1, [(300, 300), (280, 280), (260, 260)])

        violations = []
        for _ in range(detector.direction_threshold):
            violations = detector.check([obj])

        assert len(violations) == 1
        assert violations[0].violation_type == "WRONG_WAY"

    def test_perpendicular_movement_no_violation(self, direction_detector):
        """Movement perpendicular to lane direction should NOT trigger."""
        # Lane is [1, 0], moving [0, 1] (perpendicular — dot product = 0)
        obj = self._make_tracked_with_history(1, [(300, 200), (300, 220), (300, 250)])

        for _ in range(direction_detector.direction_threshold + 5):
            violations = direction_detector.check([obj])

        assert len(violations) == 0

    def test_zero_lane_direction_raises_error(self):
        """A zero direction vector should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be zero"):
            DirectionViolationDetector(lane_direction=[0.0, 0.0])
