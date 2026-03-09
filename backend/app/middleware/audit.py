"""
Audit logging helper — records significant actions to the ``audit_logs`` table.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger("operatoros.audit")


async def log_action(
    db: AsyncSession,
    *,
    user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    details: Dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """
    Persist an audit-log entry.

    This is designed to be called from route handlers *after* the primary
    operation succeeds.  It commits its own nested transaction so that
    audit failures do not roll back the parent operation.

    Parameters
    ----------
    db : AsyncSession
        The active database session.
    user_id : UUID
        The user performing the action.
    action : str
        Dot-delimited action identifier, e.g. ``"document.upload"``.
    entity_type : str
        The domain entity type, e.g. ``"document"``, ``"computation"``.
    entity_id : UUID | None
        Primary key of the affected entity (if applicable).
    details : dict | None
        Arbitrary JSON payload with extra context.
    ip_address : str | None
        Client IP address.

    Returns
    -------
    AuditLog
        The persisted audit record.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )

    try:
        async with db.begin_nested():
            db.add(entry)
        logger.debug(
            "Audit: user=%s action=%s entity=%s/%s",
            user_id,
            action,
            entity_type,
            entity_id,
        )
    except Exception:
        # Never let audit logging break the calling request
        logger.exception(
            "Failed to write audit log: user=%s action=%s", user_id, action
        )

    return entry


def get_client_ip(request) -> str | None:
    """
    Extract the real client IP, respecting ``X-Forwarded-For`` when behind
    a reverse proxy.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first (leftmost) IP in the chain
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
