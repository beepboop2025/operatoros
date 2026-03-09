"""ComplianceTask model — statutory deadlines and filing tracker."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.user import User


class TaskType(str, enum.Enum):
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


class ComplianceStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    under_review = "under_review"
    completed = "completed"
    overdue = "overdue"


class ComplianceTask(Base):
    __tablename__ = "compliance_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )

    task_type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, name="compliance_task_type", native_enum=False),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    assessment_year: Mapped[Optional[str]] = mapped_column(
        String(9), nullable=True
    )  # e.g. "2025-26"

    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus, name="compliance_status", native_enum=False),
        nullable=False,
        default=ComplianceStatus.pending,
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reminder_sent: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # --- Relationships ---
    client: Mapped["Client"] = relationship(
        back_populates="compliance_tasks", foreign_keys=[client_id]
    )
    assignee: Mapped[Optional["User"]] = relationship(
        back_populates="compliance_tasks", foreign_keys=[assigned_to]
    )

    __table_args__ = (
        Index("ix_compliance_tasks_client_id", "client_id"),
        Index("ix_compliance_tasks_due_date", "due_date"),
        Index("ix_compliance_tasks_status", "status"),
        Index("ix_compliance_tasks_assigned_to", "assigned_to"),
        Index("ix_compliance_tasks_assessment_year", "assessment_year"),
    )

    def __repr__(self) -> str:
        return f"<ComplianceTask {self.task_type.value} due={self.due_date}>"
