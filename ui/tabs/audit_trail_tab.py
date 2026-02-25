"""
AuditTrailTab - LOGIPORT v1.0
==============================
Audit trail page with full translation support.
"""

from typing import Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QDateEdit, QComboBox, QLineEdit, QSizePolicy, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QFont, QColor

from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from database.db_utils import format_local_dt
from database.models import get_session_local, AuditLog, User
from sqlalchemy import desc, func
from sqlalchemy.orm import joinedload
from datetime import datetime


ACTION_ICONS = {
    "create": "➕", "insert": "➕", "update": "✏️",
    "delete": "🗑️", "import": "📥", "export": "📤",
    "print": "🖨️", "login": "🔐", "logout": "🔓",
    "view": "👁️", "generate": "📄",
}
ACTION_COLORS = {
    "create": "#2ECC71", "insert": "#2ECC71",
    "update": "#F39C12", "delete": "#E74C3C",
    "import": "#3498DB", "export": "#9B59B6",
    "print":  "#1ABC9C", "login":  "#2ECC71",
    "logout": "#95A5A6", "generate": "#E67E22",
}
TABLE_TRANSLATION_KEYS: Dict[str, str] = {
    "transactions":    "table_transactions",
    "materials":       "table_materials",
    "clients":         "table_clients",
    "users":           "table_users",
    "documents":       "table_documents",
    "entries":         "table_entries",
    "companies":       "table_companies",
    "countries":       "countries",
    "currencies":      "currencies",
    "pricing_types":   "pricing",
    "delivery_methods":"table_delivery_methods",
    "packaging_types": "table_packaging_types",
    "material_types":  "table_material_types",
    "roles":           "roles",
}

ROWS_PER_PAGE_OPTIONS = [25, 50, 100, 200]


class AuditTrailTab(QWidget):

    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self._tm = TranslationManager.get_instance()
        self._ = self._tm.translate
        self._current_user = current_user or SettingsManager.get_instance().get("user")
        self.setObjectName("audit-trail-tab")
        self._page = 1
        self._page_size = 50
        self._total = 0
        self._all_users: list = []
        self._build_ui()
        self._load_user_list()
        self._reload()
        self._tm.language_changed.connect(self.retranslate_ui)

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(24, 20, 24, 20)
        main.setSpacing(14)
        main.addWidget(self._build_header())
        main.addWidget(self._build_filter_bar())
        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setObjectName("separator")
        main.addWidget(sep)
        self._tbl = QTableWidget()
        self._tbl.setObjectName("data-table")
        self._tbl.setColumnCount(6)
        self._tbl.setHorizontalHeaderLabels([
            self._("col_user"), self._("col_action"), self._("col_table"),
            self._("col_record_no"), self._("col_details"), self._("col_datetime")
        ])
        self._tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tbl.setFont(QFont("Tajawal", 9))
        main.addWidget(self._tbl, 1)
        main.addLayout(self._build_pagination())

    def _build_header(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self._title_lbl = QLabel(self._("audit_trail_title"))
        self._title_lbl.setFont(QFont("Tajawal", 20, QFont.Bold))
        self._title_lbl.setObjectName("dashboard-title")
        lay.addWidget(self._title_lbl)
        lay.addStretch()
        self._ts_lbl = QLabel()
        self._ts_lbl.setObjectName("text-muted")
        self._ts_lbl.setFont(QFont("Tajawal", 9))
        lay.addWidget(self._ts_lbl)
        self._ref_btn = QPushButton(self._("refresh"))
        self._ref_btn.setObjectName("btn-primary")
        self._ref_btn.setMinimumHeight(34)
        self._ref_btn.setCursor(Qt.PointingHandCursor)
        self._ref_btn.setFont(QFont("Tajawal", 10))
        self._ref_btn.clicked.connect(self._reload)
        lay.addWidget(self._ref_btn)
        self._exp_btn = QPushButton(self._("export_csv"))
        self._exp_btn.setObjectName("topbar-btn")
        self._exp_btn.setMinimumHeight(34)
        self._exp_btn.setFont(QFont("Tajawal", 10))
        self._exp_btn.setCursor(Qt.PointingHandCursor)
        self._exp_btn.clicked.connect(self._export_csv)
        lay.addWidget(self._exp_btn)
        return w

    def _build_filter_bar(self) -> QWidget:
        w = QWidget()
        w.setObjectName("card")

        # صفّان بدل صف واحد — يمنع توسّع النافذة أكثر من 1920px
        outer = QVBoxLayout(w)
        outer.setContentsMargins(14, 8, 14, 8)
        outer.setSpacing(6)

        # ── الصف الأول: تصفية التاريخ + أزرار الفترة السريعة ────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self._lbl_from = self._lbl(self._("date_from"))
        row1.addWidget(self._lbl_from)
        self._date_from = QDateEdit()
        self._date_from.setObjectName("form-input")
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        self._date_from.setDate(QDate.currentDate().addDays(-30))
        self._date_from.setFixedWidth(108)
        self._date_from.dateChanged.connect(self._on_filter_changed)
        row1.addWidget(self._date_from)

        self._lbl_to = self._lbl(self._("date_to"))
        row1.addWidget(self._lbl_to)
        self._date_to = QDateEdit()
        self._date_to.setObjectName("form-input")
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setFixedWidth(108)
        self._date_to.dateChanged.connect(self._on_filter_changed)
        row1.addWidget(self._date_to)

        sep0 = QFrame(); sep0.setFrameShape(QFrame.VLine)
        sep0.setFixedWidth(1); sep0.setFixedHeight(22)
        row1.addWidget(sep0)

        self._btn_today = QPushButton(self._("filter_today"))
        self._btn_today.setObjectName("topbar-btn"); self._btn_today.setMinimumHeight(28)
        self._btn_today.setFont(QFont("Tajawal", 9)); self._btn_today.setCursor(Qt.PointingHandCursor)
        self._btn_today.clicked.connect(self._pre_today); row1.addWidget(self._btn_today)
        self._btn_week = QPushButton(self._("filter_week"))
        self._btn_week.setObjectName("topbar-btn"); self._btn_week.setMinimumHeight(28)
        self._btn_week.setFont(QFont("Tajawal", 9)); self._btn_week.setCursor(Qt.PointingHandCursor)
        self._btn_week.clicked.connect(self._pre_week); row1.addWidget(self._btn_week)
        self._btn_month = QPushButton(self._("filter_month"))
        self._btn_month.setObjectName("topbar-btn"); self._btn_month.setMinimumHeight(28)
        self._btn_month.setFont(QFont("Tajawal", 9)); self._btn_month.setCursor(Qt.PointingHandCursor)
        self._btn_month.clicked.connect(self._pre_month); row1.addWidget(self._btn_month)

        row1.addStretch()
        outer.addLayout(row1)

        # ── الصف الثاني: فلاتر المستخدم / العملية / الجدول + بحث ───────────
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self._lbl_user = self._lbl(self._("filter_user"))
        row2.addWidget(self._lbl_user)
        self._user_combo = QComboBox()
        self._user_combo.setObjectName("form-input")
        self._user_combo.setFixedWidth(130)
        self._user_combo.addItem(self._("all"), None)
        self._user_combo.currentIndexChanged.connect(self._on_filter_changed)
        row2.addWidget(self._user_combo)

        self._lbl_action = self._lbl(self._("filter_action"))
        row2.addWidget(self._lbl_action)
        self._action_combo = QComboBox()
        self._action_combo.setObjectName("form-input")
        self._action_combo.setFixedWidth(120)
        self._action_combo.addItem(self._("all"), None)
        for act, icon in ACTION_ICONS.items():
            self._action_combo.addItem(f"{icon} {act}", act)
        self._action_combo.currentIndexChanged.connect(self._on_filter_changed)
        row2.addWidget(self._action_combo)

        self._lbl_table = self._lbl(self._("filter_table"))
        row2.addWidget(self._lbl_table)
        self._table_combo = QComboBox()
        self._table_combo.setObjectName("form-input")
        self._table_combo.setFixedWidth(130)
        self._table_combo.addItem(self._("all"), None)
        for tbl_key, tbl_trans_key in TABLE_TRANSLATION_KEYS.items():
            self._table_combo.addItem(self._(tbl_trans_key), tbl_key)
        self._table_combo.currentIndexChanged.connect(self._on_filter_changed)
        row2.addWidget(self._table_combo)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.VLine)
        sep2.setFixedWidth(1); sep2.setFixedHeight(22)
        row2.addWidget(sep2)

        self._search = QLineEdit()
        self._search.setObjectName("form-input")
        self._search.setPlaceholderText(self._("search_details_placeholder"))
        self._search.setMinimumWidth(120)
        self._search.setSizePolicy(
            self._search.sizePolicy().horizontalPolicy(),
            self._search.sizePolicy().verticalPolicy()
        )
        from PySide6.QtWidgets import QSizePolicy as QSP
        self._search.setSizePolicy(QSP.Expanding, QSP.Fixed)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(400)
        self._search_timer.timeout.connect(lambda: self._reload())
        self._search.textChanged.connect(lambda: self._search_timer.start())
        row2.addWidget(self._search, 1)

        self._clr_btn = QPushButton("✖")
        self._clr_btn.setObjectName("topbar-btn"); self._clr_btn.setMinimumHeight(28)
        self._clr_btn.setToolTip(self._("clear_filters_tooltip"))
        self._clr_btn.setCursor(Qt.PointingHandCursor)
        self._clr_btn.clicked.connect(self._clear_filters)
        row2.addWidget(self._clr_btn)

        self._count_lbl = QLabel()
        self._count_lbl.setObjectName("text-muted")
        row2.addWidget(self._count_lbl)

        outer.addLayout(row2)

        self._count_lbl.setFont(QFont("Tajawal", 9))
        return w

    def _build_pagination(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(8)
        self._btn_prev = QPushButton(self._("previous_page"))
        self._btn_prev.setObjectName("topbar-btn")
        self._btn_prev.setMinimumHeight(32)
        self._btn_prev.setCursor(Qt.PointingHandCursor)
        self._btn_prev.clicked.connect(self._prev_page)
        lay.addWidget(self._btn_prev)
        self._page_lbl = QLabel()
        self._page_lbl.setFont(QFont("Tajawal", 9))
        self._page_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._page_lbl, 1)
        self._btn_next = QPushButton(self._("next_page"))
        self._btn_next.setObjectName("topbar-btn")
        self._btn_next.setMinimumHeight(32)
        self._btn_next.setCursor(Qt.PointingHandCursor)
        self._btn_next.clicked.connect(self._next_page)
        lay.addWidget(self._btn_next)
        self._rpp_lbl = self._lbl(self._("records_per_page"))
        lay.addWidget(self._rpp_lbl)
        self._size_combo = QComboBox()
        self._size_combo.setObjectName("form-input")
        for n in ROWS_PER_PAGE_OPTIONS:
            self._size_combo.addItem(str(n), n)
        self._size_combo.setCurrentIndex(1)
        self._size_combo.currentIndexChanged.connect(self._on_size_changed)
        lay.addWidget(self._size_combo)
        return lay

    def _lbl(self, text) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Tajawal", 9))
        return lbl

    def _pre_today(self):
        t = QDate.currentDate()
        self._date_from.setDate(t); self._date_to.setDate(t)

    def _pre_week(self):
        t = QDate.currentDate()
        self._date_from.setDate(t.addDays(-t.dayOfWeek() + 1)); self._date_to.setDate(t)

    def _pre_month(self):
        t = QDate.currentDate()
        self._date_from.setDate(QDate(t.year(), t.month(), 1)); self._date_to.setDate(t)

    def _clear_filters(self):
        self._date_from.setDate(QDate.currentDate().addDays(-30))
        self._date_to.setDate(QDate.currentDate())
        self._user_combo.setCurrentIndex(0)
        self._action_combo.setCurrentIndex(0)
        self._table_combo.setCurrentIndex(0)
        self._search.clear()

    def _on_filter_changed(self, *_):
        self._page = 1
        self._reload()

    def _on_size_changed(self, *_):
        self._page_size = int(self._size_combo.currentData() or 50)
        self._page = 1
        self._reload()

    def _prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._reload()

    def _next_page(self):
        max_p = max(1, (self._total + self._page_size - 1) // self._page_size)
        if self._page < max_p:
            self._page += 1
            self._reload()

    def _load_user_list(self):
        try:
            with get_session_local()() as s:
                users = s.query(User.id, User.full_name, User.username).all()
            self._user_combo.clear()
            self._user_combo.addItem(self._("all"), None)
            for uid, fname, uname in users:
                self._user_combo.addItem(fname or uname or str(uid), uid)
        except Exception:
            pass

    def _reload(self):
        d_from  = self._date_from.date().toString("yyyy-MM-dd")
        d_to    = self._date_to.date().toString("yyyy-MM-dd") + " 23:59:59"
        user_id = self._user_combo.currentData()
        action  = self._action_combo.currentData()
        table   = self._table_combo.currentData()
        search  = self._search.text().strip().lower()
        try:
            with get_session_local()() as s:
                q = (s.query(AuditLog)
                       .options(joinedload(AuditLog.user))
                       .filter(AuditLog.timestamp >= d_from)
                       .filter(AuditLog.timestamp <= d_to))
                if user_id:
                    q = q.filter(AuditLog.user_id == user_id)
                if action:
                    q = q.filter(AuditLog.action.ilike(f"%{action}%"))
                if table:
                    q = q.filter(AuditLog.table_name == table)
                self._total = q.count()
                rows = (q.order_by(desc(AuditLog.timestamp), desc(AuditLog.id))
                          .offset((self._page - 1) * self._page_size)
                          .limit(self._page_size)
                          .all())
            if search:
                rows = [r for r in rows if
                        search in str(getattr(r, "details", "") or "").lower()
                        or search in str(getattr(r, "record_id", "") or "").lower()]
                self._total = len(rows)
        except Exception as e:
            self._render([])
            self._count_lbl.setText(f"⚠️ {e}")
            return
        self._render(rows)
        self._update_pager()
        self._ts_lbl.setText(f"{self._('last_update')} {datetime.now().strftime('%H:%M:%S')}")
        self._count_lbl.setText(self._("total_records").format(count=self._total))

    def _render(self, rows):
        self._tbl.setRowCount(0)
        for ri, row in enumerate(rows):
            self._tbl.insertRow(ri)
            action = (row.action or "").lower()
            icon   = ACTION_ICONS.get(action, "•")
            color  = ACTION_COLORS.get(action, "#3498DB")
            uname = ""
            if row.user:
                uname = getattr(row.user, "full_name", None) or getattr(row.user, "username", None) or "—"
            self._cell(ri, 0, uname)
            self._cell(ri, 1, f"{icon} {row.action or '—'}", color)
            tbl_key = row.table_name or ""
            tbl_trans_key = TABLE_TRANSLATION_KEYS.get(tbl_key)
            tbl_name = self._(tbl_trans_key) if tbl_trans_key else (tbl_key or "—")
            self._cell(ri, 2, tbl_name)
            self._cell(ri, 3, str(row.record_id or "—"))
            details = str(getattr(row, "details", "") or "")[:80]
            self._cell(ri, 4, details)
            ts = format_local_dt(row.timestamp, "%Y-%m-%d  %H:%M:%S")
            self._cell(ri, 5, ts)

    def _cell(self, row, col, text, color=None):
        item = QTableWidgetItem(str(text))
        item.setFont(QFont("Tajawal", 9))
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        if color:
            item.setForeground(QColor(color))
        self._tbl.setItem(row, col, item)

    def _update_pager(self):
        max_p = max(1, (self._total + self._page_size - 1) // self._page_size)
        self._page_lbl.setText(self._("page_of").format(page=self._page, total=max_p))
        self._btn_prev.setEnabled(self._page > 1)
        self._btn_next.setEnabled(self._page < max_p)

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self._("save_audit_log"),
            f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            import csv
            d_from  = self._date_from.date().toString("yyyy-MM-dd")
            d_to    = self._date_to.date().toString("yyyy-MM-dd") + " 23:59:59"
            user_id = self._user_combo.currentData()
            action  = self._action_combo.currentData()
            table   = self._table_combo.currentData()
            with get_session_local()() as s:
                q = (s.query(AuditLog)
                       .options(joinedload(AuditLog.user))
                       .filter(AuditLog.timestamp >= d_from)
                       .filter(AuditLog.timestamp <= d_to))
                if user_id: q = q.filter(AuditLog.user_id == user_id)
                if action:  q = q.filter(AuditLog.action.ilike(f"%{action}%"))
                if table:   q = q.filter(AuditLog.table_name == table)
                all_rows = q.order_by(desc(AuditLog.timestamp)).all()
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow([
                    self._("col_user"), self._("col_action"), self._("col_table"),
                    self._("col_record_no"), self._("col_details"), self._("col_date")
                ])
                for row in all_rows:
                    uname = ""
                    if row.user:
                        uname = getattr(row.user, "full_name", None) or getattr(row.user, "username", None) or "—"
                    w.writerow([
                        uname, row.action or "", row.table_name or "",
                        row.record_id or "", getattr(row, "details", "") or "",
                        row.timestamp.strftime("%Y-%m-%d %H:%M:%S") if row.timestamp else "",
                    ])
            QMessageBox.information(self, self._("done"),
                self._("export_success_msg").format(count=len(all_rows), path=path))
        except Exception as e:
            QMessageBox.critical(self, self._("error"),
                self._("export_failed_msg") + f"\n{e}")

    def retranslate_ui(self):
        self._ = TranslationManager.get_instance().translate
        self._title_lbl.setText(self._("audit_trail_title"))
        self._ref_btn.setText(self._("refresh"))
        self._exp_btn.setText(self._("export_csv"))
        self._tbl.setHorizontalHeaderLabels([
            self._("col_user"), self._("col_action"), self._("col_table"),
            self._("col_record_no"), self._("col_details"), self._("col_datetime")
        ])
        self._lbl_from.setText(self._("date_from"))
        self._lbl_to.setText(self._("date_to"))
        self._btn_today.setText(self._("filter_today"))
        self._btn_week.setText(self._("filter_week"))
        self._btn_month.setText(self._("filter_month"))
        self._lbl_user.setText(self._("filter_user"))
        self._lbl_action.setText(self._("filter_action"))
        self._lbl_table.setText(self._("filter_table"))
        self._user_combo.setItemText(0, self._("all"))
        self._action_combo.setItemText(0, self._("all"))
        current_table_data = self._table_combo.currentData()
        self._table_combo.blockSignals(True)
        self._table_combo.clear()
        self._table_combo.addItem(self._("all"), None)
        for tbl_key, tbl_trans_key in TABLE_TRANSLATION_KEYS.items():
            self._table_combo.addItem(self._(tbl_trans_key), tbl_key)
        idx = self._table_combo.findData(current_table_data)
        if idx >= 0:
            self._table_combo.setCurrentIndex(idx)
        self._table_combo.blockSignals(False)
        self._search.setPlaceholderText(self._("search_details_placeholder"))
        self._clr_btn.setToolTip(self._("clear_filters_tooltip"))
        self._btn_prev.setText(self._("previous_page"))
        self._btn_next.setText(self._("next_page"))
        self._rpp_lbl.setText(self._("records_per_page"))
        self._update_pager()