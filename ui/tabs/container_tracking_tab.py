"""
container_tracking_tab.py — LOGIPORT
======================================
تبويب تتبع الكونتينرات — تتبع يدوي كامل.
- ربط بالزبون (صاحب البضاعة)
- ربط بالإدخالات (many-to-many)
- ربط اختياري بالمعاملة
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QLabel, QFrame,
    QTableWidgetItem, QComboBox, QLineEdit, QSizePolicy, QMessageBox,
    QHeaderView, QAbstractItemView, QListWidgetItem,
    QTableWidget, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui  import QFont, QColor

from core.translator import TranslationManager
from core.permissions import has_perm, is_admin

from database.crud.container_tracking_crud import ContainerTrackingCRUD
from database.models.container_tracking    import ContainerTracking

_BOLD = QFont()
_BOLD.setBold(True)

_crud = ContainerTrackingCRUD()

_STATUS_META = {
    "booked":     {"icon": "📋", "color": "#6366F1"},
    "loaded":     {"icon": "📦", "color": "#0891B2"},
    "in_transit": {"icon": "🚢", "color": "#2563EB"},
    "arrived":    {"icon": "⚓", "color": "#7C3AED"},
    "customs":    {"icon": "🏛️", "color": "#D97706"},
    "delivered":  {"icon": "✅", "color": "#059669"},
    "hold":       {"icon": "⚠️",  "color": "#DC2626"},
}


class ContainerTrackingTab(QWidget):

    required_permissions = {
        "view":   "view_transactions",
        "add":    "add_transaction",
        "edit":   "edit_transaction",
        "delete": "delete_transaction",
    }

    _COLUMNS = [
        "container_no", "bl_number", "client_name", "shipping_line",
        "vessel_name", "port_of_loading", "port_of_discharge",
        "eta", "ata", "status", "entries_count",
    ]

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._            = TranslationManager.get_instance().translate
        self._rows: list[ContainerTracking] = []

        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

        self._build_ui()

    def _build_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)
        self._layout.addWidget(self._build_toolbar())

        self._table = QTableWidget()
        self._table.setObjectName("data-table")
        self._table.setColumnCount(len(self._COLUMNS))
        self._table.setHorizontalHeaderLabels([self._col_label(c) for c in self._COLUMNS])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_double_click)
        self._layout.addWidget(self._table, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("text-muted")
        self._layout.addWidget(self._status_lbl)

        self._apply_permissions()
        self._load_data()

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        h = QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText(self._("container_search_placeholder"))
        self._search.setObjectName("search-input")
        self._search.setFixedWidth(240)
        self._search.textChanged.connect(self._load_data)
        h.addWidget(self._search)

        self._status_filter = QComboBox()
        self._status_filter.setObjectName("filter-combo")
        self._status_filter.addItem(self._("all_statuses"), "")
        for s in ContainerTracking.STATUSES:
            meta = _STATUS_META.get(s, {})
            self._status_filter.addItem(f"{meta.get('icon','')} {self._(f'container_status_{s}')}", s)
        self._status_filter.currentIndexChanged.connect(self._load_data)
        h.addWidget(self._status_filter)

        h.addStretch()

        self._btn_add = QPushButton(f"+ {self._('add_container')}")
        self._btn_add.setObjectName("primary-btn")
        self._btn_add.clicked.connect(self._on_add)
        h.addWidget(self._btn_add)

        _lbl_print = self._("print_list")
        self._btn_print = QPushButton(f"🖨  {_lbl_print}")
        self._btn_print.setObjectName("secondary-btn")
        self._btn_print.setToolTip(self._("print_list_tooltip"))
        self._btn_print.clicked.connect(self._print_list)
        h.addWidget(self._btn_print)

        self._btn_refresh = QPushButton(self._("refresh"))
        self._btn_refresh.setObjectName("secondary-btn")
        self._btn_refresh.clicked.connect(self._load_data)
        h.addWidget(self._btn_refresh)

        return bar

    def _load_data(self):
        search = self._search.text().strip() if hasattr(self, "_search") else ""
        status = self._status_filter.currentData() if hasattr(self, "_status_filter") else ""
        self._rows = _crud.get_all(search=search, status=status or None)
        self._render_table()
        total = _crud.count(search=search, status=status or None)
        self._status_lbl.setText(self._("container_count_label").format(n=len(self._rows), total=total))

    def _render_table(self):
        self._table.setRowCount(0)
        self._table.setRowCount(len(self._rows))
        for row_idx, rec in enumerate(self._rows):
            for col_idx, (val, fg, bold) in enumerate(self._row_values(rec)):
                item = QTableWidgetItem(val)
                item.setData(Qt.UserRole, rec.id)
                if fg:
                    item.setForeground(QColor(fg))
                if bold:
                    item.setFont(_BOLD)
                self._table.setItem(row_idx, col_idx, item)
        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)

    def _row_values(self, rec: ContainerTracking):
        def _date(d): return d.strftime("%Y-%m-%d") if d else "—"
        meta = _STATUS_META.get(rec.status, {})
        status_txt = f"{meta.get('icon','')} {self._(f'container_status_{rec.status}')}"
        client_name = ""
        if rec.client:
            client_name = getattr(rec.client, "name_ar", None) or getattr(rec.client, "name_en", None) or ""
        entries_count = str(len(rec.entries)) if rec.entries is not None else "0"
        return [
            (rec.container_no or "",       "#2563EB", True),
            (rec.bl_number or "—",          None,     False),
            (client_name or "—",            None,     False),
            (rec.shipping_line or "—",      None,     False),
            (rec.vessel_name or "—",        None,     False),
            (rec.port_of_loading or "—",    None,     False),
            (rec.port_of_discharge or "—",  None,     False),
            (_date(rec.eta),                None,     False),
            (_date(rec.ata),                None,     False),
            (status_txt, meta.get("color"), False),
            (entries_count,                 None,     False),
        ]

    def _on_double_click(self, index):
        row = index.row()
        if row < len(self._rows):
            rec = self._rows[row]
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
                self._load_data()

    def _on_add(self):
        from ui.dialogs.add_edit_container_dialog import AddEditContainerDialog
        from PySide6.QtWidgets import QDialog
        dlg = AddEditContainerDialog(parent=self, current_user=self.current_user)
        if dlg.exec() == QDialog.Accepted:
            self._load_data()

    def _col_label(self, col: str) -> str:
        _map = {
            "container_no":     "container_no_label",
            "bl_number":        "bl_number_label",
            "client_name":      "client_label",
            "shipping_line":    "shipping_line_label",
            "vessel_name":      "vessel_name_label",
            "port_of_loading":  "port_of_loading_label",
            "port_of_discharge":"port_of_discharge_label",
            "eta":              "eta_label",
            "ata":              "ata_label",
            "status":           "status_label",
            "entries_count":    "linked_entries_count",
        }
        return self._(_map.get(col, col))

    def _apply_permissions(self):
        """يُظهر/يُخفي الأزرار حسب صلاحيات المستخدم الحالي."""
        u = self.current_user
        self.can_add    = is_admin(u) or has_perm(u, "add_transaction")
        self.can_edit   = is_admin(u) or has_perm(u, "edit_transaction")
        self.can_delete = is_admin(u) or has_perm(u, "delete_transaction")
        self._btn_add.setVisible(self.can_add)

    def set_current_user(self, user):
        """يُستدعى من main_window عند تغيير المستخدم."""
        self.current_user = user
        self._apply_permissions()
        self._load_data()

    def retranslate_ui(self):
        # أعد تعيين دالة الترجمة للغة الجديدة
        self._ = TranslationManager.get_instance().translate

        # أعد نص أزرار الـ toolbar
        self._btn_add.setText(f"+ {self._('add_container')}")
        if hasattr(self, "_btn_print"):
            self._btn_print.setText(f"🖨  {self._('print_list')}")
        if hasattr(self, "_btn_refresh"):
            self._btn_refresh.setText(self._("refresh"))

        # أعد بناء خيارات فلتر الحالة
        if hasattr(self, "_status_filter"):
            current_status = self._status_filter.currentData()
            self._status_filter.blockSignals(True)
            self._status_filter.clear()
            self._status_filter.addItem(self._("all_statuses"), "")
            for s in ContainerTracking.STATUSES:
                meta = _STATUS_META.get(s, {})
                self._status_filter.addItem(
                    f"{meta.get('icon', '')} {self._(f'container_status_{s}')}", s
                )
            # أعد اختيار الفلتر السابق
            idx = self._status_filter.findData(current_status)
            self._status_filter.setCurrentIndex(max(idx, 0))
            self._status_filter.blockSignals(False)

        # أعد ترجمة رؤوس الجدول
        if hasattr(self, "_table"):
            self._table.setHorizontalHeaderLabels(
                [self._col_label(c) for c in self._COLUMNS]
            )

        # أعد تحميل البيانات (يحدّث نصوص الحالة في الصفوف)
        self._load_data()

    def _print_list(self):
        """يولّد PDF لقائمة الكونتينرات الظاهرة حالياً ويفتحه."""
        import os, subprocess, sys
        from PySide6.QtWidgets import QMessageBox

        if not self._rows:
            QMessageBox.information(self, self._("info"), self._("no_data"))
            return

        try:
            from services.container_report_service import ContainerReportService
            lang = TranslationManager.get_instance().get_current_language()

            # نبني نص الفلتر المُطبّق
            filters_parts = []
            search = self._search.text().strip() if hasattr(self, "_search") else ""
            status = self._status_filter.currentData() if hasattr(self, "_status_filter") else ""
            if search:
                filters_parts.append(f"{self._('search')}: {search}")
            if status:
                filters_parts.append(self._(f"container_status_{status}"))
            filters_str = " | ".join(filters_parts)

            svc = ContainerReportService()
            ok, path, err = svc.render_list(self._rows, lang=lang, filters=filters_str)
            if not ok:
                QMessageBox.critical(self, self._("error"), f"{self._('pdf_error')}\n{err}")
                return

            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            QMessageBox.critical(self, self._("error"), str(e))


# ── ديالوج الإضافة / التعديل ──────────────────────────────────────────────────

class ContainerBadge(QLabel):
    """
    شارة صغيرة في entries_tab تُظهر الكونتينر المرتبط بالإدخال.
    عند الضغط عليها تفتح بطاقة الكونتينر.
    """
    def __init__(self, entry_id: int, parent=None):
        super().__init__(parent)
        self._entry_id = entry_id
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(TranslationManager.get_instance().translate("view_container"))
        self.refresh()

    def refresh(self):
        containers = _crud.get_containers_for_entry(self._entry_id)
        if containers:
            nos = ", ".join(c.container_no for c in containers[:2])
            if len(containers) > 2:
                nos += f" +{len(containers)-2}"
            self.setText(f"🚢 {nos}")
            self.setStyleSheet("color: #2563EB; font-size: 11px;")
        else:
            self.setText("")

    def mousePressEvent(self, event):
        containers = _crud.get_containers_for_entry(self._entry_id)
        if containers:
            try:
                full = _crud.get_by_id(containers[0].id)
            except Exception:
                full = containers[0]
            from ui.dialogs.view_details.view_container_dialog import ViewContainerDialog
            dlg = ViewContainerDialog(full, parent=self)
            dlg.exec()
            self.refresh()