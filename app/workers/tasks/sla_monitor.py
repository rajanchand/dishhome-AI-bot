"""SLA breach monitor — runs every minute."""

import asyncio

from loguru import logger

from app.workers.celery_app import celery_app
from app.models import AsyncSessionLocal
from app.services.ticket_service import ticket_service
from app.services.notification_service import notification_service


@celery_app.task(name="app.workers.tasks.sla_monitor.check_sla_breaches")
def check_sla_breaches():
    """Find tickets that just breached SLA, mark them, and notify."""
    return asyncio.run(_run())


async def _run():
    async with AsyncSessionLocal() as db:
        breached = await ticket_service.check_sla_breaches(db)
        for ticket in breached:
            logger.warning(f"SLA breach: {ticket.ticket_number} ({ticket.priority})")
            # notify assigned agent if any
            if ticket.assigned_agent_id:
                from sqlalchemy import select
                from app.models import User, Customer
                user = (await db.execute(select(User).where(User.id == ticket.assigned_agent_id))).scalar_one_or_none()
                customer = (await db.execute(select(Customer).where(Customer.id == ticket.customer_id))).scalar_one_or_none()
                if user and user.email:
                    await notification_service.send_sla_breach_alert(
                        agent_email=user.email,
                        ticket_number=ticket.ticket_number,
                        priority=ticket.priority,
                        customer_name=customer.full_name if customer else "",
                    )
        return {"breached_count": len(breached)}
