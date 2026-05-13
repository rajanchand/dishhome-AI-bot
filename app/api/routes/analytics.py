"""
DishHome AI Voice Bot - Analytics Routes
Dashboard metrics and analytics endpoints.
"""

from fastapi import APIRouter
from app.services.call_service import call_service
from app.core.conversation import conversation_manager

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
async def dashboard_metrics():
    """Get dashboard metrics."""
    metrics = await call_service.get_dashboard_metrics()
    active = conversation_manager.get_active_sessions()
    metrics["active_calls"] = len(active)
    return metrics


@router.get("/sessions")
async def session_stats():
    """Get current session statistics."""
    all_sessions = conversation_manager.get_all_sessions()
    active = [s for s in all_sessions if s.is_active]
    return {
        "total_sessions": len(all_sessions),
        "active_sessions": len(active),
        "sessions": [
            {
                "session_id": s.session_id,
                "language": s.language,
                "turns": s.turn_count,
                "duration": round(s.duration_seconds, 1),
                "active": s.is_active,
                "needs_handoff": s.needs_handoff,
            }
            for s in all_sessions[-20:]
        ],
    }
