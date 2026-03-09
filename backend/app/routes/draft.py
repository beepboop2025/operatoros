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

router = APIRouter(tags=["drafts"])


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
) -> DraftResponseResult:
    """Generate a draft response to an IT/GST notice.

    **Note:** This is a placeholder implementation. In production, the LLM will
    analyze the notice content, relevant tax provisions, and client-specific
    context to generate a tailored response.
    """

    # Validate notice exists
    result = await db.execute(select(Notice).where(Notice.id == body.notice_id))
    notice = result.scalar_one_or_none()
    if notice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notice not found",
        )

    draft_text = (
        f"DRAFT RESPONSE — {notice.notice_type.value.upper()}\n"
        f"{'=' * 60}\n\n"
        f"To,\nThe Assessing Officer / Proper Officer,\n\n"
        f"Subject: Response to notice dated {notice.notice_date.isoformat()}\n\n"
        f"Respected Sir/Madam,\n\n"
        f"We write this letter on behalf of our client in response to the "
        f"above-referenced notice. After careful review of the notice and "
        f"supporting records, we submit the following:\n\n"
        f"1. We acknowledge receipt of the notice.\n"
        f"2. We have reviewed the points raised therein.\n"
        f"3. Our detailed submissions with supporting documents are enclosed.\n\n"
        f"We request your good self to consider our submissions and dispose of "
        f"the matter accordingly.\n\n"
        f"Yours faithfully,\n"
        f"[Authorized Representative]\n"
        f"[Firm Name]\n"
        f"[UDIN: ____________]"
    )

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
        legal_references=[
            "Relevant sections of the Income Tax Act, 1961",
            "Central Goods and Services Tax Act, 2017 (if applicable)",
        ],
        recommended_actions=[
            "Review and customize the draft before filing",
            "Attach supporting documents",
            "Generate UDIN from ICAI portal before submission",
        ],
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
) -> AdvisoryResult:
    """Generate a draft advisory for a client on a specific topic.

    **Note:** This is a placeholder implementation. In production, the LLM will
    synthesize relevant tax laws, recent amendments, circulars, and the client's
    specific situation to produce actionable advisory.
    """

    # Validate client
    result = await db.execute(select(Client).where(Client.id == body.client_id))
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    advisory_text = (
        f"CLIENT ADVISORY\n"
        f"{'=' * 60}\n\n"
        f"Client: {client.firm_name}\n"
        f"Topic: {body.topic}\n"
        f"Date: {__import__('datetime').date.today().isoformat()}\n\n"
        f"Dear {client.contact_person},\n\n"
        f"This advisory is prepared in response to your query regarding "
        f"'{body.topic}'.\n\n"
        f"Based on our analysis of the applicable provisions and your specific "
        f"circumstances, we advise as follows:\n\n"
        f"[Advisory content will be generated by the AI system based on:\n"
        f" - Applicable tax laws and recent amendments\n"
        f" - CBDT/CBIC circulars and notifications\n"
        f" - Relevant judicial precedents\n"
        f" - Your specific financial situation]\n\n"
        f"Please note that this advisory is based on the current understanding "
        f"of applicable laws and is subject to change based on future amendments "
        f"or judicial interpretations.\n\n"
        f"For any clarification, please feel free to reach out.\n\n"
        f"Regards,\n"
        f"{current_user.full_name}"
    )

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
        references=[
            "Income Tax Act, 1961",
            "Central Goods and Services Tax Act, 2017",
            "Companies Act, 2013",
        ],
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
) -> EngagementLetterResult:
    """Generate an engagement letter template for a client.

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

    import datetime

    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=body.validity_months * 30)

    services_text = "\n".join(
        f"   {i + 1}. {service}" for i, service in enumerate(body.services)
    )

    fee_clause = (
        f"The professional fees for the above services shall be {body.fee_amount}."
        if body.fee_amount
        else "The professional fees for the above services shall be mutually agreed upon."
    )

    letter_text = (
        f"ENGAGEMENT LETTER\n"
        f"{'=' * 60}\n\n"
        f"Date: {today.isoformat()}\n\n"
        f"To,\n"
        f"{client.contact_person}\n"
        f"{client.firm_name}\n"
        f"PAN: {client.pan}\n\n"
        f"Dear {client.contact_person},\n\n"
        f"We are pleased to confirm our engagement as your professional advisors. "
        f"This letter sets out the terms of our engagement.\n\n"
        f"SCOPE OF SERVICES\n"
        f"{'-' * 40}\n"
        f"{services_text}\n\n"
        f"PROFESSIONAL FEES\n"
        f"{'-' * 40}\n"
        f"{fee_clause}\n"
        f"Payment terms: Within 15 days of invoice date.\n"
        f"GST will be charged as applicable.\n\n"
        f"PERIOD OF ENGAGEMENT\n"
        f"{'-' * 40}\n"
        f"This engagement shall be effective from {today.isoformat()} to "
        f"{end_date.isoformat()} ({body.validity_months} months).\n\n"
        f"MUTUAL OBLIGATIONS\n"
        f"{'-' * 40}\n"
        f"- We shall perform our duties with due professional care and diligence.\n"
        f"- The client shall provide all necessary information and documents in a timely manner.\n"
        f"- All information shared shall be treated as strictly confidential.\n\n"
        f"LIMITATION OF LIABILITY\n"
        f"{'-' * 40}\n"
        f"Our liability shall be limited to the fees received for the specific "
        f"engagement in question.\n\n"
        f"Please sign and return a copy of this letter to confirm your agreement "
        f"with the above terms.\n\n"
        f"Yours faithfully,\n\n"
        f"________________________\n"
        f"{current_user.full_name}\n"
        f"[Firm Name]\n"
        f"[Membership No.]\n\n"
        f"ACCEPTED AND AGREED:\n\n"
        f"________________________\n"
        f"{client.contact_person}\n"
        f"{client.firm_name}\n"
        f"Date: ________________"
    )

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
