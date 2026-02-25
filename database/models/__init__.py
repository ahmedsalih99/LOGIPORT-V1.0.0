from .base import Base, get_engine, get_session_local

# ---- Core models ---------------------------------------------------------
from .user import User
from .role import Role
from .country import Country
from .packaging_type import PackagingType
from .currency import Currency
from .material_type import MaterialType
from .permission import Permission
from .role_permission import RolePermission
from .audit_log import AuditLog
from .material import Material
from .client import Client, ClientContact
from .company import Company
from .pricing_type import PricingType
from .delivery_method import DeliveryMethod
from .pricing import Pricing
from .entry import Entry
from .entry_item import EntryItem
from .transaction import Transaction
from .transport_details import TransportDetails

# ---- Optional/where-available models ------------------------------------
# TransactionItem قد يكون في ملف مستقل أو ضمن transaction.py
try:
    from .transaction_item import TransactionItem  # type: ignore
except Exception:  # pragma: no cover
    try:
        from .transaction import TransactionItem  # type: ignore
    except Exception:
        TransactionItem = None  # type: ignore

# توافق خلفي مع كود قديم يستورد TransactionItems
TransactionItems = TransactionItem  # type: ignore

# وثائق
try:
    from .document_group import DocumentGroup  # type: ignore
except Exception:
    DocumentGroup = None  # type: ignore

try:
    from .document_type import DocumentType  # type: ignore
except Exception:
    DocumentType = None  # type: ignore

try:
    from .document import Document, DocumentTemplate  # type: ignore
except Exception:
    Document = DocumentTemplate = None  # type: ignore

__all__ = [
    # session / base
    "Base", "get_engine", "get_session_local",
    # main models
    "User", "Role", "Country", "PackagingType", "Currency", "MaterialType", "Permission",
    "RolePermission", "AuditLog", "Material", "Client", "ClientContact", "Company",
    "PricingType", "DeliveryMethod", "Pricing", "Entry", "EntryItem", "Transaction",
    # optional
    "TransactionItem", "TransactionItems", "DocumentGroup", "DocumentType", "Document", "DocumentTemplate",
]

import sqlite3 as _sqlite3
from sqlalchemy import event as _sa_event
from sqlalchemy.engine import Engine as _Engine

@_sa_event.listens_for(_Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):
    """يفعّل foreign_keys في كل اتصال SQLite جديد — مطلوب لعمل ON DELETE CASCADE."""
    if isinstance(dbapi_conn, _sqlite3.Connection):
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

def init_db():
    """إنشاء جميع الجداول."""
    Base.metadata.create_all(bind=get_engine())


def recreate_engine_and_session():
    """
    استدعي هذه الدالة إذا تغير مسار قاعدة البيانات أثناء التشغيل.
    (عادة نادرًا ما تحتاجها إذا كنت تستعمل دوال جلب ديناميكية)
    """
    pass