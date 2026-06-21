"""Notification service — create in-app alerts (the bell) and fan events out to staff.

This is the shared entry point for writing ``Notification`` rows. ``create_notification``
adds a row to a caller-owned session (atomic with the caller's work); ``notify_staff``
runs in its OWN transaction so a notification failure can never roll back the event that
triggered it — important for the public waitlist, where capturing the lead is paramount.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.notification import Notification
from app.models.user import User, UserRole

logger = logging.getLogger("operatoros.notifications")

# Who counts as "staff" for broadcast alerts.
STAFF_ROLES = (UserRole.admin, UserRole.partner)

# Human-readable labels for the self-described waitlist persona codes.
PERSONA_LABELS = {
    "nri": "NRI",
    "returning": "Returning to India",
    "ca_firm": "CA / Tax firm",
    "founder": "Founder / Business",
    "other": "Other",
}


def enqueue_signup_delivery(
    *,
    email: str,
    name: Optional[str] = None,
    persona: Optional[str] = None,
    country: Optional[str] = None,
    source: Optional[str] = None,
) -> bool:
    """Enqueue the external (email/Telegram) delivery Celery task.

    Returns False — and never raises — if the broker is unreachable, so a public
    signup is never blocked or failed by a messaging-infrastructure problem.
    Intended to be run via FastAPI BackgroundTasks (after the response is sent).
    """
    try:
        from app.tasks.notification_tasks import deliver_signup_notification

        deliver_signup_notification.delay(
            email=email, name=name, persona=persona, country=country, source=source
        )
        return True
    except Exception as exc:  # broker down, serialization error, etc.
        logger.warning("Could not enqueue signup delivery for %s: %s", email, exc)
        return False


def create_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    message: str,
    notification_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
) -> Notification:
    """Add a single in-app notification to *session* (caller commits)."""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    session.add(notification)
    return notification


async def notify_staff(
    *,
    title: str,
    message: str,
    notification_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
) -> int:
    """Best-effort: create an in-app notification for every active admin/partner.

    Runs in its own session/transaction and swallows errors (logging them), so callers
    in a public request path can fire-and-forget without risking their own transaction.
    Returns the number of notifications created (0 if none / on failure).
    """
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(User)
                .where(User.role.in_(STAFF_ROLES))
                .where(User.is_active.is_(True))
            )
            staff = result.scalars().all()
            for user in staff:
                create_notification(
                    session,
                    user_id=user.id,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
            await session.commit()
            if not staff:
                logger.info("notify_staff: no active staff to notify (%s)", notification_type)
            return len(staff)
    except Exception as exc:  # never let a notification failure escape into the caller
        logger.warning("notify_staff failed (%s): %s", notification_type, exc)
        return 0
