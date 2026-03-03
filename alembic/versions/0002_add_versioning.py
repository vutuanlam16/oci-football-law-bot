"""add versioning and conflict detection fields

Revision ID: 0002_add_versioning
Revises: 0001_init
Create Date: 2026-03-03T09:00:00.000000Z
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_versioning"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add version control columns to documents table
    op.add_column("documents", sa.Column("version_major", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("documents", sa.Column("version_minor", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("documents", sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("documents", sa.Column("effective_date", sa.Date(), nullable=True))
    op.add_column("documents", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.add_column("documents", sa.Column("superseded_by_id", sa.Integer(), nullable=True))
    
    # Add foreign key constraint for superseded_by_id
    op.create_foreign_key(
        "fk_documents_superseded_by_id",
        "documents",
        "documents",
        ["superseded_by_id"],
        ["id"],
        ondelete="SET NULL"
    )
    
    # Add indexes for efficient querying
    op.create_index("ix_documents_version_major", "documents", ["version_major"])
    op.create_index("ix_documents_version_minor", "documents", ["version_minor"])
    op.create_index("ix_documents_is_active", "documents", ["is_active"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_documents_is_active", table_name="documents")
    op.drop_index("ix_documents_version_minor", table_name="documents")
    op.drop_index("ix_documents_version_major", table_name="documents")
    
    # Drop foreign key
    op.drop_constraint("fk_documents_superseded_by_id", "documents", type_="foreignkey")
    
    # Drop columns
    op.drop_column("documents", "superseded_by_id")
    op.drop_column("documents", "archived_at")
    op.drop_column("documents", "effective_date")
    op.drop_column("documents", "is_active")
    op.drop_column("documents", "version_minor")
    op.drop_column("documents", "version_major")
