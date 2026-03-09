"""Authentication schemas — login, token, and token payload."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserResponseNested(BaseModel):
    """Minimal user info embedded in token response (avoids circular import)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponseNested


class TokenPayload(BaseModel):
    """Decoded JWT claims."""

    sub: UUID
    role: str
    exp: datetime
