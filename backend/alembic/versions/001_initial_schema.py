"""001 Initial schema — all core OperatorOS tables.

Revision ID: 001_initial
Revises: (none)
Create Date: 2026-03-09

Creates:
  - pgvector extension
  - users, clients, documents, queries
  - compliance_tasks, tax_computations, notices, audit_logs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extensions ──────────────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── users ───────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(512), nullable=False),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "admin", "partner", "associate", "client_view",
                name="user_role",
                native_enum=False,
            ),
            nullable=False,
            server_default="associate",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"])
    op.create_index(op.f("ix_users_role"), "users", ["role"])

    # ── clients ─────────────────────────────────────────────────────────────
    op.create_table(
        "clients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("firm_name", sa.String(512), nullable=False),
        sa.Column("contact_person", sa.String(256), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("pan", sa.String(10), nullable=False),
        sa.Column("gstin", sa.String(15), nullable=True),
        sa.Column("cin", sa.String(21), nullable=True),
        sa.Column(
            "entity_type",
            sa.Enum(
                "individual", "huf", "partnership", "llp", "company", "trust",
                name="entity_type",
                native_enum=False,
            ),
            nullable=False,
            server_default="individual",
        ),
        sa.Column("address_json", JSON, nullable=True),
        sa.Column(
            "assigned_to",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name=op.f("fk_clients_assigned_to_users"), ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clients")),
        sa.UniqueConstraint("pan", name=op.f("uq_clients_pan")),
    )
    op.create_index(op.f("ix_clients_pan"), "clients", ["pan"])
    op.create_index(op.f("ix_clients_gstin"), "clients", ["gstin"])
    op.create_index(op.f("ix_clients_firm_name"), "clients", ["firm_name"])
    op.create_index(op.f("ix_clients_assigned_to"), "clients", ["assigned_to"])

    # ── documents ───────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clients.id", name=op.f("fk_documents_client_id_clients"), ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "doc_type",
            sa.Enum(
                "form16", "form26as", "ais", "tis", "gstr", "notice",
                "bank_statement", "financial_statement", "rent_agreement",
                "sale_deed", "contract", "other",
                name="doc_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("file_url", sa.String(2048), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("parsed_json", JSON, nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        # pgvector column: 1536-dimension embedding
        sa.Column("embedding", sa.Column("embedding", sa.Text(), nullable=True).type, nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "uploaded", "processing", "processed", "failed",
                name="document_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column(
            "uploaded_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name=op.f("fk_documents_uploaded_by_users"), ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    # Replace the generic embedding column with proper vector type
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE documents ADD COLUMN embedding vector(1536)")

    op.create_index(op.f("ix_documents_client_id"), "documents", ["client_id"])
    op.create_index(op.f("ix_documents_doc_type"), "documents", ["doc_type"])
    op.create_index(op.f("ix_documents_status"), "documents", ["status"])
    op.create_index(op.f("ix_documents_uploaded_by"), "documents", ["uploaded_by"])

    # ── queries ─────────────────────────────────────────────────────────────
    op.create_table(
        "queries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clients.id", name=op.f("fk_queries_client_id_clients"), ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "asked_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name=op.f("fk_queries_asked_by_users"), ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("sources_cited", JSON, nullable=True),
        sa.Column(
            "query_type",
            sa.Enum(
                "factual", "computation", "advisory", "procedural",
                name="query_type",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column("model_used", sa.String(128), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_queries")),
    )
    op.create_index(op.f("ix_queries_client_id"), "queries", ["client_id"])
    op.create_index(op.f("ix_queries_asked_by"), "queries", ["asked_by"])
    op.create_index(op.f("ix_queries_query_type"), "queries", ["query_type"])
    op.create_index(op.f("ix_queries_created_at"), "queries", ["created_at"])

    # ── compliance_tasks ────────────────────────────────────────────────────
    op.create_table(
        "compliance_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clients.id", name=op.f("fk_compliance_tasks_client_id_clients"), ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_type",
            sa.Enum(
                "tds_return", "advance_tax", "itr_filing", "gst_return",
                "roc_filing", "tax_audit", "dir3_kyc", "llp_form", "other",
                name="compliance_task_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("assessment_year", sa.String(9), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "in_progress", "completed", "overdue",
                name="compliance_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "assigned_to",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name=op.f("fk_compliance_tasks_assigned_to_users"), ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reminder_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_compliance_tasks")),
    )
    op.create_index(op.f("ix_compliance_tasks_client_id"), "compliance_tasks", ["client_id"])
    op.create_index(op.f("ix_compliance_tasks_due_date"), "compliance_tasks", ["due_date"])
    op.create_index(op.f("ix_compliance_tasks_status"), "compliance_tasks", ["status"])
    op.create_index(op.f("ix_compliance_tasks_assigned_to"), "compliance_tasks", ["assigned_to"])
    op.create_index(
        op.f("ix_compliance_tasks_assessment_year"), "compliance_tasks", ["assessment_year"]
    )

    # ── tax_computations ────────────────────────────────────────────────────
    op.create_table(
        "tax_computations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clients.id", name=op.f("fk_tax_computations_client_id_clients"), ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("assessment_year", sa.String(9), nullable=False),
        sa.Column(
            "regime",
            sa.Enum(
                "old", "new",
                name="tax_regime",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("gross_income", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("deductions_json", JSON, nullable=True),
        sa.Column("tax_liability", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("computation_json", JSON, nullable=True),
        sa.Column(
            "computed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name=op.f("fk_tax_computations_computed_by_users"), ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tax_computations")),
    )
    op.create_index(
        op.f("ix_tax_computations_client_id"), "tax_computations", ["client_id"]
    )
    op.create_index(
        op.f("ix_tax_computations_assessment_year"), "tax_computations", ["assessment_year"]
    )
    op.create_index(
        op.f("ix_tax_computations_regime"), "tax_computations", ["regime"]
    )

    # ── notices ─────────────────────────────────────────────────────────────
    op.create_table(
        "notices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clients.id", name=op.f("fk_notices_client_id_clients"), ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "notice_type",
            sa.Enum(
                "intimation_143_1", "scrutiny_143_2", "reassessment_148",
                "demand", "rectification_154", "penalty",
                "gst_asmt10", "gst_drc01", "gst_drc07", "other",
                name="notice_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("notice_date", sa.Date(), nullable=False),
        sa.Column("response_deadline", sa.Date(), nullable=True),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", name=op.f("fk_notices_document_id_documents"), ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "received", "under_review", "response_drafted",
                "response_filed", "resolved",
                name="notice_status",
                native_enum=False,
            ),
            nullable=False,
            server_default="received",
        ),
        sa.Column("response_draft", sa.Text(), nullable=True),
        sa.Column("filed_response", sa.Text(), nullable=True),
        sa.Column(
            "assigned_to",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name=op.f("fk_notices_assigned_to_users"), ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notices")),
    )
    op.create_index(op.f("ix_notices_client_id"), "notices", ["client_id"])
    op.create_index(op.f("ix_notices_notice_type"), "notices", ["notice_type"])
    op.create_index(op.f("ix_notices_response_deadline"), "notices", ["response_deadline"])
    op.create_index(op.f("ix_notices_status"), "notices", ["status"])
    op.create_index(op.f("ix_notices_assigned_to"), "notices", ["assigned_to"])

    # ── audit_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name=op.f("fk_audit_logs_user_id_users"), ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("details", JSON, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"])
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"])
    op.create_index(
        op.f("ix_audit_logs_entity_type_entity_id"),
        "audit_logs",
        ["entity_type", "entity_id"],
    )
    op.create_index(op.f("ix_audit_logs_timestamp"), "audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("notices")
    op.drop_table("tax_computations")
    op.drop_table("compliance_tasks")
    op.drop_table("queries")
    op.drop_table("documents")
    op.drop_table("clients")
    op.drop_table("users")

    # Drop enums created with native_enum=False (VARCHAR-backed, no actual
    # PG enum to drop). If they were native, uncomment the lines below:
    # op.execute("DROP TYPE IF EXISTS user_role")
    # op.execute("DROP TYPE IF EXISTS entity_type")
    # op.execute("DROP TYPE IF EXISTS doc_type")
    # op.execute("DROP TYPE IF EXISTS document_status")
    # op.execute("DROP TYPE IF EXISTS query_type")
    # op.execute("DROP TYPE IF EXISTS compliance_task_type")
    # op.execute("DROP TYPE IF EXISTS compliance_status")
    # op.execute("DROP TYPE IF EXISTS tax_regime")
    # op.execute("DROP TYPE IF EXISTS notice_type")
    # op.execute("DROP TYPE IF EXISTS notice_status")

    # Note: We intentionally do NOT drop the vector extension as other
    # schemas/tables may depend on it.
