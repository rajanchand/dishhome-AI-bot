"""Billing routes: invoices, payments, webhooks, subscriptions."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db, User
from app.models.schemas import InvoiceResponse, PaymentCreate, Paginated
from app.services.billing_service import billing_service
from app.services.package_service import package_service
from app.utils.dependencies import require_permission
from app.utils.pagination import PaginationParams, get_pagination

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/invoices", response_model=Paginated)
async def list_invoices(
    pagination: PaginationParams = Depends(get_pagination),
    customer_id: Optional[UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("billing", "read")),
):
    items, total = await billing_service.list_invoices(
        db, offset=pagination.offset, limit=pagination.limit,
        customer_id=customer_id, status_filter=status_filter,
    )
    return Paginated(
        items=[InvoiceResponse.model_validate(i).model_dump() for i in items],
        total=total, page=pagination.page, page_size=pagination.page_size,
        has_more=(pagination.offset + len(items)) < total,
    )


@router.post("/invoices/generate")
async def generate_invoice(
    subscription_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("billing", "write")),
):
    invoice = await billing_service.generate_invoice(db, subscription_id)
    return InvoiceResponse.model_validate(invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("billing", "read")),
):
    invoice = await billing_service.get_invoice(db, invoice_id)
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    return InvoiceResponse.model_validate(invoice)


@router.get("/invoices/{invoice_id}/pdf")
async def invoice_pdf(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("billing", "read")),
):
    pdf_bytes = await billing_service.generate_invoice_pdf(db, invoice_id)
    if pdf_bytes is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="invoice-{invoice_id}.pdf"'},
    )


@router.post("/invoices/{invoice_id}/pay")
async def record_payment(
    invoice_id: UUID,
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("billing", "write")),
):
    payment = await billing_service.record_payment(
        db, invoice_id=invoice_id, amount=Decimal(str(payload.amount)),
        payment_method=payload.payment_method,
        transaction_id=payload.gateway_transaction_id,
        verified_by=current_user.id,
    )
    return {"detail": "Payment recorded", "payment_id": str(payment.id)}


@router.post("/webhooks/esewa")
async def esewa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    transaction_id = body.get("transaction_uuid") or body.get("transaction_id")
    invoice_id = body.get("invoice_id")
    amount = Decimal(str(body.get("total_amount", 0)))
    if not transaction_id or not invoice_id:
        raise HTTPException(400, "Missing transaction_id or invoice_id")
    is_valid = await billing_service.verify_esewa_payment(transaction_id, amount)
    if not is_valid:
        raise HTTPException(400, "Payment verification failed")
    await billing_service.record_payment(
        db, invoice_id=UUID(invoice_id), amount=amount,
        payment_method="esewa", transaction_id=transaction_id,
        gateway_response=body,
    )
    return {"status": "ok"}


@router.post("/webhooks/khalti")
async def khalti_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    token = body.get("token")
    amount = Decimal(str(body.get("amount", 0))) / 100
    invoice_id = body.get("invoice_id")
    is_valid = await billing_service.verify_khalti_payment(token, amount)
    if not is_valid:
        raise HTTPException(400, "Khalti verification failed")
    await billing_service.record_payment(
        db, invoice_id=UUID(invoice_id), amount=amount,
        payment_method="khalti", transaction_id=token,
        gateway_response=body,
    )
    return {"status": "ok"}


@router.post("/subscriptions")
async def subscribe(
    customer_id: UUID = Query(...),
    package_id: UUID = Query(...),
    billing_cycle_day: int = Query(1, ge=1, le=28),
    auto_renew: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("billing", "write")),
):
    sub = await package_service.subscribe_customer(
        db, customer_id, package_id,
        billing_cycle_day=billing_cycle_day, auto_renew=auto_renew,
        changed_by=current_user.id,
    )
    return {"detail": "Subscribed", "subscription_id": str(sub.id)}


@router.put("/subscriptions/{subscription_id}/upgrade")
async def upgrade_subscription(
    subscription_id: UUID,
    new_package_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("billing", "write")),
):
    new_sub = await package_service.upgrade_subscription(
        db, subscription_id, new_package_id, changed_by=current_user.id,
    )
    if new_sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription not found")
    return {"detail": "Upgraded", "new_subscription_id": str(new_sub.id)}
