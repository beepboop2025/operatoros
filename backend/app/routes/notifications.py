"""Notification routes — unread bell and mark-read."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationResponse

router = APIRouter(tags=["notifications"])


# --------------------------------------------------------------------------- #
#  GET /unread — List unread notifications for the current user
# --------------------------------------------------------------------------- #


@router.get(
    "/unread",
    response_model=list[NotificationResponse],
    summary="List unread notifications",
)
async def list_unread_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationResponse]:
    """Return all unread notifications for the authenticated user, newest first."""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .where(Notification.is_read.is_(False))
        .order_by(Notification.created_at.desc())
    )
    notifications = result.scalars().all()
    return [NotificationResponse.model_validate(n) for n in notifications]


# --------------------------------------------------------------------------- #
#  POST /{notification_id}/mark-read — Mark a notification as read
# --------------------------------------------------------------------------- #


@router.post(
    "/{notification_id}/mark-read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    """Mark a specific notification as read.

    Users may only mark their own notifications.
    """
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()

    if notification is None or notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    await db.flush()

    return NotificationResponse.model_validate(notification)
