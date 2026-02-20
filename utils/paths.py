"""
utils/paths.py — LOGIPORT
==========================
⚠️  هذا الملف للتوافق مع الكود القديم فقط (backward compatibility).
    مصدر الحقيقة الوحيد: core/paths.py
"""

import sys
import importlib.util
from pathlib import Path


def _load_core_paths():
    """
    يُحمّل core/paths.py مباشرة بتجاوز core/__init__.py
    يعمل في:
      - بيئة التطوير (Python عادي)
      - داخل PyInstaller EXE (sys._MEIPASS)
    """
    if "core.paths" in sys.modules:
        return sys.modules["core.paths"]

    # تحديد مسار core/paths.py
    if getattr(sys, "frozen", False):
        # داخل EXE — الملفات في sys._MEIPASS
        base = Path(sys._MEIPASS)
    else:
        # بيئة تطوير — نصعد من utils/ إلى جذر المشروع
        base = Path(__file__).resolve().parent.parent

    paths_file = base / "core" / "paths.py"

    spec = importlib.util.spec_from_file_location("core.paths", paths_file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["core.paths"] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_core_paths()

# إعادة تصدير
APP_NAME      = _mod.APP_NAME
BASE_DIR      = _mod.BASE_DIR
resource_path = _mod.resource_path
get_user_data_dir = _mod.get_user_data_dir
icons_path    = _mod.icons_path
config_path   = _mod.config_path
documents_path = _mod.documents_path
logs_path     = _mod.logs_path
backups_path  = _mod.backups_path

__all__ = [
    "APP_NAME", "BASE_DIR", "resource_path", "get_user_data_dir",
    "icons_path", "config_path", "documents_path", "logs_path", "backups_path",
]