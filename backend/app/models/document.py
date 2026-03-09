"""Document model — uploaded files, parsed content, and vector embeddings."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
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
    from app.models.client import Client
    from app.models.user import User
    from app.models.notice import Notice


class DocType(str, enum.Enum):
    form16 = "form16"
    form26as = "form26as"
    ais = "ais"
    tis = "tis"
    gstr = "gstr"
    notice = "notice"
    bank_statement = "bank_statement"
    financial_statement = "financial_statement"
    rent_agreement = "rent_agreement"
    sale_deed = "sale_deed"
    contract = "contract"
    other = "other"


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    processed = "processed"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False
    )

    doc_type: Mapped[DocType] = mapped_column(
        Enum(DocType, name="doc_type", native_enum=False), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    parsed_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[Optional[list]] = mapped_column(
        Vector(1536), nullable=True
    )

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status", native_enum=False),
        nullable=False,
        default=DocumentStatus.uploaded,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- Relationships ---
    client: Mapped["Client"] = relationship(
        back_populates="documents", foreign_keys=[client_id]
    )
    uploader: Mapped["User"] = relationship(
        back_populates="uploaded_documents", foreign_keys=[uploaded_by]
    )
    notices: Mapped[list["Notice"]] = relationship(
        back_populates="document", foreign_keys="Notice.document_id"
    )

    __table_args__ = (
        Index("ix_documents_client_id", "client_id"),
        Index("ix_documents_doc_type", "doc_type"),
        Index("ix_documents_status", "status"),
        Index("ix_documents_uploaded_by", "uploaded_by"),
    )

    def __repr__(self) -> str:
        return f"<Document {self.original_filename} type={self.doc_type.value}>"
