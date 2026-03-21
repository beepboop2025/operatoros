"""
Compliance automation engine — auto-generates calendars, tracks deadlines,
and provides notification-ready alerts.

This service is the brain behind automated compliance management.
It works with the ComplianceTask model and the calendar generator
to keep the practice on top of all statutory deadlines.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.compliance import ComplianceStatus, ComplianceTask, TaskType
from app.models.user import User
from app.utils.compliance_calendar import generate_compliance_calendar

logger = logging.getLogger("operatoros.compliance_engine")

# ── Filing date reference (Indian tax calendar) ─────────────────────────────

GST_MONTHLY_DATES = {
    "GSTR-1": 11,   # 11th of next month
    "GSTR-3B": 20,  # 20th of next month
    "GSTR-9": None,  # Annual: 31 December
}

TDS_QUARTERLY_DATES = {
    "Q1": "July 31",
    "Q2": "October 31",
    "Q3": "January 31",
    "Q4": "May 31",
}

ADVANCE_TAX_DATES = {
    "1st": "June 15",    # 15% cumulative
    "2nd": "September 15",  # 45% cumulative
    "3rd": "December 15",   # 75% cumulative
    "4th": "March 15",      # 100%
}


class ComplianceEngine:
    """Automated compliance deadline management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Auto-generate calendar for a client ──────────────────────────────

    async def generate_client_calendar(
        self,
        client_id: UUID,
        fy: str,
        audit_applicable: bool = False,
        assigned_to: Optional[UUID] = None,
    ) -> List[ComplianceTask]:
        """Generate all compliance tasks for a client for a financial year.

        Avoids creating duplicates if tasks already exist for the same
        client + task_type + due_date.
        """
        # Fetch client to determine entity type
        result = await self.db.execute(
            select(Client).where(Client.id == client_id)
        )
        client = result.scalar_one_or_none()
        if client is None:
            raise ValueError(f"Client {client_id} not found")

        # Generate the calendar
        events = generate_compliance_calendar(
            entity_type=client.entity_type.value,
            audit_applicable=audit_applicable,
            fy=fy,
        )

        # Fetch existing tasks to avoid duplicates
        existing = await self.db.execute(
            select(ComplianceTask.task_type, ComplianceTask.due_date)
            .where(ComplianceTask.client_id == client_id)
        )
        existing_set = {
            (row.task_type.value if hasattr(row.task_type, "value") else row.task_type, row.due_date.isoformat())
            for row in existing.all()
        }

        created_tasks = []
        for event in events:
            key = (event["task_type"], event["due_date"])
            if key in existing_set:
                continue

            try:
                task_type = TaskType(event["task_type"])
            except ValueError:
                task_type = TaskType.other

            task = ComplianceTask(
                client_id=client_id,
                task_type=task_type,
                description=event["description"],
                due_date=date.fromisoformat(event["due_date"]),
                status=ComplianceStatus.pending,
                assigned_to=assigned_to,
                assessment_year=fy.replace("-", "-"),
            )
            self.db.add(task)
            created_tasks.append(task)

        if created_tasks:
            await self.db.flush()
            logger.info(
                "Generated %d compliance tasks for client %s, FY %s",
                len(created_tasks),
                client_id,
                fy,
            )

        return created_tasks

    # ── Deadline monitoring ───────────────────────────────────────────────

    async def get_upcoming_deadlines(
        self,
        days_ahead: int = 7,
        firm_id: Optional[UUID] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get upcoming deadlines grouped by urgency.

        Returns:
            Dict with keys: 'overdue', 'today', 'this_week', 'next_week'
        """
        today = date.today()
        week_end = today + timedelta(days=7)
        next_week_end = today + timedelta(days=14)

        query = (
            select(ComplianceTask, Client.firm_name)
            .join(Client, ComplianceTask.client_id == Client.id)
            .where(
                and_(
                    ComplianceTask.status.notin_([ComplianceStatus.completed]),
                    ComplianceTask.due_date <= next_week_end,
                )
            )
            .order_by(ComplianceTask.due_date)
        )

        result = await self.db.execute(query)
        rows = result.all()

        groups: Dict[str, List[Dict[str, Any]]] = {
            "overdue": [],
            "today": [],
            "this_week": [],
            "next_week": [],
        }

        for task, firm_name in rows:
            item = {
                "task_id": str(task.id),
                "client_name": firm_name,
                "task_type": task.task_type.value,
                "due_date": task.due_date.isoformat(),
                "description": task.description or "",
                "status": task.status.value,
                "days_until_due": (task.due_date - today).days,
            }

            if task.due_date < today:
                groups["overdue"].append(item)
            elif task.due_date == today:
                groups["today"].append(item)
            elif task.due_date <= week_end:
                groups["this_week"].append(item)
            else:
                groups["next_week"].append(item)

        return groups

    # ── Mark completed ───────────────────────────────────────────────────

    async def mark_task_completed(
        self, task_id: UUID, completed_by: UUID
    ) -> ComplianceTask:
        """Mark a compliance task as completed."""
        result = await self.db.execute(
            select(ComplianceTask).where(ComplianceTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        task.status = ComplianceStatus.completed
        task.completed_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info("Task %s marked as completed by %s", task_id, completed_by)
        return task

    # ── Overdue marking ──────────────────────────────────────────────────

    async def mark_overdue_tasks(self) -> int:
        """Mark all past-due pending/in-progress tasks as overdue.

        Returns the number of tasks updated.
        """
        today = date.today()
        result = await self.db.execute(
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
        marked = result.scalars().all()
        count = len(marked)

        if count:
            logger.info("Marked %d tasks as overdue", count)
        return count

    # ── Dashboard summary ────────────────────────────────────────────────

    async def get_compliance_summary(self) -> Dict[str, Any]:
        """Get a high-level compliance summary across all clients."""
        today = date.today()

        # Total tasks by status
        status_result = await self.db.execute(
            select(
                ComplianceTask.status,
                func.count(ComplianceTask.id),
            ).group_by(ComplianceTask.status)
        )
        status_counts = {row[0].value: row[1] for row in status_result.all()}

        # Overdue count
        overdue_result = await self.db.execute(
            select(func.count(ComplianceTask.id)).where(
                and_(
                    ComplianceTask.due_date < today,
                    ComplianceTask.status.notin_([ComplianceStatus.completed]),
                )
            )
        )
        overdue = overdue_result.scalar_one()

        # Due this week
        week_end = today + timedelta(days=7)
        due_week_result = await self.db.execute(
            select(func.count(ComplianceTask.id)).where(
                and_(
                    ComplianceTask.due_date >= today,
                    ComplianceTask.due_date <= week_end,
                    ComplianceTask.status.notin_([ComplianceStatus.completed]),
                )
            )
        )
        due_this_week = due_week_result.scalar_one()

        total = sum(status_counts.values())
        completed = status_counts.get("completed", 0)
        completion_rate = completed / total if total > 0 else 0.0

        return {
            "total_tasks": total,
            "status_breakdown": status_counts,
            "overdue": overdue,
            "due_this_week": due_this_week,
            "completion_rate": round(completion_rate, 4),
        }
