"""
DishHome AI Voice Bot - Health Check Routes
System health monitoring endpoints.
"""

import time
from fastapi import APIRouter
from app.models.schemas import HealthStatus

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/api/health", response_model=HealthStatus)
async def health_check():
    """System health check endpoint."""
    return HealthStatus(
        status="healthy",
        version="1.0.0",
        stt_status="ready",
        tts_status="ready",
        llm_status="ready",
        database_status="ready",
        uptime_seconds=round(time.time() - _start_time, 1),
    )


@router.get("/api/ping")
async def ping():
    """Simple ping endpoint."""
    return {"status": "pong", "timestamp": time.time()}
