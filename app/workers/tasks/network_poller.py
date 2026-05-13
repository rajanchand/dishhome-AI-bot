"""Periodic network device polling — every 5 minutes."""

import asyncio

from app.workers.celery_app import celery_app
from app.models import AsyncSessionLocal
from app.services.network_service import network_service


@celery_app.task(name="app.workers.tasks.network_poller.poll_all_devices")
def poll_all_devices():
    return asyncio.run(_run())


async def _run():
    async with AsyncSessionLocal() as db:
        return await network_service.poll_all_devices(db)
