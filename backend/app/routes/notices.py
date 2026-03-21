"""Notice routes — upload, classify, track, and respond to IT/GST notices."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.middleware.audit import get_client_ip, log_action
from app.models.client import Client
from app.models.notice import Notice, NoticeStatus, NoticeType as ModelNoticeType
from app.models.user import User
from app.schemas.notice import (
    NoticeProcessRequest,
    NoticeResponse,
    NoticeResponseDraft,
    NoticeType,
)
from app.schemas.pagination import paginated_response

router = APIRouter(tags=["notices"])


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #


def _notice_to_response(notice: Notice) -> NoticeResponse:
    """Map a Notice ORM instance to the response schema."""
    return NoticeResponse(
        id=notice.id,
        client_id=notice.client_id,
        client_name=(
            notice.client.firm_name
            if hasattr(notice, "client") and notice.client
            else None
        ),
        notice_type=notice.notice_type.value,
        issue_date=notice.notice_date,
        response_deadline=notice.response_deadline,
        status=notice.status.value,
        description=notice.summary,
        assigned_to=notice.assigned_to,
        document_id=notice.document_id,
        created_at=notice.created_at,
        updated_at=notice.updated_at,
    )


# --------------------------------------------------------------------------- #
#  POST /process — Upload and classify a notice
# --------------------------------------------------------------------------- #


@router.post(
    "/process",
    response_model=NoticeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and classify a notice",
)
async def process_notice(
    body: NoticeProcessRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoticeResponse:
    """Create a notice record and classify it.

    If a document_id is provided, the notice is linked to an already-uploaded
    document. The notice_type can be auto-detected from the document content
    in a future iteration; for now it defaults to 'other' if not specified.
    """

    # Validate client
    result = await db.execute(select(Client).where(Client.id == body.client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    notice_type = ModelNoticeType.other
    if body.notice_type is not None:
        try:
            notice_type = ModelNoticeType(body.notice_type.value)
        except ValueError:
            notice_type = ModelNoticeType.other

    notice = Notice(
        client_id=body.client_id,
        notice_type=notice_type,
        notice_date=date.today(),
        response_deadline=None,  # Will be set during detailed processing
        document_id=body.document_id,
        summary=f"Notice of type {notice_type.value} received for processing.",
        status=NoticeStatus.received,
        assigned_to=current_user.id,
    )
    db.add(notice)
    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="notice.process",
        entity_type="notice",
        entity_id=notice.id,
        details={
            "client_id": str(body.client_id),
            "notice_type": notice_type.value,
        },
        ip_address=get_client_ip(request),
    )

    # Reload with relationships
    result = await db.execute(
        select(Notice)
        .options(selectinload(Notice.client))
        .where(Notice.id == notice.id)
    )
    notice = result.scalar_one()

    return _notice_to_response(notice)


# --------------------------------------------------------------------------- #
#  GET / — List notices
# --------------------------------------------------------------------------- #


@router.get(
    "/",
    summary="List all notices with filters",
)
async def list_notices(
    client_id: Optional[uuid.UUID] = Query(None, description="Filter by client"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    notice_type: Optional[str] = Query(None, description="Filter by notice type"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return a paginated list of notices with optional filters."""

    base_query = (
        select(Notice)
        .options(selectinload(Notice.client))
        .order_by(Notice.created_at.desc())
    )

    if client_id is not None:
        base_query = base_query.where(Notice.client_id == client_id)

    if status_filter is not None:
        try:
            ns = NoticeStatus(status_filter)
            base_query = base_query.where(Notice.status == ns)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {[s.value for s in NoticeStatus]}",
            )

    if notice_type is not None:
        try:
            nt = ModelNoticeType(notice_type)
            base_query = base_query.where(Notice.notice_type == nt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid notice_type. Must be one of: {[t.value for t in ModelNoticeType]}",
            )

    # Total count
    count_q = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    offset = (page - 1) * size
    paged_query = base_query.offset(offset).limit(size)

    result = await db.execute(paged_query)
    notices = result.scalars().all()

    items = [_notice_to_response(n) for n in notices]
    return paginated_response(items, total, page, size)


# --------------------------------------------------------------------------- #
#  GET /{notice_id} — Get notice details
# --------------------------------------------------------------------------- #


@router.get(
    "/{notice_id}",
    response_model=NoticeResponse,
    summary="Get notice details",
)
async def get_notice(
    notice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoticeResponse:
    """Retrieve full details for a specific notice."""

    result = await db.execute(
        select(Notice)
        .options(selectinload(Notice.client))
        .where(Notice.id == notice_id)
    )
    notice = result.scalar_one_or_none()

    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notice not found",
        )

    return _notice_to_response(notice)


# --------------------------------------------------------------------------- #
#  PUT /{notice_id} — Update notice
# --------------------------------------------------------------------------- #


class NoticeUpdateRequest(BaseModel):
    status: Optional[str] = None
    response_deadline: Optional[date] = None
    assigned_to: Optional[uuid.UUID] = None
    summary: Optional[str] = None


@router.put(
    "/{notice_id}",
    response_model=NoticeResponse,
    summary="Update notice status or details",
)
async def update_notice(
    notice_id: uuid.UUID,
    body: NoticeUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoticeResponse:
    """Update an existing notice's status, deadline, assignee, or summary."""

    result = await db.execute(
        select(Notice)
        .options(selectinload(Notice.client))
        .where(Notice.id == notice_id)
    )
    notice = result.scalar_one_or_none()

    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notice not found",
        )

    updated_fields = []

    if body.status is not None:
        try:
            notice.status = NoticeStatus(body.status)
            updated_fields.append("status")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {[s.value for s in NoticeStatus]}",
            )

    if body.response_deadline is not None:
        notice.response_deadline = body.response_deadline
        updated_fields.append("response_deadline")

    if body.assigned_to is not None:
        # Validate assignee
        assignee_result = await db.execute(
            select(User).where(User.id == body.assigned_to)
        )
        if assignee_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )
        notice.assigned_to = body.assigned_to
        updated_fields.append("assigned_to")

    if body.summary is not None:
        notice.summary = body.summary
        updated_fields.append("summary")

    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="notice.update",
        entity_type="notice",
        entity_id=notice.id,
        details={"updated_fields": updated_fields},
        ip_address=get_client_ip(request),
    )

    return _notice_to_response(notice)


# --------------------------------------------------------------------------- #
#  POST /{notice_id}/draft-response — Generate draft response
# --------------------------------------------------------------------------- #


@router.post(
    "/{notice_id}/draft-response",
    response_model=NoticeResponseDraft,
    summary="Generate a draft response for a notice",
)
async def draft_notice_response(
    notice_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoticeResponseDraft:
    """Generate a draft response for a notice.

    **Note:** This is currently a placeholder. In production, this endpoint will
    use the LLM to analyze the notice content, applicable laws, and client
    history to generate a contextually appropriate response draft.
    """

    result = await db.execute(
        select(Notice)
        .options(selectinload(Notice.client))
        .where(Notice.id == notice_id)
    )
    notice = result.scalar_one_or_none()

    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notice not found",
        )

    # Placeholder draft
    draft_text = (
        f"Draft response for {notice.notice_type.value} notice.\n\n"
        f"Respected Sir/Madam,\n\n"
        f"This is in reference to the notice dated {notice.notice_date.isoformat()} "
        f"issued to our client. We are in the process of reviewing the notice and "
        f"compiling the necessary documentation to provide a comprehensive response.\n\n"
        f"We request you to kindly allow us the time as per the statutory provisions "
        f"to submit our detailed reply.\n\n"
        f"Yours faithfully,\n"
        f"[Authorized Representative]"
    )

    # Update notice status
    notice.status = NoticeStatus.response_drafted
    notice.response_draft = draft_text
    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="notice.draft_response",
        entity_type="notice",
        entity_id=notice.id,
        ip_address=get_client_ip(request),
    )

    return NoticeResponseDraft(
        notice_id=notice.id,
        draft_text=draft_text,
        legal_references=[
            "Section 143(1) of the Income Tax Act, 1961",
            "Rule 127 of the Income Tax Rules, 1962",
        ],
        recommended_actions=[
            "Review the discrepancies highlighted in the notice",
            "Gather supporting documents (Form 16, Form 26AS, AIS)",
            "Prepare a detailed reconciliation statement",
            "File response before the deadline",
        ],
    )
