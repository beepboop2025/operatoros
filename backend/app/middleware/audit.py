"""
Audit logging — request-level middleware + action-level helper.

The AuditMiddleware automatically logs every API request (who, what, when,
from where, duration).  The ``log_action`` helper is called from route
handlers to record domain-level actions (e.g. document.upload).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger("operatoros.audit")

# ── Sensitive field sanitisation ─────────────────────────────────────────────

_SENSITIVE_FIELDS = frozenset({
    "password", "hashed_password", "secret", "token", "access_token",
    "refresh_token", "api_key", "secret_key", "authorization",
    "credit_card", "cvv", "ssn", "aadhaar",
})


def _sanitize_body(body: dict | None) -> dict | None:
    """Strip passwords and sensitive fields from request bodies."""
    if body is None:
        return None
    sanitized = {}
    for key, value in body.items():
        if key.lower() in _SENSITIVE_FIELDS:
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_body(value)
        else:
            sanitized[key] = value
    return sanitized


# ── Endpoints to skip (noisy health / docs endpoints) ───────────────────────

_SKIP_PATHS = frozenset({
    "/api/health", "/docs", "/openapi.json", "/redoc", "/",
    "/favicon.ico",
})


# ── Request-level audit middleware ───────────────────────────────────────────

class AuditMiddleware(BaseHTTPMiddleware):
    """Automatically log every API request to the audit_logs table.

    Extracts user_id from the JWT token in the Authorization header
    (without enforcing authentication — unauthenticated requests are
    logged with user_id=None).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip noisy endpoints
        if request.url.path in _SKIP_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        start_time = time.monotonic()

        # Extract user_id from JWT (best-effort, no auth enforcement)
        user_id = self._extract_user_id(request)

        # Read request body for non-GET, non-file requests
        request_body = None
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    raw = await request.body()
                    body_dict = json.loads(raw) if raw else None
                    request_body = _sanitize_body(body_dict)
                    # Truncate large bodies
                    body_str = json.dumps(request_body) if request_body else ""
                    if len(body_str) > 4096:
                        request_body = {"_truncated": True, "size": len(body_str)}
                except Exception:
                    request_body = None

        # Process the request
        response = await call_next(request)

        duration_ms = (time.monotonic() - start_time) * 1000

        # Write audit log asynchronously (fire-and-forget, never block response)
        try:
            await self._write_audit_log(
                user_id=user_id,
                endpoint=request.url.path,
                method=request.method,
                request_body=request_body,
                response_status=response.status_code,
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("user-agent", "")[:512],
                duration_ms=round(duration_ms, 2),
            )
        except Exception:
            logger.exception("Failed to write request audit log")

        return response

    @staticmethod
    def _extract_user_id(request: Request) -> UUID | None:
        """Best-effort JWT user_id extraction without auth enforcement."""
        try:
            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                return None
            token = auth_header[7:]
            from app.middleware.auth import verify_token
            payload = verify_token(token)
            return payload.sub
        except Exception:
            return None

    @staticmethod
    async def _write_audit_log(
        *,
        user_id: UUID | None,
        endpoint: str,
        method: str,
        request_body: dict | None,
        response_status: int,
        ip_address: str | None,
        user_agent: str,
        duration_ms: float,
    ) -> None:
        """Write the request audit log to the database."""
        from app.database import async_session_factory

        entry = AuditLog(
            user_id=user_id,
            action=f"request.{method.lower()}",
            entity_type="api_request",
            endpoint=endpoint,
            method=method,
            request_body=request_body,
            response_status=response_status,
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
        )

        try:
            async with async_session_factory() as session:
                session.add(entry)
                await session.commit()
        except Exception:
            logger.exception("Failed to persist request audit log for %s %s", method, endpoint)


# ── Action-level audit helper (called from routes) ───────────────────────────


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
    Persist an audit-log entry for a domain action.

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


_TRUSTED_PROXIES = {"127.0.0.1", "::1", "localhost"}


def get_client_ip(request) -> str | None:
    """
    Extract the real client IP, respecting ``X-Forwarded-For`` only when the
    request comes from a trusted proxy IP.  Otherwise use request.client.host
    to prevent IP spoofing.
    """
    client_host = request.client.host if request.client else None

    # Only trust X-Forwarded-For when the immediate connection is from a known proxy
    if client_host in _TRUSTED_PROXIES:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first (leftmost) IP in the chain
            return forwarded.split(",")[0].strip()

    return client_host
