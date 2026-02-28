"""
Migration: add bank_info to companies table

Revision ID: f9002_company_bank_info
Revises: f9001_attached_docs
Create Date: 2026-02-27
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "f9002_company_bank_info"
down_revision = "f9001_attached_docs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.add_column(
            sa.Column("bank_info", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("bank_info")
