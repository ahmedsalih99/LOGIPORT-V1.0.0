"""fix_transaction_items_fk_broken_reference

ترقيع المشكلة التي وثّقها scripts/migration_fix_fk.py:
  - transaction_items.transaction_id كان يشير لـ transactions_old (غير موجود)
  - transaction_entries.transaction_id نفس المشكلة
  → CASCADE لم يكن يعمل قط

هذا الـ migration يُعيد بناء الجدولين بـ FK صحيح يشير لـ transactions.

Revision ID: f001_fix_fk
Revises: 4f425d1a4c0a
Create Date: 2026-02-22

"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f001_fix_fk"
down_revision: Union[str, None] = "4f425d1a4c0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    يُعيد بناء transaction_items و transaction_entries بـ FK صحيح.
    render_as_batch=True في env.py يجعل هذا يعمل على SQLite
    عبر CREATE TABLE new / INSERT / DROP / RENAME.
    """
    # ── transaction_items ─────────────────────────────────────────────────────
    with op.batch_alter_table("transaction_items", recreate="always") as batch_op:
        batch_op.drop_constraint(
            "fk_transaction_items_transaction_id", type_="foreignkey"
        ) if False else None   # SQLite لا يدعم drop_constraint، batch يتولى الأمر

    # إعادة بناء الجدول كاملاً بـ FK صحيح
    with op.batch_alter_table(
        "transaction_items",
        recreate="always",
    ) as batch_op:
        batch_op.create_foreign_key(
            "fk_ti_transaction_id",
            "transactions",
            ["transaction_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # ── transaction_entries ───────────────────────────────────────────────────
    with op.batch_alter_table(
        "transaction_entries",
        recreate="always",
    ) as batch_op:
        batch_op.create_foreign_key(
            "fk_te_transaction_id",
            "transactions",
            ["transaction_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_te_entry_id",
            "entries",
            ["entry_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    """
    SQLite لا يدعم حذف FKs مباشرة.
    downgrade هنا وثائقي فقط — لا تستخدمه على بيانات إنتاج.
    """
    pass
