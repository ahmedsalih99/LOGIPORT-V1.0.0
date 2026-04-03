"""
version.py — LOGIPORT
======================
مصدر الحقيقة الوحيد لرقم الإصدار.
يُستخدم في:
  - واجهة المستخدم (About dialog)
  - نظام التحديثات
  - Inno Setup installer
  - PyInstaller spec
"""
from datetime import datetime

APP_NAME    = "LOGIPORT"
VERSION     = "1.0.0"
BUILD       = datetime.now().strftime("%Y-%m-%d")

# tuple للمقارنة السريعة: (1, 0, 0)
VERSION_TUPLE = tuple(int(x) for x in VERSION.split("."))

GITHUB_REPO = "ahmedsalih99/LOGIPORT-V1.0.0"

# URL يتحقق منه نظام التحديثات
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# URL تحميل الـ installer الجديد
DOWNLOAD_URL_TEMPLATE = (
    f"https://github.com/{GITHUB_REPO}/releases/download/v{{version}}/LOGIPORT_Setup_{{version}}.exe"
)

# معلومات النظام للعرض
APP_FULL_NAME    = f"{APP_NAME} v{VERSION}"
APP_DESCRIPTION  = "نظام إدارة اللوجستيات"
APP_COPYRIGHT    = f"© 2026 {APP_NAME}"