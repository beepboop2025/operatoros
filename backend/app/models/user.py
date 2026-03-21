"""User model — authentication and role-based access."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.document import Document
    from app.models.query import Query
    from app.models.compliance import ComplianceTask
    from app.models.computation import TaxComputation
    from app.models.notice import Notice
    from app.models.audit_log import AuditLog


class UserRole(str, enum.Enum):
    admin = "admin"
    partner = "partner"
    associate = "associate"
    client_view = "client_view"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.associate,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Multi-tenant firm association
    firm_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("firms.id"), nullable=True
    )

    # --- Relationships ---
    assigned_clients: Mapped[List["Client"]] = relationship(
        back_populates="assigned_user", foreign_keys="Client.assigned_to"
    )
    uploaded_documents: Mapped[List["Document"]] = relationship(
        back_populates="uploader", foreign_keys="Document.uploaded_by"
    )
    queries: Mapped[List["Query"]] = relationship(
        back_populates="asker", foreign_keys="Query.asked_by"
    )
    compliance_tasks: Mapped[List["ComplianceTask"]] = relationship(
        back_populates="assignee", foreign_keys="ComplianceTask.assigned_to"
    )
    tax_computations: Mapped[List["TaxComputation"]] = relationship(
        back_populates="computed_by_user", foreign_keys="TaxComputation.computed_by"
    )
    assigned_notices: Mapped[List["Notice"]] = relationship(
        back_populates="assignee", foreign_keys="Notice.assigned_to"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="user", foreign_keys="AuditLog.user_id"
    )

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_role", "role"),
    )

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role.value}>"
