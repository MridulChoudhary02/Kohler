"""
scripts/replay_simulator_to_api.py — Replay simulated telemetry JSONL to live Ingestion API.

Usage:
    cd backend/
    python scripts/replay_simulator_to_api.py \
        --telemetry simulator/output/test_set/combined_telemetry.jsonl \
        --api-url http://localhost:8000/api/v1/telemetry/ingest \
        --batch-size 50
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.seed_data import SEED


def _sensor_map() -> dict[str, str]:
    return {s["fixture_id"]: s["sensor_id"] for s in SEED["sensors"]}


def replay(
    telemetry_path: str | Path,
    api_url: str = "http://localhost:8000/api/v1/telemetry/ingest",
    batch_size: int = 50,
    quiet: bool = False,
) -> dict:
    telemetry_path = Path(telemetry_path)
    sensor_map = _sensor_map()

    if not quiet:
        print("🔄 Telemetry API Replay Harness")
        print(f"   Input:      {telemetry_path.name}")
        print(f"   API Target: {api_url}")
        print(f"   Batch Size: {batch_size}")
        print()

    # Read readings
    readings: list[dict] = []
    with open(telemetry_path) as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                # Resolve sensor_id from fixture_id if missing
                if "sensor_id" not in r or not r["sensor_id"]:
                    fid = r.get("fixture_id", "")
                    r["sensor_id"] = sensor_map.get(fid, fid)
                readings.append(r)

    # Ensure chronological order
    readings.sort(key=lambda x: x.get("timestamp", ""))

    total_readings = len(readings)
    sent_count = 0
    total_events_generated = 0
    dispatched_events = 0
    error_count = 0

    start_time = time.time()

    with httpx.Client(timeout=30.0) as client:
        for i in range(0, total_readings, batch_size):
            chunk = readings[i : i + batch_size]
            payload = chunk if batch_size > 1 else chunk[0]

            try:
                resp = client.post(api_url, json=payload)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    sent_count += len(chunk)
                    evts = data.get("events", [])
                    total_events_generated += len(evts)
                    dispatched_events += sum(1 for e in evts if e.get("status") == "dispatched")
                else:
                    error_count += len(chunk)
                    if not quiet and error_count <= batch_size:
                        print(f"⚠️ API Error ({resp.status_code}): {resp.text}")
            except Exception as e:
                error_count += len(chunk)
                if not quiet and error_count <= batch_size:
                    print(f"❌ Connection error: {e}")

            if not quiet and (sent_count % 10000 == 0 or sent_count == total_readings):
                elapsed = time.time() - start_time
                rps = sent_count / elapsed if elapsed > 0 else 0
                print(f"   Progress: {sent_count:,}/{total_readings:,} readings ({sent_count/total_readings:.1%}) | {rps:.0f} r/s | events: {total_events_generated}")

    elapsed = time.time() - start_time
    if not quiet:
        print()
        print("✅ Replay Complete")
        print(f"   Readings Sent:   {sent_count:,}/{total_readings:,}")
        print(f"   Events Created:  {total_events_generated}")
        print(f"   Dispatched:      {dispatched_events}")
        print(f"   Errors:          {error_count}")
        print(f"   Time Elapsed:    {elapsed:.2f} s ({sent_count/max(elapsed, 0.001):.0f} readings/sec)")

    return {
        "sent_count": sent_count,
        "total_events": total_events_generated,
        "dispatched_events": dispatched_events,
        "errors": error_count,
        "elapsed_s": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description="Replay simulated telemetry JSONL to live API.")
    parser.add_argument("--telemetry", default="simulator/output/test_set/combined_telemetry.jsonl",
                        help="Path to telemetry JSONL file")
    parser.add_argument("--api-url", default="http://localhost:8000/api/v1/telemetry/ingest",
                        help="Ingestion API endpoint URL")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="Number of readings per HTTP request")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    replay(
        telemetry_path=args.telemetry,
        api_url=args.api_url,
        batch_size=args.batch_size,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()
