"""
DishHome AI Voice Bot - Pydantic Schemas
Request/Response validation schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TextChatRequest(BaseModel):
    """Request schema for text-based chat."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    language: Optional[str] = None


class TextChatResponse(BaseModel):
    """Response schema for text-based chat."""
    session_id: str
    user_message: str
    response: str
    language: str
    has_audio: bool = False


class CallSummary(BaseModel):
    """Summary of a call."""
    id: int
    session_id: str
    customer_phone: Optional[str]
    language: str
    started_at: Optional[str]
    duration_seconds: float
    turn_count: int
    status: str
    resolved: bool


class DashboardMetrics(BaseModel):
    """Dashboard analytics metrics."""
    total_calls: int = 0
    active_calls: int = 0
    completed_calls: int = 0
    handoff_calls: int = 0
    avg_duration: float = 0.0
    avg_turns: float = 0.0
    nepali_calls: int = 0
    english_calls: int = 0
    resolution_rate: float = 0.0


class HealthStatus(BaseModel):
    """System health check response."""
    status: str
    version: str = "1.0.0"
    stt_status: str = "unknown"
    tts_status: str = "unknown"
    llm_status: str = "unknown"
    database_status: str = "unknown"
    uptime_seconds: float = 0.0
