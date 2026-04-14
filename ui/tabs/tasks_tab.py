"""
ui/tabs/tasks_tab.py — LOGIPORT
==================================
تاب المهام — يرث BaseTab.
"""
from __future__ import annotations

import logging
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui  import QColor
from PySide6.QtWidgets import QTableWidgetItem, QMessageBox, QMenu

from core.base_tab import BaseTab
from core.permissions import has_perm

logger = logging.getLogger(__name__)


def _priority_colors():
    try:
        from core.theme_manager import ThemeManager
        c = ThemeManager.get_instance().current_theme.colors
        return {
            "urgent": (c.get("danger_light",    "#FEF2F2"), c.get("danger",     "#DC2626")),
            "high":   (c.get("warning_light",   "#FFFBEB"), c.get("warning",    "#D97706")),
            "medium": (c.get("primary_lighter", "#EFF6FF"), c.get("primary",    "#2563EB")),
            "low":    (c.get("bg_disabled",     "#F9FAFB"), c.get("text_muted", "#6B7280")),
        }
    except Exception:
        return {
            "urgent": ("#FEF2F2", "#DC2626"),
            "high":   ("#FFFBEB", "#D97706"),
            "medium": ("#EFF6FF", "#2563EB"),
            "low":    ("#F9FAFB", "#6B7280"),
        }


class TasksTab(BaseTab):

    required_permissions = {
        "view":   "view_tasks",
        "add":    "add_task",
        "edit":   "edit_task",
        "delete": "delete_task",
    }

    def __init__(self, current_user=None, parent=None):
        super().__init__(title="tasks", parent=parent, user=current_user)
        self._filter = "all"
        self._col_widths_key = "tasks_tab_col_widths"

        self.set_columns([
            {"label": "task_title",       "key": "title"},
            {"label": "task_priority",    "key": "priority_label"},
            {"label": "task_status",      "key": "status_label"},
            {"label": "task_due_date",    "key": "due_date_str"},
            {"label": "task_assigned_to", "key": "assigned_name"},
        ])

        # هذا التاب لا يستخدم set_columns_for_role → نخفي checkbox أعمدة الإدارة
        if hasattr(self, "chk_admin_cols"):
            self.chk_admin_cols.setVisible(False)

        from ui.widgets.tasks_filter_bar import TasksFilterBar
        self._filter_bar = TasksFilterBar(self)
        self._filter_bar.filter_changed.connect(self._on_filter_change)
        self._layout.insertWidget(1, self._filter_bar)

        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(lambda _: self.reload_data())
        except Exception:
            pass

        try:
            from core.data_bus import DataBus
            DataBus.get_instance().subscribe("tasks", lambda _=None: self.reload_data())
        except Exception:
            pass

        self.reload_data()

    # ── Data ──────────────────────────────────────────────────────────────

    def reload_data(self):
        try:
            from database.crud.tasks_crud import TasksCRUD
            crud   = TasksCRUD()
            search = self.search_bar.text().strip() if hasattr(self, "search_bar") else ""

            if self._filter == "overdue":
                rows = crud.get_all(only_overdue=True, search=search or None)
            elif self._filter in ("pending", "in_progress", "done", "cancelled"):
                rows = crud.get_all(status=self._filter, search=search or None)
            else:
                rows = crud.get_all(search=search or None)

            all_tasks = crud.get_all()
            if hasattr(self, "_filter_bar"):
                self._filter_bar.update_counts(all_tasks)

            self.data = self._to_rows(rows)
        except Exception as e:
            logger.error("TasksTab.reload_data: %s", e)
            self.data = []

        self.display_data()

    def _to_rows(self, tasks: list) -> list:
        today = date.today()
        rows  = []
        for task in tasks:
            pri = getattr(task, "priority", "medium") or "medium"
            st  = getattr(task, "status",   "pending") or "pending"
            due = getattr(task, "due_date", None)
            if due:
                overdue = due < today and st not in ("done", "cancelled")
                due_str = f"⚠ {due}" if overdue else str(due)
            else:
                due_str = "—"
            assigned = getattr(task, "assigned_to", None)
            aname    = ""
            if assigned:
                aname = getattr(assigned, "full_name", None) or getattr(assigned, "username", "") or ""
            rows.append({
                "id":             task.id,
                "title":          getattr(task, "title", ""),
                "priority":       pri,
                "priority_label": self._(f"priority_{pri}"),
                "status":         st,
                "status_label":   self._(f"task_status_{st}"),
                "due_date":       due,
                "due_date_str":   due_str,
                "assigned_name":  aname or "—",
                "_task_obj":      task,
                "actions":        task,
            })
        return rows

    # ── Display ───────────────────────────────────────────────────────────

    def display_data(self):
        rows = list(self.data) if self.data else []
        if not getattr(self, "_skip_base_search", False):
            rows = self._apply_base_search(rows)
        if not getattr(self, "_skip_base_sort", False):
            rows = self._apply_base_sort(rows)

        self.total_rows  = len(rows)
        self.total_pages = max(1, (self.total_rows + self.rows_per_page - 1) // self.rows_per_page)
        self.current_page = max(1, min(self.current_page, self.total_pages))
        start     = (self.current_page - 1) * self.rows_per_page
        page_rows = rows[start: start + self.rows_per_page]

        self._update_pagination_label()
        self._update_status_bar(len(rows), len(self.data))
        searched = bool(self.search_bar.text().strip()) if hasattr(self, "search_bar") else False
        self._show_empty_state(len(rows) == 0, searched=searched)

        if not self.columns:
            self.table.setRowCount(0)
            return

        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(page_rows))
            pri_colors = _priority_colors()
            for i, row in enumerate(page_rows):
                self._set_row_checkbox(i)
                pri = row.get("priority", "medium")
                _, fg_hex = pri_colors.get(pri, ("#FFFFFF", "#1E293B"))
                for j, col in enumerate(self.columns):
                    key = col.get("key", "")
                    val = row.get(key, "")
                    item = QTableWidgetItem(str(val) if val is not None else "")
                    item.setTextAlignment(Qt.AlignCenter)
                    if key == "title":
                        item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
                        if row.get("status") == "done":
                            f = item.font(); f.setStrikeOut(True); item.setFont(f)
                        item.setData(Qt.UserRole, row.get("id"))
                    elif key == "priority_label":
                        item.setForeground(QColor(fg_hex))
                    elif key == "due_date_str" and str(val).startswith("⚠"):
                        item.setForeground(QColor("#DC2626"))
                    self.table.setItem(i, j + 1, item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.setSortingEnabled(True)
        self._stretch_columns()

    # ── Actions ───────────────────────────────────────────────────────────

    def _current_task_obj(self):
        rows = self.get_selected_rows()
        if not rows:
            return None
        idx = (self.current_page - 1) * self.rows_per_page + rows[0]
        if not self.data or idx >= len(self.data):
            return None
        return self.data[idx].get("_task_obj")

    def add_new_item(self):
        from ui.dialogs.task_dialog import TaskDialog
        dlg = TaskDialog(current_user=self.current_user, parent=self)
        if dlg.exec() and dlg.result_data:
            try:
                from database.crud.tasks_crud import TasksCRUD
                data = dict(dlg.result_data)
                data.setdefault("created_by_id", getattr(self.current_user, "id", None))
                data.pop("updated_by_id", None)   # create() لا يقبل updated_by_id
                TasksCRUD().create(**data)
                self.reload_data()
                from core.data_bus import DataBus
                DataBus.get_instance().emit("tasks")
            except Exception as e:
                QMessageBox.critical(self, self._("error"), str(e))

    def _open_edit_dialog(self, task_obj):
        if not task_obj:
            return
        from ui.dialogs.task_dialog import TaskDialog
        dlg = TaskDialog(task_data=task_obj, current_user=self.current_user, parent=self)
        if dlg.exec() and dlg.result_data:
            try:
                from database.crud.tasks_crud import TasksCRUD
                data = dict(dlg.result_data)
                data["updated_by_id"] = getattr(self.current_user, "id", None)
                data.pop("created_by_id", None)   # لا تُعدَّل عند التحديث
                TasksCRUD().update(task_obj.id, **data)
                self.reload_data()
                from core.data_bus import DataBus
                DataBus.get_instance().emit("tasks")
            except Exception as e:
                QMessageBox.critical(self, self._("error"), str(e))

    def _delete_single(self, task_obj):
        if not task_obj:
            return
        reply = QMessageBox.question(
            self, self._("confirm"), self._("task_confirm_delete"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                from database.crud.tasks_crud import TasksCRUD
                TasksCRUD().delete(task_obj.id)
                self.reload_data()
                from core.data_bus import DataBus
                DataBus.get_instance().emit("tasks")
            except Exception as e:
                QMessageBox.critical(self, self._("error"), str(e))

    def _mark_done(self, task_obj):
        if not task_obj:
            return
        try:
            from database.crud.tasks_crud import TasksCRUD
            TasksCRUD().mark_done(
                task_obj.id,
                updated_by_id=getattr(self.current_user, "id", None)
            )
            self.reload_data()
            from core.data_bus import DataBus
            DataBus.get_instance().emit("tasks")
        except Exception as e:
            QMessageBox.critical(self, self._("error"), str(e))

    def _on_row_double_clicked(self, index):
        self._open_edit_dialog(self._current_task_obj())

    def _show_context_menu(self, pos):
        task = self._current_task_obj()
        if not task:
            return
        menu = QMenu(self)
        if has_perm(self.current_user, "edit_task") or self.is_admin:
            menu.addAction(f"✏️  {self._('edit_task')}").triggered.connect(
                lambda: self._open_edit_dialog(task))
        if getattr(task, "status", "") not in ("done", "cancelled"):
            menu.addAction(f"✅  {self._('task_mark_done')}").triggered.connect(
                lambda: self._mark_done(task))
        menu.addSeparator()
        if has_perm(self.current_user, "delete_task") or self.is_admin:
            menu.addAction(f"🗑  {self._('delete_task')}").triggered.connect(
                lambda: self._delete_single(task))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _on_filter_change(self, f: str):
        self._filter = f
        self.current_page = 1
        self.reload_data()

    def retranslate_ui(self):
        super().retranslate_ui()
        if hasattr(self, "_filter_bar"):
            self._filter_bar.retranslate()
        self.reload_data()