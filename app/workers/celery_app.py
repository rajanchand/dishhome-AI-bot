"""Celery application: scheduled tasks for SLA, billing, network polling, notifications."""

from celery import Celery
from celery.schedules import crontab

from config.settings import settings

celery_app = Celery(
    "dishhome",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.sla_monitor",
        "app.workers.tasks.billing_tasks",
        "app.workers.tasks.network_poller",
        "app.workers.tasks.notification_tasks",
        "app.workers.tasks.report_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kathmandu",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    beat_schedule={
        "sla-monitor-every-minute": {
            "task": "app.workers.tasks.sla_monitor.check_sla_breaches",
            "schedule": 60.0,
        },
        "network-poll-every-5min": {
            "task": "app.workers.tasks.network_poller.poll_all_devices",
            "schedule": 300.0,
        },
        "generate-monthly-invoices": {
            "task": "app.workers.tasks.billing_tasks.generate_monthly_invoices",
            "schedule": crontab(day_of_month=1, hour=2, minute=0),
        },
        "daily-summary": {
            "task": "app.workers.tasks.report_tasks.send_daily_summary",
            "schedule": crontab(hour=8, minute=0),
        },
    },
)
