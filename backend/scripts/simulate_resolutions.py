"""
scripts/simulate_resolutions.py — Assign realistic status/resolution diversity
to freshly-ingested tickets after a replay.

Without this, every ticket ingested by replay_simulator_to_api.py sits at
status="open" with resolved_at=NULL. This script distributes tickets across
the full lifecycle (open / acknowledged / in_progress / resolved) with a
realistic SPREAD of resolution speeds, deterministically (seeded), so the
Sustainability "estimated water saved" feature has real non-zero examples
alongside honest slow ones.

Usage (from backend/ directory):
    python scripts/simulate_resolutions.py
"""
from __future__ import annotations

import asyncio
import random
from datetime import timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import Ticket, DetectionEvent

RNG = random.Random(42)  # deterministic, matches simulator's base_seed

# (weight, status, resolved_delta_minutes_range or None)
DISTRIBUTION = [
    (0.15, "resolved", (20, 90)),       # fast — well within any reference window
    (0.20, "resolved", (120, 300)),     # moderate — within 6h reference window
    (0.20, "resolved", (600, 1800)),    # slow — exceeds reference window (honest zero-savings case)
    (0.15, "in_progress", None),
    (0.15, "acknowledged", None),
    (0.15, "open", None),
]


def pick_bucket() -> tuple[str, tuple[int, int] | None]:
    r = RNG.random()
    cumulative = 0.0
    for weight, status, delta_range in DISTRIBUTION:
        cumulative += weight
        if r <= cumulative:
            return status, delta_range
    return DISTRIBUTION[-1][1], DISTRIBUTION[-1][2]


async def main() -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            rows = (
                await session.execute(
                    select(Ticket, DetectionEvent)
                    .join(DetectionEvent, Ticket.event_id == DetectionEvent.event_id)
                    .order_by(DetectionEvent.detected_at)
                )
            ).all()

            print(f"Found {len(rows)} tickets to distribute across lifecycle states.\n")

            counts: dict[str, int] = {}
            for ticket, event in rows:
                status, delta_range = pick_bucket()
                ticket.status = status
                if status == "resolved" and delta_range and event.detected_at:
                    delta_min = RNG.uniform(*delta_range)
                    ticket.resolved_at = event.detected_at + timedelta(minutes=delta_min)
                    ticket.started_at = event.detected_at + timedelta(minutes=RNG.uniform(1, 5))
                else:
                    ticket.resolved_at = None
                    if status in ("acknowledged", "in_progress"):
                        ticket.started_at = event.detected_at + timedelta(minutes=RNG.uniform(1, 5))

                counts[status] = counts.get(status, 0) + 1

            for status, n in counts.items():
                print(f"  {status:14s}: {n}")

        print("\nCommitted.")


if __name__ == "__main__":
    asyncio.run(main())
