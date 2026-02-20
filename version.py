"""
version.py — LOGIPORT
======================
مصدر الحقيقة الوحيد لرقم الإصدار.
يُستخدم في:
  - واجهة المستخدم (About dialog)
  - نظام التحديثات
  - Inno Setup installer
"""

APP_NAME    = "LOGIPORT"
VERSION     = "1.0.0"
BUILD       = "2026.02.20"
GITHUB_REPO = "ahmedsalih99/LOGIPORT"   # ← غيّر هذا

# URL يتحقق منه نظام التحديثات
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# URL تحميل الـ installer الجديد (يُبنى تلقائياً من الـ release)
# المتغير {version} يُستبدل برقم الإصدار الجديد
DOWNLOAD_URL_TEMPLATE = (
    f"https://github.com/{GITHUB_REPO}/releases/download/v{{version}}/LOGIPORT_Setup_{{version}}.exe"
)
