"""
Seed default roles, permissions, superadmin user, packages, service areas,
and test customers. Idempotent — safe to re-run.

Usage:  python scripts/seed_db.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from loguru import logger
from sqlalchemy import select

sys.path.insert(0, ".")

from app.models import (
    AsyncSessionLocal, init_db,
    User, Role, Permission, role_permissions,
    Customer, CustomerAddress, ServiceArea,
    Package, CustomerPackage, NetworkDevice,
)
from app.utils.security import hash_password
from config.rbac import ROLE_PERMISSIONS


DEFAULT_SUPERADMIN_PASSWORD = "Admin@DishHome2026!"


async def seed_roles_and_permissions(db) -> dict:
    """Seed roles + all distinct permissions referenced in ROLE_PERMISSIONS."""
    role_objs: dict = {}
    permission_objs: dict = {}

    all_perms = set()
    for role_name, perms in ROLE_PERMISSIONS.items():
        for p in perms:
            if p == "*:*":
                continue
            all_perms.add(p)

    # Permissions
    for perm_string in all_perms:
        resource, action = perm_string.split(":", 1)
        result = await db.execute(
            select(Permission).where(Permission.resource == resource, Permission.action == action)
        )
        perm = result.scalar_one_or_none()
        if perm is None:
            perm = Permission(id=uuid4(), resource=resource, action=action,
                              description=f"Allows {action} on {resource}")
            db.add(perm)
            await db.flush()
        permission_objs[perm_string] = perm

    # Roles
    role_display = {
        "superadmin": "Super Administrator",
        "admin": "Administrator",
        "support_agent": "Support Agent",
        "technician": "Field Technician",
        "customer": "Customer (Portal)",
    }
    for role_name in ROLE_PERMISSIONS.keys():
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(
                id=uuid4(),
                name=role_name,
                display_name=role_display.get(role_name, role_name.title()),
                description=f"System role: {role_name}",
                is_system=True,
            )
            db.add(role)
            await db.flush()
        role_objs[role_name] = role

    await db.commit()

    # Attach permissions to roles (superadmin gets no explicit perms — uses wildcard at runtime)
    for role_name, perms in ROLE_PERMISSIONS.items():
        if "*:*" in perms:
            continue
        role = role_objs[role_name]
        # Reload with permissions
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(Role).options(selectinload(Role.permissions)).where(Role.id == role.id)
        )
        role_loaded = result.scalar_one()
        existing = {f"{p.resource}:{p.action}" for p in role_loaded.permissions}
        for perm_string in perms:
            if perm_string in existing:
                continue
            perm = permission_objs.get(perm_string)
            if perm:
                role_loaded.permissions.append(perm)
        await db.commit()

    logger.success(f"Seeded {len(role_objs)} roles and {len(permission_objs)} permissions")
    return role_objs


async def seed_superadmin(db, role_objs: dict) -> User:
    result = await db.execute(select(User).where(User.email == "admin@dishhome.com.np"))
    user = result.scalar_one_or_none()
    if user:
        logger.info("Superadmin already exists — skipping")
        return user
    user = User(
        id=uuid4(),
        email="admin@dishhome.com.np",
        username="superadmin",
        hashed_password=hash_password(DEFAULT_SUPERADMIN_PASSWORD),
        full_name="System Super Administrator",
        phone="+9779801000000",
        role_id=role_objs["superadmin"].id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    logger.success(f"Created superadmin: admin@dishhome.com.np / {DEFAULT_SUPERADMIN_PASSWORD}")
    return user


async def seed_packages(db) -> list:
    catalog = [
        ("BASIC-30", "Basic Home Fiber 30 Mbps", "fiber", 30, 15, None, 1100, 3000, 10500, 1000),
        ("STANDARD-60", "Standard Home Fiber 60 Mbps", "fiber", 60, 30, None, 1500, 4200, 14400, 1000),
        ("PREMIUM-100", "Premium Home Fiber 100 Mbps", "fiber", 100, 50, None, 2200, 6200, 22000, 1000),
        ("PRO-200", "Pro Home Fiber 200 Mbps", "fiber", 200, 100, None, 3500, 9900, 36000, 1500),
        ("BIZ-500", "Business Fiber 500 Mbps", "fiber", 500, 250, None, 8500, 24000, 90000, 2500),
    ]
    created = []
    for code, name, ptype, down, up, quota, monthly, quarterly, annually, setup in catalog:
        result = await db.execute(select(Package).where(Package.package_code == code))
        pkg = result.scalar_one_or_none()
        if pkg is None:
            pkg = Package(
                id=uuid4(),
                package_code=code,
                name=name,
                description=f"{down} Mbps fiber broadband",
                service_type=ptype,
                speed_download_mbps=down,
                speed_upload_mbps=up,
                monthly_quota_gb=quota,
                validity_days=30,
                price_monthly=Decimal(str(monthly)),
                price_quarterly=Decimal(str(quarterly)),
                price_annually=Decimal(str(annually)),
                setup_fee=Decimal(str(setup)),
                is_active=True,
            )
            db.add(pkg)
            created.append(pkg)
    await db.commit()
    logger.success(f"Seeded {len(created)} new packages")
    return created


async def seed_service_areas(db) -> list:
    areas = [
        ("KTM-01", "Kathmandu Central", "Kathmandu", "Kathmandu", "Bagmati"),
        ("LLT-01", "Lalitpur Central", "Lalitpur", "Lalitpur", "Bagmati"),
        ("BKT-01", "Bhaktapur", "Bhaktapur", "Bhaktapur", "Bagmati"),
    ]
    created = []
    for code, name, muni, district, prov in areas:
        result = await db.execute(select(ServiceArea).where(ServiceArea.area_code == code))
        area = result.scalar_one_or_none()
        if area is None:
            area = ServiceArea(
                id=uuid4(),
                area_code=code,
                area_name=name,
                municipality=muni,
                district=district,
                province=prov,
                is_active=True,
            )
            db.add(area)
            created.append(area)
    await db.commit()
    logger.success(f"Seeded {len(created)} new service areas")
    return created


async def seed_test_customers(db) -> None:
    test_customers = [
        ("DH-2024-000001", "Ram Bahadur Thapa", "+9779841234567", "ram@example.com", "12-34-56-78901", "ne"),
        ("DH-2024-000002", "Sita Kumari Sharma", "+9779841112222", "sita@example.com", "23-45-67-89012", "ne"),
        ("DH-2024-000003", "John Doe", "+9779841999999", "john@example.com", "34-56-78-90123", "en"),
    ]
    pkg_result = await db.execute(select(Package).where(Package.package_code == "STANDARD-60"))
    standard_pkg = pkg_result.scalar_one_or_none()
    area_result = await db.execute(select(ServiceArea).where(ServiceArea.area_code == "KTM-01"))
    ktm = area_result.scalar_one_or_none()

    for code, name, phone, email, nid, lang in test_customers:
        result = await db.execute(select(Customer).where(Customer.customer_code == code))
        cust = result.scalar_one_or_none()
        if cust:
            continue
        cust = Customer(
            id=uuid4(),
            customer_code=code,
            full_name=name,
            phone_primary=phone,
            email=email,
            national_id=nid,
            preferred_language=lang,
            kyc_verified=True,
            kyc_verified_at=datetime.utcnow(),
            account_status="active",
            credit_score=720,
            loyalty_tier="silver",
        )
        db.add(cust)
        await db.flush()

        # Address
        if ktm:
            addr = CustomerAddress(
                id=uuid4(),
                customer_id=cust.id,
                address_type="installation",
                street_address=f"Test Street, Ward 5, {ktm.municipality}",
                ward="5",
                municipality=ktm.municipality,
                district=ktm.district,
                province=ktm.province,
                service_area_id=ktm.id,
                is_primary=True,
            )
            db.add(addr)

        # Subscription
        if standard_pkg:
            sub = CustomerPackage(
                id=uuid4(),
                customer_id=cust.id,
                package_id=standard_pkg.id,
                started_at=datetime.utcnow() - timedelta(days=60),
                expires_at=datetime.utcnow() + timedelta(days=30),
                billing_cycle_day=1,
                status="active",
                auto_renew=True,
            )
            db.add(sub)

        # Mock ONU device
        device = NetworkDevice(
            id=uuid4(),
            device_type="onu",
            device_model="HG8245H5",
            serial_number=f"HWTC-{code[-6:]}",
            mac_address=f"00:11:22:33:44:{int(code[-2:]):02X}",
            customer_id=cust.id,
            service_area_id=ktm.id if ktm else None,
            pppoe_username=f"dh{code[-6:]}",
            status="online",
            rx_power_dbm=Decimal("-18.50"),
            tx_power_dbm=Decimal("2.10"),
            signal_quality="good",
            uptime_seconds=86400 * 30,
            last_seen_at=datetime.utcnow(),
        )
        db.add(device)
    await db.commit()
    logger.success("Seeded test customers, addresses, subscriptions, and devices")


async def main():
    logger.info("Initializing database tables...")
    await init_db()

    async with AsyncSessionLocal() as db:
        roles = await seed_roles_and_permissions(db)
        await seed_superadmin(db, roles)
        await seed_packages(db)
        await seed_service_areas(db)
        await seed_test_customers(db)
    logger.success("Seeding complete")


if __name__ == "__main__":
    asyncio.run(main())
