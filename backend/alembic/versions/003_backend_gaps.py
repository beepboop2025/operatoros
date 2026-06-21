"""003 Backend gaps — notifications, tax intelligence feed.

Revision ID: 003_backend_gaps
Revises: 002_enterprise
Create Date: 2026-06-21

Adds:
  - notifications table for in-app user alerts
  - tax_intel table for the World Tax Radar feed
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers, used by Alembic.
revision = "003_backend_gaps"
down_revision = "002_enterprise"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name=op.f("fk_notifications_user_id_users"), ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(64), nullable=True),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"])
    op.create_index(op.f("ix_notifications_is_read"), "notifications", ["is_read"])
    op.create_index(op.f("ix_notifications_created_at"), "notifications", ["created_at"])
    op.create_index(
        op.f("ix_notifications_user_read"), "notifications", ["user_id", "is_read"]
    )

    # ── tax_intel ─────────────────────────────────────────────────────────────
    op.create_table(
        "tax_intel",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("jurisdiction", sa.String(128), nullable=True),
        sa.Column("topic", sa.String(128), nullable=True),
        sa.Column("nri_impact_score", sa.Integer(), nullable=True),
        sa.Column("matched_terms", JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tax_intel")),
    )
    op.create_index(op.f("ix_tax_intel_jurisdiction"), "tax_intel", ["jurisdiction"])
    op.create_index(op.f("ix_tax_intel_topic"), "tax_intel", ["topic"])
    op.create_index(
        op.f("ix_tax_intel_nri_impact_score"), "tax_intel", ["nri_impact_score"]
    )
    op.create_index(op.f("ix_tax_intel_created_at"), "tax_intel", ["created_at"])
    op.create_index(op.f("ix_tax_intel_published_at"), "tax_intel", ["published_at"])


def downgrade() -> None:
    op.drop_table("tax_intel")
    op.drop_table("notifications")
