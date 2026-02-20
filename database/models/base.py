"""
database/models/base.py
========================
مصدر الحقيقة الوحيد لـ Base و Engine و SessionFactory.

المبادئ:
  - Base   واحد فقط عبر المشروع كله
  - Engine واحد فقط (Singleton) — لا يُنشأ engine جديد في كل استدعاء
  - get_session_local() يُرجع دائماً نفس sessionmaker المحفوظة
  - check_same_thread=False  : مطلوب لأن PySide6 يفتح الـ UI من خيط رئيسي
                               بينما قد يستدعي CRUD من خيوط أخرى
  - expire_on_commit=False   : يمنع DetachedInstanceError عندما تُستخدم الكائنات
                               في الـ UI بعد إغلاق الجلسة
"""

from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

# ─── Singleton ──────────────────────────────────────────────────────────────
Base = declarative_base()

_engine       = None
_SessionLocal = None


def get_engine():
    """
    يُرجع engine واحد (Singleton).
    يُنشأ مرة واحدة فقط — أي استدعاء لاحق يُعيد نفس الكائن.
    """
    global _engine
    if _engine is None:
        from database.db_utils import get_db_path
        _engine = create_engine(
            f"sqlite:///{get_db_path()}",
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session_local():
    """
    يُرجع sessionmaker واحد (Singleton).

    الاستخدام الصحيح الموحَّد:
        # داخل CRUD (عبر get_session context manager):
        super().__init__(MyModel, get_session_local)   ← callable بدون ()

        # مباشرة في UI أو services:
        with get_session_local()() as session:          ← ()() لفتح session
    """
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,   # ← يمنع DetachedInstanceError في UI
        )
    return _SessionLocal


def reset_engine():
    """
    أعد تهيئة الـ engine والـ sessionmaker.
    استخدمها فقط عند تغيير مسار قاعدة البيانات أثناء التشغيل.
    """
    global _engine, _SessionLocal
    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            pass
    _engine       = None
    _SessionLocal = None