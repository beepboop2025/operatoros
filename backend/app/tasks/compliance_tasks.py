"""
Compliance automation background tasks — deadline monitoring, reminders,
overdue marking.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from app.celery_app import celery_app

logger = logging.getLogger("operatoros.tasks.compliance")


def _run_async(coro):
    """Run an async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True)
def check_upcoming_deadlines(self) -> dict:
    """Check for compliance tasks due within 7, 3, and 1 days.

    Sends reminder notifications (logged for now, can be wired to email/SMS).
    Runs daily at 9 AM via Celery Beat.
    """
    logger.info("Checking upcoming compliance deadlines")

    async def _check():
        from app.database import async_session_factory
        from app.models.compliance import ComplianceTask, ComplianceStatus
        from app.models.client import Client
        from sqlalchemy import and_, select

        today = date.today()
        reminders = {"7_day": [], "3_day": [], "1_day": [], "overdue": []}

        async with async_session_factory() as db:
            for days, bucket in [(7, "7_day"), (3, "3_day"), (1, "1_day")]:
                target_date = today + timedelta(days=days)
                result = await db.execute(
                    select(ComplianceTask, Client.firm_name)
                    .join(Client, ComplianceTask.client_id == Client.id)
                    .where(
                        and_(
                            ComplianceTask.due_date == target_date,
                            ComplianceTask.status.notin_([ComplianceStatus.completed]),
                            ComplianceTask.reminder_sent.is_(False),
                        )
                    )
                )
                for task, firm_name in result.all():
                    reminders[bucket].append({
                        "task_id": str(task.id),
                        "client_name": firm_name,
                        "task_type": task.task_type.value,
                        "due_date": task.due_date.isoformat(),
                        "description": task.description or "",
                    })
                    # Mark reminder as sent
                    task.reminder_sent = True

            # Overdue tasks that haven't been flagged
            overdue_result = await db.execute(
                select(ComplianceTask, Client.firm_name)
                .join(Client, ComplianceTask.client_id == Client.id)
                .where(
                    and_(
                        ComplianceTask.due_date < today,
                        ComplianceTask.status.notin_([ComplianceStatus.completed]),
                        ComplianceTask.reminder_sent.is_(False),
                    )
                )
            )
            for task, firm_name in overdue_result.all():
                reminders["overdue"].append({
                    "task_id": str(task.id),
                    "client_name": firm_name,
                    "task_type": task.task_type.value,
                    "due_date": task.due_date.isoformat(),
                })
                task.reminder_sent = True

            await db.commit()

        total = sum(len(v) for v in reminders.values())
        logger.info(
            "Deadline check complete: %d reminders (7d=%d, 3d=%d, 1d=%d, overdue=%d)",
            total,
            len(reminders["7_day"]),
            len(reminders["3_day"]),
            len(reminders["1_day"]),
            len(reminders["overdue"]),
        )

        return {"total_reminders": total, "breakdown": {k: len(v) for k, v in reminders.items()}}

    return _run_async(_check())


@celery_app.task(bind=True)
def mark_overdue_tasks(self) -> dict:
    """Mark tasks past their due date as 'overdue'.

    Runs daily at 12:30 AM via Celery Beat.
    """
    logger.info("Marking overdue compliance tasks")

    async def _mark():
        from app.database import async_session_factory
        from app.models.compliance import ComplianceTask, ComplianceStatus
        from sqlalchemy import and_, update

        today = date.today()

        async with async_session_factory() as db:
            result = await db.execute(
                update(ComplianceTask)
                .where(
                    and_(
                        ComplianceTask.due_date < today,
                        ComplianceTask.status.in_([
                            ComplianceStatus.pending,
                            ComplianceStatus.in_progress,
                        ]),
                    )
                )
                .values(status=ComplianceStatus.overdue)
                .returning(ComplianceTask.id)
            )
            marked_ids = result.scalars().all()
            await db.commit()

        count = len(marked_ids)
        logger.info("Marked %d tasks as overdue", count)
        return {"marked_overdue": count}

    return _run_async(_mark())


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def auto_generate_compliance_calendar(
    self, client_id: str, entity_type: str, fy: str, audit_applicable: bool = False
) -> dict:
    """Auto-generate compliance tasks for a client for a financial year.

    Creates ComplianceTask records for all statutory deadlines.
    """
    logger.info("Auto-generating compliance calendar for client %s, FY %s", client_id, fy)

    async def _generate():
        from uuid import UUID
        from app.database import async_session_factory
        from app.models.compliance import ComplianceTask, ComplianceStatus, TaskType
        from app.utils.compliance_calendar import generate_compliance_calendar

        calendar = generate_compliance_calendar(
            entity_type=entity_type,
            audit_applicable=audit_applicable,
            fy=fy,
        )

        async with async_session_factory() as db:
            created = 0
            for event in calendar:
                try:
                    task_type_val = event["task_type"]
                    # Map to TaskType enum
                    task_type = TaskType(task_type_val)
                except ValueError:
                    task_type = TaskType.other

                task = ComplianceTask(
                    client_id=UUID(client_id),
                    task_type=task_type,
                    description=event["description"],
                    due_date=date.fromisoformat(event["due_date"]),
                    status=ComplianceStatus.pending,
                )
                db.add(task)
                created += 1

            await db.commit()

        logger.info("Created %d compliance tasks for client %s", created, client_id)
        return {"client_id": client_id, "tasks_created": created, "fy": fy}

    try:
        return _run_async(_generate())
    except Exception as exc:
        logger.error("Compliance calendar generation failed for %s: %s", client_id, exc)
        raise self.retry(exc=exc)
