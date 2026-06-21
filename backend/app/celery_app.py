"""
Celery application configuration for OperatorOS background jobs.

Usage:
    celery -A app.celery_app worker --loglevel=info
    celery -A app.celery_app beat --loglevel=info
"""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

# Redis URL for broker and result backend
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "operatoros",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.report_tasks",
        "app.tasks.compliance_tasks",
        "app.tasks.notification_tasks",
    ],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="Asia/Kolkata",
    enable_utc=True,

    # Task execution
    task_soft_time_limit=300,   # 5 minutes soft limit
    task_time_limit=600,        # 10 minutes hard limit
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Result expiry
    result_expires=86400,       # 24 hours

    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=3,

    # Beat schedule for periodic tasks
    beat_schedule={
        "check-compliance-deadlines": {
            "task": "app.tasks.compliance_tasks.check_upcoming_deadlines",
            "schedule": crontab(hour=9, minute=0),  # Daily at 9 AM IST
            "args": (),
        },
        "mark-overdue-tasks": {
            "task": "app.tasks.compliance_tasks.mark_overdue_tasks",
            "schedule": crontab(hour=0, minute=30),  # Daily at 12:30 AM IST
            "args": (),
        },
    },
)
