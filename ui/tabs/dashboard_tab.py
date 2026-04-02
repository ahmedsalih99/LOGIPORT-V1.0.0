"""
DashboardTab - LOGIPORT v3.4
==============================
Clean, theme-aware dashboard.
- 5 KPI cards (compact, accent-left-border style)
- Type breakdown row with progress bars
- Quick actions panel
- Activity feed + recent transactions
"""

import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QGridLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QProgressBar,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal as _Signal
from PySide6.QtGui import QFont, QColor, QCursor

logger = logging.getLogger(__name__)

from core.translator import TranslationManager
from database.models import get_session_local
from database.db_utils import format_local_dt
from database.models import Transaction, Material, Client, AuditLog, Document
from database.models.entry import Entry
from sqlalchemy import func, desc
from datetime import datetime


# ─── helpers to get theme colors safely ──────────────────────────────────────

def _theme_colors():
    """يُعيد dict ألوان الثيم الحالي أو fallbacks آمنة."""
    try:
        from core.theme_manager import ThemeManager
        return ThemeManager.get_instance().current_theme.colors
    except Exception:
        return {}


def _c(key, fallback=""):
    return _theme_colors().get(key, fallback)


# ─────────────────────── KPI Card ────────────────────────────────────────────

# ألوان accent ثابتة لكل نوع بطاقة — هادئة ومتناسقة
_CARD_ACCENTS = {
    "transactions": "#2563EB",   # أزرق — اللون الأساسي للتطبيق
    "value":        "#10B981",   # أخضر
    "clients":      "#8B5CF6",   # بنفسجي
    "materials":    "#F59E0B",   # برتقالي دافئ (مو كاشح)
    "documents":    "#64748B",   # رمادي أردوازي
    "import":       "#2563EB",   # أزرق
    "export":       "#10B981",   # أخضر
    "transit":      "#F59E0B",   # برتقالي
    "tasks":        "#8B5CF6",   # بنفسجي
}

_CARD_ICONS = {
    "transactions": "📦",
    "value":        "💰",
    "clients":      "👥",
    "materials":    "📋",
    "documents":    "📄",
    "import":       "📥",
    "export":       "📤",
    "transit":      "🚚",
    "tasks":        "✅",
}


class KpiCard(QFrame):
    def __init__(self, title, value, subtitle, card_key="transactions", icon="📊", parent=None):
        super().__init__(parent)
        self._card_key = card_key
        self.setObjectName("kpi-card")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._build(title, value, subtitle, icon)

    def _build(self, title, value, subtitle, icon):
        accent = _CARD_ACCENTS.get(self._card_key, "#2563EB")
        bg     = _c("bg_card", "#FFFFFF")
        tp     = _c("text_primary", "#1E293B")
        ts     = _c("text_secondary", "#64748B")
        bdr    = _c("border", "#E2E8F0")

        self.setStyleSheet(f"""
            QFrame#kpi-card {{
                background: {bg};
                border-radius: 10px;
                border: 1px solid {bdr};
                border-left: 4px solid {accent};
                min-height: 78px; max-height: 90px;
            }}
            QFrame#kpi-card:hover {{
                border: 1px solid {accent}55;
                border-left: 4px solid {accent};
            }}
            QLabel {{ background: transparent; border: none; }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)

        ico = QLabel(icon)
        ico.setFixedSize(36, 36)
        ico.setAlignment(Qt.AlignCenter)
        ico.setStyleSheet(
            f"background:{accent}15; border-radius:18px; font-size:16px; border:none;"
        )
        lay.addWidget(ico)

        col = QVBoxLayout()
        col.setSpacing(1)

        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(QFont("Tajawal", 8))
        self._title_lbl.setStyleSheet(f"color:{ts};")
        col.addWidget(self._title_lbl)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setFont(QFont("Tajawal", 17, QFont.Bold))
        self.value_lbl.setStyleSheet(f"color:{tp};")
        col.addWidget(self.value_lbl)

        self._sub_lbl = QLabel(subtitle)
        self._sub_lbl.setFont(QFont("Tajawal", 8))
        self._sub_lbl.setStyleSheet(f"color:{ts};")
        col.addWidget(self._sub_lbl)

        lay.addLayout(col, 1)

    def update_value(self, v):    self.value_lbl.setText(str(v))
    def update_title(self, t):    self._title_lbl.setText(t)
    def update_subtitle(self, s): self._sub_lbl.setText(s)


# ─────────────────────── Mini Progress Card ──────────────────────────────────

class MiniProgressCard(QFrame):
    def __init__(self, label, count, value_str, pct, accent, icon, parent=None):
        super().__init__(parent)
        self._accent = accent
        self.setObjectName("mini-progress-card")
        self._bar = None
        self._count_lbl = None
        self._val_lbl   = None
        self._lbl_w     = None
        self._build(label, count, value_str, pct, icon)

    def _build(self, label, count, value_str, pct, icon):
        accent = self._accent
        bg     = _c("bg_card", "#FFFFFF")
        bdr    = _c("border", "#E2E8F0")
        tp     = _c("text_primary", "#1E293B")
        ts     = _c("text_secondary", "#64748B")

        self.setStyleSheet(f"""
            QFrame#mini-progress-card {{
                background: {bg};
                border-radius: 8px;
                border: 1px solid {bdr};
                min-height: 68px; max-height: 80px;
            }}
            QLabel {{ background: transparent; border: none; color: {tp}; }}
            QProgressBar {{
                background: {accent}18; border-radius: 3px;
                border: none; max-height: 5px;
            }}
            QProgressBar::chunk {{ background: {accent}; border-radius: 3px; }}
        """)

        # clear old layout if rebuild
        if self.layout():
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            old = self.layout()
            QWidget().setLayout(old)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(6)

        ico = QLabel(icon)
        ico.setFixedSize(20, 20)
        ico.setAlignment(Qt.AlignCenter)
        ico.setStyleSheet(
            f"background:{accent}15; border-radius:10px; font-size:11px; border:none;"
        )
        top.addWidget(ico)

        self._lbl_w = QLabel(label)
        self._lbl_w.setFont(QFont("Tajawal", 9))
        top.addWidget(self._lbl_w, 1)

        self._count_lbl = QLabel(str(count))
        self._count_lbl.setFont(QFont("Tajawal", 14, QFont.Bold))
        self._count_lbl.setStyleSheet(f"color:{accent};")
        top.addWidget(self._count_lbl)
        lay.addLayout(top)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(max(0, min(100, int(pct))))
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(5)
        lay.addWidget(self._bar)

        self._val_lbl = QLabel(value_str)
        self._val_lbl.setFont(QFont("Tajawal", 8))
        self._val_lbl.setStyleSheet(f"color:{ts};")
        lay.addWidget(self._val_lbl)

    def update_data(self, count, value_str, pct):
        if self._count_lbl: self._count_lbl.setText(str(count))
        if self._val_lbl:   self._val_lbl.setText(value_str)
        if self._bar:       self._bar.setValue(max(0, min(100, int(pct))))

    def update_label(self, label):
        if self._lbl_w: self._lbl_w.setText(label)


# ─────────────────────── Quick Action Button ─────────────────────────────────

class QuickActionBtn(QPushButton):
    def __init__(self, icon, label, callback=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 90)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._apply_style()
        self._set_text(icon, label)
        if callback:
            self.clicked.connect(callback)

    def _apply_style(self):
        bg      = _c("bg_hover", "#F0F7FF")
        bdr     = _c("border", "#E2E8F0")
        tp      = _c("text_primary", "#1E293B")
        bg_h    = _c("bg_active", "#E3F2FF")
        primary = _c("primary", "#2563EB")
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: 1px solid {bdr};
                border-radius: 12px;
                color: {tp};
                font-family: Tajawal; font-size: 11px; font-weight: 600;
                padding: 6px 4px;
            }}
            QPushButton:hover {{
                background: {bg_h};
                border-color: {primary}55;
                color: {primary};
            }}
            QPushButton:pressed {{
                background: {primary}18;
            }}
        """)

    def _set_text(self, icon, label):
        self.setText(f"{icon}\n{label}")

    def retranslate(self, icon, label):
        self._set_text(icon, label)


# ─────────────────────── Activity Item ───────────────────────────────────────

class ActivityItem(QFrame):
    _ACT_COLORS = {
        "create": "#10B981",
        "insert": "#10B981",
        "update": "#F59E0B",
        "delete": "#EF4444",
    }
    _ACT_ICONS = {
        "create": "➕",
        "insert": "➕",
        "update": "✏️",
        "delete": "🗑️",
    }

    def __init__(self, action, message, timestamp, parent=None):
        super().__init__(parent)
        self.setObjectName("activity-item")
        color = self._ACT_COLORS.get(action.lower(), _c("primary", "#2563EB"))
        icon  = self._ACT_ICONS.get(action.lower(), "📝")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 5, 8, 5)
        lay.setSpacing(8)

        ico = QLabel(icon)
        ico.setFixedSize(24, 24)
        ico.setAlignment(Qt.AlignCenter)
        ico.setStyleSheet(
            f"background:{color}18; border-radius:12px; font-size:11px;"
        )
        lay.addWidget(ico)

        col = QVBoxLayout()
        col.setSpacing(0)

        msg = QLabel(message)
        msg.setFont(QFont("Tajawal", 9))
        msg.setObjectName("activity-msg")
        col.addWidget(msg)

        ts_lbl = QLabel(f"🕒 {timestamp}")
        ts_lbl.setFont(QFont("Tajawal", 8))
        ts_lbl.setObjectName("activity-ts")
        col.addWidget(ts_lbl)

        lay.addLayout(col, 1)


# ─────────────────────── Worker Thread ───────────────────────────────────────

class _DashboardWorker(QThread):
    stats_ready        = _Signal(dict)
    activities_ready   = _Signal(list)
    transactions_ready = _Signal(list)

    def run(self):
        try:
            s = {k: 0 for k in [
                "total_transactions", "active_transactions", "total_value",
                "total_clients", "total_materials",
                "import_count", "import_value", "export_count", "export_value",
                "transit_count", "transit_value", "total_documents",
                "tasks_overdue", "tasks_pending",
            ]}
            try:
                with get_session_local()() as session:
                    s["total_transactions"]  = session.query(Transaction).count()
                    s["active_transactions"] = session.query(Transaction).filter(
                        Transaction.status == "active").count()
                    v = session.query(func.sum(Transaction.totals_value)).scalar() or 0
                    s["total_value"] = f"${float(v):,.0f}"
                    for t in ("import", "export", "transit"):
                        s[f"{t}_count"] = session.query(Transaction).filter(
                            Transaction.transaction_type == t).count()
                        s[f"{t}_value"] = float(
                            session.query(func.sum(Transaction.totals_value))
                            .filter(Transaction.transaction_type == t).scalar() or 0)
                    s["total_clients"]   = session.query(Client).count()
                    s["total_materials"] = session.query(Material).count()
                    s["total_documents"] = session.query(Document).count()
            except Exception:
                pass
            try:
                from database.crud.tasks_crud import TasksCRUD
                cr = TasksCRUD()
                s["tasks_overdue"] = cr.count_overdue()
                s["tasks_pending"] = cr.count_pending()
            except Exception:
                pass
            self.stats_ready.emit(s)

            acts = []
            try:
                with get_session_local()() as session:
                    rows = session.query(AuditLog).order_by(
                        AuditLog.timestamp.desc()).limit(10).all()
                    acts = [{"action": r.action, "table_name": r.table_name,
                             "timestamp": r.timestamp} for r in rows]
            except Exception:
                pass
            self.activities_ready.emit(acts)

            txs = []
            try:
                with get_session_local()() as session:
                    from sqlalchemy.orm import joinedload as jl
                    rows = (session.query(Transaction)
                            .options(jl(Transaction.client))
                            .order_by(Transaction.transaction_date.desc(),
                                      Transaction.id.desc())
                            .limit(10).all())
                    txs = [{
                        "transaction_no":   r.transaction_no,
                        "transaction_date": str(r.transaction_date or ""),
                        "transaction_type": r.transaction_type,
                        "totals_value":     r.totals_value,
                        "totals_gross_kg":  r.totals_gross_kg,
                        "status":           r.status,
                        "client":           r.client,
                    } for r in rows]
            except Exception:
                pass
            self.transactions_ready.emit(txs)
        except Exception:
            pass


# ─────────────────────── DashboardTab ────────────────────────────────────────

class DashboardTab(QWidget):

    _TOP_CARDS = [
        ("total_transactions", "stat_transactions",  "active_transactions_fmt", "transactions", "📦"),
        ("total_entries",      "entries",             "stat_entries_sub",        "import",       "📋"),
        ("total_clients",      "clients",             "registered_client",       "clients",      "👥"),
        ("total_materials",    "materials",           "available_material",      "materials",    "📋"),
        ("total_documents",    "documents",           "stat_documents",          "documents",    "📄"),
    ]

    # accent لكل نوع معاملة — يُستخدم في progress cards فقط
    _TYPE_CARDS = [
        ("import_count",  "import_value",  "import_type",  "#2563EB", "📥"),
        ("export_count",  "export_value",  "export_type",  "#10B981", "📤"),
        ("transit_count", "transit_value", "transit_type", "#F59E0B", "🚚"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tm = TranslationManager.get_instance()
        self._ = self._tm.translate
        self.setObjectName("dashboard-tab")
        self._stat_cards   = {}
        self._type_cards   = {}
        self._cached_stats = {}
        self._qa_buttons   = []
        self._tm.language_changed.connect(self.retranslate_ui)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        container = QWidget()
        container.setObjectName("dashboard-container")
        main = QVBoxLayout(container)
        main.setContentsMargins(22, 16, 22, 22)
        main.setSpacing(14)

        main.addWidget(self._build_header())
        main.addLayout(self._build_kpi_row())
        main.addLayout(self._build_middle_row())

        bottom = QHBoxLayout()
        bottom.setSpacing(14)
        bottom.addWidget(self._build_activities_panel(), stretch=2)
        bottom.addWidget(self._build_transactions_panel(), stretch=3)
        main.addLayout(bottom)
        main.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_all_data)
        self._refresh_timer.start(30_000)
        QTimer.singleShot(100, self.refresh_all_data)

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        self._title_lbl = QLabel(self._("dashboard_main_title"))
        self._title_lbl.setFont(QFont("Tajawal", 16, QFont.Bold))
        self._title_lbl.setObjectName("dashboard-title")
        lay.addWidget(self._title_lbl)
        lay.addStretch()

        self._update_lbl = QLabel()
        self._update_lbl.setObjectName("text-muted")
        self._update_lbl.setFont(QFont("Tajawal", 9))
        self._set_update_time()
        lay.addWidget(self._update_lbl)
        lay.addSpacing(10)

        self._refresh_btn = QPushButton(self._("refresh"))
        self._refresh_btn.setObjectName("primary-btn")
        self._refresh_btn.setMinimumHeight(30)
        self._refresh_btn.setMinimumWidth(82)
        self._refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._refresh_btn.setFont(QFont("Tajawal", 9))
        self._refresh_btn.clicked.connect(self.refresh_all_data)
        lay.addWidget(self._refresh_btn)
        return w

    # ── KPI Row ───────────────────────────────────────────────────────────────

    def _build_kpi_row(self):
        grid = QGridLayout()
        grid.setSpacing(10)
        # نبدأ بـ zeros — الـ worker يملأها بعد ثانية
        for col, (stat_key, title_key, sub_key, card_key, icon) in enumerate(self._TOP_CARDS):
            card = KpiCard(
                self._(title_key), 0,
                self._resolve_sub(sub_key, {}),
                card_key, icon
            )
            self._stat_cards[stat_key] = card
            grid.addWidget(card, 0, col)
        return grid

    # ── Middle row ────────────────────────────────────────────────────────────

    def _build_middle_row(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        # ── Type breakdown ──────────────────────────────────────────────
        tf = QFrame()
        tf.setObjectName("card")
        tf_lay = QVBoxLayout(tf)
        tf_lay.setContentsMargins(14, 12, 14, 12)
        tf_lay.setSpacing(8)

        self._type_section_title = QLabel(self._("transactions_overview"))
        self._type_section_title.setFont(QFont("Tajawal", 11, QFont.Bold))
        self._type_section_title.setObjectName("panel-title")
        tf_lay.addWidget(self._type_section_title)

        type_grid = QGridLayout()
        type_grid.setSpacing(8)
        for i, (count_key, val_key, label_key, accent, icon) in enumerate(self._TYPE_CARDS):
            # نبدأ بـ 0، الـ worker يملأ
            card = MiniProgressCard(self._(label_key), 0, "$0", 0, accent, icon)
            self._type_cards[count_key] = card
            type_grid.addWidget(card, 0, i)
        tf_lay.addLayout(type_grid)

        # Tasks strip
        self._tasks_strip_frame = self._build_tasks_strip(0)
        tf_lay.addWidget(self._tasks_strip_frame)
        row.addWidget(tf, stretch=3)

        # ── Quick Actions ───────────────────────────────────────────────
        qa = QFrame()
        qa.setObjectName("card")
        qa_lay = QVBoxLayout(qa)
        qa_lay.setContentsMargins(14, 12, 14, 12)
        qa_lay.setSpacing(10)

        self._qa_title = QLabel(self._("quick_actions_title"))
        self._qa_title.setFont(QFont("Tajawal", 11, QFont.Bold))
        self._qa_title.setObjectName("panel-title")
        qa_lay.addWidget(self._qa_title)

        _actions = [
            ("➕", "add_transaction",  self._navigate_to_add_transaction),
            ("📄", "documents",        self._navigate_to_documents),
            ("👥", "clients",          self._navigate_to_clients),
            ("📦", "transactions",     self._navigate_to_transactions),
            ("🚢", "refrigerators",    self._navigate_to_containers),
            ("✅", "tasks",            self._navigate_to_tasks),
        ]
        btns_grid = QGridLayout()
        btns_grid.setSpacing(8)
        self._qa_buttons = []
        for idx, (icon, lkey, cb) in enumerate(_actions):
            btn = QuickActionBtn(icon, self._(lkey), cb)
            r, c = divmod(idx, 3)
            btns_grid.addWidget(btn, r, c)
            self._qa_buttons.append((btn, icon, lkey))
        qa_lay.addLayout(btns_grid)
        qa_lay.addStretch()
        row.addWidget(qa, stretch=2)
        return row

    def _build_tasks_strip(self, overdue):
        f = QFrame()
        f.setObjectName("tasks-strip")
        is_ok   = overdue == 0
        color   = _c("success", "#10B981") if is_ok else _c("danger", "#EF4444")
        bg      = _c("bg_card", "#FFFFFF")
        bdr     = _c("border", "#E2E8F0")

        f.setStyleSheet(f"""
            QFrame#tasks-strip {{
                background: {bg};
                border-radius: 7px;
                border: 1px solid {color}35;
                border-left: 3px solid {color};
            }}
            QLabel {{ background: transparent; border: none; }}
        """)
        lay = QHBoxLayout(f)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)

        ico = QLabel("✅" if is_ok else "⚠️")
        ico.setFixedSize(20, 20)
        ico.setAlignment(Qt.AlignCenter)
        ico.setStyleSheet(f"background:{color}15; border-radius:10px; font-size:11px; border:none;")
        lay.addWidget(ico)

        txt = (self._("no_overdue_tasks") if is_ok
               else self._("tasks_overdue_count").format(n=overdue))
        self._tasks_lbl = QLabel(txt)
        self._tasks_lbl.setFont(QFont("Tajawal", 9))
        self._tasks_lbl.setStyleSheet(f"color:{color};")
        lay.addWidget(self._tasks_lbl, 1)
        return f

    # ── Activities ────────────────────────────────────────────────────────────

    def _build_activities_panel(self):
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        self._act_title = QLabel(self._("recent_activities_title"))
        self._act_title.setFont(QFont("Tajawal", 11, QFont.Bold))
        self._act_title.setObjectName("panel-title")
        lay.addWidget(self._act_title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        self._act_container = QWidget()
        self._act_layout = QVBoxLayout(self._act_container)
        self._act_layout.setSpacing(3)
        self._act_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self._act_container)
        lay.addWidget(scroll)
        frame.setMinimumHeight(340)
        return frame

    # ── Transactions ──────────────────────────────────────────────────────────

    def _build_transactions_panel(self):
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        self._trx_title = QLabel(self._("latest_transactions_title"))
        self._trx_title.setFont(QFont("Tajawal", 11, QFont.Bold))
        self._trx_title.setObjectName("panel-title")
        lay.addWidget(self._trx_title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        self._trans_table = QTableWidget()
        self._trans_table.setObjectName("data-table")
        self._trans_table.setColumnCount(7)
        self._trans_table.verticalHeader().setVisible(False)
        self._trans_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._trans_table.setAlternatingRowColors(True)
        self._trans_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._trans_table.setShowGrid(False)
        self._trans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._trans_table.verticalHeader().setDefaultSectionSize(32)
        self._trans_table.setFont(QFont("Tajawal", 9))
        self._trans_table.setMinimumHeight(280)
        self._update_trans_headers()

        lay.addWidget(self._trans_table)
        frame.setMinimumHeight(340)
        return frame

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _get_stats(self):
        s = {k: 0 for k in [
            "total_transactions", "active_transactions", "total_value",
            "total_clients", "total_materials", "total_entries",
            "import_count", "import_value", "export_count", "export_value",
            "transit_count", "transit_value", "total_documents",
            "tasks_overdue", "tasks_pending",
        ]}
        try:
            with get_session_local()() as session:
                s["total_transactions"]  = session.query(Transaction).count()
                s["active_transactions"] = session.query(Transaction).filter(
                    Transaction.status == "active").count()
                v = session.query(func.sum(Transaction.totals_value)).scalar() or 0
                s["total_value"] = f"${float(v):,.0f}"
                for t in ("import", "export", "transit"):
                    s[f"{t}_count"] = session.query(Transaction).filter(
                        Transaction.transaction_type == t).count()
                    s[f"{t}_value"] = float(
                        session.query(func.sum(Transaction.totals_value))
                        .filter(Transaction.transaction_type == t).scalar() or 0)
                s["total_clients"]   = session.query(Client).count()
                s["total_materials"] = session.query(Material).count()
                s["total_documents"] = session.query(Document).count()
                s["total_entries"]   = session.query(Entry).count()
        except Exception as e:
            logger.error(f"Dashboard stats error: {e}")
        try:
            from database.crud.tasks_crud import TasksCRUD
            cr = TasksCRUD()
            s["tasks_overdue"] = cr.count_overdue()
            s["tasks_pending"] = cr.count_pending()
        except Exception:
            pass
        return s

    def _resolve_sub(self, sub_key, stats):
        if sub_key == "active_transactions_fmt":
            return self._("active_transactions_fmt").format(count=stats.get("active_transactions", 0))
        if sub_key == "stat_entries_sub":
            return self._("stat_entries_sub")
        return self._(sub_key)

    # ── Activity feed ─────────────────────────────────────────────────────────

    def _load_activities(self, preloaded=None):
        while self._act_layout.count():
            item = self._act_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        TABLE_KEYS = {
            "transactions": "table_transactions", "materials": "table_materials",
            "clients":      "table_clients",      "users":     "table_users",
            "documents":    "table_documents",    "entries":   "table_entries",
            "companies":    "table_companies",
        }
        ACTION_KEYS = {
            "create": "action_create", "insert": "action_insert",
            "update": "action_update", "delete": "action_delete",
        }
        try:
            if preloaded is not None:
                data = preloaded
                for row in data:
                    action   = (row.get("action") or "update").lower()
                    tbl_name = row.get("table_name") or ""
                    tbl = self._(TABLE_KEYS[tbl_name]) if tbl_name in TABLE_KEYS else (tbl_name or "—")
                    act = self._(ACTION_KEYS[action]) if action in ACTION_KEYS else action
                    msg = self._("activity_message").format(user="—", action=act, table=tbl)
                    ts  = format_local_dt(row.get("timestamp"))
                    self._act_layout.addWidget(ActivityItem(action, msg, ts))
            else:
                from sqlalchemy.orm import joinedload as jl
                with get_session_local()() as session:
                    rows = (session.query(AuditLog)
                            .options(jl(AuditLog.user))
                            .order_by(desc(AuditLog.id))
                            .limit(12).all())
                for row in rows:
                    action = (row.action or "update").lower()
                    tbl    = self._(TABLE_KEYS[row.table_name]) if row.table_name in TABLE_KEYS else (row.table_name or "—")
                    act    = self._(ACTION_KEYS[action]) if action in ACTION_KEYS else action
                    uname  = ""
                    if row.user:
                        uname = (getattr(row.user, "full_name", None)
                                 or getattr(row.user, "username", None)
                                 or self._("system_user"))
                    msg = self._("activity_message").format(user=uname, action=act, table=tbl)
                    ts  = format_local_dt(row.timestamp)
                    self._act_layout.addWidget(ActivityItem(action, msg, ts))
        except Exception as e:
            err = QLabel(f"⚠️ {e}")
            err.setObjectName("activity-ts")
            self._act_layout.addWidget(err)
        self._act_layout.addStretch()

    # ── Transactions table ────────────────────────────────────────────────────

    def _update_trans_headers(self):
        self._trans_table.setHorizontalHeaderLabels([
            self._("col_number"), self._("transaction_date"), self._("col_type"),
            self._("col_client"), self._("col_weight_kg"), self._("col_value_usd"),
            self._("col_status"),
        ])

    def _load_transactions(self, preloaded=None):
        TYPE_MAP = {
            "import":  self._("import_type"),
            "export":  self._("export_type"),
            "transit": self._("transit_type"),
        }
        STATUS_COLORS = {
            "active":   _c("success", "#10B981"),
            "draft":    _c("warning", "#F59E0B"),
            "closed":   _c("text_muted", "#6B7280"),
            "archived": _c("text_secondary", "#94A3B8"),
        }

        try:
            from core.theme_manager import ThemeManager
            _font = QFont(ThemeManager.get_instance().get_current_font_family(), 9)
        except Exception:
            _font = QFont("Tajawal", 9)

        def _cell(txt, right=False):
            item = QTableWidgetItem(str(txt))
            item.setTextAlignment(
                (Qt.AlignRight if right else Qt.AlignCenter) | Qt.AlignVCenter
            )
            item.setFont(_font)
            return item

        try:
            if preloaded is not None:
                rows = preloaded
            else:
                from sqlalchemy.orm import joinedload as jl
                with get_session_local()() as session:
                    rows_db = (session.query(Transaction)
                               .options(jl(Transaction.client))
                               .order_by(desc(Transaction.id))
                               .limit(10).all())
                    rows = [{
                        "transaction_no":   r.transaction_no,
                        "transaction_date": str(r.transaction_date or ""),
                        "transaction_type": r.transaction_type,
                        "totals_value":     r.totals_value,
                        "totals_gross_kg":  r.totals_gross_kg,
                        "status":           r.status,
                        "client":           r.client,
                    } for r in rows_db]

            self._trans_table.setSortingEnabled(False)
            self._trans_table.setUpdatesEnabled(False)
            try:
                self._trans_table.setRowCount(len(rows))
                for r, t in enumerate(rows):
                    date_str    = str(t.get("transaction_date", "") or "—")[:10]
                    status      = t.get("status") or ""
                    status_txt  = self._(f"status_{status}") if status else "—"
                    vl          = f"${t.get('totals_value', 0) or 0:,.0f}"
                    trx_type    = t.get("transaction_type") or ""
                    type_txt    = TYPE_MAP.get(trx_type, trx_type or "—")

                    client_name = "—"
                    co = t.get("client")
                    if co:
                        lang = self._tm.get_current_language() if hasattr(self, "_tm") else "ar"
                        client_name = (
                            getattr(co, f"name_{lang}", None)
                            or getattr(co, "name_ar", None)
                            or getattr(co, "name_en", None)
                            or "—"
                        )

                    weight_txt = "—"
                    gross = t.get("totals_gross_kg")
                    if gross is not None:
                        try:
                            weight_txt = f"{float(gross):,.0f}"
                        except Exception:
                            pass

                    self._trans_table.setItem(r, 0, _cell(t.get("transaction_no") or "—"))
                    self._trans_table.setItem(r, 1, _cell(date_str))
                    self._trans_table.setItem(r, 2, _cell(type_txt))
                    self._trans_table.setItem(r, 3, _cell(client_name))
                    self._trans_table.setItem(r, 4, _cell(weight_txt, right=True))
                    self._trans_table.setItem(r, 5, _cell(vl, right=True))
                    si = _cell(status_txt)
                    si.setForeground(QColor(STATUS_COLORS.get(status, "#6B7280")))
                    self._trans_table.setItem(r, 6, si)
            finally:
                self._trans_table.setUpdatesEnabled(True)
                self._trans_table.setSortingEnabled(True)
        except Exception as e:
            logger.error(f"Dashboard transactions error: {e}")

    # ── Navigation ────────────────────────────────────────────────────────────

    def _navigate_to(self, tab_key: str):
        """ينقل للتاب المطلوب عبر switch_section في MainWindow."""
        try:
            main = self.window()
            if hasattr(main, "switch_section"):
                main.switch_section(tab_key)
        except Exception as e:
            logger.error(f"Dashboard navigate error: {e}")

    def _navigate_to_add_transaction(self):
        """ينتقل لتاب المعاملات ثم يفتح نافذة الإضافة."""
        try:
            self._navigate_to("transactions")
            main = self.window()
            trx_tab = getattr(main, "tabs", {}).get("transactions")
            if trx_tab and hasattr(trx_tab, "add_new_item"):
                # نستخدم QTimer لإعطاء وقت للتاب ليظهر أولاً
                from PySide6.QtCore import QTimer
                QTimer.singleShot(80, trx_tab.add_new_item)
        except Exception as e:
            logger.error(f"Dashboard add_transaction error: {e}")

    def _navigate_to_documents(self):       self._navigate_to("documents")
    def _navigate_to_clients(self):         self._navigate_to("clients")
    def _navigate_to_transactions(self):    self._navigate_to("transactions")
    def _navigate_to_containers(self):      self._navigate_to("container_tracking")
    def _navigate_to_tasks(self):           self._navigate_to("tasks")

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh_all_data(self):
        if getattr(self, "_worker", None) and self._worker.isRunning():
            return
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText(self._("refreshing"))
        self._set_update_time()

        self._worker = _DashboardWorker(self)
        self._worker.stats_ready.connect(self._on_stats_ready)
        self._worker.activities_ready.connect(self._on_activities_ready)
        self._worker.transactions_ready.connect(self._on_transactions_ready)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _on_stats_ready(self, stats):
        self._cached_stats.update(stats)

        # KPI cards
        for stat_key, _, sub_key, _, _ in self._TOP_CARDS:
            if card := self._stat_cards.get(stat_key):
                card.update_value(stats.get(stat_key, 0))
                card.update_subtitle(self._resolve_sub(sub_key, stats))

        # Type mini-cards
        total = max(stats.get("total_transactions", 1), 1)
        for count_key, val_key, _, _, _ in self._TYPE_CARDS:
            if card := self._type_cards.get(count_key):
                count = stats.get(count_key, 0)
                val   = stats.get(val_key, 0)
                card.update_data(count, f"${val:,.0f}", count / total * 100)

        # Tasks strip
        overdue = stats.get("tasks_overdue", 0)
        is_ok   = overdue == 0
        color   = _c("success", "#10B981") if is_ok else _c("danger", "#EF4444")
        txt = (self._("no_overdue_tasks") if is_ok
               else self._("tasks_overdue_count").format(n=overdue))
        self._tasks_lbl.setText(txt)
        self._tasks_lbl.setStyleSheet(f"color:{color};")
        # تحديث border لون الـ strip
        bg  = _c("bg_card", "#FFFFFF")
        self._tasks_strip_frame.setStyleSheet(f"""
            QFrame#tasks-strip {{
                background: {bg};
                border-radius: 7px;
                border: 1px solid {color}35;
                border-left: 3px solid {color};
            }}
            QLabel {{ background: transparent; border: none; }}
        """)

    def _on_activities_ready(self, acts):
        try:
            self._load_activities(preloaded=acts)
        except Exception:
            pass

    def _on_transactions_ready(self, txs):
        try:
            self._load_transactions(preloaded=txs)
        except Exception:
            pass

    def _on_worker_done(self):
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText(self._("refresh"))

    def _set_update_time(self):
        self._update_lbl.setText(
            f'{self._("last_update")} {datetime.now().strftime("%H:%M:%S")}'
        )

    # ── Retranslate ───────────────────────────────────────────────────────────

    def retranslate_ui(self):
        self._ = TranslationManager.get_instance().translate
        self._title_lbl.setText(self._("dashboard_main_title"))
        self._refresh_btn.setText(self._("refresh"))
        self._act_title.setText(self._("recent_activities_title"))
        self._trx_title.setText(self._("latest_transactions_title"))
        self._type_section_title.setText(self._("transactions_overview"))
        self._qa_title.setText(self._("quick_actions_title"))
        self._set_update_time()
        self._update_trans_headers()

        stats = self._cached_stats
        for stat_key, title_key, sub_key, _, _ in self._TOP_CARDS:
            if card := self._stat_cards.get(stat_key):
                card.update_title(self._(title_key))
                card.update_subtitle(self._resolve_sub(sub_key, stats))

        for count_key, _, label_key, _, _ in self._TYPE_CARDS:
            if card := self._type_cards.get(count_key):
                card.update_label(self._(label_key))

        for btn, icon, lkey in self._qa_buttons:
            btn.retranslate(icon, self._(lkey))

        self._load_activities()
        self._load_transactions()

    def closeEvent(self, event):
        if hasattr(self, "_refresh_timer"):
            self._refresh_timer.stop()
        event.accept()