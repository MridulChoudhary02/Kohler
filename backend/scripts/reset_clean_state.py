"""
backend/scripts/reset_clean_state.py — Clean / Reset Hospital Database to Single-Pass State.

Usage:
    # 1. Surgical in-place deduplication (instantaneous, keeps clean single-pass state):
    python scripts/reset_clean_state.py --deduplicate

    # 2. Full purge and reseed of base topology (clears telemetry, events, tickets):
    python scripts/reset_clean_state.py --purge-all
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.database import AsyncSessionLocal


async def deduplicate_database(verbose: bool = True) -> dict[str, int]:
    """
    Remove duplicate telemetry readings, detection events, and tickets caused by
    repeated replay runs across server restarts.
    Retains the first occurrence (MIN PK / MIN ctid) of every unique event.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 1. Delete redundant tickets linked to duplicate events
            res_t = await session.execute(text("""
                DELETE FROM tickets
                WHERE ticket_id IN (
                    SELECT t.ticket_id
                    FROM tickets t
                    WHERE t.event_id IN (
                        SELECT event_id
                        FROM detection_events
                        WHERE event_id NOT IN (
                            SELECT MIN(event_id)
                            FROM detection_events
                            GROUP BY fixture_id, detected_at, confidence_score, evidence_value
                        )
                    )
                )
            """))
            deleted_tickets = res_t.rowcount

            # 2. Delete redundant detection events
            res_e = await session.execute(text("""
                DELETE FROM detection_events
                WHERE event_id NOT IN (
                    SELECT MIN(event_id)
                    FROM detection_events
                    GROUP BY fixture_id, detected_at, confidence_score, evidence_value
                )
            """))
            deleted_events = res_e.rowcount

            # 3. Delete redundant telemetry readings
            res_tel = await session.execute(text("""
                DELETE FROM telemetry_readings t1
                USING (
                    SELECT sensor_id, timestamp, MIN(ctid) as min_ctid
                    FROM telemetry_readings
                    GROUP BY sensor_id, timestamp
                    HAVING COUNT(*) > 1
                ) t2
                WHERE t1.sensor_id = t2.sensor_id 
                  AND t1.timestamp = t2.timestamp 
                  AND t1.ctid != t2.min_ctid
            """))
            deleted_telemetry = res_tel.rowcount

        # Query remaining clean counts
        total_tel = (await session.execute(text("SELECT COUNT(*) FROM telemetry_readings"))).scalar()
        total_evs = (await session.execute(text("SELECT COUNT(*) FROM detection_events"))).scalar()
        total_tkts = (await session.execute(text("SELECT COUNT(*) FROM tickets"))).scalar()

        if verbose:
            print("✨ Database Deduplication Complete!")
            print(f"   Deleted {deleted_tickets} duplicate tickets (Remaining: {total_tkts})")
            print(f"   Deleted {deleted_events} duplicate detection events (Remaining: {total_evs})")
            print(f"   Deleted {deleted_telemetry} duplicate telemetry readings (Remaining: {total_tel})")

        return {
            "deleted_tickets": deleted_tickets,
            "deleted_events": deleted_events,
            "deleted_telemetry": deleted_telemetry,
            "remaining_tickets": total_tkts,
            "remaining_events": total_evs,
            "remaining_telemetry": total_tel,
        }


async def purge_and_reseed() -> None:
    """
    Truncates operational telemetry, detection, and ticket tables.
    Runs the base topology seeder (facilities, zones, fixtures, sensors, baselines).
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            print("⚠️ Purging operational tables (tickets, detection_events, hygiene_counters, telemetry_readings)...")
            await session.execute(text("""
                TRUNCATE TABLE tickets, detection_events, hygiene_counters, telemetry_readings CASCADE;
            """))
            print("✅ Operational tables truncated.")

    # Run seed.py to re-populate base topology and baseline profiles
    from scripts.seed import run_seed
    await run_seed()
    print("\n💡 Base topology re-seeded. To ingest a single clean pass of telemetry, run:")
    print("   python scripts/replay_simulator_to_api.py --telemetry simulator/output/test_set/combined_telemetry.jsonl --batch-size 100")


def main():
    parser = argparse.ArgumentParser(description="Database reset / deduplication utility.")
    parser.add_argument(
        "--deduplicate",
        action="store_true",
        default=True,
        help="Surgically remove replay duplicates in-place (default).",
    )
    parser.add_argument(
        "--purge-all",
        action="store_true",
        help="Truncate operational tables and reseed base topology.",
    )
    args = parser.parse_args()

    if args.purge_all:
        asyncio.run(purge_and_reseed())
    else:
        asyncio.run(deduplicate_database())


if __name__ == "__main__":
    main()
