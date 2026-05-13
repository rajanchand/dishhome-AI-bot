"""
Agent dashboard routes — call queue, screen pop, my-tickets, WS push.
"""

import asyncio
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db, User, CallRecord, Ticket
from app.services.customer_service import customer_service
from app.services.cache_service import cache_service
from app.core.conversation import conversation_manager
from app.utils.dependencies import require_permission, get_current_user
from loguru import logger

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/call-queue")
async def call_queue(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("agent", "read")),
):
    result = await db.execute(
        select(CallRecord).where(CallRecord.status == "active").order_by(desc(CallRecord.started_at))
    )
    items = [c.to_dict() for c in result.scalars()]
    # also include in-memory sessions
    in_memory = [s.to_dict() for s in conversation_manager.get_active_sessions()]
    return {"db_active": items, "in_memory_sessions": in_memory}


@router.get("/screen-pop/{session_id}")
async def screen_pop(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("agent", "read")),
):
    call = (await db.execute(
        select(CallRecord).where(CallRecord.session_id == session_id)
    )).scalar_one_or_none()
    if call is None:
        # Maybe still in-memory only
        state = conversation_manager.get_session(session_id)
        if state is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
        return {
            "session_id": session_id,
            "language": state.language,
            "duration_seconds": state.duration_seconds,
            "customer_context": state.customer_context,
            "recent_turns": state.get_history(max_turns=6),
        }
    customer_profile = None
    if call.customer_id:
        customer_profile = await customer_service.get_customer_360(db, call.customer_id)
    return {
        "session_id": session_id,
        "call": call.to_dict(),
        "customer": customer_profile,
        "ai_opening": (
            f"नमस्ते {customer_profile.get('full_name') if customer_profile else ''} जी, DishHome मा स्वागत छ।"
            if call.language == "ne"
            else f"Hello {customer_profile.get('full_name') if customer_profile else ''}, welcome to DishHome."
        ),
    }


@router.post("/sessions/{session_id}/claim")
async def claim_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("agent", "write")),
):
    call = (await db.execute(select(CallRecord).where(CallRecord.session_id == session_id))).scalar_one_or_none()
    if call is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    call.assigned_agent_id = current_user.id
    await db.commit()
    await cache_service.publish_call_event("claimed", {
        "session_id": session_id, "agent_id": str(current_user.id),
    })
    return {"detail": "Session claimed"}


@router.post("/sessions/{session_id}/note")
async def add_session_note(
    session_id: str,
    note: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("agent", "write")),
):
    call = (await db.execute(select(CallRecord).where(CallRecord.session_id == session_id))).scalar_one_or_none()
    if call is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    call.agent_notes = (call.agent_notes or "") + f"\n[{current_user.username}] {note}"
    await db.commit()
    return {"detail": "Note saved"}


@router.get("/my-tickets")
async def my_tickets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("agent", "read")),
):
    result = await db.execute(
        select(Ticket).where(Ticket.assigned_agent_id == current_user.id).order_by(desc(Ticket.created_at))
    )
    return {
        "items": [
            {
                "id": str(t.id), "ticket_number": t.ticket_number,
                "category": t.category, "priority": t.priority,
                "status": t.status, "title": t.title,
                "sla_deadline": t.sla_deadline.isoformat(),
                "breached_sla": t.breached_sla,
                "created_at": t.created_at.isoformat(),
            }
            for t in result.scalars()
        ]
    }


@router.get("/performance")
async def agent_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("agent", "read")),
):
    handled_calls = (await db.execute(
        select(func.count(CallRecord.id)).where(CallRecord.assigned_agent_id == current_user.id)
    )).scalar() or 0
    open_tk = (await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assigned_agent_id == current_user.id,
            Ticket.status.in_(["open", "in_progress"]),
        )
    )).scalar() or 0
    closed_tk = (await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assigned_agent_id == current_user.id,
            Ticket.status.in_(["resolved", "closed"]),
        )
    )).scalar() or 0
    return {
        "user_id": str(current_user.id),
        "handled_calls": int(handled_calls),
        "open_tickets": int(open_tk),
        "closed_tickets": int(closed_tk),
    }


@router.websocket("/ws/{agent_id}")
async def agent_websocket(websocket: WebSocket, agent_id: str):
    """Real-time push channel for agent dashboards (Redis pub/sub bridge)."""
    await websocket.accept()
    logger.info(f"Agent WS connected: {agent_id}")
    channels = ["calls:handoff_requested", "calls:claimed", "tickets:created",
                "tickets:updated", "tickets:sla_breach", "network:outage_detected"]
    try:
        async for event in cache_service.subscribe(channels):
            await websocket.send_text(json.dumps(event, default=str))
    except WebSocketDisconnect:
        logger.info(f"Agent WS disconnected: {agent_id}")
    except Exception as e:
        logger.warning(f"Agent WS error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
