"""
Phase 0 seed data — sample hospital with:
  - 1 facility: City General Hospital
  - 4 zones covering all 4 criticality tiers
  - 20 fixtures across those zones (≥15 required by PRD)
  - 1 sensor per fixture (SENSOR ||--|| FIXTURE per ER diagram)
  - 1 baseline_profile per fixture
  - 1 hygiene_counter per fixture
  - 1 sla_policy per zone (per SLA_POLICY table per PRD)
  - 4 technicians (one per team type)

Fixture-type distribution per zone follows PRD Section 5 fixture types:
  faucet | flush_valve | urinal | shower | scrub_tap
"""

SEED = {
    "facilities": [
        {
            "facility_id": "fac-001",
            "name": "City General Hospital",
            "type": "Hospital",
        }
    ],

    "technicians": [
        {
            "tech_id": "tech-001",
            "name": "Arjun Mehta",
            "team": "Critical Care Maintenance",
        },
        {
            "tech_id": "tech-002",
            "name": "Sunita Rao",
            "team": "General Plumbing",
        },
        {
            "tech_id": "tech-003",
            "name": "Vikram Nair",
            "team": "Clinical Support",
        },
        {
            "tech_id": "tech-004",
            "name": "Priya Sharma",
            "team": "Hygiene & Sanitation",
        },
    ],

    # ── 4 ZONES — one per criticality tier ────────────────────────────────────
    "zones": [
        {
            "zone_id":             "zone-icu",
            "facility_id":         "fac-001",
            "name":                "ICU Restrooms & Scrub Area",
            "criticality_tier":    "Tier 1",
            "occupancy_sensor_id": None,        # set after sensor creation for demo clarity
        },
        {
            "zone_id":             "zone-ot",
            "facility_id":         "fac-001",
            "name":                "Operating Theatre Scrub Stations",
            "criticality_tier":    "Tier 1",    # OT is also Tier 1 per PRD Table
            "occupancy_sensor_id": None,
        },
        {
            "zone_id":             "zone-ward",
            "facility_id":         "fac-001",
            "name":                "General Ward Restrooms",
            "criticality_tier":    "Tier 2",
            "occupancy_sensor_id": None,
        },
        {
            "zone_id":             "zone-lab",
            "facility_id":         "fac-001",
            "name":                "Lab & Staff Scrub Rooms",
            "criticality_tier":    "Tier 3",
            "occupancy_sensor_id": None,
        },
        {
            "zone_id":             "zone-lobby",
            "facility_id":         "fac-001",
            "name":                "Lobby & Visitor Washrooms",
            "criticality_tier":    "Tier 4",
            "occupancy_sensor_id": None,
        },
    ],

    # ── SLA POLICIES — one per zone, derived from PRD Section 5 table ─────────
    "sla_policies": [
        {"zone_id": "zone-icu",   "criticality_tier": "Tier 1", "response_minutes": 15},
        {"zone_id": "zone-ot",    "criticality_tier": "Tier 1", "response_minutes": 15},
        {"zone_id": "zone-ward",  "criticality_tier": "Tier 2", "response_minutes": 30},
        {"zone_id": "zone-lab",   "criticality_tier": "Tier 3", "response_minutes": 60},
        {"zone_id": "zone-lobby", "criticality_tier": "Tier 4", "response_minutes": 120},
    ],

    # ── 20 FIXTURES across 5 zones ────────────────────────────────────────────
    # PRD fixture types: faucet | flush_valve | urinal | shower | scrub_tap
    "fixtures": [
        # Zone: ICU (Tier 1) — 5 fixtures
        {"fixture_id": "fix-icu-001", "zone_id": "zone-icu", "fixture_type": "faucet",      "install_date": "2022-03-10"},
        {"fixture_id": "fix-icu-002", "zone_id": "zone-icu", "fixture_type": "flush_valve",  "install_date": "2022-03-10"},
        {"fixture_id": "fix-icu-003", "zone_id": "zone-icu", "fixture_type": "flush_valve",  "install_date": "2022-03-10"},
        {"fixture_id": "fix-icu-004", "zone_id": "zone-icu", "fixture_type": "shower",       "install_date": "2022-03-10"},
        {"fixture_id": "fix-icu-005", "zone_id": "zone-icu", "fixture_type": "faucet",       "install_date": "2023-07-15"},

        # Zone: OT (Tier 1) — 4 fixtures
        {"fixture_id": "fix-ot-001",  "zone_id": "zone-ot",  "fixture_type": "scrub_tap",   "install_date": "2021-11-01"},
        {"fixture_id": "fix-ot-002",  "zone_id": "zone-ot",  "fixture_type": "scrub_tap",   "install_date": "2021-11-01"},
        {"fixture_id": "fix-ot-003",  "zone_id": "zone-ot",  "fixture_type": "scrub_tap",   "install_date": "2021-11-01"},
        {"fixture_id": "fix-ot-004",  "zone_id": "zone-ot",  "fixture_type": "faucet",      "install_date": "2021-11-01"},

        # Zone: General Ward (Tier 2) — 5 fixtures
        {"fixture_id": "fix-ward-001","zone_id": "zone-ward", "fixture_type": "faucet",     "install_date": "2020-06-20"},
        {"fixture_id": "fix-ward-002","zone_id": "zone-ward", "fixture_type": "flush_valve", "install_date": "2020-06-20"},
        {"fixture_id": "fix-ward-003","zone_id": "zone-ward", "fixture_type": "urinal",      "install_date": "2020-06-20"},
        {"fixture_id": "fix-ward-004","zone_id": "zone-ward", "fixture_type": "shower",      "install_date": "2020-06-20"},
        {"fixture_id": "fix-ward-005","zone_id": "zone-ward", "fixture_type": "faucet",      "install_date": "2023-01-05"},

        # Zone: Lab / Staff Scrub (Tier 3) — 3 fixtures
        {"fixture_id": "fix-lab-001", "zone_id": "zone-lab",  "fixture_type": "scrub_tap",  "install_date": "2019-09-12"},
        {"fixture_id": "fix-lab-002", "zone_id": "zone-lab",  "fixture_type": "faucet",     "install_date": "2019-09-12"},
        {"fixture_id": "fix-lab-003", "zone_id": "zone-lab",  "fixture_type": "flush_valve", "install_date": "2019-09-12"},

        # Zone: Lobby (Tier 4) — 3 fixtures
        {"fixture_id": "fix-lob-001", "zone_id": "zone-lobby","fixture_type": "faucet",     "install_date": "2018-04-01"},
        {"fixture_id": "fix-lob-002", "zone_id": "zone-lobby","fixture_type": "flush_valve", "install_date": "2018-04-01"},
        {"fixture_id": "fix-lob-003", "zone_id": "zone-lobby","fixture_type": "urinal",      "install_date": "2018-04-01"},
    ],

    # ── SENSORS — 1 per fixture, SENSOR ||--|| FIXTURE ────────────────────────
    # sensor_type: "flow_occupancy_combined" for most (measures both flow and occupancy)
    # scrub_tap sensors are "flow_only" (no occupancy signal — operator is always present)
    "sensors": [
        # ICU
        {"sensor_id": "sen-icu-001", "fixture_id": "fix-icu-001", "sensor_type": "flow_occupancy_combined", "status": "active"},
        {"sensor_id": "sen-icu-002", "fixture_id": "fix-icu-002", "sensor_type": "flow_occupancy_combined", "status": "active"},
        {"sensor_id": "sen-icu-003", "fixture_id": "fix-icu-003", "sensor_type": "flow_occupancy_combined", "status": "active"},
        {"sensor_id": "sen-icu-004", "fixture_id": "fix-icu-004", "sensor_type": "flow_occupancy_combined", "status": "active"},
        {"sensor_id": "sen-icu-005", "fixture_id": "fix-icu-005", "sensor_type": "flow_occupancy_combined", "status": "active"},
        # OT
        {"sensor_id": "sen-ot-001",  "fixture_id": "fix-ot-001",  "sensor_type": "flow_only",               "status": "active"},
        {"sensor_id": "sen-ot-002",  "fixture_id": "fix-ot-002",  "sensor_type": "flow_only",               "status": "active"},
        {"sensor_id": "sen-ot-003",  "fixture_id": "fix-ot-003",  "sensor_type": "flow_only",               "status": "active"},
        {"sensor_id": "sen-ot-004",  "fixture_id": "fix-ot-004",  "sensor_type": "flow_occupancy_combined", "status": "active"},
        # Ward
        {"sensor_id": "sen-ward-001","fixture_id": "fix-ward-001","sensor_type": "flow_occupancy_combined", "status": "active"},
        {"sensor_id": "sen-ward-002","fixture_id": "fix-ward-002","sensor_type": "flow_occupancy_combined", "status": "active"},
        {"sensor_id": "sen-ward-003","fixture_id": "fix-ward-003","sensor_type": "flow_occupancy_combined", "status": "active"},
        {"sensor_id": "sen-ward-004","fixture_id": "fix-ward-004","sensor_type": "flow_occupancy_combined", "status": "active"},
        {"sensor_id": "sen-ward-005","fixture_id": "fix-ward-005","sensor_type": "flow_occupancy_combined", "status": "active"},
        # Lab
        {"sensor_id": "sen-lab-001", "fixture_id": "fix-lab-001", "sensor_type": "flow_only",               "status": "active"},
        {"sensor_id": "sen-lab-002", "fixture_id": "fix-lab-002", "sensor_type": "flow_occupancy_combined", "status": "active"},
        {"sensor_id": "sen-lab-003", "fixture_id": "fix-lab-003", "sensor_type": "flow_occupancy_combined", "status": "active"},
        # Lobby
        {"sensor_id": "sen-lob-001", "fixture_id": "fix-lob-001", "sensor_type": "flow_occupancy_combined", "status": "active"},
        {"sensor_id": "sen-lob-002", "fixture_id": "fix-lob-002", "sensor_type": "flow_occupancy_combined", "status": "active"},
        {"sensor_id": "sen-lob-003", "fixture_id": "fix-lob-003", "sensor_type": "flow_occupancy_combined", "status": "active"},
    ],

    # ── BASELINE_PROFILES ──────────────────────────────────────────────────────
    # IMPORTANT: warmup_complete=False on ALL seeded profiles.
    # These are UNTRUSTED PLACEHOLDERS (engineering estimates), not profiles
    # learned from real telemetry. The detection engine (Phase 2) must treat
    # every fixture as being in warm-up until 7 days of real telemetry
    # accumulate and it sets warmup_complete=True.
    #
    # PRD Section 7.1: different fixture types have different normal signatures.
    # mean_flush_volume (L): flush_valve ~6L, urinal ~3-3.5L, shower N/A (continuous)
    # std_off_flow: tighter for newer/higher-tier fixtures
    "baseline_profiles": [
        # ICU (Tier 1) — tight baselines, new fixtures
        {"fixture_id": "fix-icu-001", "mean_off_flow": 0.0,  "std_off_flow": 0.03, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-icu-002", "mean_off_flow": 0.0,  "std_off_flow": 0.03, "mean_flush_volume": 6.0, "mean_flush_duration_s": 8.5,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-icu-003", "mean_off_flow": 0.0,  "std_off_flow": 0.03, "mean_flush_volume": 6.0, "mean_flush_duration_s": 8.5,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-icu-004", "mean_off_flow": 0.0,  "std_off_flow": 0.05, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-icu-005", "mean_off_flow": 0.0,  "std_off_flow": 0.03, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        # OT (Tier 1) — scrub taps run longer per use
        {"fixture_id": "fix-ot-001",  "mean_off_flow": 0.0,  "std_off_flow": 0.02, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-ot-002",  "mean_off_flow": 0.0,  "std_off_flow": 0.02, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-ot-003",  "mean_off_flow": 0.0,  "std_off_flow": 0.02, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-ot-004",  "mean_off_flow": 0.0,  "std_off_flow": 0.03, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        # Ward (Tier 2)
        {"fixture_id": "fix-ward-001","mean_off_flow": 0.0,  "std_off_flow": 0.05, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-ward-002","mean_off_flow": 0.0,  "std_off_flow": 0.05, "mean_flush_volume": 6.0, "mean_flush_duration_s": 10.0, "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-ward-003","mean_off_flow": 0.0,  "std_off_flow": 0.05, "mean_flush_volume": 3.5, "mean_flush_duration_s": 6.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-ward-004","mean_off_flow": 0.0,  "std_off_flow": 0.05, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-ward-005","mean_off_flow": 0.0,  "std_off_flow": 0.05, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        # Lab (Tier 3) — older fixtures, slightly wider std
        {"fixture_id": "fix-lab-001", "mean_off_flow": 0.0,  "std_off_flow": 0.07, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-lab-002", "mean_off_flow": 0.0,  "std_off_flow": 0.07, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-lab-003", "mean_off_flow": 0.0,  "std_off_flow": 0.07, "mean_flush_volume": 6.0, "mean_flush_duration_s": 11.0, "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        # Lobby (Tier 4) — oldest fixtures, widest normal variance
        {"fixture_id": "fix-lob-001", "mean_off_flow": 0.02, "std_off_flow": 0.10, "mean_flush_volume": 0.0, "mean_flush_duration_s": 0.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-lob-002", "mean_off_flow": 0.01, "std_off_flow": 0.10, "mean_flush_volume": 6.5, "mean_flush_duration_s": 12.0, "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
        {"fixture_id": "fix-lob-003", "mean_off_flow": 0.01, "std_off_flow": 0.10, "mean_flush_volume": 3.5, "mean_flush_duration_s": 7.0,  "last_updated": "2026-09-15T00:00:00Z", "warmup_complete": False, "warmup_started_at": "2026-09-15T00:00:00Z"},
    ],

    # ── HYGIENE_COUNTERS — initial state (all just cleaned) ───────────────────
    # PRD Section 8: uses_since_clean = 0, no predicted_breach_time yet (engine computes at runtime)
    "hygiene_counters": [
        {"fixture_id": "fix-icu-001",  "uses_since_clean": 0,  "last_cleaned": "2026-09-15T06:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-icu-002",  "uses_since_clean": 3,  "last_cleaned": "2026-09-15T06:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-icu-003",  "uses_since_clean": 2,  "last_cleaned": "2026-09-15T06:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-icu-004",  "uses_since_clean": 1,  "last_cleaned": "2026-09-15T06:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-icu-005",  "uses_since_clean": 5,  "last_cleaned": "2026-09-15T06:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-ot-001",   "uses_since_clean": 8,  "last_cleaned": "2026-09-15T07:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-ot-002",   "uses_since_clean": 7,  "last_cleaned": "2026-09-15T07:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-ot-003",   "uses_since_clean": 10, "last_cleaned": "2026-09-15T07:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-ot-004",   "uses_since_clean": 6,  "last_cleaned": "2026-09-15T07:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-ward-001", "uses_since_clean": 12, "last_cleaned": "2026-09-15T05:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-ward-002", "uses_since_clean": 14, "last_cleaned": "2026-09-15T05:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-ward-003", "uses_since_clean": 9,  "last_cleaned": "2026-09-15T05:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-ward-004", "uses_since_clean": 7,  "last_cleaned": "2026-09-15T05:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-ward-005", "uses_since_clean": 11, "last_cleaned": "2026-09-15T05:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-lab-001",  "uses_since_clean": 20, "last_cleaned": "2026-09-15T04:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-lab-002",  "uses_since_clean": 18, "last_cleaned": "2026-09-15T04:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-lab-003",  "uses_since_clean": 15, "last_cleaned": "2026-09-15T04:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-lob-001",  "uses_since_clean": 30, "last_cleaned": "2026-09-15T03:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-lob-002",  "uses_since_clean": 28, "last_cleaned": "2026-09-15T03:00:00Z", "predicted_breach_time": None},
        {"fixture_id": "fix-lob-003",  "uses_since_clean": 33, "last_cleaned": "2026-09-15T03:00:00Z", "predicted_breach_time": None},
    ],
}


# ── Hygiene threshold reference (from PRD Section 5 table) ────────────────────
# Domain data (zone threshold values), not algorithm tuning — lives here, not config.py.
# The detection engine (Phase 3) imports this to check uses_since_clean.
HYGIENE_THRESHOLDS = {
    "Tier 1": {"min": 15, "max": 20},
    "Tier 2": {"min": 25, "max": 30},
    "Tier 3": {"min": 35, "max": 40},
    "Tier 4": {"min": 50, "max": 60},
}

# NOTE: All other tunable constants (EWMA λ, UCL L, confirmation windows per tier,
# confidence weights w1/w2/w3, sensor health weights, priority scoring weights,
# zone criticality weights) are defined in app/core/config.py as named Settings
# fields so they can be overridden via environment variables without code changes.
