"""
Customer service — CRM, 360° profile, KYC, search.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Customer, CustomerAddress, ServiceArea, ContactInteraction,
    CustomerPackage, Package, NetworkDevice, Ticket, CallRecord, Invoice,
)
from app.utils.validators import normalize_phone
from app.services.cache_service import cache_service


class CustomerService:
    async def _generate_customer_code(self, db: AsyncSession) -> str:
        year = datetime.utcnow().year
        result = await db.execute(
            select(func.count(Customer.id)).where(Customer.customer_code.like(f"DH-{year}-%"))
        )
        count = (result.scalar() or 0) + 1
        return f"DH-{year}-{count:06d}"

    async def create_customer(self, db: AsyncSession, data: dict) -> Customer:
        normalized = normalize_phone(data["phone_primary"]) or data["phone_primary"]
        customer = Customer(
            id=uuid4(),
            customer_code=await self._generate_customer_code(db),
            full_name=data["full_name"],
            phone_primary=normalized,
            phone_secondary=normalize_phone(data.get("phone_secondary") or "") or data.get("phone_secondary"),
            email=data.get("email"),
            national_id=data.get("national_id"),
            date_of_birth=data.get("date_of_birth"),
            preferred_language=data.get("preferred_language", "ne"),
            account_status="active",
        )
        db.add(customer)
        await db.flush()
        if data.get("address"):
            addr_data = data["address"]
            address = CustomerAddress(
                id=uuid4(),
                customer_id=customer.id,
                address_type=addr_data.get("address_type", "installation"),
                street_address=addr_data["street_address"],
                ward=addr_data.get("ward"),
                municipality=addr_data.get("municipality"),
                district=addr_data.get("district"),
                province=addr_data.get("province"),
                latitude=addr_data.get("latitude"),
                longitude=addr_data.get("longitude"),
                service_area_id=addr_data.get("service_area_id"),
                is_primary=True,
            )
            db.add(address)
        await db.commit()
        await db.refresh(customer)
        await cache_service.invalidate_customer(str(customer.id))
        logger.info(f"Created customer {customer.customer_code} ({customer.full_name})")
        return customer

    async def get_customer(self, db: AsyncSession, customer_id: UUID) -> Optional[Customer]:
        stmt = (
            select(Customer)
            .options(
                selectinload(Customer.addresses),
                selectinload(Customer.subscriptions).selectinload(CustomerPackage.package),
                selectinload(Customer.devices),
            )
            .where(Customer.id == customer_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_customer_by_phone(self, db: AsyncSession, phone: str) -> Optional[Customer]:
        normalized = normalize_phone(phone) or phone
        stmt = select(Customer).where(
            or_(
                Customer.phone_primary == normalized,
                Customer.phone_primary == phone,
                Customer.phone_secondary == normalized,
                Customer.phone_secondary == phone,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_customer_by_code(self, db: AsyncSession, code: str) -> Optional[Customer]:
        result = await db.execute(select(Customer).where(Customer.customer_code == code))
        return result.scalar_one_or_none()

    async def get_customer_360(self, db: AsyncSession, customer_id: UUID) -> Optional[dict]:
        cached = await cache_service.get_customer_profile(str(customer_id))
        if cached:
            return cached

        customer = await self.get_customer(db, customer_id)
        if customer is None:
            return None

        # Active subscription
        active_sub = next((s for s in customer.subscriptions if s.status == "active"), None)
        sub_data = None
        if active_sub:
            sub_data = {
                "id": str(active_sub.id),
                "package_name": active_sub.package.name if active_sub.package else None,
                "speed_down": active_sub.package.speed_download_mbps if active_sub.package else None,
                "speed_up": active_sub.package.speed_upload_mbps if active_sub.package else None,
                "expires_at": active_sub.expires_at.isoformat(),
                "auto_renew": active_sub.auto_renew,
                "monthly_price": float(active_sub.package.price_monthly) if active_sub.package else None,
            }

        # Recent tickets
        tk_result = await db.execute(
            select(Ticket).where(Ticket.customer_id == customer_id).order_by(desc(Ticket.created_at)).limit(5)
        )
        tickets = [
            {
                "id": str(t.id),
                "ticket_number": t.ticket_number,
                "category": t.category,
                "status": t.status,
                "priority": t.priority,
                "title": t.title,
                "created_at": t.created_at.isoformat(),
            }
            for t in tk_result.scalars()
        ]

        # Recent calls
        call_result = await db.execute(
            select(CallRecord).where(CallRecord.customer_id == customer_id).order_by(desc(CallRecord.started_at)).limit(5)
        )
        calls = [c.to_dict() for c in call_result.scalars()]

        # Outstanding invoices
        inv_result = await db.execute(
            select(Invoice).where(Invoice.customer_id == customer_id,
                                  Invoice.status.in_(["sent", "overdue"]))
        )
        invoices = [
            {
                "id": str(i.id),
                "invoice_number": i.invoice_number,
                "total_amount": float(i.total_amount),
                "due_date": i.due_date.isoformat(),
                "status": i.status,
            }
            for i in inv_result.scalars()
        ]

        profile = {
            "id": str(customer.id),
            "customer_code": customer.customer_code,
            "full_name": customer.full_name,
            "phone_primary": customer.phone_primary,
            "phone_secondary": customer.phone_secondary,
            "email": customer.email,
            "kyc_verified": customer.kyc_verified,
            "account_status": customer.account_status,
            "credit_score": customer.credit_score,
            "loyalty_tier": customer.loyalty_tier,
            "preferred_language": customer.preferred_language,
            "addresses": [
                {
                    "address_type": a.address_type,
                    "street_address": a.street_address,
                    "ward": a.ward,
                    "municipality": a.municipality,
                    "service_area_id": str(a.service_area_id) if a.service_area_id else None,
                    "is_primary": a.is_primary,
                }
                for a in customer.addresses
            ],
            "active_subscription": sub_data,
            "devices": [
                {
                    "id": str(d.id),
                    "device_type": d.device_type,
                    "serial_number": d.serial_number,
                    "mac_address": d.mac_address,
                    "status": d.status,
                    "signal_quality": d.signal_quality,
                    "rx_power_dbm": float(d.rx_power_dbm) if d.rx_power_dbm else None,
                    "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                }
                for d in customer.devices
            ],
            "recent_tickets": tickets,
            "recent_calls": calls,
            "outstanding_invoices": invoices,
            "created_at": customer.created_at.isoformat(),
            "updated_at": customer.updated_at.isoformat(),
        }
        await cache_service.set_customer_profile(str(customer_id), profile)
        return profile

    async def update_customer(self, db: AsyncSession, customer_id: UUID, data: dict) -> Optional[Customer]:
        customer = await self.get_customer(db, customer_id)
        if customer is None:
            return None
        for k, v in data.items():
            if v is not None and hasattr(customer, k):
                setattr(customer, k, v)
        customer.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(customer)
        await cache_service.invalidate_customer(str(customer_id))
        return customer

    async def search_customers(self, db: AsyncSession, query: str, limit: int = 20) -> List[Customer]:
        like = f"%{query}%"
        stmt = (
            select(Customer)
            .where(
                or_(
                    Customer.full_name.ilike(like),
                    Customer.phone_primary.ilike(like),
                    Customer.phone_secondary.ilike(like),
                    Customer.email.ilike(like),
                    Customer.customer_code.ilike(like),
                )
            )
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars())

    async def list_customers(self, db: AsyncSession, offset: int = 0, limit: int = 50,
                              status: Optional[str] = None) -> tuple[list, int]:
        stmt = select(Customer)
        count_stmt = select(func.count(Customer.id))
        if status:
            stmt = stmt.where(Customer.account_status == status)
            count_stmt = count_stmt.where(Customer.account_status == status)
        stmt = stmt.order_by(desc(Customer.created_at)).offset(offset).limit(limit)
        items_result = await db.execute(stmt)
        total_result = await db.execute(count_stmt)
        return list(items_result.scalars()), int(total_result.scalar() or 0)

    async def verify_kyc(self, db: AsyncSession, customer_id: UUID, verified_by: UUID) -> Optional[Customer]:
        customer = await self.get_customer(db, customer_id)
        if customer is None:
            return None
        customer.kyc_verified = True
        customer.kyc_verified_at = datetime.utcnow()
        customer.kyc_verified_by_user_id = verified_by
        await db.commit()
        await cache_service.invalidate_customer(str(customer_id))
        return customer

    async def suspend_account(self, db: AsyncSession, customer_id: UUID,
                               reason: str = "") -> Optional[Customer]:
        customer = await self.get_customer(db, customer_id)
        if customer is None:
            return None
        customer.account_status = "suspended"
        customer.notes = (customer.notes or "") + f"\n[SUSPEND {datetime.utcnow().isoformat()}] {reason}"
        await db.commit()
        await cache_service.invalidate_customer(str(customer_id))
        return customer

    async def unsuspend_account(self, db: AsyncSession, customer_id: UUID) -> Optional[Customer]:
        customer = await self.get_customer(db, customer_id)
        if customer is None:
            return None
        customer.account_status = "active"
        await db.commit()
        await cache_service.invalidate_customer(str(customer_id))
        return customer

    async def log_interaction(self, db: AsyncSession, customer_id: UUID,
                                interaction_type: str, summary: str, outcome: str,
                                handled_by: Optional[UUID] = None,
                                ticket_id: Optional[UUID] = None) -> ContactInteraction:
        interaction = ContactInteraction(
            id=uuid4(),
            customer_id=customer_id,
            interaction_type=interaction_type,
            summary=summary,
            outcome=outcome,
            handled_by_user_id=handled_by,
            related_ticket_id=ticket_id,
        )
        db.add(interaction)
        await db.commit()
        return interaction


customer_service = CustomerService()
