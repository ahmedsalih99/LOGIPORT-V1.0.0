"""
ui/utils/wheel_blocker.py — LOGIPORT
======================================
أداة موحّدة لحجب حدث ScrollWheel على QComboBox و QSpinBox
لمنع تغيير القيم عن طريق الخطأ أثناء التمرير في النافذة.

الاستخدام:
    from ui.utils.wheel_blocker import block_wheel

    # على widget واحد
    block_wheel(self.cmb_type)

    # على قائمة من الـ widgets
    block_wheel(self.cmb_type, self.spn_qty, self.dbl_price)

    # على كل الـ QComboBox و QSpinBox داخل container
    block_wheel_in(self)
"""
from __future__ import annotations

from typing import Union

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QWidget, QComboBox, QSpinBox, QDoubleSpinBox, QAbstractSpinBox


# ─────────────────────────────────────────────────────────────────────────────
# EventFilter داخلي
# ─────────────────────────────────────────────────────────────────────────────

class _WheelBlockerFilter(QObject):
    """
    يعترض WheelEvent ويمرّره للـ parent بدل أن يُعالجه الـ widget.
    هذا يتيح للنافذة نفسها التمرير بينما تظل قيمة الـ combo/spin ثابتة.
    """

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Wheel:
            event.ignore()
            return True          # ابتلع الحدث — لا تمرره للـ widget
        return super().eventFilter(watched, event)


# مثيل واحد مشترك (singleton) — يكفي لكل الـ widgets
_FILTER = _WheelBlockerFilter()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def block_wheel(*widgets: QWidget) -> None:
    """
    يحجب ScrollWheel على widgets محددة.

    مثال:
        block_wheel(self.cmb_type, self.spn_qty, self.dbl_price)
    """
    for w in widgets:
        if w is None:
            continue
        w.setFocusPolicy(w.focusPolicy())   # لا تغيير في الـ focus
        w.installEventFilter(_FILTER)


def block_wheel_in(container: QWidget) -> None:
    """
    يحجب ScrollWheel على كل QComboBox و QSpinBox داخل container (بشكل تعاودي).

    مثال:
        block_wheel_in(self)          # في __init__ بعد بناء الـ UI
        block_wheel_in(my_frame)      # على frame معين فقط
    """
    for child in container.findChildren(QWidget):
        if isinstance(child, (QComboBox, QAbstractSpinBox)):
            child.installEventFilter(_FILTER)