"""
Database Utilities - LOGIPORT
Utility functions for database path management and backups
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


from pathlib import Path
import shutil
import datetime
from typing import Optional, Union

# اسم قاعدة البيانات الافتراضي
DEFAULT_DB_NAME = "logiport.db"


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

def get_db_path() -> Path:
    """أعد مسار ملف قاعدة البيانات النهائي.

    المنطق:
      - إذا كان لدى SettingsManager قيمة "db_path":
          * لو كانت مجلدًا → نركّب اسم الملف باستخدام "db_name" أو الافتراضي.
          * لو كانت ملفًا (مع/بدون لاحقة) → نستعمله كما هو.
      - خلاف ذلك نستخدم مجلد العمل الحالي + اسم الملف (db_name أو الافتراضي).
    """
    sm = _read_settings()
    db_name = DEFAULT_DB_NAME
    custom_path: Optional[Union[str, Path]] = None

    if sm:
        # ملاحظة: لو كانت القيمة فارغة، نرجع للاسم الافتراضي
        db_name = sm.get("db_name", DEFAULT_DB_NAME) or DEFAULT_DB_NAME
        custom_path = sm.get("db_path")

    if custom_path:
        p = Path(str(custom_path)).expanduser()
        # إن كانت مجلدًا، اسم الملف يبنى من db_name
        if p.is_dir():
            return (p / db_name).resolve()
        # إن كانت مسارًا لملف، نستعمله مباشرة
        return p.resolve()

    # الافتراضي: مجلد العمل الحالي + db_name
    return (Path.cwd() / db_name).resolve()


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

def backup_db(dest: Optional[Union[str, Path]] = None) -> Path:
    """أنشئ نسخة احتياطية لملف قاعدة البيانات.

    * إن كان dest مجلدًا: نضع ملفًا داخله باسم {stem}-{YYYYmmdd-HHMMSS}.db
    * إن كان dest ملفًا: ننسخ إليه مباشرة (ويتم إنشاء المجلد الأب إن لزم)
    * إن كان dest None: ننشئ ملفًا بجوار القاعدة باسم {stem}.bak-YYYYmmdd-HHMMSS.db
    """
    src = get_db_path()
    if not src.exists():
        raise FileNotFoundError(f"Database file not found: {src}")

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    if dest is None:
        backup = src.with_name(f"{src.stem}.bak-{ts}{src.suffix}")
    else:
        p = Path(str(dest)).expanduser().resolve()
        if p.is_dir():
            backup = p / f"{src.stem}-{ts}{src.suffix}"
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            backup = p

    shutil.copy2(src, backup)
    return backup


def restore_db(backup_file: Union[str, Path]) -> Path:
    """استعد القاعدة من ملف نسخة احتياطية."""
    backup = Path(str(backup_file)).expanduser().resolve()
    if not backup.is_file():
        raise FileNotFoundError(f"Backup not found: {backup}")

    dst = ensure_db_dir()
    shutil.copy2(backup, dst)
    return dst


def delete_db() -> None:
    """احذف ملف القاعدة (حذر!)."""
    p = get_db_path()
    if p.exists():
        p.unlink()


def get_db_size() -> int:
    """حجم القاعدة بالبايت. يرجع 0 إذا لم تكن موجودة."""
    p = get_db_path()
    try:
        return p.stat().st_size
    except FileNotFoundError:
        return 0