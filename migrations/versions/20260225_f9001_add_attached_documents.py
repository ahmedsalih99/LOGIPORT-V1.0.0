"""add attached_documents to transport_details

Revision ID: f9001_attached_docs
Revises: f9000_transport_stamp
Create Date: 2026-02-25
"""
from alembic import op
import sqlalchemy as sa

revision = "f9001_attached_docs"
down_revision = "f9000_transport_stamp"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("transport_details") as batch_op:
        batch_op.add_column(
            sa.Column("attached_documents", sa.String(512), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("transport_details") as batch_op:
        batch_op.drop_column("attached_documents")
