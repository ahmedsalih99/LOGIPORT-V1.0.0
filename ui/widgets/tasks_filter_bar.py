"""
ui/widgets/tasks_filter_bar.py — LOGIPORT
==========================================
شريط فلاتر تاب المهام — مكوّن مستقل قابل لإعادة الاستخدام.
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton

from core.translator import TranslationManager


class TasksFilterBar(QWidget):
    filter_changed = Signal(str)

    _FILTERS = [
        ("all",         "tasks_all"),
        ("pending",     "tasks_pending"),
        ("in_progress", "tasks_in_progress"),
        ("done",        "tasks_done"),
        ("overdue",     "tasks_overdue"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate
        self._active = "all"
        self._btns:   dict = {}
        self._counts: dict = {}
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        for code, key in self._FILTERS:
            btn = QPushButton(self._(key))
            btn.setCheckable(True)
            btn.setChecked(code == "all")
            btn.setObjectName("stats-filter-btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, c=code: self._set_active(c))
            self._btns[code] = btn
            lay.addWidget(btn)
        lay.addStretch()
        self._refresh_btn_text()

    def _set_active(self, code: str):
        self._active = code
        for c, btn in self._btns.items():
            btn.setChecked(c == code)
        self.filter_changed.emit(code)

    @property
    def current_filter(self) -> str:
        return self._active

    def update_counts(self, tasks: list):
        """تحديث عدادات كل فلتر من قائمة المهام."""
        today = date.today()
        self._counts = {
            "all":         len(tasks),
            "pending":     sum(1 for t in tasks if t.status == "pending"),
            "in_progress": sum(1 for t in tasks if t.status == "in_progress"),
            "done":        sum(1 for t in tasks if t.status == "done"),
            "overdue":     sum(1 for t in tasks
                               if t.due_date and t.due_date < today
                               and t.status not in ("done", "cancelled")),
        }
        self._refresh_btn_text()

    def _refresh_btn_text(self):
        for code, btn in self._btns.items():
            label_key = dict(self._FILTERS).get(code, code)
            label = self._(label_key)
            cnt   = self._counts.get(code, "")
            btn.setText(f"{label}  {cnt}".strip() if cnt != "" else label)

    def retranslate(self):
        self._ = TranslationManager.get_instance().translate
        self._refresh_btn_text()
