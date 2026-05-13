"""SMS / Email queue tasks."""

import asyncio

from app.workers.celery_app import celery_app
from app.services.notification_service import notification_service


@celery_app.task(name="app.workers.tasks.notification_tasks.send_sms")
def send_sms(phone: str, message: str):
    return asyncio.run(notification_service.send_sms(phone, message))


@celery_app.task(name="app.workers.tasks.notification_tasks.send_email")
def send_email(to_email: str, subject: str, body: str, html: bool = False):
    return asyncio.run(notification_service.send_email(to_email, subject, body, html=html))
