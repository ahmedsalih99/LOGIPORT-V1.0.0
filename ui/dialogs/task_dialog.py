"""
ui/dialogs/task_dialog.py — LOGIPORT
=======================================
نافذة إضافة/تعديل مهمة.
"""
from __future__ import annotations
from datetime import date
from typing import Optional

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from ui.utils.wheel_blocker import block_wheel_in
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QDateEdit,
    QPushButton, QFrame, QWidget, QMessageBox, QSizePolicy,
)

try:
    from core.translator import TranslationManager
    _T = TranslationManager.get_instance()
    _ = _T.translate
except Exception:
    _ = lambda k: k

from core.base_dialog import BaseDialog as _Base


class TaskDialog(_Base):
    """
    نافذة إضافة أو تعديل مهمة.

    task_data: dict مع بيانات المهمة الحالية (None = إضافة جديدة)
    current_user: المستخدم الحالي (لتعيين created_by)
    """

    PRIORITIES = [
        ("low",    "priority_low"),
        ("medium", "priority_medium"),
        ("high",   "priority_high"),
        ("urgent", "priority_urgent"),
    ]
    STATUSES = [
        ("pending",     "task_status_pending"),
        ("in_progress", "task_status_in_progress"),
        ("done",        "task_status_done"),
        ("cancelled",   "task_status_cancelled"),
    ]
    PRIORITY_COLORS = {
        "low":    "#6B7280",
        "medium": "#2563EB",
        "high":   "#D97706",
        "urgent": "#DC2626",
    }

    def __init__(self, task_data=None, current_user=None, parent=None):
        super().__init__(parent)
        self._task   = task_data      # None = إضافة
        self._user   = current_user
        self._result = None           # dict بالبيانات عند الحفظ

        self.setWindowTitle(_("add_task") if not task_data else _("edit_task"))
        self.setMinimumWidth(480)
        self.setMinimumHeight(420)
        self.setModal(True)

        self._users_list = self._load_users()
        self._build_ui()
        if task_data:
            self._populate(task_data)

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QWidget(); hdr.setObjectName("form-dialog-header")
        hl  = QVBoxLayout(hdr); hl.setContentsMargins(22, 18, 22, 14)
        title = QLabel(_("add_task") if not self._task else _("edit_task"))
        title.setObjectName("form-dialog-title")
        f = QFont(); f.setPointSize(13); f.setBold(True); title.setFont(f)
        hl.addWidget(title)
        root.addWidget(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setObjectName("form-dialog-sep")
        root.addWidget(sep)

        # Body
        body = QWidget(); body.setObjectName("form-dialog-body")
        bl   = QVBoxLayout(body); bl.setContentsMargins(22, 18, 22, 10); bl.setSpacing(14)

        form = QFormLayout(); form.setSpacing(10); form.setLabelAlignment(Qt.AlignRight)

        # عنوان المهمة
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText(_("task_title"))
        self._title_edit.setMinimumHeight(36)
        form.addRow(QLabel(_("task_title") + " *"), self._title_edit)

        # الأولوية
        self._priority_cb = QComboBox(); self._priority_cb.setMinimumHeight(36)
        for code, key in self.PRIORITIES:
            self._priority_cb.addItem(_(key), code)
        self._priority_cb.setCurrentIndex(1)  # medium
        form.addRow(QLabel(_("task_priority")), self._priority_cb)

        # الحالة
        self._status_cb = QComboBox(); self._status_cb.setMinimumHeight(36)
        for code, key in self.STATUSES:
            self._status_cb.addItem(_(key), code)
        form.addRow(QLabel(_("task_status")), self._status_cb)

        # تاريخ الاستحقاق
        due_row = QHBoxLayout(); due_row.setSpacing(8)
        self._due_check = QPushButton(_("task_no_due"))
        self._due_check.setCheckable(True)
        self._due_check.setChecked(False)
        self._due_check.setObjectName("secondary-btn")
        self._due_check.setFixedWidth(120)
        self._due_date  = QDateEdit(); self._due_date.setCalendarPopup(True)
        self._due_date.setDate(QDate.currentDate())
        self._due_date.setVisible(False); self._due_date.setMinimumHeight(36)
        self._due_check.toggled.connect(lambda c: self._due_date.setVisible(c))
        self._due_check.toggled.connect(lambda c: self._due_check.setText(
            _("task_due_date") if c else _("task_no_due")
        ))
        due_row.addWidget(self._due_check)
        due_row.addWidget(self._due_date)
        due_row.addStretch()
        form.addRow(QLabel(_("task_due_date")), due_row)

        # مسند إلى
        self._assigned_cb = QComboBox(); self._assigned_cb.setMinimumHeight(36)
        self._assigned_cb.addItem("—", None)
        for uid, uname in self._users_list:
            self._assigned_cb.addItem(uname, uid)
        form.addRow(QLabel(_("task_assigned_to")), self._assigned_cb)

        bl.addLayout(form)

        # الوصف
        bl.addWidget(QLabel(_("task_description")))
        self._desc_edit = QTextEdit()
        self._desc_edit.setMaximumHeight(100)
        self._desc_edit.setPlaceholderText(_("task_description") + "...")
        bl.addWidget(self._desc_edit)
        bl.addStretch()

        root.addWidget(body, 1)

        # Footer
        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine); sep2.setObjectName("form-dialog-sep")
        root.addWidget(sep2)

        foot = QWidget(); foot.setObjectName("form-dialog-footer")
        fl   = QHBoxLayout(foot); fl.setContentsMargins(22, 14, 22, 16)
        self._btn_save   = QPushButton(_("save")); self._btn_save.setObjectName("primary-btn"); self._btn_save.setMinimumHeight(38)
        self._btn_cancel = QPushButton(_("cancel")); self._btn_cancel.setMinimumHeight(38)
        fl.addWidget(self._btn_save); fl.addWidget(self._btn_cancel)
        root.addWidget(foot)

        self._btn_save.clicked.connect(self._on_save)
        self._btn_cancel.clicked.connect(self.reject)

    # ─── Load ─────────────────────────────────────────────────────────────────

    def _load_users(self):
        try:
            from database.models import get_session_local, User
            s = get_session_local()()
            try:
                users = s.query(User).filter(User.is_active == True).order_by(User.username).all()
                return [(u.id, u.full_name or u.username) for u in users]
            finally:
                s.close()
        except Exception:
            return []

    def _populate(self, t):
        """ملء الحقول من بيانات المهمة الموجودة."""
        self._title_edit.setText(getattr(t, "title", "") or "")
        # priority
        for i in range(self._priority_cb.count()):
            if self._priority_cb.itemData(i) == getattr(t, "priority", "medium"):
                self._priority_cb.setCurrentIndex(i); break
        # status
        for i in range(self._status_cb.count()):
            if self._status_cb.itemData(i) == getattr(t, "status", "pending"):
                self._status_cb.setCurrentIndex(i); break
        # due_date
        if getattr(t, "due_date", None):
            d = t.due_date
            self._due_check.setChecked(True)
            self._due_date.setDate(QDate(d.year, d.month, d.day))
        # assigned_to
        aid = getattr(t, "assigned_to_id", None)
        if aid:
            for i in range(self._assigned_cb.count()):
                if self._assigned_cb.itemData(i) == aid:
                    self._assigned_cb.setCurrentIndex(i); break
        # description
        self._desc_edit.setPlainText(getattr(t, "description", "") or "")

    # ─── Save ─────────────────────────────────────────────────────────────────

    def _on_save(self):
        title = self._title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, _("warning"), _("task_title_required"))
            return

        due = None
        if self._due_check.isChecked():
            qd = self._due_date.date()
            due = date(qd.year(), qd.month(), qd.day())

        self._result = {
            "title":          title,
            "priority":       self._priority_cb.currentData(),
            "status":         self._status_cb.currentData(),
            "due_date":       due,
            "assigned_to_id": self._assigned_cb.currentData(),
            "description":    self._desc_edit.toPlainText().strip() or None,
            "created_by_id":  getattr(self._user, "id", None) if not self._task_data else None,
            "updated_by_id":  getattr(self._user, "id", None) if self._task_data else None,
        }
        self.accept()

    @property
    def result_data(self):
        return self._result
        block_wheel_in(self)
