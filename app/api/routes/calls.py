"""
DishHome AI Voice Bot - Call Management Routes
REST API for call records and management.
"""

from typing import Optional
from fastapi import APIRouter, Query
from loguru import logger

from app.services.call_service import call_service
from app.core.conversation import conversation_manager

router = APIRouter(prefix="/api/calls", tags=["calls"])


@router.get("")
async def list_calls(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
):
    """List all call records with pagination."""
    calls = await call_service.list_calls(limit=limit, offset=offset, status=status)
    return {
        "calls": [c.to_dict() for c in calls],
        "total": len(calls),
        "limit": limit,
        "offset": offset,
    }


@router.get("/active")
async def get_active_calls():
    """Get all currently active calls."""
    sessions = conversation_manager.get_active_sessions()
    return {
        "active_calls": [s.to_dict() for s in sessions],
        "count": len(sessions),
    }


@router.get("/{session_id}")
async def get_call(session_id: str):
    """Get details of a specific call."""
    record = await call_service.get_call(session_id)
    if not record:
        session = conversation_manager.get_session(session_id)
        if session:
            return {"call": session.to_dict(), "source": "active"}
        return {"error": "Call not found"}, 404

    return {"call": record.to_dict(), "source": "database"}


@router.post("/{session_id}/handoff")
async def handoff_call(session_id: str, reason: str = "Agent requested"):
    """Transfer a call to a human agent."""
    success = conversation_manager.request_handoff(session_id, reason)
    if success:
        return {"status": "handoff_requested", "session_id": session_id, "reason": reason}
    return {"error": "Session not found"}, 404
