"""
AuditTrailTab - LOGIPORT v1.0
==============================
Audit trail page with full translation support.

تحسينات:
  [1] عرض التفاصيل كاملة (before/after) عند double-click
  [2] بطاقات إحصائيات سريعة في الأعلى
  [3] تمييز صفوف الحذف بخلفية حمراء فاتحة
  [4] البحث server-side بدل الذاكرة
  [5] فلتر سريع بالضغط على خلية الجدول أو الإجراء
"""

import json
from typing import Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QDateEdit, QComboBox, QLineEdit, QSizePolicy, QFileDialog,
    QMessageBox, QDialog, QTextEdit, QScrollArea, QGridLayout,
    QApplication,
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QFont, QColor, QCursor
from ui.utils.font_utils import app_font, XS, SM, BODY, MD, BASE, LG, XL, XL2, XL3, XL4, HERO, LOGO

from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from database.db_utils import format_local_dt
from database.models import get_session_local, AuditLog, User
from sqlalchemy import desc, func, or_, String
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
    "transactions":          "table_transactions",
    "materials":             "table_materials",
    "clients":               "table_clients",
    "users":                 "table_users",
    "documents":             "table_documents",
    "entries":               "table_entries",
    "companies":             "table_companies",
    "countries":             "countries",
    "currencies":            "currencies",
    "pricing":               "pricing",
    "pricing_types":         "pricing",
    "delivery_methods":      "table_delivery_methods",
    "packaging_types":       "table_packaging_types",
    "material_types":        "table_material_types",
    "roles":                 "roles",
    "permissions":           "permissions",
    "container_tracking":    "container_tracking",
    "shipment_containers":   "table_shipment_containers",
    "offices":               "offices",
    "tasks":                 "tasks",
    "document_types":        "document_types",
    "company_roles":         "table_company_roles",
    "client_contacts":       "table_client_contacts",
    "company_banks":         "table_company_banks",
    "company_partner_links": "table_company_partners",
    "entry_items":           "entry_items",
    "transaction_items":     "table_transaction_items",
    "transport_details":     "table_transport_details",
}

ROWS_PER_PAGE_OPTIONS = [25, 50, 100, 200]

# لون خلفية فاتح لصفوف الحذف [3]
_DELETE_ROW_BG = QColor(254, 226, 226)   # أحمر فاتح جداً


# ─────────────────────────────────────────────────────────────────────────────
# [1] Dialog تفاصيل العملية
# ─────────────────────────────────────────────────────────────────────────────

class _AuditDetailDialog(QDialog):
    """يعرض before/after JSON بشكل منسّق عند double-click على صف."""

    def __init__(self, parent, row: AuditLog, translate):
        super().__init__(parent)
        self._ = translate
        self.setWindowTitle(self._("audit_detail_title"))
        self.setMinimumSize(620, 460)
        self.setSizeGripEnabled(True)
        self._build(row)

    def _build(self, row: AuditLog):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 16, 20, 16)

        # ── معلومات العملية ─────────────────────────────────────────
        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(16)
        info_grid.setVerticalSpacing(6)

        def _info_row(r, label, value, color=None):
            lbl = QLabel(label)
            lbl.setFont(app_font(SM, bold=True))
            val = QLabel(str(value or "—"))
            val.setFont(app_font(SM))
            val.setWordWrap(True)
            if color:
                val.setStyleSheet(f"color: {color};")
            info_grid.addWidget(lbl, r, 0)
            info_grid.addWidget(val, r, 1)

        action = (row.action or "").lower()
        icon   = ACTION_ICONS.get(action, "•")
        color  = ACTION_COLORS.get(action, "#3498DB")
        uname  = ""
        if row.user:
            uname = getattr(row.user, "full_name", None) or getattr(row.user, "username", None) or "—"
        tbl_key = row.table_name or ""
        tbl_trans = TABLE_TRANSLATION_KEYS.get(tbl_key)
        tbl_name  = self._(tbl_trans) if tbl_trans else (tbl_key or "—")
        ts = format_local_dt(row.timestamp, "%Y-%m-%d  %H:%M:%S")

        _info_row(0, self._("col_user"),      uname)
        _info_row(1, self._("col_action"),     f"{icon} {row.action or '—'}", color)
        _info_row(2, self._("col_table"),      tbl_name)
        _info_row(3, self._("col_record_no"),  row.record_id or "—")
        _info_row(4, self._("col_datetime"),   ts)
        lay.addLayout(info_grid)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("form-dialog-sep")
        lay.addWidget(sep)

        # ── before / after ──────────────────────────────────────────
        try:
            raw = json.loads(getattr(row, "details", "") or "{}")
            before_data = raw.get("before") or raw.get("before_data")
            after_data  = raw.get("after")  or raw.get("after_data")
        except Exception:
            before_data = None
            after_data  = None

        # إذا ما في before/after — عرض details خام
        if not before_data and not after_data:
            lbl = QLabel(self._("audit_no_changes"))
            lbl.setFont(app_font(SM))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setObjectName("text-muted")
            lay.addWidget(lbl)
        else:
            h_lay = QHBoxLayout()
            h_lay.setSpacing(12)
            for title, data in (
                (self._("audit_before"), before_data),
                (self._("audit_after"),  after_data),
            ):
                col = QVBoxLayout()
                col.setSpacing(4)
                t_lbl = QLabel(title)
                t_lbl.setFont(app_font(BODY, bold=True))
                t_lbl.setAlignment(Qt.AlignCenter)
                col.addWidget(t_lbl)
                te = QTextEdit()
                te.setReadOnly(True)
                te.setFont(app_font(XS))
                te.setObjectName("form-input")
                if data:
                    try:
                        te.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))
                    except Exception:
                        te.setPlainText(str(data))
                else:
                    te.setPlaceholderText("—")
                col.addWidget(te)
                h_lay.addLayout(col)
            lay.addLayout(h_lay)

        # ── زر إغلاق ────────────────────────────────────────────────
        btn_close = QPushButton(self._("close") if hasattr(self, "_") else "Close")
        btn_close.setObjectName("primary-btn")
        btn_close.setMinimumHeight(34)
        btn_close.clicked.connect(self.accept)
        lay.addWidget(btn_close, alignment=Qt.AlignRight)


# ─────────────────────────────────────────────────────────────────────────────
# AuditTrailTab
# ─────────────────────────────────────────────────────────────────────────────

class AuditTrailTab(QWidget):

    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self._tm = TranslationManager.get_instance()
        self._ = self._tm.translate
        self._current_user = current_user or SettingsManager.get_instance().get("user")
        self.setObjectName("audit-trail-tab")
        self._page      = 1
        self._page_size = 50
        self._total     = 0
        self._all_users: list = []
        self._build_ui()
        self._load_user_list()
        self._reload()
        self._tm.language_changed.connect(self.retranslate_ui)

        # DataBus — يتجدد عند أي عملية write في أي تاب
        try:
            from core.data_bus import DataBus
            DataBus.get_instance().data_changed.connect(
                lambda _entity: self._reload()
            )
        except Exception:
            pass

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(24, 20, 24, 20)
        main.setSpacing(14)
        main.addWidget(self._build_header())
        main.addWidget(self._build_stats_bar())   # [2]
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
        self._tbl.setSortingEnabled(True)
        self._tbl.setFont(app_font(SM))
        # [1] double-click → تفاصيل كاملة
        self._tbl.doubleClicked.connect(self._on_row_double_clicked)
        # [5] single-click → فلتر سريع
        self._tbl.cellClicked.connect(self._on_cell_clicked)
        main.addWidget(self._tbl, 1)
        main.addLayout(self._build_pagination())

    # ── [2] Stats bar ─────────────────────────────────────────────────────────

    def _build_stats_bar(self) -> QWidget:
        """بطاقات إحصائيات سريعة: إجمالي، إنشاء، تعديل، حذف."""
        w = QWidget()
        w.setObjectName("stats-bar")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(10)

        self._stat_widgets: Dict[str, QLabel] = {}
        cards = [
            ("total",  self._("audit_stat_total"),  "#0D1B2A", "#C9A84C"),
            ("create", self._("audit_stat_create"), "#065F46", "#D1FAE5"),
            ("update", self._("audit_stat_update"), "#92400E", "#FEF3C7"),
            ("delete", self._("audit_stat_delete"), "#7F1D1D", "#FEE2E2"),
        ]
        for key, label, fg, bg in cards:
            card = QWidget()
            card.setStyleSheet(
                f"background:{bg}; border-radius:8px; padding:2px 6px;"
            )
            cl = QHBoxLayout(card)
            cl.setContentsMargins(10, 6, 10, 6)
            cl.setSpacing(8)
            name_lbl = QLabel(label)
            name_lbl.setFont(app_font(SM))
            name_lbl.setStyleSheet(f"color:{fg}; background:transparent;")
            val_lbl = QLabel("—")
            val_lbl.setFont(app_font(BODY, bold=True))
            val_lbl.setStyleSheet(f"color:{fg}; background:transparent;")
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cl.addWidget(name_lbl)
            cl.addWidget(val_lbl)
            self._stat_widgets[key] = val_lbl
            lay.addWidget(card)

        lay.addStretch()
        return w

    def _update_stats(self, d_from: str, d_to: str, user_id, table):
        """يحسب الإحصائيات من DB للفترة المحددة."""
        try:
            with get_session_local()() as s:
                base = s.query(AuditLog).filter(
                    AuditLog.timestamp >= d_from,
                    AuditLog.timestamp <= d_to,
                )
                if user_id:
                    base = base.filter(AuditLog.user_id == user_id)
                if table:
                    base = base.filter(AuditLog.table_name == table)

                total   = base.count()
                creates = base.filter(AuditLog.action.in_(["create", "insert"])).count()
                updates = base.filter(AuditLog.action == "update").count()
                deletes = base.filter(AuditLog.action == "delete").count()

            self._stat_widgets["total"].setText(str(total))
            self._stat_widgets["create"].setText(str(creates))
            self._stat_widgets["update"].setText(str(updates))
            self._stat_widgets["delete"].setText(str(deletes))
        except Exception:
            for w in self._stat_widgets.values():
                w.setText("—")

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self._title_lbl = QLabel(self._("audit_trail_title"))
        self._title_lbl.setFont(app_font(XL3, bold=True))
        self._title_lbl.setObjectName("dashboard-title")
        lay.addWidget(self._title_lbl)
        lay.addStretch()
        self._ts_lbl = QLabel()
        self._ts_lbl.setObjectName("text-muted")
        self._ts_lbl.setFont(app_font(SM))
        lay.addWidget(self._ts_lbl)
        self._ref_btn = QPushButton(self._("refresh"))
        self._ref_btn.setObjectName("btn-primary")
        self._ref_btn.setMinimumHeight(34)
        self._ref_btn.setCursor(Qt.PointingHandCursor)
        self._ref_btn.setFont(app_font(BODY))
        self._ref_btn.clicked.connect(self._reload)
        lay.addWidget(self._ref_btn)
        self._exp_btn = QPushButton(self._("export_csv"))
        self._exp_btn.setObjectName("topbar-btn")
        self._exp_btn.setMinimumHeight(34)
        self._exp_btn.setFont(app_font(BODY))
        self._exp_btn.setCursor(Qt.PointingHandCursor)
        self._exp_btn.clicked.connect(self._export_csv)
        lay.addWidget(self._exp_btn)
        return w

    # ── Filter bar ────────────────────────────────────────────────────────────

    def _build_filter_bar(self) -> QWidget:
        from core.base_tab import DateRangeBar

        self._date_bar = DateRangeBar(self, default_months=0)
        self._date_bar._date_from.setDate(QDate.currentDate().addDays(-30))
        self._date_bar.changed.connect(self._on_filter_changed)

        self._date_from = self._date_bar._date_from
        self._date_to   = self._date_bar._date_to

        self._user_combo = QComboBox()
        self._user_combo.setObjectName("form-input")
        self._user_combo.setFixedWidth(130)
        self._user_combo.addItem(self._("all"), None)
        self._user_combo.currentIndexChanged.connect(self._on_filter_changed)
        self._date_bar.add_widget(self._user_combo)

        self._action_combo = QComboBox()
        self._action_combo.setObjectName("form-input")
        self._action_combo.setFixedWidth(120)
        self._action_combo.addItem(self._("all"), None)
        for act, icon in ACTION_ICONS.items():
            self._action_combo.addItem(f"{icon} {act}", act)
        self._action_combo.currentIndexChanged.connect(self._on_filter_changed)
        self._date_bar.add_widget(self._action_combo)

        self._table_combo = QComboBox()
        self._table_combo.setObjectName("form-input")
        self._table_combo.setFixedWidth(130)
        self._table_combo.addItem(self._("all"), None)
        for tbl_key, tbl_trans_key in TABLE_TRANSLATION_KEYS.items():
            self._table_combo.addItem(self._(tbl_trans_key), tbl_key)
        self._table_combo.currentIndexChanged.connect(self._on_filter_changed)
        self._date_bar.add_widget(self._table_combo)

        self._search = QLineEdit()
        self._search.setObjectName("form-input")
        self._search.setPlaceholderText(self._("search_details_placeholder"))
        self._search.setMinimumWidth(120)
        self._search.textChanged.connect(self._on_filter_changed)
        self._date_bar.add_widget(self._search)

        self._clr_btn = QPushButton("🗑")
        self._clr_btn.setObjectName("filter-clear-btn")
        self._clr_btn.setFixedSize(28, 28)
        self._clr_btn.setCursor(Qt.PointingHandCursor)
        self._clr_btn.setToolTip(self._("clear_filters_tooltip"))
        self._clr_btn.clicked.connect(self._clear_filters)
        self._date_bar.add_widget(self._clr_btn)

        self._count_lbl = QLabel()
        self._count_lbl.setObjectName("filter-count-lbl")
        self._date_bar.add_widget(self._count_lbl)

        return self._date_bar

    # ── Pagination ────────────────────────────────────────────────────────────

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
        self._page_lbl.setFont(app_font(SM))
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
        lbl.setFont(app_font(SM))
        return lbl

    # ── Filters logic ─────────────────────────────────────────────────────────

    def _clear_filters(self):
        if hasattr(self, "_date_bar"):
            self._date_bar._set_clear()
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

    # ── Data loading ──────────────────────────────────────────────────────────

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
        search  = self._search.text().strip()

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
                # [4] البحث server-side — يشمل كل الصفحات
                if search:
                    q = q.filter(
                        or_(
                            AuditLog.details.ilike(f"%{search}%"),
                            AuditLog.record_id.cast(String).ilike(f"%{search}%"),
                        )
                    )
                self._total = q.count()
                rows = (q.order_by(desc(AuditLog.timestamp), desc(AuditLog.id))
                          .offset((self._page - 1) * self._page_size)
                          .limit(self._page_size)
                          .all())
                # احتفظ بالـ objects قبل إغلاق الجلسة
                self._cached_rows = list(rows)

        except Exception as e:
            self._render([])
            self._count_lbl.setText(f"⚠️ {e}")
            return

        self._render(self._cached_rows)
        self._update_pager()
        self._update_stats(d_from, d_to, user_id, table)   # [2]
        self._ts_lbl.setText(f"{self._("last_update")} {datetime.now().strftime('%H:%M:%S')}")
        self._count_lbl.setText(self._("total_records").format(count=self._total))

    # ── Render ────────────────────────────────────────────────────────────────

    def _render(self, rows):
        self._tbl.setSortingEnabled(False)
        self._tbl.setUpdatesEnabled(False)
        try:
            self._tbl.setRowCount(len(rows))
            for ri, row in enumerate(rows):
                action = (row.action or "").lower()
                icon   = ACTION_ICONS.get(action, "•")
                color  = ACTION_COLORS.get(action, "#3498DB")
                uname  = ""
                if row.user:
                    uname = getattr(row.user, "full_name", None) or getattr(row.user, "username", None) or "—"
                tbl_key = row.table_name or ""
                tbl_trans_key = TABLE_TRANSLATION_KEYS.get(tbl_key)
                tbl_name = self._(tbl_trans_key) if tbl_trans_key else (tbl_key or "—")
                ts = format_local_dt(row.timestamp, "%Y-%m-%d  %H:%M:%S")
                details_short = str(getattr(row, "details", "") or "")[:80]

                # [3] تمييز صفوف الحذف بخلفية حمراء فاتحة
                row_bg = _DELETE_ROW_BG if action == "delete" else None

                self._cell(ri, 0, uname,         row_bg=row_bg)
                self._cell(ri, 1, f"{icon} {row.action or '—'}", color, row_bg=row_bg)

                # [5] خلية الجدول قابلة للضغط — tooltip يوضح ذلك
                tbl_item = self._make_item(tbl_name, row_bg=row_bg)
                tbl_item.setToolTip(self._("audit_click_filter"))
                tbl_item.setForeground(QColor("#2563EB"))
                self._tbl.setItem(ri, 2, tbl_item)

                self._cell(ri, 3, str(row.record_id or "—"), row_bg=row_bg)
                self._cell(ri, 4, details_short,             row_bg=row_bg)
                self._cell(ri, 5, ts,                        row_bg=row_bg)
        finally:
            self._tbl.setUpdatesEnabled(True)
            self._tbl.setSortingEnabled(True)

    def _make_item(self, text, color=None, row_bg=None) -> QTableWidgetItem:
        item = QTableWidgetItem(str(text))
        item.setFont(app_font(SM))
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        if color:
            item.setForeground(QColor(color))
        if row_bg:
            item.setBackground(row_bg)
        return item

    def _cell(self, row, col, text, color=None, row_bg=None):
        self._tbl.setItem(row, col, self._make_item(text, color, row_bg))

    def _update_pager(self):
        max_p = max(1, (self._total + self._page_size - 1) // self._page_size)
        self._page_lbl.setText(self._("page_of").format(page=self._page, total=max_p))
        self._btn_prev.setEnabled(self._page > 1)
        self._btn_next.setEnabled(self._page < max_p)

    # ── [1] Double-click → تفاصيل كاملة ──────────────────────────────────────

    def _on_row_double_clicked(self, index):
        ri = index.row()
        cached = getattr(self, "_cached_rows", [])
        if 0 <= ri < len(cached):
            dlg = _AuditDetailDialog(self, cached[ri], self._)
            dlg.exec()

    # ── [5] Click على خلية → فلتر سريع ──────────────────────────────────────

    def _on_cell_clicked(self, row: int, col: int):
        """
        col 1 = إجراء → فلتر action combo
        col 2 = جدول  → فلتر table combo
        """
        cached = getattr(self, "_cached_rows", [])
        if not (0 <= row < len(cached)):
            return
        log_row = cached[row]

        if col == 1:   # إجراء
            action = (log_row.action or "").lower()
            idx = self._action_combo.findData(action)
            if idx >= 0:
                self._action_combo.setCurrentIndex(idx)

        elif col == 2:   # جدول
            tbl = log_row.table_name or ""
            idx = self._table_combo.findData(tbl)
            if idx >= 0:
                self._table_combo.setCurrentIndex(idx)

    # ── Export CSV ────────────────────────────────────────────────────────────

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
            search  = self._search.text().strip()
            with get_session_local()() as s:
                q = (s.query(AuditLog)
                       .options(joinedload(AuditLog.user))
                       .filter(AuditLog.timestamp >= d_from)
                       .filter(AuditLog.timestamp <= d_to))
                if user_id: q = q.filter(AuditLog.user_id == user_id)
                if action:  q = q.filter(AuditLog.action.ilike(f"%{action}%"))
                if table:   q = q.filter(AuditLog.table_name == table)
                if search:
                    q = q.filter(
                        or_(
                            AuditLog.details.ilike(f"%{search}%"),
                            AuditLog.record_id.cast(String).ilike(f"%{search}%"),
                        )
                    )
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

    # ── Retranslate ───────────────────────────────────────────────────────────

    def retranslate_ui(self):
        self._ = TranslationManager.get_instance().translate
        self._title_lbl.setText(self._("audit_trail_title"))
        self._ref_btn.setText(self._("refresh"))
        self._exp_btn.setText(self._("export_csv"))
        self._tbl.setHorizontalHeaderLabels([
            self._("col_user"), self._("col_action"), self._("col_table"),
            self._("col_record_no"), self._("col_details"), self._("col_datetime")
        ])
        if hasattr(self, "_date_bar"):
            self._date_bar.retranslate()
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