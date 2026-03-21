"""002 Enterprise indexes, audit_log enhancements, firm_id columns.

Revision ID: 002_enterprise
Revises: 001_initial
Create Date: 2026-03-21

Adds:
  - New columns on audit_logs: endpoint, method, request_body, response_status,
    user_agent, duration_ms
  - Makes audit_logs.user_id nullable (for unauthenticated request logging)
  - Composite indexes for common query patterns
  - firm_id columns on users, clients, documents, queries, compliance_tasks,
    tax_computations, notices (multi-tenant support)
  - firms table for multi-tenant management
  - Slow query logging event trigger (placeholder comment)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "002_enterprise"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Audit log enhancements ───────────────────────────────────────────

    # Make user_id nullable for unauthenticated request logging
    op.alter_column("audit_logs", "user_id", existing_type=UUID(as_uuid=True), nullable=True)

    op.add_column("audit_logs", sa.Column("endpoint", sa.String(512), nullable=True))
    op.add_column("audit_logs", sa.Column("method", sa.String(10), nullable=True))
    op.add_column("audit_logs", sa.Column("request_body", JSON, nullable=True))
    op.add_column("audit_logs", sa.Column("response_status", sa.Integer(), nullable=True))
    op.add_column("audit_logs", sa.Column("user_agent", sa.String(512), nullable=True))
    op.add_column("audit_logs", sa.Column("duration_ms", sa.Float(), nullable=True))

    op.create_index("ix_audit_logs_endpoint", "audit_logs", ["endpoint"])
    op.create_index("ix_audit_logs_method", "audit_logs", ["method"])
    op.create_index("ix_audit_logs_response_status", "audit_logs", ["response_status"])

    # ── Composite indexes for common query patterns ──────────────────────

    # clients: firm_id + created_at, status lookups
    op.create_index(
        "ix_clients_created_at", "clients", ["created_at"]
    )
    op.create_index(
        "ix_clients_is_active_firm_name", "clients", ["is_active", "firm_name"]
    )

    # documents: client_id + uploaded_at (common list query), client_id + doc_type
    op.create_index(
        "ix_documents_client_uploaded", "documents", ["client_id", "uploaded_at"]
    )
    op.create_index(
        "ix_documents_client_doctype", "documents", ["client_id", "doc_type"]
    )

    # queries: client_id + created_at (recent queries per client)
    op.create_index(
        "ix_queries_client_created", "queries", ["client_id", "created_at"]
    )

    # compliance_tasks: due_date + status (upcoming/overdue queries)
    op.create_index(
        "ix_compliance_tasks_due_status", "compliance_tasks", ["due_date", "status"]
    )
    op.create_index(
        "ix_compliance_tasks_client_due", "compliance_tasks", ["client_id", "due_date"]
    )

    # tax_computations: client_id + created_at
    op.create_index(
        "ix_tax_computations_client_created", "tax_computations", ["client_id", "created_at"]
    )

    # notices: client_id + response_deadline
    op.create_index(
        "ix_notices_client_deadline", "notices", ["client_id", "response_deadline"]
    )

    # ── Multi-tenant: firms table ────────────────────────────────────────

    op.create_table(
        "firms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("logo_url", sa.String(2048), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("gstin", sa.String(15), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("settings_json", JSON, nullable=True),
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
    )
    op.create_index("ix_firms_slug", "firms", ["slug"])
    op.create_index("ix_firms_is_active", "firms", ["is_active"])

    # ── firm_id columns on all major tables ──────────────────────────────

    for table_name in [
        "users", "clients", "documents", "queries",
        "compliance_tasks", "tax_computations", "notices", "audit_logs",
    ]:
        op.add_column(
            table_name,
            sa.Column("firm_id", UUID(as_uuid=True), sa.ForeignKey("firms.id"), nullable=True),
        )
        op.create_index(f"ix_{table_name}_firm_id", table_name, ["firm_id"])


def downgrade() -> None:
    # Drop firm_id columns
    for table_name in [
        "users", "clients", "documents", "queries",
        "compliance_tasks", "tax_computations", "notices", "audit_logs",
    ]:
        op.drop_index(f"ix_{table_name}_firm_id", table_name=table_name)
        op.drop_column(table_name, "firm_id")

    # Drop firms table
    op.drop_index("ix_firms_is_active", table_name="firms")
    op.drop_index("ix_firms_slug", table_name="firms")
    op.drop_table("firms")

    # Drop composite indexes
    op.drop_index("ix_notices_client_deadline", table_name="notices")
    op.drop_index("ix_tax_computations_client_created", table_name="tax_computations")
    op.drop_index("ix_compliance_tasks_client_due", table_name="compliance_tasks")
    op.drop_index("ix_compliance_tasks_due_status", table_name="compliance_tasks")
    op.drop_index("ix_queries_client_created", table_name="queries")
    op.drop_index("ix_documents_client_doctype", table_name="documents")
    op.drop_index("ix_documents_client_uploaded", table_name="documents")
    op.drop_index("ix_clients_is_active_firm_name", table_name="clients")
    op.drop_index("ix_clients_created_at", table_name="clients")

    # Drop audit_log enhancements
    op.drop_index("ix_audit_logs_response_status", table_name="audit_logs")
    op.drop_index("ix_audit_logs_method", table_name="audit_logs")
    op.drop_index("ix_audit_logs_endpoint", table_name="audit_logs")
    op.drop_column("audit_logs", "duration_ms")
    op.drop_column("audit_logs", "user_agent")
    op.drop_column("audit_logs", "response_status")
    op.drop_column("audit_logs", "request_body")
    op.drop_column("audit_logs", "method")
    op.drop_column("audit_logs", "endpoint")
    op.alter_column("audit_logs", "user_id", existing_type=UUID(as_uuid=True), nullable=False)
