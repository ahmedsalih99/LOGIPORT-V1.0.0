"""
ui/tabs/tasks_tab.py — LOGIPORT
==================================
تاب المهام الكامل — المرحلة 5.

الميزات:
- جدول المهام مع ألوان الأولوية والحالة
- فلاتر: الكل / قيد الانتظار / جارٍ / منجز / متأخرة
- إضافة / تعديل / حذف / تعيين كمنجز
- بحث نصي
- RTL/LTR aware
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QFrame, QMenu, QMessageBox, QSizePolicy, QAbstractItemView,
)

from core.translator import TranslationManager

def _get_priority_colors():
    """ألوان الأولوية — تتكيف مع الثيم."""
    try:
        from core.theme_manager import ThemeManager
        c = ThemeManager.get_instance().current_theme.colors
        return {
            "urgent": (c.get("danger_light",   "#FEF2F2"), c.get("danger",         "#DC2626")),
            "high":   (c.get("warning_light",  "#FFFBEB"), c.get("warning",        "#D97706")),
            "medium": (c.get("primary_lighter","#EFF6FF"), c.get("primary",        "#2563EB")),
            "low":    (c.get("bg_disabled",    "#F9FAFB"), c.get("text_muted",     "#6B7280")),
        }
    except Exception:
        return {
            "urgent": ("#FEF2F2", "#DC2626"),
            "high":   ("#FFFBEB", "#D97706"),
            "medium": ("#EFF6FF", "#2563EB"),
            "low":    ("#F9FAFB", "#6B7280"),
        }
_PRIORITY_COLORS = _get_priority_colors()  # initial load
def _get_status_badge():
    """ألوان بادجات الحالة — تتكيف مع الثيم."""
    try:
        from core.theme_manager import ThemeManager
        c = ThemeManager.get_instance().current_theme.colors
        return {
            "pending":     (c.get("warning_light",  "#FEF3C7"), c.get("warning_active",  "#92400E")),
            "in_progress": (c.get("primary_light",  "#DBEAFE"), c.get("primary_active",  "#1E40AF")),
            "done":        (c.get("success_light",  "#D1FAE5"), c.get("success_active",  "#065F46")),
            "cancelled":   (c.get("bg_disabled",    "#F3F4F6"), c.get("text_muted",      "#6B7280")),
        }
    except Exception:
        return {
            "pending":     ("#FEF3C7", "#92400E"),
            "in_progress": ("#DBEAFE", "#1E40AF"),
            "done":        ("#D1FAE5", "#065F46"),
            "cancelled":   ("#F3F4F6", "#6B7280"),
        }
_STATUS_BADGE = _get_status_badge()  # initial load


class TasksTab(QWidget):

    required_permissions = {
        "view":   "view_tasks",
        "add":    "add_task",
        "edit":   "edit_task",
        "delete": "delete_task",
    }

    _COLUMNS = ["title", "priority", "status", "due_date", "assigned_to"]

    _ROWS_PER_PAGE = 50

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self._user  = current_user
        self._       = TranslationManager.get_instance().translate
        self._rows: list = []
        self._filter = "all"    # all | pending | in_progress | done | overdue
        # pagination state
        self._current_page  = 1
        self._total_pages   = 1
        self._total_rows    = 0
        TranslationManager.get_instance().language_changed.connect(self._retranslate)
        self._build_ui()
        self._load()
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(lambda _: self._load())
        except Exception:
            pass

    # ─── Permissions ─────────────────────────────────────────────────────────

    def _user_id(self) -> int | None:
        """يرجع ID المستخدم الحالي."""
        if isinstance(self._user, dict):
            return self._user.get("id")
        return getattr(self._user, "id", None)

    def _can(self, action: str) -> bool:
        try:
            from core.permissions import has_perm
            return has_perm(self._user, self.required_permissions.get(action, ""))
        except Exception:
            return True

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        # ── شريط الأدوات ───────────────────────────────────────────────────
        toolbar = QHBoxLayout(); toolbar.setSpacing(8)

        self._btn_add = QPushButton(f"+ {self._('add_task')}")
        self._btn_add.setObjectName("primary-btn")
        self._btn_add.setMinimumHeight(36)
        self._btn_add.clicked.connect(self._on_add)
        toolbar.addWidget(self._btn_add)

        toolbar.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText(f"🔍  {self._('search')}...")
        self._search.setMinimumHeight(36)
        self._search.setFixedWidth(240)
        self._search.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self._search)

        self._btn_refresh = QPushButton(self._("refresh"))
        self._btn_refresh.setObjectName("secondary-btn")
        self._btn_refresh.setMinimumHeight(36)
        self._btn_refresh.clicked.connect(self._load)
        toolbar.addWidget(self._btn_refresh)

        lay.addLayout(toolbar)

        # ── فلاتر الحالة ───────────────────────────────────────────────────
        self._filter_bar = _FilterBar(self)
        self._filter_bar.filter_changed.connect(self._on_filter_change)
        lay.addWidget(self._filter_bar)

        # ── الجدول ─────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setObjectName("data-table")
        self._table.setColumnCount(len(self._COLUMNS))
        self._table.setHorizontalHeaderLabels(self._col_headers())
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        self._table.doubleClicked.connect(self._on_edit)
        self._table.verticalHeader().setDefaultSectionSize(44)
        lay.addWidget(self._table, 1)

        # ── شريط الحالة ────────────────────────────────────────────────────
        self._status_lbl = QLabel()
        self._status_lbl.setObjectName("text-secondary")
        lay.addWidget(self._status_lbl)

        # ── شريط الـ pagination ─────────────────────────────────────────────
        pg_bar = QHBoxLayout(); pg_bar.setSpacing(6)
        self._btn_prev = QPushButton("◀")
        self._btn_prev.setObjectName("pagination-btn")
        self._btn_prev.setFixedWidth(32)
        self._btn_prev.setMinimumHeight(30)
        self._btn_prev.clicked.connect(self._prev_page)

        self._lbl_page = QLabel()
        self._lbl_page.setObjectName("text-secondary")
        self._lbl_page.setAlignment(Qt.AlignCenter)
        self._lbl_page.setMinimumWidth(100)

        self._btn_next = QPushButton("▶")
        self._btn_next.setObjectName("pagination-btn")
        self._btn_next.setFixedWidth(32)
        self._btn_next.setMinimumHeight(30)
        self._btn_next.clicked.connect(self._next_page)

        pg_bar.addStretch()
        pg_bar.addWidget(self._btn_prev)
        pg_bar.addWidget(self._lbl_page)
        pg_bar.addWidget(self._btn_next)
        pg_bar.addStretch()
        lay.addLayout(pg_bar)

    def _col_headers(self):
        return [
            self._("task_title"), self._("task_priority"),
            self._("task_status"), self._("task_due_date"),
            self._("task_assigned_to"),
        ]

    # ─── Data ─────────────────────────────────────────────────────────────────

    def _load(self):
        try:
            from database.crud.tasks_crud import TasksCRUD
            crud = TasksCRUD()
            search = self._search.text().strip() if hasattr(self, "_search") else ""

            if self._filter == "overdue":
                self._rows = crud.get_all(only_overdue=True, search=search or None)
            elif self._filter in ("pending", "in_progress", "done", "cancelled"):
                self._rows = crud.get_all(status=self._filter, search=search or None)
            else:
                self._rows = crud.get_all(search=search or None)

            self._filter_bar.update_counts(crud)
        except Exception as e:
            self._rows = []
            import logging; logging.getLogger(__name__).error("TasksTab load: %s", e)

        # حساب pagination
        self._total_rows  = len(self._rows)
        self._total_pages = max(1, (self._total_rows + self._ROWS_PER_PAGE - 1) // self._ROWS_PER_PAGE)
        self._current_page = max(1, min(self._current_page, self._total_pages))
        self._refresh_table()

    def _refresh_table(self):
        # slice الصفحة الحالية
        start     = (self._current_page - 1) * self._ROWS_PER_PAGE
        page_rows = self._rows[start: start + self._ROWS_PER_PAGE]

        self._table.setRowCount(len(page_rows))

        today = date.today()

        for ri, task in enumerate(page_rows):
            pri = getattr(task, "priority", "medium")
            bg_hex, _ = _get_priority_colors().get(pri, ("#FFFFFF", "#6B7280"))

            # عنوان
            t_item = QTableWidgetItem(getattr(task, "title", ""))
            t_item.setData(Qt.UserRole, task.id)
            if getattr(task, "status", "") == "done":
                f = t_item.font(); f.setStrikeOut(True); t_item.setFont(f)
            self._table.setItem(ri, 0, t_item)

            # أولوية
            pri_label = self._(f"priority_{pri}")
            pri_item  = QTableWidgetItem(pri_label)
            pri_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(ri, 1, pri_item)

            # حالة
            st = getattr(task, "status", "pending")
            st_item = QTableWidgetItem(self._(f"task_status_{st}"))
            st_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(ri, 2, st_item)

            # تاريخ الاستحقاق
            due = getattr(task, "due_date", None)
            if due:
                overdue = due < today and st not in ("done", "cancelled")
                due_text = f"⚠ {due}" if overdue else str(due)
                due_item = QTableWidgetItem(due_text)
                if overdue:
                    due_item.setForeground(QColor("#DC2626"))
            else:
                due_item = QTableWidgetItem("—")
                due_item.setForeground(QColor("#9CA3AF"))
            due_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(ri, 3, due_item)

            # مسند إلى
            assigned = getattr(task, "assigned_to", None)
            aname = ""
            if assigned:
                aname = getattr(assigned, "full_name", None) or getattr(assigned, "username", "") or ""
            a_item = QTableWidgetItem(aname or "—")
            self._table.setItem(ri, 4, a_item)

        self._status_lbl.setText(self._("tasks_count").format(n=self._total_rows))
        self._btn_add.setEnabled(self._can("add"))
        # تحديث labels pagination
        self._lbl_page.setText(f"{self._current_page} / {self._total_pages}")
        self._btn_prev.setEnabled(self._current_page > 1)
        self._btn_next.setEnabled(self._current_page < self._total_pages)

    # ─── Actions ─────────────────────────────────────────────────────────────

    def _current_task(self):
        row = self._table.currentRow()
        if row < 0:
            return None
        offset = (self._current_page - 1) * self._ROWS_PER_PAGE
        idx = offset + row
        if 0 <= idx < len(self._rows):
            return self._rows[idx]
        return None

    def _on_add(self):
        from ui.dialogs.task_dialog import TaskDialog
        dlg = TaskDialog(current_user=self._user, parent=self)
        if dlg.exec() and dlg.result_data:
            try:
                from database.crud.tasks_crud import TasksCRUD
                data = dict(dlg.result_data)
                data.setdefault("created_by_id", self._user_id())
                TasksCRUD().create(**data)
                self._load()
                from core.data_bus import DataBus
                DataBus.get_instance().emit('tasks')
            except Exception as e:
                QMessageBox.critical(self, self._("error"), str(e))

    def _on_edit(self, *_):
        if not self._can("edit"):
            return
        task = self._current_task()
        if not task:
            return
        from ui.dialogs.task_dialog import TaskDialog
        dlg = TaskDialog(task_data=task, current_user=self._user, parent=self)
        if dlg.exec() and dlg.result_data:
            try:
                from database.crud.tasks_crud import TasksCRUD
                data = dict(dlg.result_data)
                data["updated_by_id"] = self._user_id()
                TasksCRUD().update(task.id, **data)
                self._load()
                from core.data_bus import DataBus
                DataBus.get_instance().emit('tasks')
            except Exception as e:
                QMessageBox.critical(self, self._("error"), str(e))

    def _on_mark_done(self):
        task = self._current_task()
        if not task:
            return
        try:
            from database.crud.tasks_crud import TasksCRUD
            TasksCRUD().mark_done(task.id, updated_by_id=self._user_id())
            self._load()
            from core.data_bus import DataBus
            DataBus.get_instance().emit('tasks')
        except Exception as e:
            QMessageBox.critical(self, self._("error"), str(e))

    def _on_delete(self):
        if not self._can("delete"):
            return
        task = self._current_task()
        if not task:
            return
        reply = QMessageBox.question(
            self, self._("confirm"), self._("task_confirm_delete"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                from database.crud.tasks_crud import TasksCRUD
                TasksCRUD().delete(task.id)
                self._load()
                from core.data_bus import DataBus
                DataBus.get_instance().emit('tasks')
            except Exception as e:
                QMessageBox.critical(self, self._("error"), str(e))

    def _on_context_menu(self, pos):
        task = self._current_task()
        if not task:
            return
        menu = QMenu(self)
        if self._can("edit"):
            menu.addAction(f"✏️  {self._('edit_task')}").triggered.connect(self._on_edit)
        if getattr(task, "status", "") not in ("done", "cancelled"):
            menu.addAction(f"✅  {self._('task_mark_done')}").triggered.connect(self._on_mark_done)
        menu.addSeparator()
        if self._can("delete"):
            menu.addAction(f"🗑  {self._('delete_task')}").triggered.connect(self._on_delete)
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _prev_page(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._refresh_table()

    def _next_page(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._refresh_table()

    def _on_filter_change(self, f: str):
        self._filter = f
        self._current_page = 1  # reset page on filter change
        self._load()

    def _on_search_changed(self, _):
        self._current_page = 1
        QTimer.singleShot(300, self._load)

    def _retranslate(self):
        self._  = TranslationManager.get_instance().translate
        self._btn_add.setText(f"+ {self._('add_task')}")
        self._btn_refresh.setText(self._("refresh"))
        self._table.setHorizontalHeaderLabels(self._col_headers())
        self._filter_bar.retranslate()
        self._load()


# ─── FilterBar ────────────────────────────────────────────────────────────────

class _FilterBar(QWidget):
    from PySide6.QtCore import Signal
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
        self._btns   = {}
        self._counts = {}
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
        # تحديث عند تغيير الثيم

    def _set_active(self, code: str):
        self._active = code
        for c, btn in self._btns.items():
            btn.setChecked(c == code)
        self.filter_changed.emit(code)


    def update_counts(self, crud):
        """تحديث عدادات كل فلتر."""
        try:
            from database.crud.tasks_crud import TasksCRUD
            all_tasks = crud.get_all()
            today = date.today()
            self._counts = {
                "all":         str(len(all_tasks)),
                "pending":     str(sum(1 for t in all_tasks if t.status == "pending")),
                "in_progress": str(sum(1 for t in all_tasks if t.status == "in_progress")),
                "done":        str(sum(1 for t in all_tasks if t.status == "done")),
                "overdue":     str(sum(1 for t in all_tasks
                                       if t.due_date and t.due_date < today
                                       and t.status not in ("done","cancelled"))),
            }
        except Exception:
            self._counts = {}
        # تحديث نص الأزرار
        self._refresh_btn_text()

    def _refresh_btn_text(self):
        """تحديث نص الأزرار بالعداد الحالي."""
        for code, btn in self._btns.items():
            label_key = dict(self._FILTERS).get(code, code)
            label = self._(label_key)
            cnt = self._counts.get(code, "")
            btn.setText(f"{label}  {cnt}".strip())

    def retranslate(self):
        self._ = TranslationManager.get_instance().translate
        self._refresh_btn_text()