"""
OperatorOS SQLAlchemy models.

Shared declarative Base and re-exports for every domain model.
"""

from datetime import datetime, date
from typing import Optional
from uuid import uuid4

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------- Shared Base ----------

NAMING = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class Base(DeclarativeBase):
    metadata = NAMING


# ---------- Model imports ----------

from app.models.user import User  # noqa: E402
from app.models.client import Client  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.models.query import Query  # noqa: E402
from app.models.compliance import ComplianceTask  # noqa: E402
from app.models.computation import TaxComputation  # noqa: E402
from app.models.notice import Notice  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402
from app.models.firm import Firm  # noqa: E402

__all__ = [
    "Base",
    "User",
    "Client",
    "Document",
    "Query",
    "ComplianceTask",
    "TaxComputation",
    "Notice",
    "AuditLog",
    "Firm",
]
