"""
HUNTER.OS - Celery Configuration
Background task queue for rate-limited sending, discovery, and scheduled jobs.
"""
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "hunteros",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Rate limiting defaults
    task_default_rate_limit="10/m",
    # Result expiration
    result_expires=3600,
    # Beat schedule (replaces APScheduler in production)
    beat_schedule={
        "process-workflows": {
            "task": "app.tasks.process_due_workflows",
            "schedule": 60.0,  # Every minute
        },
        "check-replies": {
            "task": "app.tasks.check_email_replies",
            "schedule": 120.0,  # Every 2 minutes
        },
        "reset-monthly-usage": {
            "task": "app.tasks.reset_monthly_usage",
            "schedule": 86400.0,  # Daily check (actual reset on 1st)
        },
        "auto-select-ab-winners": {
            "task": "app.tasks.auto_select_ab_winners",
            "schedule": 3600.0,  # Every hour
        },
    },
)

celery_app.autodiscover_tasks(["app"])
