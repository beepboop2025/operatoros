"""Firm management routes — multi-tenant CA firm administration."""

from __future__ import annotations

import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.middleware.audit import get_client_ip, log_action
from app.models.firm import Firm
from app.models.user import User

router = APIRouter(tags=["firms"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class FirmCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=512)
    slug: Optional[str] = Field(None, min_length=1, max_length=128)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)


class FirmUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=512)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    logo_url: Optional[str] = None


class FirmResponse(BaseModel):
    id: str
    name: str
    slug: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=256)
    role: str = Field("associate", pattern=r"^(admin|partner|associate|client_view)$")


# ── Helpers ──────────────────────────────────────────────────────────────────


def _slugify(name: str) -> str:
    """Convert firm name to URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug[:128]


def _firm_to_response(firm: Firm) -> FirmResponse:
    return FirmResponse(
        id=str(firm.id),
        name=firm.name,
        slug=firm.slug,
        address=firm.address,
        phone=firm.phone,
        email=firm.email,
        gstin=firm.gstin,
        logo_url=firm.logo_url,
        is_active=firm.is_active,
        created_at=firm.created_at.isoformat() if firm.created_at else "",
        updated_at=firm.updated_at.isoformat() if firm.updated_at else "",
    )


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=FirmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new firm (admin only)",
)
async def create_firm(
    body: FirmCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
) -> FirmResponse:
    """Create a new CA firm for multi-tenant operation."""
    slug = body.slug or _slugify(body.name)

    # Check unique slug
    existing = await db.execute(select(Firm).where(Firm.slug == slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A firm with this slug already exists",
        )

    firm = Firm(
        name=body.name,
        slug=slug,
        address=body.address,
        phone=body.phone,
        email=body.email,
        gstin=body.gstin,
    )
    db.add(firm)
    await db.flush()

    # Assign the creating user to this firm
    current_user.firm_id = firm.id
    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="firm.create",
        entity_type="firm",
        entity_id=firm.id,
        details={"name": body.name, "slug": slug},
        ip_address=get_client_ip(request),
    )

    return _firm_to_response(firm)


@router.get(
    "/",
    response_model=list[FirmResponse],
    summary="List all firms (admin only)",
)
async def list_firms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
) -> list[FirmResponse]:
    """List all registered firms."""
    result = await db.execute(
        select(Firm).where(Firm.is_active.is_(True)).order_by(Firm.name)
    )
    firms = result.scalars().all()
    return [_firm_to_response(f) for f in firms]


@router.get(
    "/{firm_id}",
    response_model=FirmResponse,
    summary="Get firm details",
)
async def get_firm(
    firm_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FirmResponse:
    """Get details for a specific firm."""
    result = await db.execute(select(Firm).where(Firm.id == firm_id))
    firm = result.scalar_one_or_none()
    if firm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firm not found")
    return _firm_to_response(firm)


@router.put(
    "/{firm_id}",
    response_model=FirmResponse,
    summary="Update firm details",
)
async def update_firm(
    firm_id: uuid.UUID,
    body: FirmUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "partner"])),
) -> FirmResponse:
    """Update firm details. Only admin and partner roles."""
    result = await db.execute(select(Firm).where(Firm.id == firm_id))
    firm = result.scalar_one_or_none()
    if firm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firm not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(firm, field, value)

    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="firm.update",
        entity_type="firm",
        entity_id=firm.id,
        details={"updated_fields": list(update_data.keys())},
        ip_address=get_client_ip(request),
    )

    return _firm_to_response(firm)


@router.post(
    "/{firm_id}/invite",
    summary="Invite a user to the firm",
    status_code=status.HTTP_201_CREATED,
)
async def invite_user_to_firm(
    firm_id: uuid.UUID,
    body: InviteUserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "partner"])),
) -> dict:
    """Invite a new user to a firm. Creates the user account with a temporary password."""
    # Verify firm exists
    firm_result = await db.execute(select(Firm).where(Firm.id == firm_id))
    firm = firm_result.scalar_one_or_none()
    if firm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firm not found")

    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # Create user with temporary password
    from app.middleware.auth import hash_password
    import secrets

    temp_password = secrets.token_urlsafe(12)
    from app.models.user import UserRole

    user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(temp_password),
        role=UserRole(body.role),
        firm_id=firm_id,
    )
    db.add(user)
    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="firm.invite_user",
        entity_type="user",
        entity_id=user.id,
        details={
            "firm_id": str(firm_id),
            "email": body.email,
            "role": body.role,
        },
        ip_address=get_client_ip(request),
    )

    return {
        "user_id": str(user.id),
        "email": body.email,
        "role": body.role,
        "firm_id": str(firm_id),
        "temporary_password": temp_password,
        "message": "User created. Please share the temporary password securely.",
    }
