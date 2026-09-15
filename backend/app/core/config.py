"""
Application settings — loaded from environment variables / .env file.

Every tunable constant named in PRD Sections 7–10 is defined here as a
named field so detection logic never contains magic numbers.
"""
import json
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Infrastructure ────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://kohler:kohler@localhost:5432/kohler_hospital"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://kohler:kohler@localhost:5432/kohler_hospital"
    DEBUG: bool = False
    APP_NAME: str = "Kohler Smart Facility & Sustainability Manager"
    APP_VERSION: str = "0.1.0"

    # ── LLM (Phase 7 — unused until then) ────────────────────────────────────
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: str = ""

    # ── Section 7.1 — Baseline learning ──────────────────────────────────────
    # α for nightly exponentially-weighted baseline update
    BASELINE_ALPHA: float = 0.1
    # Days of telemetry required before detection is trusted at full sensitivity
    BASELINE_WARMUP_DAYS: int = 7

    # ── Section 7.2 — EWMA control chart ─────────────────────────────────────
    # λ in: EWMA_t = λ × flow_t + (1−λ) × EWMA_(t−1)
    EWMA_LAMBDA: float = 0.2
    # L in: UCL = mean_off_flow + L × std_off_flow
    UCL_L_FACTOR: float = 3.0
    # Confirmation windows (minutes) per criticality tier before a candidate
    # leak event is raised. Tier 1=shortest, Tier 4=longest.
    CONFIRMATION_WINDOW_TIER1_MIN: int = 3
    CONFIRMATION_WINDOW_TIER2_MIN: int = 5
    CONFIRMATION_WINDOW_TIER3_MIN: int = 7
    CONFIRMATION_WINDOW_TIER4_MIN: int = 10

    # ── Section 7.5 — Confidence scoring weights ──────────────────────────────
    # confidence = w1×(EWMA deviation, normalised)
    #            + w2×(occupancy cross-check boost, 0 or 1)
    #            + w3×(post-flush pattern match, 0 or 1)
    #            − penalty(sensor_health_score)
    CONFIDENCE_W1: float = 0.40   # EWMA deviation component
    CONFIDENCE_W2: float = 0.35   # occupancy cross-check boost
    CONFIDENCE_W3: float = 0.25   # post-flush pattern match

    # Confidence dispatch thresholds (Section 7.5)
    CONFIDENCE_LOG_ONLY: float = 0.5   # below this → logged only, not dispatched
    CONFIDENCE_ESCALATE: float = 0.8   # at or above → escalated priority

    # ── Section 8 — Hygiene threshold prediction ──────────────────────────────
    # Raise a predictive hygiene ticket when breach is this many minutes away
    HYGIENE_LEAD_TIME_MINUTES: int = 30
    # Tier 1 gets a shorter lead time (more critical — default to half)
    HYGIENE_LEAD_TIME_TIER1_MINUTES: int = 15
    # Sliding window for computing recent_use_rate (minutes)
    HYGIENE_USE_RATE_WINDOW_MINUTES: int = 60

    # ── Section 9 — Sensor health scoring ────────────────────────────────────
    # sensor_health_score = 1 − (w_miss×missing_rate + w_flat×flatline_flag
    #                            + w_oor×out_of_range_rate + w_drift×drift_flag)
    SENSOR_HEALTH_W_MISSING:    float = 0.30
    SENSOR_HEALTH_W_FLATLINE:   float = 0.30
    SENSOR_HEALTH_W_OUT_OF_RANGE: float = 0.20
    SENSOR_HEALTH_W_DRIFT:      float = 0.20
    # Below this score, downgrade events to "logged only" and raise sensor ticket
    SENSOR_HEALTH_DEGRADED_THRESHOLD: float = 0.60

    # ── Section 10 — Ticket priority scoring ─────────────────────────────────
    # priority_score = (zone_criticality_weight × w_zone)
    #                + (confidence_score × w_conf)
    #                + (normalised_estimated_waste × w_waste)
    #                + (SLA_urgency_factor × w_sla)
    PRIORITY_W_ZONE:  float = 0.40
    PRIORITY_W_CONF:  float = 0.30
    PRIORITY_W_WASTE: float = 0.20
    PRIORITY_W_SLA:   float = 0.10

    # Zone criticality weights (Tier 1 → highest weight)
    CRITICALITY_WEIGHT_TIER1: float = 1.00
    CRITICALITY_WEIGHT_TIER2: float = 0.75
    CRITICALITY_WEIGHT_TIER3: float = 0.50
    CRITICALITY_WEIGHT_TIER4: float = 0.25

    class Config:
        env_file = ".env"
        case_sensitive = True

    # ── Derived helpers (not env-overridable, computed from above) ────────────
    @property
    def confirmation_windows(self) -> dict[str, int]:
        """Map criticality tier → confirmation window in minutes."""
        return {
            "Tier 1": self.CONFIRMATION_WINDOW_TIER1_MIN,
            "Tier 2": self.CONFIRMATION_WINDOW_TIER2_MIN,
            "Tier 3": self.CONFIRMATION_WINDOW_TIER3_MIN,
            "Tier 4": self.CONFIRMATION_WINDOW_TIER4_MIN,
        }

    @property
    def criticality_weights(self) -> dict[str, float]:
        """Map criticality tier → zone weight for priority scoring."""
        return {
            "Tier 1": self.CRITICALITY_WEIGHT_TIER1,
            "Tier 2": self.CRITICALITY_WEIGHT_TIER2,
            "Tier 3": self.CRITICALITY_WEIGHT_TIER3,
            "Tier 4": self.CRITICALITY_WEIGHT_TIER4,
        }


settings = Settings()

