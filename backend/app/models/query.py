"""Query model — RAG questions, answers, and provenance tracking."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.user import User


class QueryType(str, enum.Enum):
    factual = "factual"
    computation = "computation"
    advisory = "advisory"
    procedural = "procedural"


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True
    )
    asked_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sources_cited: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON, nullable=True
    )

    query_type: Mapped[Optional[QueryType]] = mapped_column(
        Enum(QueryType, name="query_type", native_enum=False), nullable=True
    )
    model_used: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- Relationships ---
    client: Mapped[Optional["Client"]] = relationship(
        back_populates="queries", foreign_keys=[client_id]
    )
    asker: Mapped["User"] = relationship(
        back_populates="queries", foreign_keys=[asked_by]
    )

    __table_args__ = (
        Index("ix_queries_client_id", "client_id"),
        Index("ix_queries_asked_by", "asked_by"),
        Index("ix_queries_query_type", "query_type"),
        Index("ix_queries_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Query {self.id} type={self.query_type}>"
