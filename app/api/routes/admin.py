"""
Super Admin routes — DB-backed user management, RBAC, audit logs, system stats.
"""

import json
import os
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    get_db, User, Role, AuditLog, Customer, Ticket, NetworkDevice,
    Invoice, CallRecord,
)
from app.models.schemas import UserCreate, UserUpdate, UserResponse, Paginated
from app.utils.security import hash_password, validate_password_strength
from app.utils.dependencies import require_permission, require_role
from app.utils.pagination import PaginationParams, get_pagination

router = APIRouter(prefix="/api/admin", tags=["admin"])

FAQ_FILE = "app/knowledge/dishhome_faq.json"


def _read_faqs() -> dict:
    if not os.path.exists(FAQ_FILE):
        return {"faqs": []}
    with open(FAQ_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_faqs(data: dict) -> None:
    with open(FAQ_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Dashboard stats ─────────────────────────────────────────────────────────

@router.get("/dashboard/stats")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("analytics", "read")),
):
    total_customers = (await db.execute(select(func.count(Customer.id)))).scalar() or 0
    active_tickets = (await db.execute(
        select(func.count(Ticket.id)).where(Ticket.status.in_(["open", "in_progress"]))
    )).scalar() or 0
    total_devices = (await db.execute(
        select(func.count(NetworkDevice.id)).where(NetworkDevice.device_type == "onu")
    )).scalar() or 0
    online_devices = (await db.execute(
        select(func.count(NetworkDevice.id)).where(
            NetworkDevice.device_type == "onu", NetworkDevice.status == "online",
        )
    )).scalar() or 0
    unpaid_invoices = (await db.execute(
        select(func.count(Invoice.id)).where(Invoice.status.in_(["sent", "overdue"]))
    )).scalar() or 0
    active_calls = (await db.execute(
        select(func.count(CallRecord.id)).where(CallRecord.status == "active")
    )).scalar() or 0
    return {
        "total_customers": int(total_customers),
        "active_tickets": int(active_tickets),
        "total_devices": int(total_devices),
        "online_devices": int(online_devices),
        "network_health_percent": round((online_devices / total_devices * 100) if total_devices else 100, 1),
        "unpaid_invoices": int(unpaid_invoices),
        "active_calls": int(active_calls),
    }


# ─── Users ──────────────────────────────────────────────────────────────────

@router.get("/users", response_model=Paginated)
async def list_users(
    pagination: PaginationParams = Depends(get_pagination),
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("users", "read")),
):
    stmt = select(User).options(selectinload(User.role))
    count_stmt = select(func.count(User.id))
    if role:
        stmt = stmt.join(Role).where(Role.name == role)
        count_stmt = count_stmt.join(Role).where(Role.name == role)
    stmt = stmt.order_by(desc(User.created_at)).offset(pagination.offset).limit(pagination.limit)
    items = list((await db.execute(stmt)).scalars())
    total = (await db.execute(count_stmt)).scalar() or 0
    return Paginated(
        items=[
            UserResponse(
                id=u.id, email=u.email, username=u.username, full_name=u.full_name,
                phone=u.phone, role_name=u.role.name if u.role else "",
                is_active=u.is_active, is_mfa_enabled=u.is_mfa_enabled,
                last_login_at=u.last_login_at, created_at=u.created_at,
            ).model_dump()
            for u in items
        ],
        total=int(total), page=pagination.page, page_size=pagination.page_size,
        has_more=(pagination.offset + len(items)) < total,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("users", "write")),
):
    is_strong, reason = validate_password_strength(payload.password)
    if not is_strong:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
    role = (await db.execute(select(Role).where(Role.name == payload.role_name))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Role '{payload.role_name}' not found")
    user = User(
        email=str(payload.email).lower(),
        username=payload.username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    user.role = role
    return UserResponse(
        id=user.id, email=user.email, username=user.username, full_name=user.full_name,
        phone=user.phone, role_name=role.name, is_active=user.is_active,
        is_mfa_enabled=user.is_mfa_enabled, last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("users", "write")),
):
    stmt = select(User).options(selectinload(User.role)).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role_name:
        role = (await db.execute(select(Role).where(Role.name == payload.role_name))).scalar_one_or_none()
        if role is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Role '{payload.role_name}' not found")
        user.role_id = role.id
        user.role = role
    await db.commit()
    await db.refresh(user)
    return UserResponse(
        id=user.id, email=user.email, username=user.username, full_name=user.full_name,
        phone=user.phone, role_name=user.role.name if user.role else "",
        is_active=user.is_active, is_mfa_enabled=user.is_mfa_enabled,
        last_login_at=user.last_login_at, created_at=user.created_at,
    )


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("users", "write")),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.is_active = False
    user.refresh_token_hash = None
    await db.commit()
    return {"detail": "User deactivated"}


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: UUID,
    new_password: str = Query(..., min_length=12),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("superadmin", "admin")),
):
    is_strong, reason = validate_password_strength(new_password)
    if not is_strong:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.hashed_password = hash_password(new_password)
    user.refresh_token_hash = None
    user.failed_login_count = 0
    user.locked_until = None
    await db.commit()
    return {"detail": "Password reset"}


# ─── Roles & Permissions ────────────────────────────────────────────────────

@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("users", "read")),
):
    stmt = select(Role).options(selectinload(Role.permissions))
    roles = list((await db.execute(stmt)).scalars())
    return {
        "items": [
            {
                "id": str(r.id), "name": r.name, "display_name": r.display_name,
                "description": r.description, "is_system": r.is_system,
                "permissions": [f"{p.resource}:{p.action}" for p in r.permissions],
            }
            for r in roles
        ]
    }


# ─── Audit Logs ─────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=Paginated)
async def list_audit_logs(
    pagination: PaginationParams = Depends(get_pagination),
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("audit_logs", "read")),
):
    stmt = select(AuditLog)
    count_stmt = select(func.count(AuditLog.id))
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
        count_stmt = count_stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action.like(f"%{action}%"))
        count_stmt = count_stmt.where(AuditLog.action.like(f"%{action}%"))
    stmt = stmt.order_by(desc(AuditLog.timestamp)).offset(pagination.offset).limit(pagination.limit)
    items = list((await db.execute(stmt)).scalars())
    total = (await db.execute(count_stmt)).scalar() or 0
    return Paginated(
        items=[
            {
                "id": str(a.id), "user_id": str(a.user_id) if a.user_id else None,
                "action": a.action, "resource_type": a.resource_type,
                "request_method": a.request_method, "request_path": a.request_path,
                "response_status": a.response_status,
                "ip_address": str(a.ip_address) if a.ip_address else None,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in items
        ],
        total=int(total), page=pagination.page, page_size=pagination.page_size,
        has_more=(pagination.offset + len(items)) < total,
    )


@router.get("/audit-logs/export")
async def export_audit_logs(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("audit_logs", "read")),
):
    result = await db.execute(select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(10000))
    rows = [
        "id,user_id,action,resource_type,method,path,status,ip,timestamp"
    ]
    for a in result.scalars():
        rows.append(",".join([
            str(a.id), str(a.user_id) if a.user_id else "", a.action or "",
            a.resource_type or "", a.request_method or "", (a.request_path or "").replace(",", " "),
            str(a.response_status or ""), str(a.ip_address) if a.ip_address else "",
            a.timestamp.isoformat(),
        ]))
    csv_body = "\n".join(rows)

    async def stream():
        yield csv_body.encode("utf-8")

    return StreamingResponse(
        stream(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )


# ─── FAQs (kept for backwards-compat with existing admin.html UI) ───────────

@router.get("/faqs")
async def get_faqs(_user: User = Depends(require_permission("faqs", "read"))):
    return _read_faqs()


@router.post("/faqs")
async def add_faq(faq: dict, _user: User = Depends(require_permission("faqs", "write"))):
    data = _read_faqs()
    data["faqs"].append(faq)
    _write_faqs(data)
    return {"status": "success"}


@router.put("/faqs/{index}")
async def update_faq(
    index: int, faq: dict,
    _user: User = Depends(require_permission("faqs", "write")),
):
    data = _read_faqs()
    if index < 0 or index >= len(data["faqs"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "FAQ not found")
    data["faqs"][index] = faq
    _write_faqs(data)
    return {"status": "success"}


@router.delete("/faqs/{index}")
async def delete_faq(
    index: int,
    _user: User = Depends(require_permission("faqs", "delete")),
):
    data = _read_faqs()
    if index < 0 or index >= len(data["faqs"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "FAQ not found")
    data["faqs"].pop(index)
    _write_faqs(data)
    return {"status": "success"}
