"""Enterprise ticketing API routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db, User
from app.models.schemas import (
    TicketCreate, TicketUpdate, TicketResponse, TicketCommentCreate,
    TicketCommentResponse, Paginated,
)
from app.services.ticket_service import ticket_service
from app.utils.dependencies import require_permission, get_current_user
from app.utils.pagination import PaginationParams, get_pagination

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.get("", response_model=Paginated)
async def list_tickets(
    pagination: PaginationParams = Depends(get_pagination),
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    customer_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("tickets", "read")),
):
    items, total = await ticket_service.list_tickets(
        db, offset=pagination.offset, limit=pagination.limit,
        status_filter=status_filter, priority_filter=priority,
        agent_id=agent_id, customer_id=customer_id,
    )
    return Paginated(
        items=[TicketResponse.model_validate(t).model_dump() for t in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        has_more=(pagination.offset + len(items)) < total,
    )


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("tickets", "write")),
):
    ticket = await ticket_service.create_ticket(
        db, payload.model_dump(), created_by=current_user.id,
    )
    return TicketResponse.model_validate(ticket)


@router.get("/sla-dashboard")
async def sla_dashboard(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("tickets", "read")),
):
    return await ticket_service.get_sla_dashboard(db)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("tickets", "read")),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return TicketResponse.model_validate(ticket)


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: UUID,
    payload: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("tickets", "write")),
):
    ticket = await ticket_service.update_ticket(
        db, ticket_id, payload.model_dump(exclude_unset=True),
    )
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/assign")
async def assign_agent(
    ticket_id: UUID,
    agent_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("tickets", "write")),
):
    ticket = await ticket_service.assign_agent(db, ticket_id, agent_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return {"detail": "Agent assigned"}


@router.post("/{ticket_id}/vendor")
async def assign_vendor(
    ticket_id: UUID,
    vendor_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("tickets", "write")),
):
    ticket = await ticket_service.assign_vendor(db, ticket_id, vendor_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return {"detail": "Vendor assigned"}


@router.post("/{ticket_id}/comments", response_model=TicketCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    ticket_id: UUID,
    payload: TicketCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("tickets", "write")),
):
    comment = await ticket_service.add_comment(
        db, ticket_id, payload.content, author_user_id=current_user.id,
        author_type="agent", is_internal=payload.is_internal,
    )
    return TicketCommentResponse.model_validate(comment)


@router.post("/{ticket_id}/escalate")
async def escalate(
    ticket_id: UUID,
    reason: str = Query("Manual escalation"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("tickets", "escalate")),
):
    ticket = await ticket_service.escalate_ticket(db, ticket_id, reason)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return {"detail": "Ticket escalated", "new_priority": ticket.priority}


@router.post("/{ticket_id}/resolve")
async def resolve(
    ticket_id: UUID,
    resolution_notes: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("tickets", "write")),
):
    ticket = await ticket_service.resolve_ticket(
        db, ticket_id, resolution_notes, agent_id=current_user.id,
    )
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return {"detail": "Ticket resolved"}


@router.post("/{ticket_id}/close")
async def close_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("tickets", "write")),
):
    ticket = await ticket_service.close_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return {"detail": "Ticket closed"}
