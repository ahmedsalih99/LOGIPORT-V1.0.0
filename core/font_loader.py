"""
core/font_loader.py — LOGIPORT
================================
نظام تحميل الخطوط المدمجة في التطبيق.

الاستخدام:
    from core.font_loader import load_app_fonts
    load_app_fonts()   # يُستدعى مرة واحدة في main.py قبل ThemeManager

ترتيب الاستدعاء المطلوب في main.py:
    app = QApplication(sys.argv)
    load_app_fonts()          # ← هنا
    settings.apply_all_settings()  # يستدعي ThemeManager الذي يستخدم الخط

الخطوط المدمجة:
    IBM Plex Sans Arabic — الخط الرئيسي للتطبيق
    Weights: Thin(100), ExtraLight(200), Light(300),
             Regular(400), Medium(500), SemiBold(600), Bold(700)

مسار ملفات الخط:
    resources/fonts/IBMPlexSansArabic-*.ttf
    (مُدمجة في EXE عبر PyInstaller datas)
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# اسم الخط كما يُعرَّف في Qt بعد التسجيل
FONT_FAMILY = "IBM Plex Sans Arabic"

# الخط الاحتياطي إذا فشل التحميل
FALLBACK_FAMILY = "Tajawal"

# أسماء ملفات الخط (بدون مسار)
_FONT_FILES = [
    "IBMPlexSansArabic-Thin.ttf",
    "IBMPlexSansArabic-ExtraLight.ttf",
    "IBMPlexSansArabic-Light.ttf",
    "IBMPlexSansArabic-Regular.ttf",
    "IBMPlexSansArabic-Medium.ttf",
    "IBMPlexSansArabic-SemiBold.ttf",
    "IBMPlexSansArabic-Bold.ttf",
]

_loaded = False   # منع التحميل المكرر


def _get_fonts_dir() -> Path:
    """يُعيد مسار مجلد الخطوط — يعمل في بيئة التطوير وداخل EXE."""
    from core.paths import resource_path
    return Path(resource_path("resources", "fonts"))


def load_app_fonts() -> bool:
    """
    يُحمِّل خطوط IBM Plex Sans Arabic في Qt font database.

    يُعيد True إذا نجح تحميل الخط الرئيسي (Regular على الأقل).
    يُعيد False إذا فشل — التطبيق يستمر بالخط الاحتياطي.

    آمن للاستدعاء أكثر من مرة (idempotent).
    """
    global _loaded
    if _loaded:
        return True

    try:
        from PySide6.QtGui import QFontDatabase
    except ImportError:
        logger.error("PySide6 not available — cannot load fonts")
        return False

    fonts_dir = _get_fonts_dir()
    loaded_count = 0
    failed = []

    for filename in _FONT_FILES:
        font_path = fonts_dir / filename
        if not font_path.exists():
            logger.warning(f"Font file missing: {font_path}")
            failed.append(filename)
            continue

        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id == -1:
            logger.warning(f"Failed to load font: {filename}")
            failed.append(filename)
        else:
            loaded_count += 1
            logger.debug(f"Loaded font: {filename} (id={font_id})")

    if loaded_count == 0:
        logger.error(
            f"No IBM Plex Sans Arabic fonts loaded from {fonts_dir}. "
            f"Falling back to '{FALLBACK_FAMILY}'."
        )
        _loaded = True
        return False

    # تحقق من أن Qt تعرّف على الـ family بعد التسجيل
    families = QFontDatabase.families()
    if FONT_FAMILY not in families:
        # بعض إصدارات Qt تسجّل بأسماء مختلفة — ابحث عن IBM
        ibm_families = [f for f in families if "IBM" in f or "Plex" in f]
        if ibm_families:
            logger.info(f"Font registered as: {ibm_families}")
        else:
            logger.warning(
                f"'{FONT_FAMILY}' not found in Qt font database after loading "
                f"{loaded_count} files. Check font file validity."
            )

    if failed:
        logger.warning(f"Failed to load {len(failed)} font weight(s): {failed}")

    logger.debug(
        f"IBM Plex Sans Arabic: {loaded_count}/{len(_FONT_FILES)} weights loaded"
    )
    _loaded = True
    return True


def get_loaded_family() -> str:
    """
    يُعيد اسم الـ family المتاح فعلاً في Qt.
    يُستخدم في ThemeManager كـ fallback آمن.
    """
    try:
        from PySide6.QtGui import QFontDatabase
        families = QFontDatabase.families()
        if FONT_FAMILY in families:
            return FONT_FAMILY
        # ابحث عن أي IBM Plex
        for f in families:
            if "IBM" in f and "Plex" in f:
                return f
    except Exception:
        pass
    return FALLBACK_FAMILY