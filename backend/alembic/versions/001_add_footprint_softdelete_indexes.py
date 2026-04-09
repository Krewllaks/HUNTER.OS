"""Add digital footprint columns, soft delete, and composite indexes to leads

Revision ID: 001_footprint
Revises: None
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa

revision = "001_footprint"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Digital Footprint columns
    op.add_column("leads", sa.Column("social_profiles", sa.JSON(), server_default="[]"))
    op.add_column("leads", sa.Column("digital_footprint_score", sa.Float(), server_default="0.0"))
    op.add_column("leads", sa.Column("footprint_scanned_at", sa.DateTime(), nullable=True))

    # Soft delete columns
    op.add_column("leads", sa.Column("is_deleted", sa.Boolean(), server_default="0", nullable=False))
    op.add_column("leads", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # Indexes
    op.create_index("ix_leads_is_deleted", "leads", ["is_deleted"])
    op.create_index("ix_leads_user_status", "leads", ["user_id", "status"])
    op.create_index("ix_leads_user_created", "leads", ["user_id", "created_at"])
    op.create_index("ix_leads_user_score", "leads", ["user_id", "intent_score"])


def downgrade() -> None:
    op.drop_index("ix_leads_user_score", table_name="leads")
    op.drop_index("ix_leads_user_created", table_name="leads")
    op.drop_index("ix_leads_user_status", table_name="leads")
    op.drop_index("ix_leads_is_deleted", table_name="leads")

    op.drop_column("leads", "deleted_at")
    op.drop_column("leads", "is_deleted")
    op.drop_column("leads", "footprint_scanned_at")
    op.drop_column("leads", "digital_footprint_score")
    op.drop_column("leads", "social_profiles")
