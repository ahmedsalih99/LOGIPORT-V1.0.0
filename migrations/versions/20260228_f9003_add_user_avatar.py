"""add user avatar_path column

Revision ID: f9003
Revises: f9002
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa

revision = 'f9003_user_avatar'
down_revision = 'f9002_company_bank_info'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('avatar_path', sa.String(500), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('avatar_path')
