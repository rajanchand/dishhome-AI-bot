"""
Customer self-service portal API.

PortalUser-scoped: customers can only see their own profile, usage, invoices,
and tickets. No staff data exposed.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db, PortalUser, Customer, Invoice, Ticket
from app.utils.security import (
    hash_password, verify_password, create_access_token, verify_token,
    validate_password_strength,
)
from app.services.customer_service import customer_service
from app.services.ticket_service import ticket_service
from app.services.network_service import network_service

router = APIRouter(prefix="/api/portal", tags=["portal"])

portal_oauth = OAuth2PasswordBearer(tokenUrl="/api/portal/auth/login", auto_error=False)


class PortalLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class PortalRegisterRequest(BaseModel):
    customer_code: str
    email: EmailStr
    password: str = Field(..., min_length=12)


class PortalTicketCreate(BaseModel):
    category: str
    title: str
    description: str
    priority: str = "medium"


async def get_portal_user(
    token: Optional[str] = Depends(portal_oauth),
    db: AsyncSession = Depends(get_db),
) -> PortalUser:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    try:
        payload = verify_token(token, expected_type="access")
    except JWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {e}")
    if payload.get("portal") is not True:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a portal token")
    user_id = payload.get("sub")
    user = (await db.execute(select(PortalUser).where(PortalUser.id == UUID(user_id)))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


@router.post("/auth/register")
async def register(payload: PortalRegisterRequest, db: AsyncSession = Depends(get_db)):
    is_strong, reason = validate_password_strength(payload.password)
    if not is_strong:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
    customer = await customer_service.get_customer_by_code(db, payload.customer_code)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer code not found")
    existing = (await db.execute(
        select(PortalUser).where(PortalUser.email == str(payload.email).lower())
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    user = PortalUser(
        customer_id=customer.id,
        email=str(payload.email).lower(),
        hashed_password=hash_password(payload.password),
        is_verified=True,  # auto-verify in MVP; production would email a link
    )
    db.add(user)
    customer.portal_user_id = user.id
    await db.commit()
    await db.refresh(user)
    return {"detail": "Registered", "portal_user_id": str(user.id)}


@router.post("/auth/login")
async def login(payload: PortalLoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(
        select(PortalUser).where(PortalUser.email == str(payload.email).lower())
    )).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    user.last_login_at = datetime.utcnow()
    await db.commit()
    token = create_access_token({"sub": str(user.id), "portal": True})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/my/profile")
async def my_profile(
    user: PortalUser = Depends(get_portal_user),
    db: AsyncSession = Depends(get_db),
):
    if user.customer_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer link missing")
    profile = await customer_service.get_customer_360(db, user.customer_id)
    return profile


@router.get("/my/usage")
async def my_usage(
    user: PortalUser = Depends(get_portal_user),
    db: AsyncSession = Depends(get_db),
):
    # Just return last 30 days from the customer's primary device metrics
    from app.models import NetworkDevice
    device = (await db.execute(
        select(NetworkDevice).where(
            NetworkDevice.customer_id == user.customer_id,
            NetworkDevice.device_type == "onu",
        )
    )).scalar_one_or_none()
    if device is None:
        return {"history": []}
    history = await network_service.get_device_history(db, device.id, hours=24 * 30)
    return {"history": history}


@router.get("/my/invoices")
async def my_invoices(
    user: PortalUser = Depends(get_portal_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice).where(Invoice.customer_id == user.customer_id).order_by(desc(Invoice.created_at))
    )
    return {
        "items": [
            {
                "id": str(i.id), "invoice_number": i.invoice_number,
                "total_amount": float(i.total_amount),
                "due_date": i.due_date.isoformat(),
                "status": i.status, "paid_at": i.paid_at.isoformat() if i.paid_at else None,
            }
            for i in result.scalars()
        ]
    }


@router.get("/my/tickets")
async def my_tickets(
    user: PortalUser = Depends(get_portal_user),
    db: AsyncSession = Depends(get_db),
):
    items, _ = await ticket_service.list_tickets(db, customer_id=user.customer_id, limit=50)
    return {
        "items": [
            {
                "id": str(t.id), "ticket_number": t.ticket_number,
                "category": t.category, "priority": t.priority, "status": t.status,
                "title": t.title, "created_at": t.created_at.isoformat(),
                "sla_deadline": t.sla_deadline.isoformat(),
            }
            for t in items
        ]
    }


@router.post("/my/tickets")
async def create_my_ticket(
    payload: PortalTicketCreate,
    user: PortalUser = Depends(get_portal_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.create_ticket(db, {
        "customer_id": user.customer_id,
        "category": payload.category, "priority": payload.priority,
        "title": payload.title, "description": payload.description,
    })
    return {"detail": "Ticket created", "ticket_number": ticket.ticket_number}


@router.get("/area/outage")
async def my_area_outage(
    user: PortalUser = Depends(get_portal_user),
    db: AsyncSession = Depends(get_db),
):
    outage = await network_service.get_customer_area_outage(db, user.customer_id)
    if outage is None:
        return {"has_outage": False}
    return {
        "has_outage": True,
        "title": outage.title,
        "severity": outage.severity,
        "estimated_resolution": outage.estimated_resolution.isoformat() if outage.estimated_resolution else None,
        "detected_at": outage.detected_at.isoformat(),
    }


@router.post("/speed-test")
async def log_speed_test(
    download_mbps: float,
    upload_mbps: float,
    latency_ms: float,
    user: PortalUser = Depends(get_portal_user),
):
    # Stub: in production, persist this to a speed_test_results table
    return {"recorded": True, "download_mbps": download_mbps, "upload_mbps": upload_mbps}
