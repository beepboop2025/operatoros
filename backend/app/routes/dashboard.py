"""Dashboard routes — aggregated statistics, compliance overview, recent activity."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.database import get_db
from app.dependencies import get_current_user, get_redis
from app.models.client import Client
from app.models.compliance import ComplianceStatus, ComplianceTask
from app.models.computation import TaxComputation
from app.models.document import Document, DocumentStatus
from app.models.query import Query as QueryModel
from app.models.user import User
from app.schemas.dashboard import (
    ComplianceOverview,
    ComplianceOverviewItem,
    DashboardStats,
    RecentActivity,
    RecentComputationItem,
    RecentDocumentItem,
    RecentQueryItem,
)

router = APIRouter(tags=["dashboard"])


# --------------------------------------------------------------------------- #
#  GET /stats — Dashboard statistics
# --------------------------------------------------------------------------- #


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_conn: aioredis.Redis = Depends(get_redis),
) -> DashboardStats:
    """Return aggregate statistics for the dashboard: total clients, tasks,
    overdue items, documents processed, and queries today.

    Results are cached in Redis for 60 seconds.
    """
    from app.services.cache import CacheService, TTL_DASHBOARD_STATS

    cache = CacheService(redis_conn)
    cache_key = CacheService.dashboard_key("stats")
    cached = await cache.get(cache_key)
    if cached is not None:
        return DashboardStats(**cached)

    today = date.today()
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    # Total active clients
    total_clients_result = await db.execute(
        select(func.count(Client.id)).where(Client.is_active.is_(True))
    )
    total_clients = total_clients_result.scalar_one()

    # Active tasks (pending + in_progress)
    active_tasks_result = await db.execute(
        select(func.count(ComplianceTask.id)).where(
            ComplianceTask.status.in_([
                ComplianceStatus.pending,
                ComplianceStatus.in_progress,
            ])
        )
    )
    active_tasks = active_tasks_result.scalar_one()

    # Overdue tasks
    overdue_tasks_result = await db.execute(
        select(func.count(ComplianceTask.id)).where(
            and_(
                ComplianceTask.due_date < today,
                ComplianceTask.status.notin_([ComplianceStatus.completed]),
            )
        )
    )
    overdue_tasks = overdue_tasks_result.scalar_one()

    # Documents processed
    docs_processed_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.status == DocumentStatus.processed
        )
    )
    documents_processed = docs_processed_result.scalar_one()

    # Queries today
    queries_today_result = await db.execute(
        select(func.count(QueryModel.id)).where(
            QueryModel.created_at >= today_start
        )
    )
    queries_today = queries_today_result.scalar_one()

    stats = DashboardStats(
        total_clients=total_clients,
        active_tasks=active_tasks,
        overdue_tasks=overdue_tasks,
        documents_processed=documents_processed,
        queries_today=queries_today,
        revenue_this_month=Decimal("0"),  # Placeholder: no revenue model yet
    )

    await cache.set(cache_key, stats.model_dump(mode="json"), TTL_DASHBOARD_STATS)
    return stats


# --------------------------------------------------------------------------- #
#  GET /compliance-overview — Compliance summary
# --------------------------------------------------------------------------- #


@router.get(
    "/compliance-overview",
    response_model=ComplianceOverview,
    summary="Get compliance overview for dashboard",
)
async def get_compliance_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplianceOverview:
    """Return a compliance overview with upcoming tasks (next 7 days),
    overdue tasks, and overall completion rate.
    """

    today = date.today()
    seven_days = today + timedelta(days=7)

    # Upcoming 7 days
    upcoming_result = await db.execute(
        select(ComplianceTask, Client.firm_name)
        .join(Client, ComplianceTask.client_id == Client.id)
        .where(
            and_(
                ComplianceTask.due_date >= today,
                ComplianceTask.due_date <= seven_days,
                ComplianceTask.status.notin_([ComplianceStatus.completed]),
            )
        )
        .order_by(ComplianceTask.due_date)
        .limit(20)
    )
    upcoming_rows = upcoming_result.all()

    upcoming_items = [
        ComplianceOverviewItem(
            id=task.id,
            client_name=firm_name,
            task_type=task.task_type.value,
            due_date=task.due_date.isoformat(),
            status=task.status.value,
            days_until_due=(task.due_date - today).days,
        )
        for task, firm_name in upcoming_rows
    ]

    # Overdue
    overdue_result = await db.execute(
        select(ComplianceTask, Client.firm_name)
        .join(Client, ComplianceTask.client_id == Client.id)
        .where(
            and_(
                ComplianceTask.due_date < today,
                ComplianceTask.status.notin_([ComplianceStatus.completed]),
            )
        )
        .order_by(ComplianceTask.due_date)
        .limit(20)
    )
    overdue_rows = overdue_result.all()

    overdue_items = [
        ComplianceOverviewItem(
            id=task.id,
            client_name=firm_name,
            task_type=task.task_type.value,
            due_date=task.due_date.isoformat(),
            status=task.status.value,
            days_until_due=(task.due_date - today).days,
        )
        for task, firm_name in overdue_rows
    ]

    # Completion rate
    total_result = await db.execute(select(func.count(ComplianceTask.id)))
    total_tasks = total_result.scalar_one()

    completed_result = await db.execute(
        select(func.count(ComplianceTask.id)).where(
            ComplianceTask.status == ComplianceStatus.completed
        )
    )
    completed_tasks = completed_result.scalar_one()

    completion_rate = (
        completed_tasks / total_tasks if total_tasks > 0 else 0.0
    )

    return ComplianceOverview(
        upcoming_7_days=upcoming_items,
        overdue=overdue_items,
        completion_rate=round(completion_rate, 4),
    )


# --------------------------------------------------------------------------- #
#  GET /recent-activity — Recent queries, documents, computations
# --------------------------------------------------------------------------- #


@router.get(
    "/recent-activity",
    response_model=RecentActivity,
    summary="Get recent activity for dashboard",
)
async def get_recent_activity(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecentActivity:
    """Return the 10 most recent queries, documents, and computations."""

    # Recent queries
    queries_result = await db.execute(
        select(QueryModel, User.full_name)
        .outerjoin(User, QueryModel.asked_by == User.id)
        .order_by(QueryModel.created_at.desc())
        .limit(10)
    )
    recent_queries = [
        RecentQueryItem(
            id=q.id,
            question=q.question[:200],
            query_type=q.query_type.value if q.query_type else "general",
            asked_by_name=full_name,
            created_at=q.created_at,
        )
        for q, full_name in queries_result.all()
    ]

    # Recent documents
    docs_result = await db.execute(
        select(Document, Client.firm_name)
        .outerjoin(Client, Document.client_id == Client.id)
        .order_by(Document.uploaded_at.desc())
        .limit(10)
    )
    recent_documents = [
        RecentDocumentItem(
            id=doc.id,
            original_filename=doc.original_filename,
            doc_type=doc.doc_type.value,
            client_name=firm_name,
            uploaded_at=doc.uploaded_at,
        )
        for doc, firm_name in docs_result.all()
    ]

    # Recent computations
    comps_result = await db.execute(
        select(TaxComputation, Client.firm_name)
        .outerjoin(Client, TaxComputation.client_id == Client.id)
        .order_by(TaxComputation.created_at.desc())
        .limit(10)
    )
    recent_computations = [
        RecentComputationItem(
            id=comp.id,
            computation_type=(
                comp.computation_json.get("type", "income_tax")
                if comp.computation_json
                else "income_tax"
            ),
            client_name=firm_name,
            result_summary=(
                f"AY {comp.assessment_year} | {comp.regime.value} regime"
                + (f" | Tax: {comp.tax_liability}" if comp.tax_liability else "")
            ),
            created_at=comp.created_at,
        )
        for comp, firm_name in comps_result.all()
    ]

    return RecentActivity(
        recent_queries=recent_queries,
        recent_documents=recent_documents,
        recent_computations=recent_computations,
    )


# --------------------------------------------------------------------------- #
#  GET /compliance-calendar — Upcoming filing dates
# --------------------------------------------------------------------------- #


@router.get(
    "/compliance-calendar",
    summary="Upcoming filing dates across all clients",
)
async def get_compliance_calendar(
    months: int = Query(3, ge=1, le=12, description="Months to look ahead"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Return upcoming statutory filing dates grouped by month.

    Includes GST monthly (1st, 11th, 13th, 20th), TDS quarterly,
    ITR annual, and advance tax dates.
    """
    from app.utils.compliance_calendar import generate_compliance_calendar

    # Generate a reference calendar for a generic entity
    fy_start = date.today().year if date.today().month >= 4 else date.today().year - 1
    fy = f"{fy_start}-{(fy_start + 1) % 100:02d}"
    generic_calendar = generate_compliance_calendar(
        entity_type="private_limited",
        audit_applicable=True,
        fy=fy,
    )

    # Filter to upcoming dates
    cutoff = date.today() + timedelta(days=months * 30)
    upcoming = [
        item for item in generic_calendar
        if date.fromisoformat(item["due_date"]) >= date.today()
        and date.fromisoformat(item["due_date"]) <= cutoff
    ]

    # Also fetch actual compliance tasks from DB
    result = await db.execute(
        select(ComplianceTask, Client.firm_name)
        .join(Client, ComplianceTask.client_id == Client.id)
        .where(
            and_(
                ComplianceTask.due_date >= date.today(),
                ComplianceTask.due_date <= cutoff,
                ComplianceTask.status.notin_([ComplianceStatus.completed]),
            )
        )
        .order_by(ComplianceTask.due_date)
        .limit(100)
    )
    db_tasks = [
        {
            "id": str(task.id),
            "client_name": firm_name,
            "task_type": task.task_type.value,
            "due_date": task.due_date.isoformat(),
            "status": task.status.value,
            "description": task.description or "",
        }
        for task, firm_name in result.all()
    ]

    return {
        "statutory_calendar": upcoming,
        "client_tasks": db_tasks,
    }


# --------------------------------------------------------------------------- #
#  GET /workload — Tasks per associate, completion rates
# --------------------------------------------------------------------------- #


@router.get(
    "/workload",
    summary="Workload distribution across team members",
)
async def get_workload(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return task counts per associate with completion rates.

    Used for the workload chart on the dashboard.
    """
    from app.models.user import User as UserModel

    # Tasks per assignee with status breakdown
    result = await db.execute(
        select(
            UserModel.id,
            UserModel.full_name,
            func.count(ComplianceTask.id).label("total"),
            func.count(ComplianceTask.id).filter(
                ComplianceTask.status == ComplianceStatus.completed
            ).label("completed"),
            func.count(ComplianceTask.id).filter(
                ComplianceTask.status == ComplianceStatus.pending
            ).label("pending"),
            func.count(ComplianceTask.id).filter(
                ComplianceTask.status == ComplianceStatus.in_progress
            ).label("in_progress"),
            func.count(ComplianceTask.id).filter(
                and_(
                    ComplianceTask.due_date < date.today(),
                    ComplianceTask.status.notin_([ComplianceStatus.completed]),
                )
            ).label("overdue"),
        )
        .outerjoin(ComplianceTask, ComplianceTask.assigned_to == UserModel.id)
        .where(UserModel.is_active.is_(True))
        .group_by(UserModel.id, UserModel.full_name)
        .order_by(func.count(ComplianceTask.id).desc())
    )

    team_workload = []
    for row in result.all():
        completion_rate = (
            row.completed / row.total if row.total > 0 else 0.0
        )
        team_workload.append({
            "user_id": str(row.id),
            "name": row.full_name,
            "total_tasks": row.total,
            "completed": row.completed,
            "pending": row.pending,
            "in_progress": row.in_progress,
            "overdue": row.overdue,
            "completion_rate": round(completion_rate, 4),
        })

    return {"team": team_workload}
