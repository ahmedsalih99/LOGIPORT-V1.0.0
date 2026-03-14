import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

# اسم مجلد النسخ الاحتياطية
BACKUP_DIR_NAME = "backups"
MAX_BACKUPS     = 30   # الحد الأقصى للنسخ الاحتياطية المحفوظة


# --------------------------------------------------
# Internal Helpers
# --------------------------------------------------

def _get_db_path() -> Path:
    """
    Always return the correct database path.
    """
    try:
        from database.db_utils import get_db_path
        return get_db_path()
    except Exception as e:
        raise RuntimeError(f"Cannot resolve database path: {e}")



def _backup_dir() -> Path:
    """
    يُرجع مجلد النسخ الاحتياطية داخل AppData.
    """
    try:
        from core.paths import backups_path
        return backups_path()
    except Exception:
        # fallback: بجانب قاعدة البيانات
        db_path = _get_db_path()
        backup_dir = db_path.parent / BACKUP_DIR_NAME
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir


# --------------------------------------------------
# Internal helpers
# --------------------------------------------------

def _cleanup_old_backups(db_stem: str) -> None:
    """يحذف النسخ الاحتياطية القديمة إذا تجاوز عددها MAX_BACKUPS. يحتفظ بالأحدث دائماً."""
    backup_dir = _backup_dir()
    files = sorted(
        backup_dir.glob(f"{db_stem}_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old_file in files[MAX_BACKUPS:]:
        try:
            old_file.unlink()
            logger.info("Old backup removed: %s", old_file.name)
        except Exception as e:
            logger.warning("Could not remove old backup %s: %s", old_file, e)


# --------------------------------------------------
# Public API
# --------------------------------------------------

def backup(dest: Optional[Path] = None) -> Path:
    """
    Create a timestamped backup of the database.

    Returns:
        Path to the new backup file.

    Raises:
        FileNotFoundError if database doesn't exist.
    """

    src = _get_db_path()

    if not src.exists():
        raise FileNotFoundError(f"Database not found: {src}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if dest is None:
        dest = _backup_dir() / f"{src.stem}_backup_{timestamp}{src.suffix}"
    else:
        dest = Path(dest)

    shutil.copy2(src, dest)

    logger.info(f"Backup created: {dest} ({dest.stat().st_size / 1024:.1f} KB)")

    # حذف النسخ القديمة إذا تجاوزنا الحد الأقصى
    try:
        _cleanup_old_backups(src.stem)
    except Exception as _ce:
        logger.warning("Backup cleanup failed (non-critical): %s", _ce)

    return dest


def list_backups() -> List[Path]:
    """
    Return list of backup files sorted newest-first.
    """

    backup_dir = _backup_dir()

    files = sorted(
        backup_dir.glob("*_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    return files


def restore(backup_path: Path) -> Path:
    """
    Restore the database from a backup file.

    Safety:
        Automatically creates a safety copy before restore.

    Returns:
        Path to restored database.
    """

    backup_path = Path(backup_path)

    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    dst = _get_db_path()

    # 🔐 Safety copy before overwrite
    if dst.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_backup = dst.with_name(
            f"{dst.stem}_before_restore_{timestamp}{dst.suffix}"
        )
        shutil.copy2(dst, safety_backup)
        logger.info(f"Safety backup created: {safety_backup}")

    shutil.copy2(backup_path, dst)
    logger.info(f"Database restored from {backup_path} → {dst}")

    return dst


def get_db_info() -> dict:
    """
    Return detailed information about the database.
    """

    try:
        db_path = _get_db_path()

        if not db_path.exists():
            return {
                "path": str(db_path),
                "exists": False
            }

        stat = db_path.stat()

        return {
            "path": str(db_path),
            "exists": True,
            "size_bytes": stat.st_size,
            "size_kb": round(stat.st_size / 1024, 2),
            "last_modified": datetime.fromtimestamp(
                stat.st_mtime
            ).strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }