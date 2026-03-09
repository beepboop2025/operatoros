"""Document schemas — upload, search, and response."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocType(str, Enum):
    itr = "itr"
    form_16 = "form_16"
    form_26as = "form_26as"
    balance_sheet = "balance_sheet"
    pnl_statement = "pnl_statement"
    gst_return = "gst_return"
    tds_return = "tds_return"
    bank_statement = "bank_statement"
    notice = "notice"
    computation = "computation"
    audit_report = "audit_report"
    agreement = "agreement"
    other = "other"


class DocStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    processed = "processed"
    failed = "failed"


# ---------- Request ----------

class DocumentUpload(BaseModel):
    client_id: UUID
    doc_type: DocType


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1024)
    client_id: Optional[UUID] = None
    doc_type: Optional[DocType] = None
    limit: int = Field(10, ge=1, le=100)


# ---------- Response ----------

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    doc_type: DocType
    original_filename: str
    summary: Optional[str] = None
    status: DocStatus
    uploaded_by: Optional[UUID] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None


class DocumentSearchResult(BaseModel):
    document: DocumentResponse
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    excerpt: str
