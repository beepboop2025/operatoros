"""Notice model — income tax and GST notices, response tracking."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.document import Document
    from app.models.user import User


class NoticeType(str, enum.Enum):
    intimation_143_1 = "intimation_143_1"
    scrutiny_143_2 = "scrutiny_143_2"
    reassessment_148 = "reassessment_148"
    demand = "demand"
    rectification_154 = "rectification_154"
    penalty = "penalty"
    gst_asmt10 = "gst_asmt10"
    gst_drc01 = "gst_drc01"
    gst_drc07 = "gst_drc07"
    other = "other"


class NoticeStatus(str, enum.Enum):
    received = "received"
    under_review = "under_review"
    response_drafted = "response_drafted"
    response_filed = "response_filed"
    resolved = "resolved"


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )

    notice_type: Mapped[NoticeType] = mapped_column(
        Enum(NoticeType, name="notice_type", native_enum=False), nullable=False
    )
    notice_date: Mapped[date] = mapped_column(Date, nullable=False)
    response_deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )

    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[NoticeStatus] = mapped_column(
        Enum(NoticeStatus, name="notice_status", native_enum=False),
        nullable=False,
        default=NoticeStatus.received,
    )
    response_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filed_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
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
        back_populates="notices", foreign_keys=[client_id]
    )
    document: Mapped[Optional["Document"]] = relationship(
        back_populates="notices", foreign_keys=[document_id]
    )
    assignee: Mapped[Optional["User"]] = relationship(
        back_populates="assigned_notices", foreign_keys=[assigned_to]
    )

    __table_args__ = (
        Index("ix_notices_client_id", "client_id"),
        Index("ix_notices_notice_type", "notice_type"),
        Index("ix_notices_response_deadline", "response_deadline"),
        Index("ix_notices_status", "status"),
        Index("ix_notices_assigned_to", "assigned_to"),
    )

    def __repr__(self) -> str:
        return f"<Notice {self.notice_type.value} status={self.status.value}>"
