"""Draft generation routes — notice responses, client advisories, engagement letters."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.middleware.audit import get_client_ip, log_action
from app.models.client import Client
from app.models.notice import Notice
from app.models.user import User
from app.services.communication_drafter import CommunicationDrafter
from app.services.openrouter import OpenRouterClient

router = APIRouter(tags=["drafts"])


# --------------------------------------------------------------------------- #
#  Service dependency
# --------------------------------------------------------------------------- #

_drafter_singleton: CommunicationDrafter | None = None


def get_drafter() -> CommunicationDrafter:
    """Return the shared CommunicationDrafter instance."""
    global _drafter_singleton
    if _drafter_singleton is None:
        _drafter_singleton = CommunicationDrafter(openrouter=OpenRouterClient())
    return _drafter_singleton


# --------------------------------------------------------------------------- #
#  Request / Response schemas
# --------------------------------------------------------------------------- #


class DraftResponseRequest(BaseModel):
    notice_id: uuid.UUID
    additional_context: Optional[str] = Field(
        None, max_length=4096, description="Extra context for the draft"
    )


class DraftResponseResult(BaseModel):
    notice_id: uuid.UUID
    draft_text: str
    legal_references: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    status: str = "draft_generated"


class AdvisoryRequest(BaseModel):
    client_id: uuid.UUID
    topic: str = Field(..., min_length=1, max_length=512)
    context: Optional[str] = Field(None, max_length=4096)


class AdvisoryResult(BaseModel):
    client_id: uuid.UUID
    topic: str
    advisory_text: str
    references: list[str] = Field(default_factory=list)
    status: str = "draft_generated"


class EngagementLetterRequest(BaseModel):
    client_id: uuid.UUID
    services: list[str] = Field(..., min_length=1, description="List of services to include")
    fee_amount: Optional[str] = Field(None, description="Fee amount or description")
    validity_months: int = Field(12, ge=1, le=60)


class EngagementLetterResult(BaseModel):
    client_id: uuid.UUID
    letter_text: str
    services_included: list[str]
    status: str = "draft_generated"


# --------------------------------------------------------------------------- #
#  POST /response — Draft response to a notice
# --------------------------------------------------------------------------- #


@router.post(
    "/response",
    response_model=DraftResponseResult,
    summary="Generate a draft response to a notice",
)
async def draft_response(
    body: DraftResponseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    drafter: CommunicationDrafter = Depends(get_drafter),
) -> DraftResponseResult:
    """Generate a draft response to an IT/GST notice using the LLM.

    The LLM analyzes the notice content, relevant tax provisions, and any
    additional context to generate a tailored response. If the LLM service is
    unavailable, a 503 is returned so the caller knows drafting failed.
    """

    # Validate notice exists
    result = await db.execute(
        select(Notice)
        .where(Notice.id == body.notice_id)
    )
    notice = result.scalar_one_or_none()
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notice not found",
        )

    client = notice.client
    client_details = (
        f"Client: {client.firm_name}\n"
        f"PAN: {client.pan}\n"
        f"GSTIN: {client.gstin or 'N/A'}\n"
        f"Entity type: {client.entity_type.value}"
    )
    notice_summary = (
        f"Notice type: {notice.notice_type.value}\n"
        f"Notice date: {notice.notice_date.isoformat()}\n"
        f"Response deadline: {notice.response_deadline.isoformat() if notice.response_deadline else 'N/A'}\n"
        f"Summary: {notice.summary or 'N/A'}"
    )
    legal_position = body.additional_context or "No additional legal position provided."

    try:
        draft_text = await drafter.draft_notice_response(
            notice_summary=notice_summary,
            client_details=client_details,
            legal_position=legal_position,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to generate draft response at this time: {exc}",
        ) from exc

    await log_action(
        db,
        user_id=current_user.id,
        action="draft.notice_response",
        entity_type="notice",
        entity_id=notice.id,
        ip_address=get_client_ip(request),
    )

    return DraftResponseResult(
        notice_id=notice.id,
        draft_text=draft_text,
        legal_references=[],
        recommended_actions=[],
    )


# --------------------------------------------------------------------------- #
#  POST /advisory — Client advisory
# --------------------------------------------------------------------------- #


@router.post(
    "/advisory",
    response_model=AdvisoryResult,
    summary="Generate a client advisory",
)
async def draft_advisory(
    body: AdvisoryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    drafter: CommunicationDrafter = Depends(get_drafter),
) -> AdvisoryResult:
    """Generate a draft advisory for a client on a specific topic using the LLM."""

    # Validate client
    result = await db.execute(select(Client).where(Client.id == body.client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    details = body.context or "No additional details provided."

    try:
        advisory_text = await drafter.draft_advisory(
            topic=body.topic,
            client_name=client.firm_name,
            details=details,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to generate advisory at this time: {exc}",
        ) from exc

    await log_action(
        db,
        user_id=current_user.id,
        action="draft.advisory",
        entity_type="client",
        entity_id=client.id,
        details={"topic": body.topic},
        ip_address=get_client_ip(request),
    )

    return AdvisoryResult(
        client_id=client.id,
        topic=body.topic,
        advisory_text=advisory_text,
        references=[],
    )


# --------------------------------------------------------------------------- #
#  POST /engagement-letter — Engagement letter template
# --------------------------------------------------------------------------- #


@router.post(
    "/engagement-letter",
    response_model=EngagementLetterResult,
    summary="Generate an engagement letter",
)
async def draft_engagement_letter(
    body: EngagementLetterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    drafter: CommunicationDrafter = Depends(get_drafter),
) -> EngagementLetterResult:
    """Generate an engagement letter for a client using the LLM.

    Produces a customizable letter covering the specified services,
    fees, and validity period.
    """

    # Validate client
    result = await db.execute(select(Client).where(Client.id == body.client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    fees = body.fee_amount or "To be mutually agreed upon"

    try:
        letter_text = await drafter.draft_engagement_letter(
            client_name=client.firm_name,
            services=body.services,
            fees=fees,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to generate engagement letter at this time: {exc}",
        ) from exc

    await log_action(
        db,
        user_id=current_user.id,
        action="draft.engagement_letter",
        entity_type="client",
        entity_id=client.id,
        details={"services": body.services},
        ip_address=get_client_ip(request),
    )

    return EngagementLetterResult(
        client_id=client.id,
        letter_text=letter_text,
        services_included=body.services,
    )
