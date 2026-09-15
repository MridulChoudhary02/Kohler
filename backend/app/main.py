"""
Kohler Smart Facility & Sustainability Manager — Hospital Edition
FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.detection_service import detection_service
from app.api import telemetry, events


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler — runs startup and shutdown tasks."""
    print("🏥 Starting up Kohler Facility Platform...")
    async with AsyncSessionLocal() as db_session:
        await detection_service.initialize(db_session=db_session)
    yield
    print("🏥 Shutting down Kohler Facility Platform...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Hospital-grade facility telemetry, leak detection, hygiene prediction, and ticket dispatch system.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — open for dev; tighten for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# Phase 4 Routers
app.include_router(telemetry.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
