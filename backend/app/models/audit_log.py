"""AuditLog model — immutable record of every significant action."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    action: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # e.g. "query.create", "document.upload"
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # e.g. "document", "computation"
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Request-level fields for middleware audit trail
    endpoint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    request_body: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True
    )  # supports IPv6

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # --- Relationships ---
    user: Mapped[Optional["User"]] = relationship(
        back_populates="audit_logs", foreign_keys=[user_id]
    )

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_endpoint", "endpoint"),
        Index("ix_audit_logs_method", "method"),
        Index("ix_audit_logs_response_status", "response_status"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by={self.user_id}>"
