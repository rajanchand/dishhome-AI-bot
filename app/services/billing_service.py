"""
Billing service — invoice generation, payment processing (eSewa/Khalti),
PDF generation via ReportLab.
"""

import io
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

import httpx
from loguru import logger
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Invoice, InvoiceItem, Payment, Customer, CustomerPackage
from config.settings import settings
from config.rbac import VAT_PERCENT


class BillingService:
    async def _generate_invoice_number(self, db: AsyncSession) -> str:
        year = datetime.utcnow().year
        result = await db.execute(
            select(func.count(Invoice.id)).where(Invoice.invoice_number.like(f"INV-{year}-%"))
        )
        count = (result.scalar() or 0) + 1
        return f"INV-{year}-{count:06d}"

    async def generate_invoice(
        self, db: AsyncSession, subscription_id: UUID,
        custom_items: Optional[list] = None,
    ) -> Invoice:
        sub = (await db.execute(
            select(CustomerPackage)
            .options(selectinload(CustomerPackage.package))
            .where(CustomerPackage.id == subscription_id)
        )).scalar_one_or_none()
        if sub is None:
            raise ValueError(f"Subscription {subscription_id} not found")
        pkg = sub.package
        period_start = date.today().replace(day=1)
        period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        subtotal = Decimal(str(pkg.price_monthly))
        tax_amount = (subtotal * Decimal(str(VAT_PERCENT)) / Decimal("100")).quantize(Decimal("0.01"))
        total = subtotal + tax_amount

        invoice = Invoice(
            id=uuid4(),
            invoice_number=await self._generate_invoice_number(db),
            customer_id=sub.customer_id,
            subscription_id=sub.id,
            billing_period_start=period_start,
            billing_period_end=period_end,
            subtotal=subtotal,
            tax_percent=Decimal(str(VAT_PERCENT)),
            tax_amount=tax_amount,
            total_amount=total,
            due_date=period_end + timedelta(days=7),
            status="sent",
        )
        db.add(invoice)
        await db.flush()
        item = InvoiceItem(
            id=uuid4(),
            invoice_id=invoice.id,
            description=f"{pkg.name} ({period_start.isoformat()} → {period_end.isoformat()})",
            quantity=1,
            unit_price=subtotal,
            total=subtotal,
            item_type="subscription",
        )
        db.add(item)
        for ci in (custom_items or []):
            db.add(InvoiceItem(
                id=uuid4(), invoice_id=invoice.id,
                description=ci["description"], quantity=ci.get("quantity", 1),
                unit_price=Decimal(str(ci["unit_price"])),
                total=Decimal(str(ci["unit_price"])) * Decimal(str(ci.get("quantity", 1))),
                item_type=ci.get("item_type", "custom"),
            ))
        await db.commit()
        await db.refresh(invoice)
        logger.info(f"Invoice {invoice.invoice_number} generated: NPR {total}")
        return invoice

    async def get_invoice(self, db: AsyncSession, invoice_id: UUID) -> Optional[Invoice]:
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.items), selectinload(Invoice.payments))
            .where(Invoice.id == invoice_id)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_invoices(
        self, db: AsyncSession, offset: int = 0, limit: int = 50,
        customer_id: Optional[UUID] = None,
        status_filter: Optional[str] = None,
    ) -> tuple[list, int]:
        stmt = select(Invoice)
        count_stmt = select(func.count(Invoice.id))
        conds = []
        if customer_id:
            conds.append(Invoice.customer_id == customer_id)
        if status_filter:
            conds.append(Invoice.status == status_filter)
        if conds:
            stmt = stmt.where(and_(*conds))
            count_stmt = count_stmt.where(and_(*conds))
        stmt = stmt.order_by(desc(Invoice.created_at)).offset(offset).limit(limit)
        items = list((await db.execute(stmt)).scalars())
        total = (await db.execute(count_stmt)).scalar() or 0
        return items, int(total)

    async def record_payment(
        self, db: AsyncSession, invoice_id: UUID, amount: Decimal,
        payment_method: str, transaction_id: Optional[str] = None,
        verified_by: Optional[UUID] = None,
        gateway_response: Optional[dict] = None,
    ) -> Payment:
        invoice = await self.get_invoice(db, invoice_id)
        if invoice is None:
            raise ValueError("Invoice not found")
        payment = Payment(
            id=uuid4(),
            invoice_id=invoice_id,
            customer_id=invoice.customer_id,
            amount=amount,
            payment_method=payment_method,
            gateway_transaction_id=transaction_id,
            gateway_response=gateway_response,
            status="completed",
            paid_at=datetime.utcnow(),
            verified_by_user_id=verified_by,
        )
        db.add(payment)
        total_paid = sum((p.amount for p in invoice.payments), Decimal("0")) + amount
        if total_paid >= invoice.total_amount:
            invoice.status = "paid"
            invoice.paid_at = datetime.utcnow()
            invoice.payment_method = payment_method
            invoice.payment_reference = transaction_id
        await db.commit()
        await db.refresh(payment)
        logger.info(f"Payment recorded: {payment.id} (NPR {amount} via {payment_method})")
        return payment

    async def verify_esewa_payment(self, transaction_id: str, amount: Decimal) -> bool:
        if not settings.esewa_merchant_code:
            logger.warning("eSewa not configured — skipping verification")
            return True
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"{settings.esewa_base_url}/api/epay/transaction/status/",
                    json={
                        "product_code": settings.esewa_merchant_code,
                        "transaction_uuid": transaction_id,
                        "total_amount": str(amount),
                    },
                )
                data = r.json()
                return data.get("status") == "COMPLETE"
        except Exception as e:
            logger.warning(f"eSewa verification error: {e}")
            return False

    async def verify_khalti_payment(self, token: str, amount: Decimal) -> bool:
        if not settings.khalti_secret_key:
            return True
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"{settings.khalti_base_url}/payment/verify/",
                    headers={"Authorization": f"Key {settings.khalti_secret_key}"},
                    data={"token": token, "amount": int(amount * 100)},
                )
                return r.status_code == 200
        except Exception as e:
            logger.warning(f"Khalti verification error: {e}")
            return False

    async def generate_invoice_pdf(self, db: AsyncSession, invoice_id: UUID) -> Optional[bytes]:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        invoice = await self.get_invoice(db, invoice_id)
        if invoice is None:
            return None
        customer = (await db.execute(
            select(Customer).where(Customer.id == invoice.customer_id)
        )).scalar_one()
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        styles = getSampleStyleSheet()
        elems = [
            Paragraph("<b>DishHome ISP - Tax Invoice</b>", styles["Title"]),
            Spacer(1, 12),
            Paragraph(f"<b>Invoice:</b> {invoice.invoice_number}", styles["Normal"]),
            Paragraph(f"<b>Customer:</b> {customer.full_name} ({customer.customer_code})", styles["Normal"]),
            Paragraph(f"<b>Phone:</b> {customer.phone_primary}", styles["Normal"]),
            Paragraph(f"<b>Period:</b> {invoice.billing_period_start} → {invoice.billing_period_end}", styles["Normal"]),
            Paragraph(f"<b>Due Date:</b> {invoice.due_date}", styles["Normal"]),
            Spacer(1, 12),
        ]
        data = [["Description", "Qty", "Unit Price (NPR)", "Total (NPR)"]]
        for item in invoice.items:
            data.append([item.description, str(item.quantity),
                          f"{item.unit_price:.2f}", f"{item.total:.2f}"])
        data.append(["", "", "Subtotal", f"{invoice.subtotal:.2f}"])
        data.append(["", "", f"VAT ({invoice.tax_percent}%)", f"{invoice.tax_amount:.2f}"])
        data.append(["", "", "Total", f"{invoice.total_amount:.2f}"])
        table = Table(data, colWidths=[260, 50, 90, 90])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0066cc")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        elems.append(table)
        doc.build(elems)
        return buf.getvalue()


billing_service = BillingService()
