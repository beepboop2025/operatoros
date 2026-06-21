"""005 Fix undersized enum varchar columns.

Revision ID: 005_fix_enum_lengths
Revises: 004_waitlist
Create Date: 2026-06-21

Migration 001 hardcoded several non-native Enum columns as VARCHAR(11), but the
ORM models (Enum(..., native_enum=False)) size them to their longest value. The
mismatch made some valid values un-insertable:
  - clients.entity_type        11 -> 15  ('private_limited', 'public_limited')
  - compliance_tasks.task_type 11 -> 17  ('professional_tax')
  - compliance_tasks.status    11 -> 12  ('under_review')
"""

from alembic import op
import sqlalchemy as sa

revision = "005_fix_enum_lengths"
down_revision = "004_waitlist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("clients", "entity_type", type_=sa.String(15), existing_nullable=False)
    op.alter_column("compliance_tasks", "task_type", type_=sa.String(17), existing_nullable=False)
    op.alter_column("compliance_tasks", "status", type_=sa.String(12), existing_nullable=False)


def downgrade() -> None:
    op.alter_column("compliance_tasks", "status", type_=sa.String(11), existing_nullable=False)
    op.alter_column("compliance_tasks", "task_type", type_=sa.String(11), existing_nullable=False)
    op.alter_column("clients", "entity_type", type_=sa.String(11), existing_nullable=False)
