"""
Kohler Smart Facility & Sustainability Manager — Hospital Edition
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Hospital-grade facility telemetry, leak detection, hygiene prediction, and ticket dispatch system.",
    docs_url="/docs",
    redoc_url="/redoc",
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


# Phase 4+ routers will be registered here as:
# from app.api import telemetry, tickets, events, zones
# app.include_router(telemetry.router, prefix="/api/v1")
# ...
