"""
container_tracking_tab.py — LOGIPORT v2
=========================================
تبويب تتبع البوليصات — تتبع يدوي كامل.

أعمدة الجدول الرئيسي (حسب الطلب):
  رقم البوليصة | شركة الشحن | صاحب البضاعة | نوع البضاعة | العدد |
  الدولة المرسلة | ميناء الوصول | تسليم الاوراق | تتبع الكارجو |
  تاريخ استلام الاوراق | عدد الكونترات | حالة البوليصة | ETA | الحالة
"""
from __future__ import annotations

from datetime import date as _date_type

from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QLabel,
    QTableWidgetItem, QLineEdit, QSizePolicy, QMessageBox,
    QHeaderView, QAbstractItemView, QTableWidget,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui  import QFont, QColor

from core.translator import TranslationManager
from core.permissions import has_perm, is_admin

from database.crud.container_tracking_crud import ContainerTrackingCRUD
from database.models.container_tracking    import ContainerTracking

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

_ETA_OVERDUE_BG = "#FEE2E2"
_ETA_OVERDUE_FG = "#DC2626"
_ETA_TODAY_BG   = "#FEF3C7"
_ETA_TODAY_FG   = "#D97706"
_ETA_SOON_FG    = "#059669"


def _eta_state(eta, status: str):
    if not eta or status not in _ACTIVE_STATUSES:
        return None, 0
    today = _date_type.today()
    try:
        delta = (eta - today).days
    except Exception:
        return None, 0
    if delta < 0:   return "overdue", abs(delta)
    if delta == 0:  return "today",   0
    if delta <= 3:  return "soon",    delta
    return "normal", delta


# ─── Stats / Filter Bar ───────────────────────────────────────────────────────

class _StatsBar(QWidget):
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
        if callable(getattr(self, "on_filter_change", None)):
            self.on_filter_change(key)

    def _set_active(self, key: str):
        self._active_filter = key
        for k, btn in self._btns.items():
            btn.setChecked(k == key)

    def update_counts(self, rows):
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

    @property
    def current_filter(self) -> str:
        return self._active_filter


# ─── Column definitions ───────────────────────────────────────────────────────

# (key, label_key, min_width, stretch)
_COLUMNS = [
    ("bl_number",          "bl_number_label",          110, False),
    ("shipping_line",      "shipping_line_label",       120, False),
    ("client_name",        "client_label",              130, True),
    ("cargo_type",         "cargo_type_label",          110, False),
    ("quantity",           "quantity_label",             70, False),
    ("origin_country",     "origin_country_label",      110, False),
    ("port_of_discharge",  "port_of_discharge_label",   110, False),
    ("docs_delivered",     "docs_delivered_col",         80, False),
    ("cargo_tracking",     "cargo_tracking_label",      120, True),
    ("docs_received_date", "docs_received_date_label",   90, False),
    ("containers_count",   "containers_count_label",     60, False),
    ("bl_status",          "bl_status_label",            90, False),
    ("eta",                "eta_label",                  80, False),
    ("status",             "col_status",                 90, False),
]


# ─── Main Tab ─────────────────────────────────────────────────────────────────

class ContainerTrackingTab(QWidget):

    required_permissions = {
        "view":   "view_transactions",
        "add":    "add_transaction",
        "edit":   "edit_transaction",
        "delete": "delete_transaction",
    }

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._            = TranslationManager.get_instance().translate
        self._rows: list  = []
        self._all_rows: list = []
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)
        self._build_ui()
        # تحديث تلقائي عند تغيير بيانات الحاويات من أي مكان
        try:
            from core.data_bus import DataBus
            DataBus.get_instance().subscribe("containers", self._load_data)
        except Exception:
            pass

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(8)
        self._layout.addWidget(self._build_toolbar())

        self._stats_bar = _StatsBar(self)
        self._stats_bar.on_filter_change = self._on_status_filter_change
        self._layout.addWidget(self._stats_bar)

        self._table = QTableWidget()
        self._table.setObjectName("data-table")
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(
            [self._(c[1]) for c in _COLUMNS]
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        for i, (_, _, min_w, stretch) in enumerate(_COLUMNS):
            self._table.setColumnWidth(i, min_w)
            if stretch:
                hdr.setSectionResizeMode(i, QHeaderView.Stretch)
        hdr.setStretchLastSection(False)

        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
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
        h   = QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText(self._("container_search_placeholder"))
        self._search.setObjectName("search-input")
        self._search.setFixedWidth(280)
        self._search.textChanged.connect(self._on_search_change)
        h.addWidget(self._search)
        h.addStretch()

        self._btn_add = QPushButton(f"+ {self._('add_container')}")
        self._btn_add.setObjectName("primary-btn")
        self._btn_add.clicked.connect(self._on_add)
        h.addWidget(self._btn_add)

        self._btn_print = QPushButton(f"🖨  {self._('print_list')}")
        self._btn_print.setObjectName("secondary-btn")
        self._btn_print.setToolTip(self._("print_list_tooltip"))
        self._btn_print.clicked.connect(self._print_list)
        h.addWidget(self._btn_print)

        self._btn_refresh = QPushButton(self._("refresh"))
        self._btn_refresh.setObjectName("secondary-btn")
        self._btn_refresh.clicked.connect(self._load_data)
        h.addWidget(self._btn_refresh)

        return bar

    # ── Data ──────────────────────────────────────────────────────────────────

    def _on_search_change(self):
        if not hasattr(self, "_search_timer"):
            self._search_timer = QTimer(self)
            self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(self._load_data)
        self._search_timer.start(250)

    def _load_data(self):
        search = self._search.text().strip() if hasattr(self, "_search") else ""
        self._all_rows = _crud.get_all(search=search, status=None)
        if hasattr(self, "_stats_bar"):
            self._stats_bar.update_counts(self._all_rows)
        current_filter = self._stats_bar.current_filter if hasattr(self, "_stats_bar") else ""
        self._apply_status_filter(current_filter)

    def _apply_status_filter(self, status_key: str):
        if status_key:
            self._rows = [r for r in self._all_rows if r.status == status_key]
        else:
            self._rows = list(self._all_rows)
        self._render_table()
        self._status_lbl.setText(
            self._("container_count_label").format(n=len(self._rows), total=len(self._all_rows))
        )

    def _on_status_filter_change(self, status_key: str):
        self._apply_status_filter(status_key)

    # ── Render ────────────────────────────────────────────────────────────────

    def _render_table(self):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        self._table.setRowCount(len(self._rows))
        cell_font = QFont()
        cell_font.setPointSize(9)

        for row_idx, rec in enumerate(self._rows):
            eta_state, eta_days = _eta_state(rec.eta, rec.status or "")
            for col_idx, (key, _, _, _) in enumerate(_COLUMNS):
                val, fg, bg = self._cell_value(rec, key)
                item = QTableWidgetItem(val)
                item.setData(Qt.UserRole, rec.id)
                item.setFont(cell_font)
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                # ETA coloring
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
                self._table.setItem(row_idx, col_idx, item)

        self._table.setSortingEnabled(True)

    def _cell_value(self, rec: ContainerTracking, key: str):
        """يعيد (نص, fg_color أو None, bg_color أو None)"""
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
            # اعرض أول سطر فقط في الجدول
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

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_double_click(self, index):
        row = index.row()
        if row >= len(self._rows):
            return
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
        from core.data_bus import DataBus
        DataBus.get_instance().emit("containers")

    def _on_add(self):
        from ui.dialogs.add_edit_container_dialog import AddEditContainerDialog
        from PySide6.QtWidgets import QDialog
        dlg = AddEditContainerDialog(parent=self, current_user=self.current_user)
        if dlg.exec() == QDialog.Accepted:
            self._load_data()
            from core.data_bus import DataBus
            DataBus.get_instance().emit("containers")

    def _apply_permissions(self):
        u = self.current_user
        self.can_add    = is_admin(u) or has_perm(u, "add_transaction")
        self.can_edit   = is_admin(u) or has_perm(u, "edit_transaction")
        self.can_delete = is_admin(u) or has_perm(u, "delete_transaction")
        self._btn_add.setVisible(self.can_add)

    def set_current_user(self, user):
        self.current_user = user
        self._apply_permissions()
        self._load_data()

    def select_record_by_id(self, record_id: int):
        if not self._all_rows:
            self._load_data()
        for row_idx, rec in enumerate(self._rows):
            if getattr(rec, "id", None) == record_id:
                self._table.setCurrentCell(row_idx, 0)
                self._table.selectRow(row_idx)
                self._table.scrollToItem(self._table.item(row_idx, 0))
                return
        self._stats_bar._set_active("")
        self._on_status_filter_change("")
        for row_idx, rec in enumerate(self._rows):
            if getattr(rec, "id", None) == record_id:
                self._table.setCurrentCell(row_idx, 0)
                self._table.selectRow(row_idx)
                self._table.scrollToItem(self._table.item(row_idx, 0))
                return

    # ── Retranslate ───────────────────────────────────────────────────────────

    def retranslate_ui(self):
        self._ = TranslationManager.get_instance().translate
        self._btn_add.setText(f"+ {self._('add_container')}")
        if hasattr(self, "_btn_print"):
            self._btn_print.setText(f"🖨  {self._('print_list')}")
        if hasattr(self, "_btn_refresh"):
            self._btn_refresh.setText(self._("refresh"))
        if hasattr(self, "_stats_bar"):
            self._stats_bar.retranslate()
        if hasattr(self, "_table"):
            self._table.setHorizontalHeaderLabels(
                [self._(c[1]) for c in _COLUMNS]
            )
        self._load_data()

    # ── Print ─────────────────────────────────────────────────────────────────

    def _print_list(self):
        if not self._rows:
            QMessageBox.information(self, self._("info"), self._("no_data"))
            return

        from PySide6.QtCore import QThread, Signal, QObject
        from PySide6.QtWidgets import QApplication

        rows_snapshot = list(self._rows)
        lang          = TranslationManager.get_instance().get_current_language()
        filters_parts = []
        search        = self._search.text().strip() if hasattr(self, "_search") else ""
        active_filter = self._stats_bar.current_filter if hasattr(self, "_stats_bar") else ""
        if search:
            filters_parts.append(f"{self._('search')}: {search}")
        if active_filter:
            filters_parts.append(self._(f"container_status_{active_filter}"))
        filters_str = " | ".join(filters_parts)

        class _PrintWorker(QObject):
            finished = Signal(bool, str, str)

            def __init__(self, rows, lang, filters):
                super().__init__()
                self._rows    = rows
                self._lang    = lang
                self._filters = filters

            def run(self):
                try:
                    from services.container_report_service import ContainerReportService
                    svc      = ContainerReportService()
                    ok, path, err = svc.render_list(
                        self._rows, lang=self._lang, filters=self._filters
                    )
                    self.finished.emit(ok, path, err)
                except Exception as e:
                    self.finished.emit(False, "", str(e))

        self._print_thread = QThread(self)
        self._print_worker = _PrintWorker(rows_snapshot, lang, filters_str)
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
                if sys.platform == "win32":
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])
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