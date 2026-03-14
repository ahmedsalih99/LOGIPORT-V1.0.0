"""
database/models/base.py
========================
مصدر الحقيقة الوحيد لـ Base و Engine و SessionFactory.

إعدادات multi-user / multi-office:
  - WAL journal mode   : القراءة والكتابة في نفس الوقت بدون حجب
  - busy_timeout=5000  : ينتظر 5 ثوانٍ بدل "database is locked" فوراً
  - foreign_keys=ON    : يُفعَّل على كل connection جديد
  - check_same_thread=False : PySide6 يستدعي CRUD من خيوط متعددة
  - expire_on_commit=False  : يمنع DetachedInstanceError في الـ UI
"""

import logging
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine, event

logger = logging.getLogger(__name__)

Base = declarative_base()
_engine       = None
_SessionLocal = None


def _apply_sqlite_pragmas(dbapi_connection, connection_record):
    """يُطبَّق على كل connection جديد — يضمن WAL + FK + timeout على كل thread."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA busy_timeout = 5000")
        cursor.execute("PRAGMA cache_size = -8000")
        cursor.execute("PRAGMA temp_store = MEMORY")
        cursor.execute("PRAGMA mmap_size = 134217728")
        cursor.execute("PRAGMA wal_autocheckpoint = 1000")
    except Exception as e:
        logger.warning("SQLite PRAGMA setup failed: %s", e)
    finally:
        cursor.close()


def get_engine():
    """يُرجع engine واحد (Singleton) مع WAL + FK enforcement."""
    global _engine
    if _engine is None:
        from database.db_utils import get_db_path
        _engine = create_engine(
            f"sqlite:///{get_db_path()}",
            echo=False,
            future=True,
            connect_args={
                "check_same_thread": False,
                "timeout": 10,
            },
            pool_timeout=10,
            pool_pre_ping=True,
        )
        event.listen(_engine, "connect", _apply_sqlite_pragmas)
        logger.info("Database engine created with WAL + FK enforcement")
    return _engine


def get_session_local():
    """يُرجع sessionmaker واحد (Singleton)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def reset_engine():
    """أعد تهيئة الـ engine عند تغيير مسار قاعدة البيانات."""
    global _engine, _SessionLocal
    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            pass
    _engine       = None
    _SessionLocal = None
    logger.info("Database engine reset")
