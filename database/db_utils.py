from __future__ import annotations

from pathlib import Path
import shutil
import datetime
from typing import Optional, Union
import os

# اسم قاعدة البيانات الافتراضي
DEFAULT_DB_NAME = "logiport.db"


# -----------------------------
# Datetime utilities
# -----------------------------

def utc_to_local(dt: datetime.datetime) -> datetime.datetime:
    """
    يحوّل datetime مخزّن بـ UTC (naive) إلى التوقيت المحلي للجهاز.
    يستخدم في العرض فقط — لا في الحفظ.
    """
    if dt is None:
        return dt
    # أضف tzinfo=UTC ثم حوّل للتوقيت المحلي ثم اسحب tzinfo
    import datetime as _dt
    utc_aware = dt.replace(tzinfo=_dt.timezone.utc)
    return utc_aware.astimezone().replace(tzinfo=None)


def format_local_dt(dt: datetime.datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """
    يعرض datetime بالتوقيت المحلي. الاستخدام:
        format_local_dt(row.timestamp)           → "2024-01-15 14:30"
        format_local_dt(row.created_at, "%H:%M") → "14:30"
    """
    if dt is None:
        return "—"
    return utc_to_local(dt).strftime(fmt)


def utc_now() -> datetime.datetime:
    """
    المصدر الوحيد للوقت الحالي في المشروع.

    - يُرجع datetime naive (بدون tzinfo) بتوقيت UTC
    - متوافق مع SQLite الذي لا يدعم timezone-aware datetimes
    - يجب استخدام هذه الدالة في كل مكان بدلاً من:
        datetime.utcnow()          ← deprecated في Python 3.12
        datetime.now()             ← يُرجع التوقيت المحلي
        datetime.now(timezone.utc) ← aware datetime — مشكلة مع SQLite
    """
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


# -----------------------------
# Helpers
# -----------------------------

def _read_settings():
    """حاول قراءة الإعدادات بدون خلق اعتمادية دائرية.
    ترجع None إذا لم تتوفر SettingsManager بعد (مثلاً أثناء التهيئة المبكرة).
    """
    try:
        from core.settings_manager import SettingsManager  # import داخل الدالة لتجنب الدوران
        return SettingsManager.get_instance()
    except Exception:
        return None


# -----------------------------
# DB Path utilities
# -----------------------------

from core.paths import get_user_data_dir

def get_db_path() -> Path:
    """
    Always return database path inside AppData.
    Single source of truth.
    """
    base_dir = get_user_data_dir()
    return base_dir / DEFAULT_DB_NAME

def ensure_db_dir() -> Path:
    """أنشئ مجلد قاعدة البيانات إن لزم وأعد المسار الكامل للملف."""
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_default_db_path() -> Path:
    """أعد المسار الافتراضي (CWD + db_name) بدون اعتبار db_path المخصص."""
    sm = _read_settings()
    name = (sm.get("db_name", DEFAULT_DB_NAME) if sm else DEFAULT_DB_NAME) or DEFAULT_DB_NAME
    return (Path.cwd() / name).resolve()


# -----------------------------
# DB existence / init
# -----------------------------

def db_exists() -> bool:
    """تحقق من وجود ملف قاعدة البيانات فعليًا."""
    return get_db_path().is_file()


def init_db_if_not_exists() -> Path:
    """إنشاء قاعدة البيانات إن لم تكن موجودة، باستدعاء database.models.init_db().
    يعيد المسار النهائي للملف.
    """
    path = ensure_db_dir()
    if not path.exists():
        # نفترض أن الحِزمة database.models توفّر init_db() على مستوى الحزمة
        from database.models import init_db  # noqa: WPS433 (import inside function)
        init_db()
    return path


# -----------------------------
# Maintenance: backup/restore/delete/size
# -----------------------------


def get_db_size() -> int:
    """حجم القاعدة بالبايت. يرجع 0 إذا لم تكن موجودة."""
    p = get_db_path()
    try:
        return p.stat().st_size
    except FileNotFoundError:
        return 0


# -----------------------------
# SQLAlchemy Engine / Session
# -----------------------------
# مُفوَّض بالكامل إلى database.models.base  (مصدر الحقيقة الوحيد)
# هذا يضمن: Singleton engine + expire_on_commit=False + check_same_thread=False

def get_engine():
    """Singleton engine — مُفوَّض إلى models.base."""
    from database.models.base import get_engine as _get_engine
    return _get_engine()


def get_session_local():
    """Singleton sessionmaker — مُفوَّض إلى models.base."""
    from database.models.base import get_session_local as _gsl
    return _gsl()


def reset_engine():
    """أعد تهيئة الـ engine عند تغيير مسار DB."""
    from database.models.base import reset_engine as _reset
    _reset()