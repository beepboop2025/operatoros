"""TaxComputation model — income tax computation worksheets."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.user import User


class TaxRegime(str, enum.Enum):
    old = "old"
    new = "new"


class TaxComputation(Base):
    __tablename__ = "tax_computations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )
    assessment_year: Mapped[str] = mapped_column(
        String(9), nullable=False
    )  # e.g. "2025-26"

    regime: Mapped[TaxRegime] = mapped_column(
        Enum(TaxRegime, name="tax_regime", native_enum=False), nullable=False
    )
    gross_income: Mapped[Optional[Any]] = mapped_column(
        Numeric(precision=15, scale=2), nullable=True
    )
    deductions_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    tax_liability: Mapped[Optional[Any]] = mapped_column(
        Numeric(precision=15, scale=2), nullable=True
    )
    computation_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    computed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # --- Relationships ---
    client: Mapped["Client"] = relationship(
        back_populates="tax_computations", foreign_keys=[client_id]
    )
    computed_by_user: Mapped[Optional["User"]] = relationship(
        back_populates="tax_computations", foreign_keys=[computed_by]
    )

    __table_args__ = (
        Index("ix_tax_computations_client_id", "client_id"),
        Index("ix_tax_computations_assessment_year", "assessment_year"),
        Index("ix_tax_computations_regime", "regime"),
    )

    def __repr__(self) -> str:
        return f"<TaxComputation AY={self.assessment_year} regime={self.regime.value}>"
