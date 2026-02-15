"""
Video Processing Pipeline — Main entry point for the Vision Engine.

Captures video from a source (webcam, file, RTSP), runs detection +
tracking + violation checks per frame, and displays annotated output.

Usage:
    python -m backend.vision.pipeline --source path/to/video.mp4
    python -m backend.vision.pipeline --source 0   # webcam
"""

from __future__ import annotations

import argparse
import logging
import time

import cv2
import numpy as np

from backend.config import get_settings
from backend.vision.detector import YOLODetector
from backend.vision.tracker import CentroidTracker
from backend.vision.violation_manager import ViolationManager

logger = logging.getLogger(__name__)

# ── Colors (BGR) ─────────────────────────────────────────────────────────────
COLOR_GREEN = (0, 255, 100)
COLOR_RED = (0, 0, 255)
COLOR_YELLOW = (0, 220, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_VIOLATION_BG = (0, 0, 180)


def draw_detections(
    frame: np.ndarray,
    tracked_objects: list,
    violations: list,
) -> np.ndarray:
    """Draw bounding boxes, labels, and violation indicators on the frame."""
    violation_obj_ids = {v.object_id for v in violations}

    for obj in tracked_objects:
        x1, y1, x2, y2 = obj.bbox
        is_violating = obj.object_id in violation_obj_ids

        # Choose color based on violation status
        color = COLOR_RED if is_violating else COLOR_GREEN

        # Bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Label: class name + ID + confidence
        label = f"{obj.class_name} #{obj.object_id} {obj.confidence:.0%}"

        # Label background
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
        cv2.putText(
            frame, label, (x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_WHITE, 1, cv2.LINE_AA,
        )

        # Draw centroid
        cv2.circle(frame, obj.centroid, 4, color, -1)

        # Draw centroid trail
        if len(obj.centroid_history) > 1:
            points = list(obj.centroid_history)
            for i in range(1, len(points)):
                alpha = i / len(points)  # Fade old points
                trail_color = tuple(int(c * alpha) for c in color)
                cv2.line(frame, points[i - 1], points[i], trail_color, 2)

    # Draw violation banners
    for v in violations:
        _draw_violation_banner(frame, v)

    return frame


def _draw_violation_banner(frame: np.ndarray, violation) -> None:
    """Draw a violation alert banner at the top of the frame."""
    text = f"⚠ {violation.violation_type} — Vehicle #{violation.object_id}"
    h, w = frame.shape[:2]

    # Semi-transparent red banner
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 40), COLOR_VIOLATION_BG, -1)
    frame[:] = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

    cv2.putText(
        frame, text, (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_WHITE, 2, cv2.LINE_AA,
    )


def draw_fps(frame: np.ndarray, fps: float) -> np.ndarray:
    """Draw FPS counter on the frame."""
    h = frame.shape[0]
    text = f"FPS: {fps:.1f}"
    cv2.putText(
        frame, text, (10, h - 15),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_GREEN, 2, cv2.LINE_AA,
    )
    return frame


def draw_lane_direction(frame: np.ndarray, direction: list[float]) -> np.ndarray:
    """Draw lane direction arrow indicator on the frame."""
    h, w = frame.shape[:2]
    center = (w - 60, h - 30)
    dx, dy = direction
    endpoint = (int(center[0] + dx * 30), int(center[1] + dy * 30))

    cv2.arrowedLine(frame, center, endpoint, COLOR_YELLOW, 2, tipLength=0.4)
    cv2.putText(
        frame, "Lane", (w - 90, h - 45),
        cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_YELLOW, 1, cv2.LINE_AA,
    )
    return frame


class VideoPipeline:
    """
    Main video processing pipeline.

    Connects: VideoCapture → Detector → Tracker → ViolationManager → Display
    """

    def __init__(self, source: int | str | None = None):
        settings = get_settings()
        self.source = source if source is not None else settings.get_video_source()

        # Initialize components
        self.detector = YOLODetector(model_path=settings.model_path)
        self.tracker = CentroidTracker()
        self.violation_manager = ViolationManager()

        # Lane direction for overlay
        self.lane_direction = settings.get_lane_direction()

        # FPS tracking
        self._frame_times: list[float] = []
        self._fps = 0.0

    def _update_fps(self) -> None:
        """Calculate rolling average FPS."""
        now = time.time()
        self._frame_times.append(now)

        # Keep only last 30 frame timestamps
        if len(self._frame_times) > 30:
            self._frame_times = self._frame_times[-30:]

        if len(self._frame_times) >= 2:
            elapsed = self._frame_times[-1] - self._frame_times[0]
            if elapsed > 0:
                self._fps = (len(self._frame_times) - 1) / elapsed

    def run(self, display: bool = True, max_frames: int | None = None) -> None:
        """
        Run the video processing pipeline.

        Args:
            display: Whether to show the annotated video in a window.
            max_frames: Optional limit on frames to process (for testing).
        """
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            logger.error("Failed to open video source: %s", self.source)
            raise RuntimeError(f"Cannot open video source: {self.source}")

        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        logger.info(
            "Pipeline started — source=%s, resolution=%dx%d, total_frames=%s",
            self.source,
            frame_width,
            frame_height,
            total_frames if total_frames > 0 else "live",
        )

        frame_count = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.info("End of video stream")
                    break

                frame_count += 1
                if max_frames and frame_count > max_frames:
                    break

                # ── 1. Detect ────────────────────────────────────────────
                detections = self.detector.detect(frame)

                # ── 2. Track ─────────────────────────────────────────────
                tracked_objects = self.tracker.update(detections)

                # ── 3. Check violations ──────────────────────────────────
                violations = self.violation_manager.check_violations(
                    tracked_objects, frame
                )

                # ── 4. Annotate ──────────────────────────────────────────
                if display:
                    self._update_fps()
                    annotated = frame.copy()
                    annotated = self.violation_manager.draw_overlays(annotated)
                    annotated = draw_detections(annotated, tracked_objects, violations)
                    annotated = draw_fps(annotated, self._fps)
                    annotated = draw_lane_direction(annotated, self.lane_direction)

                    cv2.imshow("Traffic Violation System", annotated)

                    # Quit on 'q' or ESC
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), 27):
                        logger.info("User quit")
                        break
        finally:
            cap.release()
            if display:
                cv2.destroyAllWindows()

            logger.info(
                "Pipeline stopped — processed %d frames, %d violations detected",
                frame_count,
                self.violation_manager.total_violations,
            )


def main():
    """CLI entry point for the video pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Traffic Violation Detection Pipeline"
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Video source: file path, RTSP URL, or webcam index (default: from .env)",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Run without video display window (headless mode)",
    )
    args = parser.parse_args()

    # Parse source
    source = args.source
    if source is not None:
        try:
            source = int(source)
        except ValueError:
            pass

    pipeline = VideoPipeline(source=source)
    pipeline.run(display=not args.no_display)


if __name__ == "__main__":
    main()
