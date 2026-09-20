"""
Database connection — SQLAlchemy async engine + session factory.
DATABASE_URL is read from environment (see .env.example).
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

import sys
from sqlalchemy.pool import NullPool
from sqlalchemy import select, func
from datetime import datetime, timezone

pool_kwargs = {"poolclass": NullPool} if "pytest" in sys.modules else {"pool_size": 10, "max_overflow": 20}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    **pool_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_data_now(db: AsyncSession) -> datetime:
    """Return a data-driven 'now' timestamp: the greatest of telemetry and detection event timestamps.

    Falls back to wall-clock UTC if no data present.
    """
    # Import models here to avoid module import cycles at top-level
    from app.models.models import TelemetryReading, DetectionEvent

    telemetry_max = select(func.max(TelemetryReading.timestamp)).scalar_subquery()
    detection_max = select(func.max(DetectionEvent.detected_at)).scalar_subquery()
    stmt = select(func.greatest(telemetry_max, detection_max))
    res = await db.execute(stmt)
    max_dt = res.scalar()
    if max_dt is None:
        return datetime.now(timezone.utc)
    if max_dt.tzinfo is None:
        return max_dt.replace(tzinfo=timezone.utc)
    return max_dt
