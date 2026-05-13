"""DB-backed vendor management service (replaces legacy mock)."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Vendor, RMARequest, Ticket


class VendorService:
    async def list_vendors(
        self, db: AsyncSession, active_only: bool = True,
        vendor_type: Optional[str] = None,
    ) -> List[Vendor]:
        stmt = select(Vendor).order_by(Vendor.company_name)
        if active_only:
            stmt = stmt.where(Vendor.is_active == True)  # noqa
        if vendor_type:
            stmt = stmt.where(Vendor.vendor_type == vendor_type)
        return list((await db.execute(stmt)).scalars())

    async def get_vendor(self, db: AsyncSession, vendor_id: UUID) -> Optional[Vendor]:
        stmt = (
            select(Vendor)
            .options(selectinload(Vendor.contracts))
            .where(Vendor.id == vendor_id)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def create_vendor(self, db: AsyncSession, data: dict) -> Vendor:
        vendor = Vendor(id=uuid4(), **{k: v for k, v in data.items() if v is not None})
        db.add(vendor)
        await db.commit()
        await db.refresh(vendor)
        logger.info(f"Vendor created: {vendor.vendor_code} ({vendor.company_name})")
        return vendor

    async def update_vendor(self, db: AsyncSession, vendor_id: UUID, data: dict) -> Optional[Vendor]:
        vendor = await self.get_vendor(db, vendor_id)
        if vendor is None:
            return None
        for k, v in data.items():
            if v is not None and hasattr(vendor, k):
                setattr(vendor, k, v)
        await db.commit()
        return vendor

    async def deactivate_vendor(self, db: AsyncSession, vendor_id: UUID) -> bool:
        vendor = await self.get_vendor(db, vendor_id)
        if vendor is None:
            return False
        vendor.is_active = False
        await db.commit()
        return True

    async def get_vendor_performance(self, db: AsyncSession, vendor_id: UUID) -> dict:
        vendor = await self.get_vendor(db, vendor_id)
        if vendor is None:
            return {}
        total_tickets = (await db.execute(
            select(func.count(Ticket.id)).where(Ticket.assigned_vendor_id == vendor_id)
        )).scalar() or 0
        resolved = (await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assigned_vendor_id == vendor_id,
                Ticket.status.in_(["resolved", "closed"]),
            )
        )).scalar() or 0
        breached = (await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assigned_vendor_id == vendor_id,
                Ticket.breached_sla == True,  # noqa
            )
        )).scalar() or 0
        return {
            "vendor_id": str(vendor.id),
            "vendor_code": vendor.vendor_code,
            "company_name": vendor.company_name,
            "rating": float(vendor.rating),
            "total_tickets": int(total_tickets),
            "resolved_tickets": int(resolved),
            "sla_breaches": int(breached),
            "completion_rate": round((resolved / total_tickets * 100) if total_tickets else 0, 2),
            "sla_compliance": round(((total_tickets - breached) / total_tickets * 100) if total_tickets else 100, 2),
        }

    async def list_vendor_tickets(self, db: AsyncSession, vendor_id: UUID) -> List[Ticket]:
        result = await db.execute(
            select(Ticket).where(Ticket.assigned_vendor_id == vendor_id).order_by(desc(Ticket.created_at))
        )
        return list(result.scalars())

    # ── RMA ────────────────────────────────────────────────────────────
    async def _next_rma_number(self, db: AsyncSession) -> str:
        year = datetime.utcnow().year
        count = (await db.execute(
            select(func.count(RMARequest.id)).where(RMARequest.rma_number.like(f"RMA-{year}-%"))
        )).scalar() or 0
        return f"RMA-{year}-{count + 1:05d}"

    async def create_rma(self, db: AsyncSession, data: dict, created_by: Optional[UUID] = None) -> RMARequest:
        rma = RMARequest(
            id=uuid4(),
            rma_number=await self._next_rma_number(db),
            vendor_id=data["vendor_id"],
            device_serial=data["device_serial"],
            device_model=data.get("device_model"),
            issue_description=data["issue_description"],
            customer_id=data.get("customer_id"),
            ticket_id=data.get("ticket_id"),
            status="initiated",
            created_by_user_id=created_by,
        )
        db.add(rma)
        await db.commit()
        await db.refresh(rma)
        return rma

    async def update_rma_status(self, db: AsyncSession, rma_id: UUID, new_status: str,
                                  replacement_serial: Optional[str] = None) -> Optional[RMARequest]:
        rma = (await db.execute(select(RMARequest).where(RMARequest.id == rma_id))).scalar_one_or_none()
        if rma is None:
            return None
        rma.status = new_status
        if new_status == "shipped":
            rma.shipped_at = datetime.utcnow()
        if new_status == "received":
            rma.received_at = datetime.utcnow()
        if replacement_serial:
            rma.replacement_serial = replacement_serial
        if new_status == "closed":
            rma.closed_at = datetime.utcnow()
        await db.commit()
        return rma


vendor_service = VendorService()
