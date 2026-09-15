"""
seed.py — Phase 0 database seeder.

Usage (from backend/ directory):
    python scripts/seed.py

Requires:
  - PostgreSQL running with kohler_hospital DB and migrations applied
  - .env file or environment variables set
"""
import asyncio
import uuid
from datetime import datetime, timezone

import asyncpg
from scripts.seed_data import SEED


async def run_seed():
    from app.core.config import settings

    # Build a raw asyncpg connection URL (strip the +asyncpg prefix for raw asyncpg)
    url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)

    print("🌱 Seeding database…\n")

    try:
        async with conn.transaction():
            # 1. Facilities
            print("  → facilities")
            for f in SEED["facilities"]:
                await conn.execute(
                    "INSERT INTO facilities (facility_id, name, type) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                    f["facility_id"], f["name"], f["type"]
                )

            # 2. Technicians
            print("  → technicians")
            for t in SEED["technicians"]:
                await conn.execute(
                    "INSERT INTO technicians (tech_id, name, team) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                    t["tech_id"], t["name"], t["team"]
                )

            # 3. Zones
            print("  → zones")
            for z in SEED["zones"]:
                await conn.execute(
                    "INSERT INTO zones (zone_id, facility_id, name, criticality_tier, occupancy_sensor_id) "
                    "VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
                    z["zone_id"], z["facility_id"], z["name"],
                    z["criticality_tier"], z["occupancy_sensor_id"]
                )

            # 4. SLA Policies
            print("  → sla_policies")
            for s in SEED["sla_policies"]:
                await conn.execute(
                    "INSERT INTO sla_policies (zone_id, criticality_tier, response_minutes) "
                    "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                    s["zone_id"], s["criticality_tier"], s["response_minutes"]
                )

            # 5. Fixtures
            print("  → fixtures")
            for fx in SEED["fixtures"]:
                await conn.execute(
                    "INSERT INTO fixtures (fixture_id, zone_id, fixture_type, install_date) "
                    "VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
                    fx["fixture_id"], fx["zone_id"], fx["fixture_type"], fx["install_date"]
                )

            # 6. Sensors
            print("  → sensors")
            for sn in SEED["sensors"]:
                await conn.execute(
                    "INSERT INTO sensors (sensor_id, fixture_id, sensor_type, status) "
                    "VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
                    sn["sensor_id"], sn["fixture_id"], sn["sensor_type"], sn["status"]
                )

            # 7. Baseline Profiles
            print("  → baseline_profiles")
            now = datetime.now(timezone.utc)
            for bp in SEED["baseline_profiles"]:
                last_updated = datetime.fromisoformat(bp["last_updated"].replace("Z", "+00:00"))
                warmup_started = datetime.fromisoformat(bp["warmup_started_at"].replace("Z", "+00:00"))
                await conn.execute(
                    "INSERT INTO baseline_profiles "
                    "(fixture_id, mean_off_flow, std_off_flow, mean_flush_volume, mean_flush_duration_s, "
                    "last_updated, warmup_complete, warmup_started_at) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT DO NOTHING",
                    bp["fixture_id"], bp["mean_off_flow"], bp["std_off_flow"],
                    bp["mean_flush_volume"], bp["mean_flush_duration_s"],
                    last_updated, bp["warmup_complete"], warmup_started
                )


            # 8. Hygiene Counters
            print("  → hygiene_counters")
            for hc in SEED["hygiene_counters"]:
                last_cleaned = datetime.fromisoformat(hc["last_cleaned"].replace("Z", "+00:00"))
                await conn.execute(
                    "INSERT INTO hygiene_counters "
                    "(id, fixture_id, uses_since_clean, last_cleaned, predicted_breach_time) "
                    "VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
                    str(uuid.uuid4()), hc["fixture_id"], hc["uses_since_clean"],
                    last_cleaned, hc["predicted_breach_time"]
                )

        print("\n✅ Seed complete!")
        print(f"   {len(SEED['facilities'])} facility")
        print(f"   {len(SEED['zones'])} zones  (Tier 1×2, Tier 2×1, Tier 3×1, Tier 4×1)")
        print(f"   {len(SEED['fixtures'])} fixtures")
        print(f"   {len(SEED['sensors'])} sensors")
        print(f"   {len(SEED['baseline_profiles'])} baseline profiles")
        print(f"   {len(SEED['hygiene_counters'])} hygiene counters")
        print(f"   {len(SEED['technicians'])} technicians")
        print(f"   {len(SEED['sla_policies'])} SLA policies")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_seed())
