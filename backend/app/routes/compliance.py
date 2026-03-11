"""Compliance routes — task management, overdue tracking, calendar generation."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.middleware.audit import get_client_ip, log_action
from app.models.client import Client
from app.models.compliance import ComplianceStatus, ComplianceTask, TaskType as ModelTaskType
from app.models.user import User
from app.schemas.compliance import (
    ComplianceCalendarResponse,
    ComplianceTaskCreate,
    ComplianceTaskResponse,
    ComplianceTaskUpdate,
)
from app.utils.compliance_calendar import generate_compliance_calendar

router = APIRouter(tags=["compliance"])


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #


# Valid status transitions: prevents illogical jumps like completed -> pending
_VALID_TRANSITIONS: dict[ComplianceStatus, set[ComplianceStatus]] = {
    ComplianceStatus.pending: {ComplianceStatus.in_progress, ComplianceStatus.completed},
    ComplianceStatus.in_progress: {ComplianceStatus.pending, ComplianceStatus.completed},
    ComplianceStatus.completed: set(),  # terminal state — no going back
}


def _task_to_response(task: ComplianceTask) -> ComplianceTaskResponse:
    """Map a ComplianceTask ORM instance to the response schema."""
    return ComplianceTaskResponse(
        id=task.id,
        client_id=task.client_id,
        client_name=(
            task.client.firm_name if hasattr(task, "client") and task.client else None
        ),
        task_type=task.task_type.value,
        description=task.description or "",
        status=task.status.value,
        due_date=task.due_date,
        assessment_year=task.assessment_year or "",
        assigned_to=task.assigned_to,
        assigned_to_name=(
            task.assignee.full_name
            if hasattr(task, "assignee") and task.assignee
            else None
        ),
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# --------------------------------------------------------------------------- #
#  GET /tasks — List compliance tasks
# --------------------------------------------------------------------------- #


@router.get(
    "/tasks",
    response_model=list[ComplianceTaskResponse],
    summary="List all compliance tasks with filters",
)
async def list_tasks(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    client_id: Optional[uuid.UUID] = Query(None, description="Filter by client"),
    due_from: Optional[date] = Query(None, description="Due date range start"),
    due_to: Optional[date] = Query(None, description="Due date range end"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ComplianceTaskResponse]:
    """Return compliance tasks with optional filters for status, client, and due date range."""

    query = (
        select(ComplianceTask)
        .options(
            selectinload(ComplianceTask.client),
            selectinload(ComplianceTask.assignee),
        )
        .order_by(ComplianceTask.due_date)
    )

    if status_filter:
        try:
            cs = ComplianceStatus(status_filter)
            query = query.where(ComplianceTask.status == cs)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {[s.value for s in ComplianceStatus]}",
            )

    if client_id is not None:
        query = query.where(ComplianceTask.client_id == client_id)

    if due_from is not None:
        query = query.where(ComplianceTask.due_date >= due_from)

    if due_to is not None:
        query = query.where(ComplianceTask.due_date <= due_to)

    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return [_task_to_response(t) for t in tasks]


# --------------------------------------------------------------------------- #
#  POST /tasks — Create a compliance task
# --------------------------------------------------------------------------- #


@router.post(
    "/tasks",
    response_model=ComplianceTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a compliance task",
)
async def create_task(
    body: ComplianceTaskCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplianceTaskResponse:
    """Create a new compliance task for a client."""

    # Validate client
    result = await db.execute(select(Client).where(Client.id == body.client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    # Validate assignee if provided
    if body.assigned_to is not None:
        assignee_result = await db.execute(
            select(User).where(User.id == body.assigned_to)
        )
        if assignee_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )

    task = ComplianceTask(
        client_id=body.client_id,
        task_type=ModelTaskType(body.task_type.value),
        description=body.description,
        due_date=body.due_date,
        assessment_year=body.assessment_year,
        assigned_to=body.assigned_to or current_user.id,
        status=ComplianceStatus.pending,
    )
    db.add(task)
    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="compliance.task_create",
        entity_type="compliance_task",
        entity_id=task.id,
        details={
            "task_type": body.task_type.value,
            "client_id": str(body.client_id),
            "due_date": body.due_date.isoformat(),
        },
        ip_address=get_client_ip(request),
    )

    # Reload with relationships
    result = await db.execute(
        select(ComplianceTask)
        .options(
            selectinload(ComplianceTask.client),
            selectinload(ComplianceTask.assignee),
        )
        .where(ComplianceTask.id == task.id)
    )
    task = result.scalar_one()

    return _task_to_response(task)


# --------------------------------------------------------------------------- #
#  PUT /tasks/{task_id} — Update task
# --------------------------------------------------------------------------- #


@router.put(
    "/tasks/{task_id}",
    response_model=ComplianceTaskResponse,
    summary="Update compliance task status",
)
async def update_task(
    task_id: uuid.UUID,
    body: ComplianceTaskUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplianceTaskResponse:
    """Update an existing compliance task's status, assignee, or description."""

    result = await db.execute(
        select(ComplianceTask)
        .options(
            selectinload(ComplianceTask.client),
            selectinload(ComplianceTask.assignee),
        )
        .where(ComplianceTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    update_data = body.model_dump(exclude_unset=True)

    if "status" in update_data and update_data["status"] is not None:
        new_status = ComplianceStatus(update_data["status"].value)
        allowed = _VALID_TRANSITIONS.get(task.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from '{task.status.value}' to '{new_status.value}'",
            )
        task.status = new_status
        # Set completed_at when marking as completed
        if task.status == ComplianceStatus.completed:
            from datetime import datetime, timezone
            task.completed_at = datetime.now(timezone.utc)

    if "assigned_to" in update_data and update_data["assigned_to"] is not None:
        # Validate assignee
        assignee_result = await db.execute(
            select(User).where(User.id == update_data["assigned_to"])
        )
        if assignee_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )
        task.assigned_to = update_data["assigned_to"]

    if "description" in update_data and update_data["description"] is not None:
        task.description = update_data["description"]

    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="compliance.task_update",
        entity_type="compliance_task",
        entity_id=task.id,
        details={"updated_fields": list(update_data.keys())},
        ip_address=get_client_ip(request),
    )

    return _task_to_response(task)


# --------------------------------------------------------------------------- #
#  GET /overdue — All overdue tasks
# --------------------------------------------------------------------------- #


@router.get(
    "/overdue",
    response_model=list[ComplianceTaskResponse],
    summary="List all overdue tasks across all clients",
)
async def list_overdue_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ComplianceTaskResponse]:
    """Return all tasks that are past their due date and not yet completed."""

    today = date.today()
    result = await db.execute(
        select(ComplianceTask)
        .options(
            selectinload(ComplianceTask.client),
            selectinload(ComplianceTask.assignee),
        )
        .where(
            and_(
                ComplianceTask.due_date < today,
                ComplianceTask.status.notin_([
                    ComplianceStatus.completed,
                ]),
            )
        )
        .order_by(ComplianceTask.due_date)
    )
    tasks = result.scalars().all()

    return [_task_to_response(t) for t in tasks]


# --------------------------------------------------------------------------- #
#  POST /generate — Generate compliance calendar
# --------------------------------------------------------------------------- #


@router.post(
    "/generate",
    response_model=list[dict],
    summary="Generate compliance calendar for a client",
)
async def generate_calendar(
    client_id: uuid.UUID = Query(..., description="Client ID"),
    fy: str = Query(..., description="Financial year, e.g. '2025-26'"),
    audit_applicable: bool = Query(False, description="Whether tax audit applies"),
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Generate a compliance calendar for the given client and financial year.

    Uses the client's entity type and the provided parameters to produce
    all statutory deadlines for the FY.
    """

    # Validate client
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    calendar = generate_compliance_calendar(
        entity_type=client.entity_type.value,
        audit_applicable=audit_applicable,
        fy=fy,
    )

    await log_action(
        db,
        user_id=current_user.id,
        action="compliance.generate_calendar",
        entity_type="client",
        entity_id=client.id,
        details={"fy": fy, "audit_applicable": audit_applicable},
        ip_address=get_client_ip(request),
    )

    return calendar


# --------------------------------------------------------------------------- #
#  GET /upcoming — Tasks due in next N days
# --------------------------------------------------------------------------- #


@router.get(
    "/upcoming",
    response_model=list[ComplianceTaskResponse],
    summary="Tasks due within a specified number of days",
)
async def list_upcoming_tasks(
    days: int = Query(7, ge=1, le=90, description="Number of days to look ahead"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ComplianceTaskResponse]:
    """Return all non-completed tasks due within the next N days (default 7)."""

    today = date.today()
    cutoff = today + timedelta(days=days)

    result = await db.execute(
        select(ComplianceTask)
        .options(
            selectinload(ComplianceTask.client),
            selectinload(ComplianceTask.assignee),
        )
        .where(
            and_(
                ComplianceTask.due_date >= today,
                ComplianceTask.due_date <= cutoff,
                ComplianceTask.status.notin_([ComplianceStatus.completed]),
            )
        )
        .order_by(ComplianceTask.due_date)
    )
    tasks = result.scalars().all()

    return [_task_to_response(t) for t in tasks]
