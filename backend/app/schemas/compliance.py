"""Compliance schemas — task tracking and calendar views."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class TaskType(str, Enum):
    itr_filing = "itr_filing"
    advance_tax = "advance_tax"
    tds_return = "tds_return"
    gst_return = "gst_return"
    audit = "audit"
    tax_audit = "tax_audit"
    roc_filing = "roc_filing"
    esi_pf = "esi_pf"
    professional_tax = "professional_tax"
    dir3_kyc = "dir3_kyc"
    llp_form = "llp_form"
    other = "other"


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    under_review = "under_review"
    completed = "completed"
    overdue = "overdue"


# ---------- Create / Update ----------

class ComplianceTaskCreate(BaseModel):
    client_id: UUID
    task_type: TaskType
    description: str = Field(..., min_length=1, max_length=2048)
    due_date: date
    assessment_year: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}$",
        description="Assessment year in YYYY-YY format, e.g. 2025-26",
    )
    assigned_to: Optional[UUID] = None


class ComplianceTaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    assigned_to: Optional[UUID] = None
    description: Optional[str] = Field(None, min_length=1, max_length=2048)


# ---------- Response ----------

class ComplianceTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    client_name: Optional[str] = None
    task_type: TaskType
    description: str
    status: TaskStatus
    due_date: date
    assessment_year: str
    assigned_to: Optional[UUID] = None
    assigned_to_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_until_due(self) -> int:
        return (self.due_date - date.today()).days


class ComplianceCalendarResponse(BaseModel):
    tasks: list[ComplianceTaskResponse]
    overdue_count: int = 0
    upcoming_count: int = 0
