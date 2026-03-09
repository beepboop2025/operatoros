"""Client schemas — firm/entity management."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class EntityType(str, Enum):
    individual = "individual"
    huf = "huf"
    partnership = "partnership"
    llp = "llp"
    private_limited = "private_limited"
    public_limited = "public_limited"
    trust = "trust"
    society = "society"
    aop = "aop"
    boi = "boi"


class ComplianceStats(BaseModel):
    """Roll-up compliance stats embedded in client responses."""

    total_tasks: int = 0
    completed_tasks: int = 0
    overdue_tasks: int = 0
    pending_tasks: int = 0


# ---------- Validators ----------

def _validate_pan(v: str) -> str:
    """PAN must be exactly 10 alphanumeric chars in pattern: AAAAA9999A."""
    import re

    v = v.strip().upper()
    if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", v):
        raise ValueError("Invalid PAN format — expected AAAAA9999A")
    return v


def _validate_gstin(v: Optional[str]) -> Optional[str]:
    """GSTIN is 15 chars: 2-digit state code + PAN + 1 entity + 1 'Z' + 1 check."""
    import re

    if v is None:
        return v
    v = v.strip().upper()
    if not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]", v):
        raise ValueError("Invalid GSTIN format — expected 15-character GSTIN")
    return v


def _validate_cin(v: Optional[str]) -> Optional[str]:
    """CIN is 21 alphanumeric characters."""
    import re

    if v is None:
        return v
    v = v.strip().upper()
    if not re.fullmatch(r"[A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}", v):
        raise ValueError("Invalid CIN format — expected 21-character CIN")
    return v


# ---------- Create / Update ----------

class ClientCreate(BaseModel):
    firm_name: str = Field(..., min_length=1, max_length=512)
    contact_person: str = Field(..., min_length=1, max_length=256)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    pan: str = Field(..., min_length=10, max_length=10)
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    cin: Optional[str] = Field(None, min_length=21, max_length=21)
    entity_type: EntityType
    address: Optional[str] = Field(None, max_length=1024)

    _validate_pan = field_validator("pan")(_validate_pan)
    _validate_gstin = field_validator("gstin")(_validate_gstin)
    _validate_cin = field_validator("cin")(_validate_cin)


class ClientUpdate(BaseModel):
    firm_name: Optional[str] = Field(None, min_length=1, max_length=512)
    contact_person: Optional[str] = Field(None, min_length=1, max_length=256)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    pan: Optional[str] = Field(None, min_length=10, max_length=10)
    gstin: Optional[str] = Field(None, min_length=15, max_length=15)
    cin: Optional[str] = Field(None, min_length=21, max_length=21)
    entity_type: Optional[EntityType] = None
    address: Optional[str] = Field(None, max_length=1024)

    _validate_pan = field_validator("pan")(_validate_pan)
    _validate_gstin = field_validator("gstin")(_validate_gstin)
    _validate_cin = field_validator("cin")(_validate_cin)


# ---------- Response ----------

class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    firm_name: str
    contact_person: str
    email: str
    phone: Optional[str] = None
    pan: str
    gstin: Optional[str] = None
    cin: Optional[str] = None
    entity_type: EntityType
    address: Optional[str] = None
    assigned_to: Optional[UUID] = None
    assigned_to_name: Optional[str] = None
    compliance_stats: Optional[ComplianceStats] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
