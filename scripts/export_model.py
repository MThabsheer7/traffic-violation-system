"""
YOLO26n Model Export Script.

Downloads the YOLO26n pretrained model from Ultralytics and exports it
to OpenVINO IR format (.xml + .bin) for optimized CPU inference.

Pipeline:
    1. Download YOLO26n weights (.pt) via Ultralytics API
    2. Export to OpenVINO IR format (FP32 baseline)
    3. Save to models/ directory

Usage:
    python scripts/export_model.py
    python scripts/export_model.py --model-variant yolo26s  # Use small instead of nano
    python scripts/export_model.py --output-dir ./custom_models
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ultralytics import YOLO  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Supported model variants ─────────────────────────────────────────────────
MODEL_VARIANTS = {
    "yolo26n": "yolo26n.pt",   # Nano — fastest, ideal for edge
    "yolo26s": "yolo26s.pt",   # Small — balanced
    "yolo26m": "yolo26m.pt",   # Medium — more accurate
}

DEFAULT_VARIANT = "yolo26n"
DEFAULT_IMG_SIZE = 640


def export_to_openvino(
    model_variant: str = DEFAULT_VARIANT,
    output_dir: str | None = None,
    img_size: int = DEFAULT_IMG_SIZE,
    half: bool = False,
) -> Path:
    """
    Download YOLO26n and export to OpenVINO IR format.

    Args:
        model_variant: Model variant to use (yolo26n, yolo26s, yolo26m).
        output_dir: Directory to save the exported model.
        img_size: Input image size for the model.
        half: Whether to export in FP16 (half precision).

    Returns:
        Path to the exported OpenVINO model directory.
    """
    if model_variant not in MODEL_VARIANTS:
        raise ValueError(
            f"Unknown model variant: {model_variant}. "
            f"Choose from: {list(MODEL_VARIANTS.keys())}"
        )

    weight_name = MODEL_VARIANTS[model_variant]
    models_dir = Path(output_dir) if output_dir else PROJECT_ROOT / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("YOLO26n Model Export Pipeline")
    logger.info("=" * 60)

    # ── Step 1: Download / Load model ────────────────────────────────────
    logger.info("Step 1/2: Loading %s (will download if not cached)...", weight_name)
    model = YOLO(weight_name)
    logger.info("Model loaded successfully: %s", model.model_name)
    logger.info("  Parameters: %s", f"{sum(p.numel() for p in model.model.parameters()):,}")

    # ── Step 2: Export to OpenVINO ───────────────────────────────────────
    logger.info("Step 2/2: Exporting to OpenVINO IR format...")
    export_path = model.export(
        format="openvino",
        imgsz=img_size,
        half=half,
    )

    export_dir = Path(export_path)
    logger.info("=" * 60)
    logger.info("Export complete!")
    logger.info("  Output directory: %s", export_dir)

    # List exported files
    for f in sorted(export_dir.iterdir()):
        size_mb = f.stat().st_size / (1024 * 1024)
        logger.info("  %s (%.1f MB)", f.name, size_mb)

    logger.info("=" * 60)
    logger.info("Next step: Run 'python scripts/quantize_model.py' for INT8 quantization")

    return export_dir


def main():
    parser = argparse.ArgumentParser(
        description="Export YOLO26n to OpenVINO IR format"
    )
    parser.add_argument(
        "--model-variant",
        type=str,
        default=DEFAULT_VARIANT,
        choices=list(MODEL_VARIANTS.keys()),
        help=f"Model variant to export (default: {DEFAULT_VARIANT})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for exported model (default: models/)",
    )
    parser.add_argument(
        "--img-size",
        type=int,
        default=DEFAULT_IMG_SIZE,
        help=f"Input image size (default: {DEFAULT_IMG_SIZE})",
    )
    parser.add_argument(
        "--half",
        action="store_true",
        help="Export in FP16 half precision",
    )
    args = parser.parse_args()

    export_to_openvino(
        model_variant=args.model_variant,
        output_dir=args.output_dir,
        img_size=args.img_size,
        half=args.half,
    )


if __name__ == "__main__":
    main()
