"""004 Waitlist — public early-access capture from the landing page.

Revision ID: 004_waitlist
Revises: 003_backend_gaps
Create Date: 2026-06-21

Adds:
  - waitlist_entries table for landing-page "Request access" signups
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "004_waitlist"
down_revision = "003_backend_gaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "waitlist_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(256), nullable=True),
        sa.Column("persona", sa.String(64), nullable=True),
        sa.Column("country", sa.String(128), nullable=True),
        sa.Column("source", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_waitlist_entries")),
        sa.UniqueConstraint("email", name=op.f("uq_waitlist_entries_email")),
    )
    op.create_index("ix_waitlist_entries_email", "waitlist_entries", ["email"])
    op.create_index("ix_waitlist_entries_persona", "waitlist_entries", ["persona"])
    op.create_index("ix_waitlist_entries_created_at", "waitlist_entries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_waitlist_entries_created_at", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_persona", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_email", table_name="waitlist_entries")
    op.drop_table("waitlist_entries")
