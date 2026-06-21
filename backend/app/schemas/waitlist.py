"""Pydantic schemas for the public waitlist / early-access capture."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class WaitlistCreateRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(default=None, max_length=256)
    persona: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Self-described segment: nri | returning | ca_firm | founder | other",
    )
    country: Optional[str] = Field(default=None, max_length=128)
    source: Optional[str] = Field(default=None, max_length=128)


class WaitlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: Optional[str] = None
    persona: Optional[str] = None
    country: Optional[str] = None
    source: Optional[str] = None
    created_at: datetime
