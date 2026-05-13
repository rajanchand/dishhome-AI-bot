"""Package catalog and subscription management."""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Package, CustomerPackage, Customer


class PackageService:
    async def list_packages(self, db: AsyncSession, active_only: bool = True) -> List[Package]:
        stmt = select(Package).order_by(Package.sort_order, Package.price_monthly)
        if active_only:
            stmt = stmt.where(Package.is_active == True)  # noqa
        return list((await db.execute(stmt)).scalars())

    async def get_package(self, db: AsyncSession, package_id: UUID) -> Optional[Package]:
        return (await db.execute(select(Package).where(Package.id == package_id))).scalar_one_or_none()

    async def create_package(self, db: AsyncSession, data: dict) -> Package:
        pkg = Package(id=uuid4(), **data)
        db.add(pkg)
        await db.commit()
        await db.refresh(pkg)
        return pkg

    async def update_package(self, db: AsyncSession, package_id: UUID, data: dict) -> Optional[Package]:
        pkg = await self.get_package(db, package_id)
        if pkg is None:
            return None
        for k, v in data.items():
            if v is not None and hasattr(pkg, k):
                setattr(pkg, k, v)
        pkg.updated_at = datetime.utcnow()
        await db.commit()
        return pkg

    async def subscribe_customer(
        self, db: AsyncSession, customer_id: UUID, package_id: UUID,
        billing_cycle_day: int = 1, auto_renew: bool = True,
        changed_by: Optional[UUID] = None,
    ) -> CustomerPackage:
        pkg = await self.get_package(db, package_id)
        if pkg is None:
            raise ValueError(f"Package {package_id} not found")
        # Deactivate any current active subscription
        existing = (await db.execute(
            select(CustomerPackage).where(
                CustomerPackage.customer_id == customer_id,
                CustomerPackage.status == "active",
            )
        )).scalars().all()
        for prev in existing:
            prev.status = "cancelled"
        # Create new
        sub = CustomerPackage(
            id=uuid4(),
            customer_id=customer_id,
            package_id=package_id,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=pkg.validity_days),
            billing_cycle_day=billing_cycle_day,
            status="active",
            auto_renew=auto_renew,
            previous_package_id=existing[0].package_id if existing else None,
            changed_by_user_id=changed_by,
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        logger.info(f"Subscribed customer {customer_id} → {pkg.name}")
        return sub

    async def upgrade_subscription(
        self, db: AsyncSession, subscription_id: UUID, new_package_id: UUID,
        changed_by: Optional[UUID] = None,
    ) -> Optional[CustomerPackage]:
        sub = (await db.execute(select(CustomerPackage).where(CustomerPackage.id == subscription_id))).scalar_one_or_none()
        if sub is None:
            return None
        new_sub = await self.subscribe_customer(
            db, sub.customer_id, new_package_id,
            billing_cycle_day=sub.billing_cycle_day,
            auto_renew=sub.auto_renew,
            changed_by=changed_by,
        )
        return new_sub


package_service = PackageService()
