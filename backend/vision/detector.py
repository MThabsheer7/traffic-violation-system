"""
YOLO26n Object Detector — OpenVINO INT8 Inference Engine.

Loads a YOLO26n model exported to OpenVINO IR format and runs inference
on individual frames. Returns structured Detection objects for vehicle
classes only (car, truck, bus, motorcycle).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── COCO class IDs for vehicles ──────────────────────────────────────────────
VEHICLE_CLASS_IDS = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


@dataclass
class Detection:
    """A single detected object in a frame."""

    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2) — top-left, bottom-right
    class_id: int
    class_name: str
    confidence: float
    center: tuple[int, int] = field(init=False)

    def __post_init__(self):
        x1, y1, x2, y2 = self.bbox
        self.center = ((x1 + x2) // 2, (y1 + y2) // 2)


class YOLODetector:
    """
    YOLO26n detector using OpenVINO runtime for optimized CPU inference.

    Supports both OpenVINO IR (.xml/.bin) and ONNX model formats.
    Filters detections to vehicle classes only.
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.45,
        input_size: tuple[int, int] = (640, 640),
    ):
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.input_size = input_size  # (width, height)
        self._model = None
        self._compiled_model = None
        self._input_layer = None
        self._output_layer = None

        self._load_model()

    def _load_model(self) -> None:
        """Load and compile the model using OpenVINO runtime."""
        import openvino as ov

        core = ov.Core()

        # Determine model file path
        model_file = self._resolve_model_path()
        logger.info("Loading model from: %s", model_file)

        # Read and compile model for CPU
        self._model = core.read_model(str(model_file))
        self._compiled_model = core.compile_model(self._model, "CPU")

        # Cache input/output layer references
        self._input_layer = self._compiled_model.input(0)
        self._output_layer = self._compiled_model.output(0)

        logger.info(
            "Model loaded — input shape: %s, output shape: %s",
            self._input_layer.shape,
            self._output_layer.shape,
        )

    def _resolve_model_path(self) -> Path:
        """Find the model file (.xml or .onnx) in the model directory."""
        if self.model_path.is_file():
            return self.model_path

        # Search for OpenVINO IR first, then ONNX
        for ext in (".xml", ".onnx"):
            candidates = list(self.model_path.glob(f"*{ext}"))
            if candidates:
                return candidates[0]

        raise FileNotFoundError(
            f"No model file (.xml or .onnx) found in {self.model_path}"
        )

    def _preprocess(self, frame: np.ndarray) -> tuple[np.ndarray, float, tuple[int, int]]:
        """
        Preprocess frame for YOLO inference with letterbox resizing.

        Returns:
            input_tensor: Preprocessed tensor ready for inference (1, 3, H, W)
            scale: Scale factor applied during resize
            pad: (pad_x, pad_y) padding applied
        """
        target_w, target_h = self.input_size
        h, w = frame.shape[:2]

        # Compute letterbox scale (maintain aspect ratio)
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)

        # Resize with letterbox
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Pad to target size (center the image)
        pad_x = (target_w - new_w) // 2
        pad_y = (target_h - new_h) // 2

        canvas = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
        canvas[pad_y : pad_y + new_h, pad_x : pad_x + new_w] = resized

        # HWC → CHW, normalize to [0, 1], add batch dimension
        blob = canvas.astype(np.float32) / 255.0
        blob = blob.transpose(2, 0, 1)  # CHW
        blob = np.expand_dims(blob, axis=0)  # NCHW

        return blob, scale, (pad_x, pad_y)

    def _postprocess(
        self,
        output: np.ndarray,
        scale: float,
        pad: tuple[int, int],
        original_shape: tuple[int, int],
    ) -> list[Detection]:
        """
        Post-process YOLO26n output tensor into Detection objects.

        YOLO26n is NMS-free — output is already de-duplicated.
        Output shape: (1, num_classes + 4, num_detections) for YOLO26n.
        """
        # Squeeze batch dimension → (num_classes + 4, num_detections)
        predictions = np.squeeze(output, axis=0)

        # YOLO outputs: (4 + num_classes, N) → transpose to (N, 4 + num_classes)
        if predictions.shape[0] < predictions.shape[1]:
            predictions = predictions.T

        detections: list[Detection] = []
        pad_x, pad_y = pad
        orig_h, orig_w = original_shape

        for pred in predictions:
            # First 4 values are box coordinates (cx, cy, w, h)
            cx, cy, bw, bh = pred[:4]
            class_scores = pred[4:]

            # Get best class
            class_id = int(np.argmax(class_scores))
            confidence = float(class_scores[class_id])

            # Filter: confidence threshold + vehicle classes only
            if confidence < self.confidence_threshold:
                continue
            if class_id not in VEHICLE_CLASS_IDS:
                continue

            # Convert from center format to corner format
            x1 = cx - bw / 2
            y1 = cy - bh / 2
            x2 = cx + bw / 2
            y2 = cy + bh / 2

            # Remove letterbox padding and rescale to original frame
            x1 = int((x1 - pad_x) / scale)
            y1 = int((y1 - pad_y) / scale)
            x2 = int((x2 - pad_x) / scale)
            y2 = int((y2 - pad_y) / scale)

            # Clamp to frame boundaries
            x1 = max(0, min(x1, orig_w - 1))
            y1 = max(0, min(y1, orig_h - 1))
            x2 = max(0, min(x2, orig_w - 1))
            y2 = max(0, min(y2, orig_h - 1))

            # Skip degenerate boxes
            if x2 <= x1 or y2 <= y1:
                continue

            detections.append(
                Detection(
                    bbox=(x1, y1, x2, y2),
                    class_id=class_id,
                    class_name=VEHICLE_CLASS_IDS[class_id],
                    confidence=confidence,
                )
            )

        return detections

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """
        Run detection on a single BGR frame.

        Args:
            frame: BGR image as numpy array (H, W, 3)

        Returns:
            List of Detection objects for vehicles found in the frame.
        """
        original_shape = frame.shape[:2]  # (H, W)

        # Preprocess
        blob, scale, pad = self._preprocess(frame)

        # Inference
        result = self._compiled_model([blob])
        output = result[self._output_layer]

        # Post-process
        detections = self._postprocess(output, scale, pad, original_shape)

        logger.debug("Detected %d vehicles", len(detections))
        return detections
