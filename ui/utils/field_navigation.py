"""
ui/utils/field_navigation.py — LOGIPORT
=========================================
نظام التنقل بين حقول الـ dialogs وتبديل لغة الكيبورد.

الميزات:
  1. Enter/Return → ينتقل للحقل التالي (Tab behavior)
     Shift+Enter    → ينتقل للحقل السابق
  2. تبديل لغة الكيبورد تلقائياً عند focus الحقل
  3. InputMethodHints على كل حقل (يساعد IME)
  4. [توسعة] تغطية كاملة: dialogs + tabs + objectName المخصصة
  5. [توسعة] fallback ذكي: يشوف محتوى الحقل الحالي إذا لم يُحدَّد
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
    # أسماء attributes
    "name_ar", "ar_name", "arabic", "notes",
    "city_ar", "description", "description_ar", "full_name",
    "address_ar", "notes_ar", "city_name",   # address_ar فقط — مش address العامة
    "edit_label_ar",
    # أسماء objectName مخصصة
    "driver-name-input",        # txt_driver_name في transport_tab
    "loading-place-input",      # txt_loading_place
    "delivery-place-input",     # txt_delivery_place
    "issuing-authority-input",  # txt_issuing_authority
    # مفاتيح i18n
    "arabic_name", "client_name_ar", "company_name_ar", "name_in_arabic",
    "driver_name", "loading_place", "delivery_place", "issuing_authority",
})

_EN_KEYWORDS = frozenset({
    # أسماء attributes
    "name_en", "en_name", "name_tr", "tr_name", "english", "turkish",
    "code", "phone", "mobile", "fax", "email", "website", "url",
    "number", "no", "ref", "id", "username", "password",
    "transport_ref", "bl_number", "booking", "vessel", "container_no",
    "batch_no", "seal_no", "entry_no", "transaction_no",
    "account", "iban", "swift", "tax_id", "tax", "registration",
    "cmr_number", "booking_no", "voyage_no", "shipping_line",
    "registration_number", "symbol", "website", "bank_name",
    "branch", "beneficiary_name", "swift_bic", "account_number",
    "port_of_loading", "port_of_discharge", "final_destination",
    "address_en", "address_tr",               # عناوين إنجليزي/تركي
    "city",                                   # اسم المدينة — إنجليزي
    "edit_label_en", "edit_label_tr", "edit_username",
    # أسماء objectName مخصصة
    "truck-plate-input",        # txt_truck_plate في transport_tab
    "certificate-no-input",     # txt_certificate_no
    "transaction-number-input", # txt_trx_no
    "form-input",               # cmr_no, cmr2_no, cmr2_label
    "attached-docs-input",      # txt_attached_docs
    # مفاتيح i18n
    "english_name", "turkish_name", "client_code", "client_name_en",
    "company_code", "port_of_loading_label", "port_of_discharge_label",
    "bl_number", "seal_no_label", "transport_ref_label",
    "cmr_number_label", "certificate_no", "truck_plate",
})

_KL_ARABIC  = "00000401"  # Arabic (Saudi Arabia)
_KL_ENGLISH = "00000409"  # English (US)

_win_user32 = None
_last_layout: Optional[str] = None   # تجنب التبديل المكرر


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


def _has_arabic(text: str) -> bool:
    """يتحقق إذا النص يحتوي على أحرف عربية."""
    return any("\u0600" <= c <= "\u06FF" for c in text)


def _detect_lang_by_name(name: str) -> Optional[str]:
    """
    يحدد اللغة بناءً على اسم نصي فقط (objectName أو attribute name).
    للاستخدام من QTextEdit وغيرها خارج الـ event filter.
    """
    name = name.lower().replace("-", "_")
    for kw in _AR_KEYWORDS:
        if kw.replace("-", "_") in name:
            return "ar"
    for kw in _EN_KEYWORDS:
        if kw.replace("-", "_") in name:
            return "en"
    if "_ar" in name:
        return "ar"
    if "_en" in name or "_tr" in name:
        return "en"
    return None


def _detect_lang(widget: QLineEdit) -> Optional[str]:
    """
    يحدد اللغة المتوقعة بالترتيب:
      1. objectName أو اسم الـ attribute
      2. placeholderText
      3. [fallback] محتوى الحقل الحالي
    """
    obj_name    = (widget.objectName() or "").lower().replace("-", "_")
    placeholder = (widget.placeholderText() or "").lower()
    combined    = obj_name + " " + placeholder

    # 1. Keywords على objectName / placeholder
    for kw in _AR_KEYWORDS:
        if kw.replace("-", "_") in combined:
            return "ar"
    for kw in _EN_KEYWORDS:
        if kw.replace("-", "_") in combined:
            return "en"

    # 2. placeholder يحتوي عربي؟
    if _has_arabic(placeholder):
        return "ar"

    # 3. [fallback] محتوى الحقل الحالي
    current_text = widget.text()
    if current_text:
        if _has_arabic(current_text):
            return "ar"
        # نص لاتيني موجود → إنجليزي
        if current_text.strip():
            return "en"

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
    - FocusIn على QLineEdit → switch keyboard language
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
    يُعيِّن objectName على QLineEdit من اسم الـ attribute في الـ dialog/tab.
    مثال: self.name_ar = QLineEdit() → objectName = "name_ar"
    لا يُعيِّن إذا كان objectName مخصصاً مسبقاً (غير فارغ).
    """
    if not hasattr(root, "__dict__"):
        return
    for attr_name, attr_val in vars(root).items():
        if isinstance(attr_val, QLineEdit) and not attr_val.objectName():
            attr_val.setObjectName(attr_name)


def setup_field_ux(root: QWidget) -> _FieldNavFilter:
    """
    يُثبِّت Enter navigation + keyboard switch على أي QWidget
    (dialog أو tab أو أي widget آخر).
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