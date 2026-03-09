"""Notice schemas — IT/GST notice processing and response drafting."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class NoticeType(str, Enum):
    intimation_143_1 = "intimation_143_1"
    scrutiny_143_2 = "scrutiny_143_2"
    demand_156 = "demand_156"
    rectification_154 = "rectification_154"
    penalty_271 = "penalty_271"
    reassessment_148 = "reassessment_148"
    information_133_6 = "information_133_6"
    gst_asmt_10 = "gst_asmt_10"
    gst_drc_01 = "gst_drc_01"
    other = "other"


class UrgencyLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# ---------- Request ----------

class NoticeProcessRequest(BaseModel):
    client_id: UUID
    notice_type: Optional[NoticeType] = None
    document_id: Optional[UUID] = None


# ---------- Response ----------

class NoticeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    client_name: Optional[str] = None
    notice_type: NoticeType
    section: Optional[str] = None
    description: Optional[str] = None
    issue_date: Optional[date] = None
    response_deadline: Optional[date] = None
    status: str
    assigned_to: Optional[UUID] = None
    document_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_until_deadline(self) -> Optional[int]:
        if self.response_deadline is None:
            return None
        return (self.response_deadline - date.today()).days

    @computed_field  # type: ignore[prop-decorator]
    @property
    def urgency_level(self) -> UrgencyLevel:
        days = self.days_until_deadline
        if days is None:
            return UrgencyLevel.medium
        if days < 0:
            return UrgencyLevel.critical
        if days <= 3:
            return UrgencyLevel.high
        if days <= 10:
            return UrgencyLevel.medium
        return UrgencyLevel.low


class NoticeResponseDraft(BaseModel):
    notice_id: UUID
    draft_text: str
    legal_references: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
