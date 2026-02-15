"""
Shared test fixtures for the traffic violation system tests.
"""

from __future__ import annotations

import pytest

from backend.vision.detector import Detection
from backend.vision.tracker import CentroidTracker, TrackedObject


@pytest.fixture
def sample_detections() -> list[Detection]:
    """Sample vehicle detections for testing."""
    return [
        Detection(bbox=(100, 200, 200, 300), class_id=2, class_name="car", confidence=0.92),
        Detection(bbox=(400, 300, 500, 400), class_id=7, class_name="truck", confidence=0.85),
    ]


@pytest.fixture
def tracker() -> CentroidTracker:
    """A fresh centroid tracker instance."""
    return CentroidTracker(max_disappeared=10, max_distance=80)


@pytest.fixture
def tracked_car() -> TrackedObject:
    """A tracked car object for direct use in violation tests."""
    obj = TrackedObject(
        object_id=1,
        centroid=(300, 500),
        bbox=(250, 450, 350, 550),
        class_id=2,
        class_name="car",
        confidence=0.9,
    )
    return obj
