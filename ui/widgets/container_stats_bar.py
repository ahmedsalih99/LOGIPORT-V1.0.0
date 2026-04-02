"""
ui/widgets/container_stats_bar.py — LOGIPORT
=============================================
شريط إحصائيات / فلاتر تاب تتبع الكونتينر — مكوّن مستقل.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton

from core.translator import TranslationManager
from database.models.container_tracking import ContainerTracking

_STATUS_META = {
    "booked":     {"icon": "📋", "color": "#6366F1"},
    "in_transit": {"icon": "🚢", "color": "#2563EB"},
    "arrived":    {"icon": "⚓", "color": "#7C3AED"},
    "customs":    {"icon": "🏛️", "color": "#D97706"},
    "delivered":  {"icon": "✅", "color": "#059669"},
    "hold":       {"icon": "⚠️",  "color": "#DC2626"},
}


class ContainerStatsBar(QWidget):
    filter_changed = Signal(str)   # status_key أو "" للكل

    def __init__(self, parent=None):
        super().__init__(parent)
        self._     = TranslationManager.get_instance().translate
        self._btns: dict = {}
        self._active_filter = ""
        self._build()

    def _build(self):
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 4)
        h.setSpacing(6)

        all_btn = self._make_btn("", self._("container_filter_all"))
        h.addWidget(all_btn)
        self._btns[""] = all_btn

        for status in ContainerTracking.STATUSES:
            meta  = _STATUS_META.get(status, {})
            label = f"{meta.get('icon','')} {self._(f'container_status_{status}')}"
            btn   = self._make_btn(status, label)
            h.addWidget(btn)
            self._btns[status] = btn

        h.addStretch()
        self._set_active("")

    def _make_btn(self, status_key: str, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setObjectName("stats-filter-btn")
        btn.setFixedHeight(28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _, k=status_key: self._on_click(k))
        return btn

    def _on_click(self, key: str):
        self._set_active(key)
        self.filter_changed.emit(key)

    def _set_active(self, key: str):
        self._active_filter = key
        for k, btn in self._btns.items():
            btn.setChecked(k == key)

    @property
    def current_filter(self) -> str:
        return self._active_filter

    def update_counts(self, rows: list):
        counts = {"": len(rows)}
        for status in ContainerTracking.STATUSES:
            counts[status] = sum(1 for r in rows if r.status == status)
        for key, btn in self._btns.items():
            n = counts.get(key, 0)
            if key == "":
                lbl = self._("container_filter_all")
            else:
                meta = _STATUS_META.get(key, {})
                lbl  = f"{meta.get('icon','')} {self._(f'container_status_{key}')}"
            btn.setText(f"{lbl}  {n}" if n else lbl)
            if key != "":
                btn.setVisible(n > 0 or self._active_filter == key)

    def retranslate(self):
        self._ = TranslationManager.get_instance().translate
        for key, btn in self._btns.items():
            if key == "":
                btn.setText(self._("container_filter_all"))
            else:
                meta = _STATUS_META.get(key, {})
                btn.setText(f"{meta.get('icon','')} {self._(f'container_status_{key}')}")
