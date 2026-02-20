"""
core/paths.py — LOGIPORT
=========================
مصدر الحقيقة الوحيد لجميع المسارات في التطبيق.

المبدأ:
  - BASE_DIR / resource_path() → ملفات التطبيق (icons, config, templates)
    - بيئة تطوير: جذر المشروع
    - داخل EXE (PyInstaller): sys._MEIPASS (مجلد temp المستخرج)

  - get_user_data_dir() → بيانات المستخدم القابلة للكتابة
    - Windows: %APPDATA%/LOGIPORT/
    - Linux/Mac: ~/.local/share/LOGIPORT/
    - هذا المجلد لا يتأثر بالـ build أو تحديث التطبيق

الاستخدام:
    from core.paths import resource_path, get_user_data_dir, BASE_DIR

    # موارد التطبيق (للقراءة فقط):
    logo = resource_path("icons", "logo.png")
    template = resource_path("documents", "templates", "invoice.html")

    # بيانات المستخدم (للقراءة والكتابة):
    db_path = Path(get_user_data_dir()) / "logiport.db"
    settings = Path(get_user_data_dir()) / "settings.json"
"""

import os
import sys
from pathlib import Path


APP_NAME = "LOGIPORT"


# ══════════════════════════════════════════════
# موارد التطبيق (Read-Only)
# ══════════════════════════════════════════════

if getattr(sys, "frozen", False):
    # داخل PyInstaller EXE → الملفات مستخرجة في sys._MEIPASS
    BASE_DIR = Path(sys._MEIPASS)
else:
    # بيئة تطوير → جذر المشروع (core/paths.py → ارتقِ مجلداً)
    BASE_DIR = Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> str:
    """
    يُرجع المسار الكامل لملف مورد داخل التطبيق (icons, config, templates...).

    مثال:
        resource_path("icons", "logo.png")
        → "/path/to/app/icons/logo.png"
    """
    return str(BASE_DIR.joinpath(*parts))


# دوال مساعدة للمسارات الشائعة (موارد)
def icons_path(filename: str = "") -> Path:
    """مسار مجلد الأيقونات أو ملف محدد داخله."""
    p = BASE_DIR / "icons"
    return p / filename if filename else p


def config_path(filename: str = "") -> Path:
    """مسار مجلد الإعدادات أو ملف محدد داخله."""
    p = BASE_DIR / "config"
    return p / filename if filename else p


def documents_path(*parts: str) -> Path:
    """مسار مجلد المستندات (templates, static...)."""
    return BASE_DIR / "documents" / Path(*parts) if parts else BASE_DIR / "documents"


# ══════════════════════════════════════════════
# بيانات المستخدم (Read-Write)
# ══════════════════════════════════════════════

def get_user_data_dir() -> Path:
    """
    يُرجع مجلد بيانات المستخدم (قابل للكتابة دائماً).

    Windows : %APPDATA%/LOGIPORT/
    Linux   : ~/.local/share/LOGIPORT/
    Mac     : ~/.local/share/LOGIPORT/

    يُنشئ المجلد تلقائياً إن لم يكن موجوداً.
    """
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        if not appdata:
            # fallback نادر جداً
            appdata = str(Path.home() / "AppData" / "Roaming")
        base = Path(appdata)
    else:
        base = Path.home() / ".local" / "share"

    user_dir = base / APP_NAME
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def logs_path(filename: str = "") -> Path:
    """مسار مجلد السجلات داخل بيانات المستخدم."""
    p = get_user_data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p / filename if filename else p


def backups_path(filename: str = "") -> Path:
    """مسار مجلد النسخ الاحتياطية داخل بيانات المستخدم."""
    p = get_user_data_dir() / "backups"
    p.mkdir(parents=True, exist_ok=True)
    return p / filename if filename else p