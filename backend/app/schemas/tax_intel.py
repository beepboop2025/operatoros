"""World Tax Radar schemas — ingest request and list response."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaxIntelIngestRequest(BaseModel):
    """Payload accepted from the social-scraper connector."""

    title: str = Field(..., min_length=1, max_length=512)
    summary: Optional[str] = None
    source_url: str = Field(..., min_length=1, max_length=2048)
    published_at: Optional[datetime] = None
    jurisdiction: Optional[str] = Field(None, max_length=128)
    topic: Optional[str] = Field(None, max_length=128)
    nri_impact_score: Optional[int] = Field(None, ge=0, le=100)
    matched_terms: list[str] = Field(default_factory=list)


class TaxIntelResponse(BaseModel):
    """A single tax intelligence feed item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: Optional[str] = None
    source_url: str
    published_at: Optional[datetime] = None
    jurisdiction: Optional[str] = None
    topic: Optional[str] = None
    nri_impact_score: Optional[int] = None
    matched_terms: Optional[list[str]] = None
    created_at: datetime
