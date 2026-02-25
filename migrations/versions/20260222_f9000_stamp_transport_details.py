"""stamp_db_with_transport_details

هذا الـ migration يُوثّق الحالة الحالية للـ DB:
  - جدول transport_details موجود (أُنشئ يدوياً أو عبر migration سابق)
  - لا يوجد hs_code في materials (قرار تصميمي — code الموجود يكفي)

الهدف: stamp الـ DB على هذه النقطة حتى لا يُعيد Alembic تطبيق الـ baseline.

Revision ID: f9000_transport_stamp
Revises: f001_fix_fk
Create Date: 2026-02-22
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "f9000_transport_stamp"
down_revision: Union[str, None] = "f001_fix_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    transport_details موجود فعلاً في DB — لا نُنشئه مجدداً.
    هذا الـ migration وثائقي فقط، يُثبّت نقطة الـ stamp.
    """
    # تحقق أن الجدول موجود فعلاً، إذا لم يكن موجوداً أنشئه
    conn = op.get_bind()
    tables = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name='transport_details'")
    ).fetchall()

    if not tables:
        # الجدول غير موجود — أنشئه (حالة DB نظيفة جديدة)
        op.create_table(
            "transport_details",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("carrier_company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
            sa.Column("truck_plate", sa.String(32), nullable=True),
            sa.Column("driver_name", sa.String(128), nullable=True),
            sa.Column("loading_place", sa.String(255), nullable=True),
            sa.Column("delivery_place", sa.String(255), nullable=True),
            sa.Column("shipment_date", sa.Date(), nullable=True),
            sa.Column("certificate_no", sa.String(64), nullable=True),
            sa.Column("issuing_authority", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        )
        with op.batch_alter_table("transport_details") as batch_op:
            batch_op.create_index("ix_transport_details_transaction_id", ["transaction_id"], unique=True)


def downgrade() -> None:
    op.drop_table("transport_details")
