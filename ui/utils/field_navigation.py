"""
ui/utils/field_navigation.py — LOGIPORT
=========================================
نظام التنقل بين حقول الـ dialogs وتبديل لغة الكيبورد.

الميزات:
  1. Enter/Return → ينتقل للحقل التالي (Tab behavior)
     Shift+Enter    → ينتقل للحقل السابق
  2. تبديل لغة الكيبورد تلقائياً عند focus الحقل
  3. InputMethodHints على كل حقل (يساعد IME)
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QWidget, QLineEdit, QAbstractSpinBox, QDateEdit,
)

logger = logging.getLogger(__name__)

# ── مجموعات حقول حسب نوع الإدخال المتوقع ─────────────────────────────────────
_AR_KEYWORDS = frozenset({
    # attribute names
    "name_ar", "ar_name", "arabic", "notes", "address", "city_ar",
    "description", "description_ar", "city", "full_name",
    # placeholder i18n keys
    "arabic_name", "client_name_ar", "company_name_ar", "name_in_arabic",
})
_EN_KEYWORDS = frozenset({
    # attribute names
    "name_en", "en_name", "name_tr", "tr_name", "english", "turkish",
    "code", "phone", "mobile", "fax", "email", "website", "url",
    "number", "no", "ref", "id", "username", "password",
    "transport_ref", "bl_number", "booking", "vessel", "container_no",
    "batch_no", "seal_no", "entry_no", "transaction_no",
    "account", "iban", "swift", "tax_id", "tax", "registration",
    "cmr_number", "booking_no", "voyage_no", "shipping_line",
    # placeholder i18n keys
    "english_name", "turkish_name", "client_code", "client_name_en",
    "company_code", "port_of_loading", "port_of_discharge",
})

_KL_ARABIC  = "00000401"  # Arabic (Saudi Arabia)
_KL_ENGLISH = "00000409"  # English (US)

_win_user32 = None
_last_layout: Optional[str] = None   # avoid redundant switches


def _get_user32():
    global _win_user32
    if _win_user32 is not None:
        return _win_user32
    if sys.platform != "win32":
        _win_user32 = False
        return None
    try:
        import ctypes
        _win_user32 = ctypes.windll.user32
    except Exception:
        _win_user32 = False
    return _win_user32 or None


def _switch_keyboard(layout_id: str) -> bool:
    """يبدّل لغة الكيبورد على Windows."""
    global _last_layout
    if _last_layout == layout_id:
        return True   # already set
    user32 = _get_user32()
    if not user32:
        return False
    try:
        KLF_ACTIVATE = 0x00000001
        WM_INPUTLANGCHANGEREQUEST = 0x0050
        HWND_BROADCAST = 0xFFFF
        hkl = user32.LoadKeyboardLayoutW(layout_id, KLF_ACTIVATE)
        if hkl:
            user32.PostMessageW(HWND_BROADCAST, WM_INPUTLANGCHANGEREQUEST, 0, hkl)
            _last_layout = layout_id
            return True
    except Exception as e:
        logger.debug("keyboard switch failed: %s", e)
    return False


def _detect_lang(widget: QLineEdit) -> Optional[str]:
    """يحدد اللغة المتوقعة بناءً على objectName أو placeholderText."""
    name = (widget.objectName() or "").lower().replace("-", "_")
    placeholder = (widget.placeholderText() or "").lower()
    combined = name + " " + placeholder

    for kw in _AR_KEYWORDS:
        if kw in combined:
            return "ar"
    for kw in _EN_KEYWORDS:
        if kw in combined:
            return "en"

    # placeholder يحتوي عربي؟
    if any("\u0600" <= c <= "\u06FF" for c in placeholder):
        return "ar"

    return None


def _apply_hints(widget: QLineEdit, lang: Optional[str]) -> None:
    """يضبط Qt InputMethodHints."""
    if lang == "en":
        widget.setInputMethodHints(
            Qt.InputMethodHint.ImhPreferLatin |
            Qt.InputMethodHint.ImhNoAutoUppercase
        )
    else:
        widget.setInputMethodHints(Qt.InputMethodHint.ImhNone)


class _FieldNavFilter(QObject):
    """
    Event filter:
    - Enter → next field
    - Shift+Enter → previous field
    - FocusIn on QLineEdit → switch keyboard language
    """

    def __init__(self, root: QWidget):
        super().__init__(root)
        self._root = root

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        etype = event.type()

        # Enter → Tab navigation
        if etype == QEvent.Type.KeyPress:
            if isinstance(obj, (QLineEdit, QAbstractSpinBox, QDateEdit)):
                key = event.key()
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    mods = event.modifiers()
                    if mods & Qt.KeyboardModifier.ShiftModifier:
                        self._root.focusPreviousChild()
                    else:
                        self._root.focusNextChild()
                    return True

        # FocusIn → keyboard language
        if etype == QEvent.Type.FocusIn:
            if isinstance(obj, QLineEdit) and not obj.isReadOnly():
                lang = _detect_lang(obj)
                _apply_hints(obj, lang)
                if lang == "ar":
                    _switch_keyboard(_KL_ARABIC)
                elif lang == "en":
                    _switch_keyboard(_KL_ENGLISH)

        return False


def _auto_set_object_names(root: QWidget) -> None:
    """
    يُعيِّن objectName على QLineEdit من اسم الـ attribute في الـ dialog.
    مثال: self.name_ar = QLineEdit() → objectName = "name_ar"
    """
    if not hasattr(root, "__dict__"):
        return
    for attr_name, attr_val in vars(root).items():
        if isinstance(attr_val, QLineEdit) and not attr_val.objectName():
            attr_val.setObjectName(attr_name)


def setup_field_ux(root: QWidget) -> _FieldNavFilter:
    """
    يُثبِّت Enter navigation + keyboard switch على dialog.
    يُستدعى في showEvent أو آخر __init__.
    """
    # أولاً: عيِّن objectName من أسماء الـ attributes تلقائياً
    _auto_set_object_names(root)

    filt = _FieldNavFilter(root)

    # خزِّن في root لمنع garbage collection
    root._field_nav_filter = filt

    for child in root.findChildren(QWidget):
        if isinstance(child, (QLineEdit, QAbstractSpinBox, QDateEdit)):
            child.installEventFilter(filt)

    return filt
