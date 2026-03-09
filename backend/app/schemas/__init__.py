"""
OperatorOS Pydantic schemas — re-exports for convenient imports.

Usage:
    from app.schemas import LoginRequest, UserResponse, ClientCreate, ...
"""

# Auth
from app.schemas.auth import (
    LoginRequest,
    TokenPayload,
    TokenResponse,
)

# User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserRole,
    UserUpdate,
)

# Client
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    ComplianceStats,
    EntityType,
)

# Document
from app.schemas.document import (
    DocStatus,
    DocType,
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResult,
    DocumentUpload,
)

# Query
from app.schemas.query import (
    QueryRequest,
    QueryResponse,
    QueryType,
)

# Compliance
from app.schemas.compliance import (
    ComplianceCalendarResponse,
    ComplianceTaskCreate,
    ComplianceTaskResponse,
    ComplianceTaskUpdate,
    TaskStatus,
    TaskType,
)

# Computation
from app.schemas.computation import (
    AgeCategory,
    AssetType,
    CapitalGainsRequest,
    CapitalGainsResponse,
    Deductions,
    GainType,
    GSTRequest,
    GSTResponse,
    IncomeTaxRequest,
    IncomeTaxResponse,
    InterestRequest,
    InterestResponse,
    InterestSection,
    MonthWiseDetail,
    PaymentType,
    RecipientType,
    RegimeBreakdown,
    SupplyType,
    SupplyTypeDetermined,
    TDSRequest,
    TDSResponse,
)

# Notice
from app.schemas.notice import (
    NoticeProcessRequest,
    NoticeResponse,
    NoticeResponseDraft,
    NoticeType,
    UrgencyLevel,
)

# Dashboard
from app.schemas.dashboard import (
    ComplianceOverview,
    ComplianceOverviewItem,
    DashboardStats,
    RecentActivity,
    RecentComputationItem,
    RecentDocumentItem,
    RecentQueryItem,
)

__all__ = [
    # Auth
    "LoginRequest",
    "TokenPayload",
    "TokenResponse",
    # User
    "UserCreate",
    "UserResponse",
    "UserRole",
    "UserUpdate",
    # Client
    "ClientCreate",
    "ClientListResponse",
    "ClientResponse",
    "ClientUpdate",
    "ComplianceStats",
    "EntityType",
    # Document
    "DocStatus",
    "DocType",
    "DocumentResponse",
    "DocumentSearchRequest",
    "DocumentSearchResult",
    "DocumentUpload",
    # Query
    "QueryRequest",
    "QueryResponse",
    "QueryType",
    # Compliance
    "ComplianceCalendarResponse",
    "ComplianceTaskCreate",
    "ComplianceTaskResponse",
    "ComplianceTaskUpdate",
    "TaskStatus",
    "TaskType",
    # Computation
    "AgeCategory",
    "AssetType",
    "CapitalGainsRequest",
    "CapitalGainsResponse",
    "Deductions",
    "GainType",
    "GSTRequest",
    "GSTResponse",
    "IncomeTaxRequest",
    "IncomeTaxResponse",
    "InterestRequest",
    "InterestResponse",
    "InterestSection",
    "MonthWiseDetail",
    "PaymentType",
    "RecipientType",
    "RegimeBreakdown",
    "SupplyType",
    "SupplyTypeDetermined",
    "TDSRequest",
    "TDSResponse",
    # Notice
    "NoticeProcessRequest",
    "NoticeResponse",
    "NoticeResponseDraft",
    "NoticeType",
    "UrgencyLevel",
    # Dashboard
    "ComplianceOverview",
    "ComplianceOverviewItem",
    "DashboardStats",
    "RecentActivity",
    "RecentComputationItem",
    "RecentDocumentItem",
    "RecentQueryItem",
]
