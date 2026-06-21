"""WaitlistEntry model — early-access / interest capture from the public landing page."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # Self-described segment: nri | returning | ca_firm | founder | other
    persona: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Where the signup came from (landing CTA id, campaign, etc.)
    source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_waitlist_entries_email", "email"),
        Index("ix_waitlist_entries_persona", "persona"),
        Index("ix_waitlist_entries_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<WaitlistEntry {self.email} persona={self.persona}>"
