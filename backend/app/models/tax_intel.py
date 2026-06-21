"""World Tax Radar model — external tax intelligence feed items."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class TaxIntel(Base):
    __tablename__ = "tax_intel"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    jurisdiction: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    nri_impact_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    matched_terms: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_tax_intel_jurisdiction", "jurisdiction"),
        Index("ix_tax_intel_topic", "topic"),
        Index("ix_tax_intel_nri_impact_score", "nri_impact_score"),
        Index("ix_tax_intel_created_at", "created_at"),
        Index("ix_tax_intel_published_at", "published_at"),
    )

    def __repr__(self) -> str:
        return f"<TaxIntel {self.title[:40]} jurisdiction={self.jurisdiction}>"
