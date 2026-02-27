"""
user_utils.py — LOGIPORT
========================
دوال مساعدة مشتركة للتعامل مع كائن المستخدم الحالي.
تُستخدم من BaseWindow وBaseDialog وأي مكان آخر يحتاج استخراج المستخدم.
"""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_current_user(settings=None) -> Any:
    """
    استخراج المستخدم الحالي من QApplication أو SettingsManager.

    الأولوية:
        1. QApplication.property("user")  — الأسرع والأحدث دائماً
        2. settings.get("user")           — fallback إذا لم يُعيَّن في التطبيق

    Returns:
        User object أو {}
    """
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            user = app.property("user")
            if user:
                return user
    except Exception as e:
        logger.debug(f"get_current_user: QApplication lookup failed: {e}")

    try:
        if settings is not None:
            user = settings.get("user")
            if user:
                return user
    except Exception as e:
        logger.debug(f"get_current_user: settings lookup failed: {e}")

    return {}


def get_user_display_name(user: Any) -> str:
    """
    إرجاع الاسم المعروض للمستخدم بصيغة موحّدة.

    Returns:
        "full_name#id" أو "username#id" أو "Unknown"
    """
    if not user:
        return "Unknown"
    try:
        if isinstance(user, dict):
            name = user.get("full_name") or user.get("username") or "Unknown"
            uid = user.get("id", "?")
        else:
            name = (
                getattr(user, "full_name", None)
                or getattr(user, "username", None)
                or "Unknown"
            )
            uid = getattr(user, "id", "?")
        return f"{name}#{uid}"
    except Exception:
        return "Unknown"


def get_user_id(user: Any) -> Optional[int]:
    """
    إرجاع ID المستخدم بأمان سواء كان ORM object أو dict.
    """
    if not user:
        return None
    try:
        if isinstance(user, dict):
            return user.get("id")
        return getattr(user, "id", None)
    except Exception:
        return None


def format_user_log_prefix(user: Any, class_name: str = "") -> str:
    """
    بناء بادئة الـ log الموحّدة بصيغة: "ClassName: [User: name#id]"
    تُستخدم في log_event داخل BaseWindow وBaseDialog.
    """
    display = get_user_display_name(user)
    prefix = f"{class_name}: " if class_name else ""
    return f"{prefix}[User: {display}]"
