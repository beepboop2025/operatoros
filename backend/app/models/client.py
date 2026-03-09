"""Client model — firms / individuals managed by the practice."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document
    from app.models.query import Query
    from app.models.compliance import ComplianceTask
    from app.models.computation import TaxComputation
    from app.models.notice import Notice


class EntityType(str, enum.Enum):
    individual = "individual"
    huf = "huf"
    partnership = "partnership"
    llp = "llp"
    private_limited = "private_limited"
    public_limited = "public_limited"
    trust = "trust"
    society = "society"
    aop = "aop"
    boi = "boi"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    firm_name: Mapped[str] = mapped_column(String(512), nullable=False)
    contact_person: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    pan: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    cin: Mapped[Optional[str]] = mapped_column(String(21), nullable=True)

    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type", native_enum=False),
        nullable=False,
        default=EntityType.individual,
    )
    address_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    onboarded_at: Mapped[Optional[datetime]] = mapped_column(
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
    assigned_user: Mapped[Optional["User"]] = relationship(
        back_populates="assigned_clients", foreign_keys=[assigned_to]
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="client", foreign_keys="Document.client_id"
    )
    queries: Mapped[List["Query"]] = relationship(
        back_populates="client", foreign_keys="Query.client_id"
    )
    compliance_tasks: Mapped[List["ComplianceTask"]] = relationship(
        back_populates="client", foreign_keys="ComplianceTask.client_id"
    )
    tax_computations: Mapped[List["TaxComputation"]] = relationship(
        back_populates="client", foreign_keys="TaxComputation.client_id"
    )
    notices: Mapped[List["Notice"]] = relationship(
        back_populates="client", foreign_keys="Notice.client_id"
    )

    __table_args__ = (
        Index("ix_clients_pan", "pan"),
        Index("ix_clients_gstin", "gstin"),
        Index("ix_clients_firm_name", "firm_name"),
        Index("ix_clients_assigned_to", "assigned_to"),
    )

    def __repr__(self) -> str:
        return f"<Client {self.firm_name} PAN={self.pan}>"
