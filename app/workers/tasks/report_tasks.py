"""Daily summary reports."""

import asyncio

from loguru import logger
from sqlalchemy import select, func

from app.workers.celery_app import celery_app
from app.models import AsyncSessionLocal, CallRecord, Ticket, NetworkDevice


@celery_app.task(name="app.workers.tasks.report_tasks.send_daily_summary")
def send_daily_summary():
    return asyncio.run(_run())


async def _run():
    async with AsyncSessionLocal() as db:
        total_calls = (await db.execute(select(func.count(CallRecord.id)))).scalar() or 0
        open_tickets = (await db.execute(
            select(func.count(Ticket.id)).where(Ticket.status.in_(["open", "in_progress"]))
        )).scalar() or 0
        offline_devices = (await db.execute(
            select(func.count(NetworkDevice.id)).where(NetworkDevice.status == "offline")
        )).scalar() or 0
        summary = {
            "total_calls": int(total_calls),
            "open_tickets": int(open_tickets),
            "offline_devices": int(offline_devices),
        }
        logger.info(f"Daily summary: {summary}")
        return summary
