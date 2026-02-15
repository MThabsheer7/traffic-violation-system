"""
Seed script — populates the SQLite database with realistic demo data.

Creates ~50 sample violation alerts spread across the last 48 hours,
useful for testing the dashboard UI and API endpoints.

Usage:
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --count 100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from backend.api.database import get_session_factory, init_db  # noqa: E402
from backend.api.models import Alert  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Sample Data ───────────────────────────────────────────────────────────────

VIOLATION_TYPES = ["ILLEGAL_PARKING", "WRONG_WAY"]
VEHICLE_CLASSES = ["car", "truck", "bus", "motorcycle"]
ZONE_IDS = ["zone_A", "zone_B", "zone_C", None]

# Hourly weight distribution (more violations during peak hours)
HOUR_WEIGHTS = {
    0: 0.1, 1: 0.05, 2: 0.05, 3: 0.05, 4: 0.1, 5: 0.2,
    6: 0.5, 7: 0.8, 8: 1.0, 9: 0.9, 10: 0.7, 11: 0.6,
    12: 0.7, 13: 0.6, 14: 0.5, 15: 0.6, 16: 0.8, 17: 1.0,
    18: 0.9, 19: 0.7, 20: 0.5, 21: 0.3, 22: 0.2, 23: 0.15,
}


def _generate_alert(base_time: datetime) -> Alert:
    """Generate a single random violation alert."""
    # Pick a weighted random hour
    hours = list(HOUR_WEIGHTS.keys())
    weights = list(HOUR_WEIGHTS.values())
    hour = random.choices(hours, weights=weights, k=1)[0]

    # Random time within that hour
    timestamp = base_time.replace(
        hour=hour,
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
        microsecond=0,
    )

    violation_type = random.choice(VIOLATION_TYPES)
    vehicle_class = random.choice(VEHICLE_CLASSES)

    return Alert(
        violation_type=violation_type,
        confidence=round(random.uniform(0.65, 0.98), 2),
        object_id=random.randint(1, 200),
        snapshot_path=f"snapshots/{violation_type.lower()}_{random.randint(1000, 9999)}.jpg",
        zone_id=random.choice(ZONE_IDS),
        metadata_json=json.dumps({
            "vehicle_class": vehicle_class,
            "speed_estimate": round(random.uniform(0, 60), 1) if violation_type == "WRONG_WAY" else None,
        }),
        timestamp=timestamp,
    )


async def seed(count: int = 50) -> None:
    """Seed the database with sample alerts."""
    await init_db()
    factory = get_session_factory()

    now = datetime.now(timezone.utc)
    alerts = []

    for day_offset in range(3):  # Last 3 days
        base = now - timedelta(days=day_offset)
        day_count = count // 3 + (1 if day_offset < count % 3 else 0)
        for _ in range(day_count):
            alerts.append(_generate_alert(base))

    async with factory() as session:
        session.add_all(alerts)
        await session.commit()

    logger.info("Seeded %d sample violation alerts", len(alerts))
    logger.info("  Date range: %s to %s", min(a.timestamp for a in alerts), max(a.timestamp for a in alerts))
    logger.info("  Types: %s", {t: sum(1 for a in alerts if a.violation_type == t) for t in VIOLATION_TYPES})


def main():
    parser = argparse.ArgumentParser(description="Seed demo violation data")
    parser.add_argument("--count", type=int, default=50, help="Number of alerts to generate")
    args = parser.parse_args()

    asyncio.run(seed(count=args.count))


if __name__ == "__main__":
    main()
