"""
Compliance tracking service — overdue detection, deadline monitoring,
reminder generation, and automatic status updates.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.compliance import ComplianceStatus, ComplianceTask
from app.models.client import Client
from app.models.user import User

logger = logging.getLogger(__name__)


class ComplianceTracker:
    """Track compliance deadlines, generate reminders, and auto-mark overdue tasks."""

    # ── Overdue tasks ────────────────────────────────────────────────────

    @staticmethod
    async def check_overdue_tasks(db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Return all tasks that are past their due date and not yet completed.

        These are tasks with status in (pending, in_progress) where
        due_date < today.
        """
        today = date.today()

        stmt = (
            select(ComplianceTask)
            .options(
                joinedload(ComplianceTask.client),
                joinedload(ComplianceTask.assignee),
            )
            .where(
                and_(
                    ComplianceTask.due_date < today,
                    ComplianceTask.status.in_([
                        ComplianceStatus.pending,
                        ComplianceStatus.in_progress,
                    ]),
                )
            )
            .order_by(ComplianceTask.due_date.asc())
        )

        result = await db.execute(stmt)
        tasks = result.unique().scalars().all()

        overdue_list: List[Dict[str, Any]] = []
        for task in tasks:
            days_overdue = (today - task.due_date).days
            overdue_list.append({
                "task_id": str(task.id),
                "client_id": str(task.client_id),
                "client_name": task.client.firm_name if task.client else None,
                "task_type": task.task_type.value,
                "description": task.description,
                "due_date": task.due_date.isoformat(),
                "days_overdue": days_overdue,
                "status": task.status.value,
                "assigned_to": str(task.assigned_to) if task.assigned_to else None,
                "assigned_to_name": task.assignee.full_name if task.assignee else None,
                "assessment_year": task.assessment_year,
            })

        logger.info("Found %d overdue compliance tasks", len(overdue_list))
        return overdue_list

    # ── Upcoming deadlines ───────────────────────────────────────────────

    @staticmethod
    async def get_upcoming_deadlines(
        db: AsyncSession, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Return tasks due within the next *days* days.

        Includes tasks that are pending or in_progress.
        """
        today = date.today()
        cutoff = today + timedelta(days=days)

        stmt = (
            select(ComplianceTask)
            .options(
                joinedload(ComplianceTask.client),
                joinedload(ComplianceTask.assignee),
            )
            .where(
                and_(
                    ComplianceTask.due_date >= today,
                    ComplianceTask.due_date <= cutoff,
                    ComplianceTask.status.in_([
                        ComplianceStatus.pending,
                        ComplianceStatus.in_progress,
                    ]),
                )
            )
            .order_by(ComplianceTask.due_date.asc())
        )

        result = await db.execute(stmt)
        tasks = result.unique().scalars().all()

        upcoming: List[Dict[str, Any]] = []
        for task in tasks:
            days_until = (task.due_date - today).days
            upcoming.append({
                "task_id": str(task.id),
                "client_id": str(task.client_id),
                "client_name": task.client.firm_name if task.client else None,
                "task_type": task.task_type.value,
                "description": task.description,
                "due_date": task.due_date.isoformat(),
                "days_until_due": days_until,
                "status": task.status.value,
                "assigned_to": str(task.assigned_to) if task.assigned_to else None,
                "assigned_to_name": task.assignee.full_name if task.assignee else None,
                "assessment_year": task.assessment_year,
            })

        logger.info(
            "Found %d upcoming tasks due within %d days", len(upcoming), days
        )
        return upcoming

    # ── Reminder generation ──────────────────────────────────────────────

    @staticmethod
    async def generate_reminders(db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Find tasks due within the next 15 days that have NOT had a reminder sent.

        Returns a list of reminder dicts and marks each task's reminder_sent = True.
        """
        today = date.today()
        cutoff = today + timedelta(days=15)

        stmt = (
            select(ComplianceTask)
            .options(
                joinedload(ComplianceTask.client),
                joinedload(ComplianceTask.assignee),
            )
            .where(
                and_(
                    ComplianceTask.due_date >= today,
                    ComplianceTask.due_date <= cutoff,
                    ComplianceTask.status.in_([
                        ComplianceStatus.pending,
                        ComplianceStatus.in_progress,
                    ]),
                    ComplianceTask.reminder_sent == False,  # noqa: E712
                )
            )
            .order_by(ComplianceTask.due_date.asc())
        )

        result = await db.execute(stmt)
        tasks = result.unique().scalars().all()

        reminders: List[Dict[str, Any]] = []
        task_ids_to_update: List[UUID] = []

        for task in tasks:
            days_until = (task.due_date - today).days
            urgency = (
                "URGENT" if days_until <= 3
                else "IMPORTANT" if days_until <= 7
                else "UPCOMING"
            )

            client_name = task.client.firm_name if task.client else "Unknown client"
            assignee_name = task.assignee.full_name if task.assignee else "Unassigned"

            message = (
                f"[{urgency}] {task.task_type.value.upper().replace('_', ' ')} "
                f"for {client_name} "
                f"(AY {task.assessment_year or 'N/A'}) is due on "
                f"{task.due_date.strftime('%d %b %Y')} "
                f"({days_until} day{'s' if days_until != 1 else ''} remaining). "
                f"Assigned to: {assignee_name}. "
                f"Status: {task.status.value}."
            )

            reminders.append({
                "task_id": str(task.id),
                "client_id": str(task.client_id),
                "client_name": client_name,
                "task_type": task.task_type.value,
                "due_date": task.due_date.isoformat(),
                "days_until_due": days_until,
                "urgency": urgency,
                "assigned_to": str(task.assigned_to) if task.assigned_to else None,
                "assigned_to_name": assignee_name,
                "message": message,
            })

            task_ids_to_update.append(task.id)

        # Mark reminder_sent = True for all processed tasks
        if task_ids_to_update:
            stmt_update = (
                update(ComplianceTask)
                .where(ComplianceTask.id.in_(task_ids_to_update))
                .values(reminder_sent=True)
            )
            await db.execute(stmt_update)
            await db.flush()

        logger.info("Generated %d compliance reminders", len(reminders))
        return reminders

    # ── Auto-mark overdue ────────────────────────────────────────────────

    @staticmethod
    async def auto_mark_overdue(db: AsyncSession) -> int:
        """
        Automatically update status to 'overdue' for all pending/in_progress
        tasks that are past their due date.

        Returns the number of tasks updated.
        """
        today = date.today()

        stmt = (
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
        )

        result = await db.execute(stmt)
        await db.flush()

        count = result.rowcount  # type: ignore[union-attr]
        if count > 0:
            logger.warning("Auto-marked %d tasks as overdue", count)
        else:
            logger.info("No tasks to mark as overdue")

        return count

    # ── Dashboard summary ────────────────────────────────────────────────

    @staticmethod
    async def get_compliance_summary(db: AsyncSession) -> Dict[str, Any]:
        """
        Return a dashboard summary of compliance health.

        Useful for the main dashboard widget.
        """
        today = date.today()
        next_7 = today + timedelta(days=7)
        next_30 = today + timedelta(days=30)

        # Count overdue
        overdue_stmt = select(ComplianceTask).where(
            and_(
                ComplianceTask.due_date < today,
                ComplianceTask.status.in_([
                    ComplianceStatus.pending,
                    ComplianceStatus.in_progress,
                ]),
            )
        )
        overdue_result = await db.execute(overdue_stmt)
        overdue_count = len(overdue_result.scalars().all())

        # Count due this week
        week_stmt = select(ComplianceTask).where(
            and_(
                ComplianceTask.due_date >= today,
                ComplianceTask.due_date <= next_7,
                ComplianceTask.status.in_([
                    ComplianceStatus.pending,
                    ComplianceStatus.in_progress,
                ]),
            )
        )
        week_result = await db.execute(week_stmt)
        due_this_week = len(week_result.scalars().all())

        # Count due this month
        month_stmt = select(ComplianceTask).where(
            and_(
                ComplianceTask.due_date >= today,
                ComplianceTask.due_date <= next_30,
                ComplianceTask.status.in_([
                    ComplianceStatus.pending,
                    ComplianceStatus.in_progress,
                ]),
            )
        )
        month_result = await db.execute(month_stmt)
        due_this_month = len(month_result.scalars().all())

        # Count completed this month
        month_start = today.replace(day=1)
        completed_stmt = select(ComplianceTask).where(
            and_(
                ComplianceTask.status == ComplianceStatus.completed,
                ComplianceTask.completed_at >= month_start,
            )
        )
        completed_result = await db.execute(completed_stmt)
        completed_this_month = len(completed_result.scalars().all())

        health = "good"
        if overdue_count > 5:
            health = "critical"
        elif overdue_count > 0:
            health = "warning"

        return {
            "health": health,
            "overdue_count": overdue_count,
            "due_this_week": due_this_week,
            "due_this_month": due_this_month,
            "completed_this_month": completed_this_month,
            "as_of": today.isoformat(),
        }
