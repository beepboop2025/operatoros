"""Waitlist routes — public early-access capture from the landing page.

POST is intentionally unauthenticated (it is the public "Request access" form) and
idempotent on email, so a repeat signup returns 200 instead of a unique-violation 500.
GET is protected (admin bearer token or ingest API key) so leads aren't world-readable.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_api_key_or_admin
from app.models.waitlist import WaitlistEntry
from app.schemas.pagination import paginated_response
from app.schemas.waitlist import WaitlistCreateRequest, WaitlistResponse
from app.services.notification_service import (
    PERSONA_LABELS,
    enqueue_signup_delivery,
    notify_staff,
)

router = APIRouter(tags=["waitlist"])


@router.post(
    "/",
    response_model=WaitlistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join the early-access waitlist (public)",
)
async def join_waitlist(
    body: WaitlistCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> WaitlistResponse:
    """Capture an early-access signup. Idempotent on email."""
    email = body.email.lower().strip()

    existing = await db.scalar(
        select(WaitlistEntry).where(WaitlistEntry.email == email)
    )
    if existing is not None:
        # Already on the list — treat as success, refresh any newly provided detail.
        existing.name = body.name or existing.name
        existing.persona = body.persona or existing.persona
        existing.country = body.country or existing.country
        await db.flush()
        return WaitlistResponse.model_validate(existing)

    entry = WaitlistEntry(
        email=email,
        name=body.name,
        persona=body.persona,
        country=body.country,
        source=body.source or "landing",
    )
    db.add(entry)
    await db.flush()

    # Best-effort: ping staff in-app so leads are seen in real time. Isolated in its own
    # transaction inside notify_staff — it can never roll back this signup.
    detail = ", ".join(
        part
        for part in (PERSONA_LABELS.get(entry.persona or "", entry.persona), entry.country)
        if part
    )
    await notify_staff(
        title="New early-access signup",
        message=f"{entry.name or entry.email} joined the waitlist"
        + (f" — {detail}" if detail else "")
        + (f" ({entry.email})" if entry.name else ""),
        notification_type="waitlist_signup",
        entity_type="waitlist_entry",
        entity_id=entry.id,
    )

    # External delivery (email / Telegram) runs AFTER the response is sent, so a slow or
    # down broker never delays the signup. The enqueue itself is broker-failure-safe.
    background_tasks.add_task(
        enqueue_signup_delivery,
        email=entry.email,
        name=entry.name,
        persona=entry.persona,
        country=entry.country,
        source=entry.source,
    )

    return WaitlistResponse.model_validate(entry)


@router.get(
    "/",
    summary="List waitlist signups (admin / API key only)",
)
async def list_waitlist(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_api_key_or_admin),
) -> dict:
    """Return a paginated list of waitlist signups, newest first."""
    base_query = select(WaitlistEntry).order_by(WaitlistEntry.created_at.desc())
    total = (await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )).scalar_one()

    offset = (page - 1) * size
    result = await db.execute(base_query.offset(offset).limit(size))
    items = [WaitlistResponse.model_validate(e) for e in result.scalars().all()]
    return paginated_response(items, total, page, size)


def _csv_safe(value: object) -> str:
    """Neutralise CSV formula injection.

    Waitlist fields are public, attacker-supplied. A value beginning with =, +, -, @
    (or a control char) is executed as a formula when the CSV is opened in Excel/Sheets,
    so we prefix such values with a single quote to force them to be treated as text.
    """
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


@router.get(
    "/export.csv",
    summary="Export all waitlist signups as CSV (admin / API key only)",
)
async def export_waitlist_csv(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_api_key_or_admin),
) -> StreamingResponse:
    """Stream every waitlist signup as a CSV download, oldest first."""
    result = await db.execute(
        select(WaitlistEntry).order_by(WaitlistEntry.created_at.asc())
    )
    entries = result.scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["email", "name", "persona", "country", "source", "created_at"])
    for e in entries:
        writer.writerow([
            _csv_safe(e.email),
            _csv_safe(e.name),
            _csv_safe(PERSONA_LABELS.get(e.persona or "", e.persona)),
            _csv_safe(e.country),
            _csv_safe(e.source),
            e.created_at.isoformat() if e.created_at else "",
        ])
    buffer.seek(0)

    filename = f"operatoros-waitlist-{datetime.now(timezone.utc):%Y%m%d}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
