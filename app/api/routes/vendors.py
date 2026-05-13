"""Vendor management routes — CRUD, performance, RMA."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db, User
from app.models.schemas import VendorCreate, VendorResponse
from app.services.vendor_service import vendor_service
from app.utils.dependencies import require_permission

router = APIRouter(prefix="/api/vendors", tags=["vendors"])


@router.get("")
async def list_vendors(
    active_only: bool = Query(True),
    vendor_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("vendors", "read")),
):
    items = await vendor_service.list_vendors(db, active_only=active_only, vendor_type=vendor_type)
    return {"items": [VendorResponse.model_validate(v).model_dump() for v in items]}


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    payload: VendorCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("vendors", "write")),
):
    vendor = await vendor_service.create_vendor(db, payload.model_dump())
    return VendorResponse.model_validate(vendor)


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("vendors", "read")),
):
    vendor = await vendor_service.get_vendor(db, vendor_id)
    if vendor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found")
    return VendorResponse.model_validate(vendor)


@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: UUID,
    payload: VendorCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("vendors", "write")),
):
    vendor = await vendor_service.update_vendor(db, vendor_id, payload.model_dump(exclude_unset=True))
    if vendor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found")
    return VendorResponse.model_validate(vendor)


@router.delete("/{vendor_id}")
async def deactivate_vendor(
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("vendors", "write")),
):
    if not await vendor_service.deactivate_vendor(db, vendor_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found")
    return {"detail": "Vendor deactivated"}


@router.get("/{vendor_id}/performance")
async def vendor_performance(
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("vendors", "read")),
):
    perf = await vendor_service.get_vendor_performance(db, vendor_id)
    if not perf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found")
    return perf


@router.get("/{vendor_id}/tickets")
async def vendor_tickets(
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("vendors", "read")),
):
    items = await vendor_service.list_vendor_tickets(db, vendor_id)
    return {
        "items": [
            {
                "id": str(t.id), "ticket_number": t.ticket_number,
                "status": t.status, "priority": t.priority,
                "title": t.title, "created_at": t.created_at.isoformat(),
            }
            for t in items
        ]
    }


@router.post("/rma")
async def create_rma(
    vendor_id: UUID = Query(...),
    device_serial: str = Query(...),
    issue_description: str = Query(...),
    customer_id: Optional[UUID] = None,
    ticket_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("vendors", "write")),
):
    rma = await vendor_service.create_rma(db, {
        "vendor_id": vendor_id,
        "device_serial": device_serial,
        "issue_description": issue_description,
        "customer_id": customer_id,
        "ticket_id": ticket_id,
    }, created_by=current_user.id)
    return {"detail": "RMA created", "rma_number": rma.rma_number}


@router.put("/rma/{rma_id}")
async def update_rma(
    rma_id: UUID,
    new_status: str = Query(...),
    replacement_serial: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("vendors", "write")),
):
    rma = await vendor_service.update_rma_status(db, rma_id, new_status, replacement_serial)
    if rma is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "RMA not found")
    return {"detail": "RMA updated", "status": rma.status}
