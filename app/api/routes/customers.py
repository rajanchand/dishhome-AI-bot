"""
Customer 360° CRM routes — full CRUD, search, KYC, suspend, related entities.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db, User
from app.models.schemas import (
    CustomerCreate, CustomerUpdate, CustomerResponse, Customer360, Paginated,
)
from app.services.customer_service import customer_service
from app.utils.dependencies import require_permission, get_current_user
from app.utils.pagination import PaginationParams, get_pagination

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=Paginated)
async def list_customers(
    pagination: PaginationParams = Depends(get_pagination),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("customers", "read")),
):
    items, total = await customer_service.list_customers(
        db, offset=pagination.offset, limit=pagination.limit, status=status_filter,
    )
    return Paginated(
        items=[
            CustomerResponse.model_validate(c).model_dump() for c in items
        ],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        has_more=(pagination.offset + len(items)) < total,
    )


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("customers", "write")),
):
    customer = await customer_service.create_customer(db, payload.model_dump())
    return CustomerResponse.model_validate(customer)


@router.get("/search")
async def search_customers(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("customers", "read")),
):
    results = await customer_service.search_customers(db, q, limit=limit)
    return {"items": [CustomerResponse.model_validate(c).model_dump() for c in results]}


@router.get("/{customer_id}", response_model=Customer360)
async def get_customer_360(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("customers", "read")),
):
    profile = await customer_service.get_customer_360(db, customer_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return profile


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("customers", "write")),
):
    customer = await customer_service.update_customer(
        db, customer_id, payload.model_dump(exclude_unset=True),
    )
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return CustomerResponse.model_validate(customer)


@router.post("/{customer_id}/verify-kyc")
async def verify_kyc(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("customers", "write")),
):
    customer = await customer_service.verify_kyc(db, customer_id, current_user.id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return {"detail": "KYC verified", "customer_id": str(customer.id)}


@router.post("/{customer_id}/suspend")
async def suspend(
    customer_id: UUID,
    reason: str = Query("Manual suspension"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("customers", "write")),
):
    customer = await customer_service.suspend_account(db, customer_id, reason=reason)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return {"detail": "Account suspended"}


@router.post("/{customer_id}/unsuspend")
async def unsuspend(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("customers", "write")),
):
    customer = await customer_service.unsuspend_account(db, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return {"detail": "Account reactivated"}


@router.get("/{customer_id}/tickets")
async def customer_tickets(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("customers", "read")),
):
    profile = await customer_service.get_customer_360(db, customer_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return {"items": profile.get("recent_tickets", [])}


@router.get("/{customer_id}/invoices")
async def customer_invoices(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("customers", "read")),
):
    profile = await customer_service.get_customer_360(db, customer_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return {"items": profile.get("outstanding_invoices", [])}


@router.get("/{customer_id}/devices")
async def customer_devices(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("customers", "read")),
):
    profile = await customer_service.get_customer_360(db, customer_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return {"items": profile.get("devices", [])}


@router.get("/{customer_id}/calls")
async def customer_calls(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("customers", "read")),
):
    profile = await customer_service.get_customer_360(db, customer_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return {"items": profile.get("recent_calls", [])}
