"""Monthly invoice generation."""

import asyncio
from datetime import datetime

from loguru import logger
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.models import AsyncSessionLocal, CustomerPackage
from app.services.billing_service import billing_service


@celery_app.task(name="app.workers.tasks.billing_tasks.generate_monthly_invoices")
def generate_monthly_invoices():
    return asyncio.run(_run())


async def _run():
    today = datetime.utcnow().day
    async with AsyncSessionLocal() as db:
        subs = (await db.execute(
            select(CustomerPackage).where(
                CustomerPackage.status == "active",
                CustomerPackage.billing_cycle_day == today,
            )
        )).scalars().all()
        generated = 0
        for sub in subs:
            try:
                await billing_service.generate_invoice(db, sub.id)
                generated += 1
            except Exception as e:
                logger.warning(f"Invoice gen failed for sub {sub.id}: {e}")
        return {"generated": generated, "billing_day": today}
