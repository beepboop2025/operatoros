"""Audit log routes — admin-only access to the full audit trail."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(tags=["audit"])


@router.get(
    "/",
    summary="List audit logs (admin only)",
    dependencies=[Depends(require_role(["admin"]))],
)
async def list_audit_logs(
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user"),
    endpoint: Optional[str] = Query(None, description="Filter by endpoint"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    action: Optional[str] = Query(None, description="Filter by action"),
    status_code: Optional[int] = Query(None, description="Filter by response status"),
    date_from: Optional[date] = Query(None, description="Start date (inclusive)"),
    date_to: Optional[date] = Query(None, description="End date (inclusive)"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return paginated audit logs with flexible filtering.

    Only users with the ``admin`` role can access this endpoint.
    """
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())

    filters = []
    if user_id is not None:
        filters.append(AuditLog.user_id == user_id)
    if endpoint is not None:
        filters.append(AuditLog.endpoint.ilike(f"%{endpoint}%"))
    if method is not None:
        filters.append(AuditLog.method == method.upper())
    if action is not None:
        filters.append(AuditLog.action.ilike(f"%{action}%"))
    if status_code is not None:
        filters.append(AuditLog.response_status == status_code)
    if date_from is not None:
        filters.append(
            AuditLog.timestamp >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        )
    if date_to is not None:
        next_day = datetime(date_to.year, date_to.month, date_to.day, tzinfo=timezone.utc)
        from datetime import timedelta
        filters.append(AuditLog.timestamp < next_day + timedelta(days=1))

    if filters:
        query = query.where(and_(*filters))

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginate
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)
    result = await db.execute(query)
    logs = result.scalars().all()

    items = [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id) if log.entity_id else None,
            "endpoint": log.endpoint,
            "method": log.method,
            "request_body": log.request_body,
            "response_status": log.response_status,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "duration_ms": log.duration_ms,
            "details": log.details,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": size,
    }
