"""Dashboard schemas — aggregated stats, compliance overview, recent activity."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------- Top-level stats ----------

class DashboardStats(BaseModel):
    total_clients: int = Field(..., ge=0)
    active_tasks: int = Field(..., ge=0)
    overdue_tasks: int = Field(..., ge=0)
    documents_processed: int = Field(..., ge=0)
    queries_today: int = Field(..., ge=0)
    revenue_this_month: Decimal = Field(Decimal("0"), ge=0)


# ---------- Compliance overview ----------

class ComplianceOverviewItem(BaseModel):
    """Lightweight task summary used in the dashboard compliance widget."""

    id: UUID
    client_name: str
    task_type: str
    due_date: str  # ISO date string for easy frontend consumption
    status: str
    days_until_due: int


class ComplianceOverview(BaseModel):
    upcoming_7_days: list[ComplianceOverviewItem] = Field(default_factory=list)
    overdue: list[ComplianceOverviewItem] = Field(default_factory=list)
    completion_rate: float = Field(0.0, ge=0.0, le=1.0)


# ---------- Recent activity ----------

class RecentQueryItem(BaseModel):
    id: UUID
    question: str
    query_type: str
    asked_by_name: Optional[str] = None
    created_at: datetime


class RecentDocumentItem(BaseModel):
    id: UUID
    original_filename: str
    doc_type: str
    client_name: Optional[str] = None
    uploaded_at: datetime


class RecentComputationItem(BaseModel):
    id: UUID
    computation_type: str
    client_name: Optional[str] = None
    result_summary: Optional[str] = None
    created_at: datetime


class RecentActivity(BaseModel):
    recent_queries: list[RecentQueryItem] = Field(default_factory=list)
    recent_documents: list[RecentDocumentItem] = Field(default_factory=list)
    recent_computations: list[RecentComputationItem] = Field(default_factory=list)
