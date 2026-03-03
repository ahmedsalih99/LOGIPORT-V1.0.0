"""
database/mixins.py
==================
Re-exports DB path/session helpers من database.db_utils (مصدر الحقيقة).
الدوال الخاصة بهذا الملف: backup_db, restore_db, delete_db.
"""
from __future__ import annotations
import logging
import shutil
import datetime
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

# ── Re-exports من db_utils (مصدر الحقيقة الوحيد) ────────────────────────────
from database.db_utils import (          # noqa: F401
    get_db_path,
    ensure_db_dir,
    get_default_db_path,
    db_exists,
    init_db_if_not_exists,
    get_db_size,
    get_engine,
    get_session_local,
    reset_engine,
)


# ── دوال خاصة بـ mixins (غير موجودة في db_utils) ────────────────────────────

def backup_db(dest: Optional[Union[str, Path]] = None) -> Path:
    """أنشئ نسخة احتياطية لملف قاعدة البيانات.

    * إن كان dest مجلدًا: يضع ملفًا باسم {stem}-{YYYYmmdd-HHMMSS}.db
    * إن كان dest ملفًا:   ينسخ إليه مباشرة (يُنشئ المجلد الأب إن لزم)
    * إن كان dest None:    ينشئ ملفًا بجوار القاعدة
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
    """احذف ملف القاعدة (احذر!)."""
    p = get_db_path()
    if p.exists():
        p.unlink()