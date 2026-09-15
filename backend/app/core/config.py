"""
Application settings — loaded from environment variables / .env file.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://kohler:kohler@localhost:5432/kohler_hospital"

    # Sync URL for Alembic (uses psycopg2 driver, not asyncpg)
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://kohler:kohler@localhost:5432/kohler_hospital"

    # App
    DEBUG: bool = False
    APP_NAME: str = "Kohler Smart Facility & Sustainability Manager"
    APP_VERSION: str = "0.1.0"

    # LLM (Phase 7 — unused until then)
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: str = ""

    # Detection engine tuning (PRD Section 7, tunable values)
    EWMA_LAMBDA: float = 0.2        # λ in EWMA control chart
    UCL_L_FACTOR: float = 3.0       # L × std_off_flow for UCL
    BASELINE_ALPHA: float = 0.1     # α for nightly EWMA baseline update
    BASELINE_WARMUP_DAYS: int = 7   # days before full-sensitivity detection

    # Confidence thresholds (Section 7.5)
    CONFIDENCE_LOG_ONLY: float = 0.5
    CONFIDENCE_ESCALATE: float = 0.8

    # Hygiene prediction lead time (Section 8)
    HYGIENE_LEAD_TIME_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
