"""Query schemas — AI-powered Q&A on client documents."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QueryType(str, Enum):
    general = "general"
    compliance = "compliance"
    computation = "computation"
    notice = "notice"
    document = "document"


# ---------- Request ----------

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4096)
    client_id: Optional[UUID] = None
    context: Optional[str] = Field(None, max_length=8192)


# ---------- Response ----------

class QueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question: str
    response: str
    sources_cited: list[str] = Field(default_factory=list)
    query_type: QueryType
    model_used: str
    tokens_used: int = Field(..., ge=0)
    asked_by: Optional[UUID] = None
    client_id: Optional[UUID] = None
    created_at: datetime
