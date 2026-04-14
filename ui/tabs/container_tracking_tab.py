"""
container_tracking_tab.py — LOGIPORT v3
=========================================
تبويب تتبع البوليصات — يرث BaseTab.
"""
from __future__ import annotations

import logging
from datetime import date as _date_type

from PySide6.QtCore  import Qt, QTimer
from PySide6.QtGui   import QColor, QFont
from PySide6.QtWidgets import (
    QTableWidgetItem, QMessageBox, QWidget, QHBoxLayout,
    QPushButton, QLineEdit,
)

from core.base_tab import BaseTab
from core.permissions import has_perm, is_admin
from database.crud.container_tracking_crud import ContainerTrackingCRUD
from database.models.container_tracking    import ContainerTracking

logger = logging.getLogger(__name__)

_crud = ContainerTrackingCRUD()

_STATUS_META = {
    "booked":     {"icon": "📋", "color": "#6366F1"},
    "in_transit": {"icon": "🚢", "color": "#2563EB"},
    "arrived":    {"icon": "⚓", "color": "#7C3AED"},
    "customs":    {"icon": "🏛️", "color": "#D97706"},
    "delivered":  {"icon": "✅", "color": "#059669"},
    "hold":       {"icon": "⚠️",  "color": "#DC2626"},
}

_ACTIVE_STATUSES = {"booked", "in_transit", "arrived", "customs"}
_ETA_OVERDUE_BG  = "#FEE2E2";  _ETA_OVERDUE_FG = "#DC2626"
_ETA_TODAY_BG    = "#FEF3C7";  _ETA_TODAY_FG   = "#D97706"
_ETA_SOON_FG     = "#059669"

# (key, label_key, min_width, stretch)
_COLUMNS = [
    ("bl_number",          "bl_number_label",        110, False),
    ("shipping_line",      "shipping_line_label",     120, False),
    ("client_name",        "client_label",            130, True),
    ("cargo_type",         "cargo_type_label",        110, False),
    ("quantity",           "quantity_label",           70, False),
    ("origin_country",     "origin_country_label",    110, False),
    ("port_of_discharge",  "port_of_discharge_label", 110, False),
    ("docs_delivered",     "docs_delivered_col",       80, False),
    ("cargo_tracking",     "cargo_tracking_label",    120, True),
    ("docs_received_date", "docs_received_date_label", 90, False),
    ("containers_count",   "containers_count_label",   60, False),
    ("bl_status",          "bl_status_label",          90, False),
    ("eta",                "eta_label",                80, False),
    ("status",             "col_status",               90, False),
]


def _eta_state(eta, status: str):
    if not eta or status not in _ACTIVE_STATUSES:
        return None, 0
    today = _date_type.today()
    try:
        delta = (eta - today).days
    except Exception:
        return None, 0
    if delta < 0:  return "overdue", abs(delta)
    if delta == 0: return "today",   0
    if delta <= 3: return "soon",    delta
    return "normal", delta


class ContainerTrackingTab(BaseTab):

    required_permissions = {
        "view":   "view_transactions",
        "add":    "add_transaction",
        "edit":   "edit_transaction",
        "delete": "delete_transaction",
    }

    def __init__(self, current_user=None, parent=None):
        super().__init__(title="container_tracking", parent=parent, user=current_user)
        self._all_rows: list = []
        self._col_widths_key = "container_tracking_tab_col_widths"

        # أعمدة الجدول
        self.set_columns([
            {"label": lbl, "key": key}
            for key, lbl, _, _ in _COLUMNS
        ])

        # هذا التاب لا يستخدم set_columns_for_role → نخفي checkbox أعمدة الإدارة
        if hasattr(self, "chk_admin_cols"):
            self.chk_admin_cols.setVisible(False)

        # شريط الفلاتر / الإحصائيات
        from ui.widgets.container_stats_bar import ContainerStatsBar
        self._stats_bar = ContainerStatsBar(self)
        self._stats_bar.filter_changed.connect(self._on_status_filter_change)
        self._layout.insertWidget(1, self._stats_bar)

        # زر طباعة إضافي في شريط الأدوات
        self._btn_print = QPushButton(f"🖨  {self._('print_list')}")
        self._btn_print.setObjectName("secondary-btn")
        self._btn_print.setToolTip(self._("print_list_tooltip"))
        self._btn_print.clicked.connect(self._print_list)
        self.top_bar.addWidget(self._btn_print)

        self._apply_permissions()

        try:
            from core.data_bus import DataBus
            DataBus.get_instance().subscribe("containers", lambda _=None: self.reload_data())
        except Exception:
            pass

        self.reload_data()

    # ── Permissions ───────────────────────────────────────────────────────

    def _apply_permissions(self):
        u = self.current_user
        self.can_add    = is_admin(u) or has_perm(u, "add_transaction")
        self.can_edit   = is_admin(u) or has_perm(u, "edit_transaction")
        self.can_delete = is_admin(u) or has_perm(u, "delete_transaction")
        if hasattr(self, "btn_add"):
            self.btn_add.setVisible(self.can_add)

    def set_current_user(self, user):
        super().set_current_user(user)
        self._apply_permissions()

    # ── Data ──────────────────────────────────────────────────────────────

    def reload_data(self):
        search = self.search_bar.text().strip() if hasattr(self, "search_bar") else ""
        try:
            self._all_rows = _crud.get_all(search=search, status=None)
        except Exception as e:
            logger.error("ContainerTrackingTab.reload_data: %s", e)
            self._all_rows = []

        if hasattr(self, "_stats_bar"):
            self._stats_bar.update_counts(self._all_rows)

        current_filter = self._stats_bar.current_filter if hasattr(self, "_stats_bar") else ""
        self._apply_status_filter(current_filter)

    def _apply_status_filter(self, status_key: str):
        if status_key:
            self.data = [r for r in self._all_rows if r.status == status_key]
        else:
            self.data = list(self._all_rows)
        self.display_data()
        if hasattr(self, "_update_status_bar"):
            self._update_status_bar(len(self.data), len(self._all_rows))

    def _on_status_filter_change(self, status_key: str):
        self._apply_status_filter(status_key)

    # ── Display ───────────────────────────────────────────────────────────

    def display_data(self):
        rows = list(self.data) if self.data else []

        self.total_rows  = len(rows)
        self.total_pages = max(1, (self.total_rows + self.rows_per_page - 1) // self.rows_per_page)
        self.current_page = max(1, min(self.current_page, self.total_pages))
        start     = (self.current_page - 1) * self.rows_per_page
        page_rows = rows[start: start + self.rows_per_page]

        self._update_pagination_label()
        searched = bool(self.search_bar.text().strip()) if hasattr(self, "search_bar") else False
        self._show_empty_state(len(rows) == 0, searched=searched)

        if not self.columns:
            self.table.setRowCount(0)
            return

        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        cell_font = QFont(); cell_font.setPointSize(9)
        try:
            self.table.setRowCount(len(page_rows))
            for row_idx, rec in enumerate(page_rows):
                self._set_row_checkbox(row_idx)
                eta_state, eta_days = _eta_state(rec.eta, rec.status or "")
                for col_idx, (key, _, _, _) in enumerate(_COLUMNS):
                    val, fg, bg = self._cell_value(rec, key)
                    item = QTableWidgetItem(val)
                    item.setData(Qt.UserRole, rec.id)
                    item.setFont(cell_font)
                    item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    if key == "eta" and eta_state:
                        if eta_state == "overdue":
                            item.setForeground(QColor(_ETA_OVERDUE_FG))
                            item.setBackground(QColor(_ETA_OVERDUE_BG))
                            item.setToolTip(self._("container_eta_overdue").format(days=eta_days))
                        elif eta_state == "today":
                            item.setForeground(QColor(_ETA_TODAY_FG))
                            item.setBackground(QColor(_ETA_TODAY_BG))
                            item.setToolTip(self._("container_eta_today"))
                        elif eta_state == "soon":
                            item.setForeground(QColor(_ETA_SOON_FG))
                            item.setToolTip(self._("container_eta_days_left").format(days=eta_days))
                    else:
                        if fg: item.setForeground(QColor(fg))
                        if bg: item.setBackground(QColor(bg))
                    self.table.setItem(row_idx, col_idx + 1, item)  # +1 للـ checkbox
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.setSortingEnabled(True)

        self._stretch_columns()

    def _cell_value(self, rec: ContainerTracking, key: str):
        def _date(d): return d.strftime("%Y-%m-%d") if d else "—"
        if key == "bl_number":
            return (rec.bl_number or "—", "#2563EB", None)
        if key == "shipping_line":
            return (rec.shipping_line or "—", None, None)
        if key == "client_name":
            name = (getattr(rec, "_client_name_ar", None)
                    or getattr(rec, "_client_name_en", None)
                    or (getattr(rec.client, "name_ar", None) if rec.client else None)
                    or "—")
            return (name, None, None)
        if key == "cargo_type":
            return (rec.cargo_type or "—", None, None)
        if key == "quantity":
            return (rec.quantity or "—", None, None)
        if key == "origin_country":
            return (rec.origin_country or "—", None, None)
        if key == "port_of_discharge":
            return (rec.port_of_discharge or "—", None, None)
        if key == "docs_delivered":
            if rec.docs_delivered:
                return ("✅ " + self._("yes"), "#059669", None)
            return ("—", None, None)
        if key == "cargo_tracking":
            txt = (rec.cargo_tracking or "—")
            return (txt.split("\n")[0][:50], None, None)
        if key == "docs_received_date":
            return (_date(rec.docs_received_date), None, None)
        if key == "containers_count":
            return (str(rec.containers_count) if rec.containers_count else "—", None, None)
        if key == "bl_status":
            if rec.bl_status:
                return (self._(f"bl_status_{rec.bl_status}"), None, None)
            return ("—", None, None)
        if key == "eta":
            return (_date(rec.eta), None, None)
        if key == "status":
            meta = _STATUS_META.get(rec.status, {})
            txt  = f"{meta.get('icon','')} {self._(f'container_status_{rec.status}')}"
            return (txt, meta.get("color"), None)
        return ("—", None, None)

    # ── Actions ───────────────────────────────────────────────────────────

    def _on_row_double_clicked(self, index):
        row = index.row()
        # أضف offset الـ pagination
        real_idx = (self.current_page - 1) * self.rows_per_page + row
        if real_idx >= len(self.data):
            return
        rec = self.data[real_idx]
        self._open_container_dialog(rec)

    def _open_container_dialog(self, rec):
        """يفتح dialog تفاصيل الكونتينر."""
        try:
            full_rec = _crud.get_by_id(rec.id)
        except Exception:
            full_rec = rec
        from ui.dialogs.view_details.view_container_dialog import ViewContainerDialog
        dlg = ViewContainerDialog(
            full_rec,
            current_user=self.current_user,
            parent=self,
            can_edit=self.can_edit,
            can_delete=self.can_delete,
        )
        if dlg.exec():
            self.reload_data()
        from core.data_bus import DataBus
        DataBus.get_instance().emit("containers")

    def _get_selected_rec(self):
        """يرجع الـ record المحدد حالياً."""
        rows = self.get_selected_rows()
        if not rows:
            return None
        real_idx = (self.current_page - 1) * self.rows_per_page + rows[0]
        if real_idx >= len(self.data):
            return None
        return self.data[real_idx]

    def _show_context_menu(self, pos):
        """Context menu مخصص للكونتينرات."""
        from PySide6.QtWidgets import QMenu
        rec = self._get_selected_rec()
        if not rec:
            return
        menu = QMenu(self)
        act_view = menu.addAction(f"👁  {self._('view')}")
        if self.can_edit:
            act_edit = menu.addAction(f"✏️  {self._('edit')}")
        else:
            act_edit = None
        if self.can_delete:
            menu.addSeparator()
            act_delete = menu.addAction(f"🗑  {self._('delete')}")
        else:
            act_delete = None

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action is None:
            return
        if action == act_view:
            self._open_container_dialog(rec)
        elif act_edit and action == act_edit:
            self._open_container_dialog(rec)
        elif act_delete and action == act_delete:
            self._confirm_delete(rec)

    def _confirm_delete(self, rec):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, self._("confirm"), self._("confirm_delete"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                _crud.delete(rec.id)
                self.reload_data()
                from core.data_bus import DataBus
                DataBus.get_instance().emit("containers")
            except Exception as e:
                QMessageBox.critical(self, self._("error"), str(e))

    def add_new_item(self):
        from ui.dialogs.add_edit_container_dialog import AddEditContainerDialog
        from PySide6.QtWidgets import QDialog
        dlg = AddEditContainerDialog(parent=self, current_user=self.current_user)
        if dlg.exec() == QDialog.Accepted:
            self.reload_data()
            from core.data_bus import DataBus
            DataBus.get_instance().emit("containers")

    def _open_edit_dialog(self, obj):
        if obj:
            self._open_container_dialog(obj)

    def _delete_single(self, obj):
        if obj:
            self._confirm_delete(obj)

    def select_record_by_id(self, record_id: int):
        if not self._all_rows:
            self.reload_data()
        for row_idx, rec in enumerate(self.data):
            if getattr(rec, "id", None) == record_id:
                self.table.setCurrentCell(row_idx, 0)
                self.table.selectRow(row_idx)
                self.table.scrollToItem(self.table.item(row_idx, 0))
                return
        if hasattr(self, "_stats_bar"):
            self._stats_bar._set_active("")
        self._on_status_filter_change("")
        for row_idx, rec in enumerate(self.data):
            if getattr(rec, "id", None) == record_id:
                self.table.setCurrentCell(row_idx, 0)
                self.table.selectRow(row_idx)
                self.table.scrollToItem(self.table.item(row_idx, 0))
                return

    # ── Retranslate ───────────────────────────────────────────────────────

    def retranslate_ui(self):
        super().retranslate_ui()
        if hasattr(self, "_btn_print"):
            self._btn_print.setText(f"🖨  {self._('print_list')}")
        if hasattr(self, "_stats_bar"):
            self._stats_bar.retranslate()
        # تحديث headers الجدول
        if hasattr(self, "table"):
            from PySide6.QtWidgets import QHeaderView
            self.table.setHorizontalHeaderLabels(
                [""] + [self._(lbl) for _, lbl, _, _ in _COLUMNS]
            )
        self.reload_data()

    # ── Print ─────────────────────────────────────────────────────────────

    def _print_list(self):
        if not self.data:
            QMessageBox.information(self, self._("info"), self._("no_data"))
            return
        from PySide6.QtCore  import QThread, Signal, QObject
        from PySide6.QtWidgets import QApplication
        from core.translator import TranslationManager

        rows_snapshot = list(self.data)
        lang          = TranslationManager.get_instance().get_current_language()
        search        = self.search_bar.text().strip() if hasattr(self, "search_bar") else ""
        active_filter = self._stats_bar.current_filter if hasattr(self, "_stats_bar") else ""
        parts = []
        if search:       parts.append(f"{self._('search')}: {search}")
        if active_filter: parts.append(self._(f"container_status_{active_filter}"))
        filters_str = " | ".join(parts)

        class _Worker(QObject):
            finished = Signal(bool, str, str)
            def __init__(self, rows, lang, filters):
                super().__init__()
                self._rows = rows; self._lang = lang; self._filters = filters
            def run(self):
                try:
                    from services.container_report_service import ContainerReportService
                    ok, path, err = ContainerReportService().render_list(
                        self._rows, lang=self._lang, filters=self._filters)
                    self.finished.emit(ok, path, err)
                except Exception as e:
                    self.finished.emit(False, "", str(e))

        self._print_thread = QThread(self)
        self._print_worker = _Worker(rows_snapshot, lang, filters_str)
        self._print_worker.moveToThread(self._print_thread)

        def _on_done(ok, path, err):
            QApplication.restoreOverrideCursor()
            self._btn_print.setEnabled(True)
            self._btn_print.setText(f"🖨  {self._('print_list')}")
            self._print_thread.quit()
            if not ok:
                QMessageBox.critical(self, self._("error"), f"{self._('pdf_error')}\n{err}")
                return
            import os, subprocess, sys
            try:
                if sys.platform == "win32":   os.startfile(path)
                elif sys.platform == "darwin": subprocess.Popen(["open", path])
                else:                          subprocess.Popen(["xdg-open", path])
            except Exception:
                QMessageBox.warning(self, self._("info"), path)

        self._print_thread.started.connect(self._print_worker.run)
        self._print_worker.finished.connect(_on_done)
        self._print_worker.finished.connect(self._print_worker.deleteLater)
        self._print_thread.finished.connect(self._print_thread.deleteLater)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._btn_print.setEnabled(False)
        self._btn_print.setText(f"⏳  {self._('generating')}")
        self._print_thread.start()