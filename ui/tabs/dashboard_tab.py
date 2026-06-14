"""
DashboardTab - LOGIPORT — Navy + Gold Brand Design
====================================================
تصميم جديد:
- Hero Banner Navy داكن: المعاملات + المعاملات النشطة + الزبائن
- 4 KPI cards بشريط لوني علوي رفيع (بدون إجمالي القيمة)
- توزيع المعاملات (import/export/transit) + progress bars
- إجراءات سريعة
- جدول أحدث المعاملات + سجل الأنشطة
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


# ─── helpers ─────────────────────────────────────────────────────────────────

def _theme_colors():
    try:
        from core.theme_manager import ThemeManager
        return ThemeManager.get_instance().current_theme.colors
    except Exception:
        return {}

def _c(key, fallback=""):
    return _theme_colors().get(key, fallback)


# ─── Brand Colors ─────────────────────────────────────────────────────────────
NAVY   = "#0D1B2A"
NAVY2  = "#1B2F4A"
GOLD   = "#C9A84C"
GOLD_A = "rgba(201,168,76,0.15)"
GOLD_B = "rgba(201,168,76,0.25)"

# ─── KPI accents ─────────────────────────────────────────────────────────────
_CARD_ACCENTS = {
    "transactions": GOLD,
    "value":        "#10B981",
    "clients":      "#8B5CF6",
    "materials":    "#F59E0B",
    "documents":    "#64748B",
    "import":       GOLD,
    "export":       "#10B981",
    "transit":      "#EF4444",
    "tasks":        "#8B5CF6",
}

_TYPE_ICONS = {
    "import":  "📥",
    "export":  "📤",
    "transit": "🚚",
}


# ─────────────────────── Hero Banner ─────────────────────────────────────────

class HeroBanner(QFrame):
    """Hero Banner Navy — يستخدم stylesheet مع _apply_theme لضمان التحديث."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hero-banner")
        self._labels = {}
        self._build()
        self._apply_theme()
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(self._apply_theme)
        except Exception:
            pass

    def _apply_theme(self, _=None):
        self.setStyleSheet(f"""
            QFrame#hero-banner {{
                background   : {NAVY};
                border-radius: 12px;
                border       : none;
            }}
            QLabel {{
                background: transparent;
                border    : none;
            }}
        """)

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(0)

        stats = [
            ("hero_transactions", "stat_transactions"),
            ("hero_active",       "active_transactions_lbl"),
            ("hero_clients",      "clients"),
        ]

        for i, (val_key, lbl_key) in enumerate(stats):
            if i > 0:
                sep = QFrame()
                sep.setFixedSize(1, 44)
                sep.setStyleSheet(f"background: {GOLD_B}; border: none;")
                lay.addWidget(sep)

            col = QVBoxLayout()
            col.setSpacing(3)
            col.setAlignment(Qt.AlignCenter)

            val_lbl = QLabel("—")
            val_lbl.setFont(QFont("Tajawal", 28, QFont.Bold))
            val_lbl.setStyleSheet(f"color: {GOLD}; background: transparent;")
            val_lbl.setAlignment(Qt.AlignCenter)

            txt_lbl = QLabel()
            txt_lbl.setFont(QFont("Tajawal", 9))
            txt_lbl.setStyleSheet("color: rgba(255,255,255,0.55); background: transparent;")
            txt_lbl.setAlignment(Qt.AlignCenter)

            col.addWidget(val_lbl)
            col.addWidget(txt_lbl)

            wrap = QWidget()
            wrap.setStyleSheet("background: transparent;")
            wrap.setLayout(col)
            lay.addWidget(wrap, 1)

            self._labels[val_key] = val_lbl
            self._labels[lbl_key] = txt_lbl

        self.setFixedHeight(90)

    def update_stats(self, stats: dict):
        self._labels["hero_transactions"].setText(str(stats.get("total_transactions", 0)))
        self._labels["hero_active"].setText(str(stats.get("active_transactions", 0)))
        self._labels["hero_clients"].setText(str(stats.get("total_clients", 0)))

    def retranslate_ui(self, translate):
        try:
            self._labels["active_transactions_lbl"].setText(translate("active_transactions_lbl"))
        except Exception:
            pass
        try:
            self._labels["clients"].setText(translate("clients"))
        except Exception:
            pass
        try:
            self._labels["stat_transactions"].setText(translate("stat_transactions"))
        except Exception:
            pass


# ─────────────────────── KPI Card ────────────────────────────────────────────

class KpiCard(QFrame):
    """KPI Card — تستخدم QPalette لضمان تحديث الخلفية مع الثيم."""

    def __init__(self, title, value, subtitle, card_key="transactions", icon="📊", parent=None):
        super().__init__(parent)
        self._card_key = card_key
        self._accent   = _CARD_ACCENTS.get(card_key, GOLD)
        self.setObjectName("kpi-card")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._icon_str = icon
        self._build(title, value, subtitle, icon)
        self._apply_theme()
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(self._apply_theme)
        except Exception:
            pass

    def _apply_theme(self, _=None):
        accent = self._accent
        bg  = _c("bg_card",       "#FFFFFF")
        bdr = _c("border",        "#E2E8F0")
        tp  = _c("text_primary",  "#0D1B2A")
        ts  = _c("text_secondary","#64748B")
        bh  = _c("border_hover",  "#C9A84C")

        self.setStyleSheet(f"""
            QFrame#kpi-card {{
                background : {bg};
                border      : 1px solid {bdr};
                border-top  : 3px solid {accent};
                border-radius: 10px;
            }}
            QFrame#kpi-card:hover {{
                border-color: {bh};
                border-top  : 3px solid {accent};
            }}
            QLabel {{
                background: transparent;
                border    : none;
            }}
        """)
        if hasattr(self, "value_lbl"):
            self.value_lbl.setStyleSheet(f"color:{tp}; background:transparent;")
        if hasattr(self, "_title_lbl"):
            self._title_lbl.setStyleSheet(f"color:{ts}; background:transparent;")
        if hasattr(self, "_sub_lbl"):
            self._sub_lbl.setStyleSheet(f"color:{ts}; background:transparent;")
        if hasattr(self, "_ico_lbl"):
            self._ico_lbl.setStyleSheet(
                f"background:{accent}22; border-radius:14px; font-size:13px; border:none;"
            )

    def _build(self, title, value, subtitle, icon):
        accent = self._accent
        tp = _c("text_primary",   "#0D1B2A")
        ts = _c("text_secondary", "#64748B")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 12)
        lay.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(QFont("Tajawal", 9))
        self._title_lbl.setStyleSheet(f"color:{ts}; background:transparent;")
        top_row.addWidget(self._title_lbl, 1)

        self._ico_lbl = QLabel(icon)
        self._ico_lbl.setFixedSize(28, 28)
        self._ico_lbl.setAlignment(Qt.AlignCenter)
        self._ico_lbl.setStyleSheet(
            f"background:{accent}22; border-radius:14px; font-size:13px; border:none;"
        )
        top_row.addWidget(self._ico_lbl)
        lay.addLayout(top_row)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setFont(QFont("Tajawal", 22, QFont.Bold))
        self.value_lbl.setStyleSheet(f"color:{tp}; background:transparent;")
        lay.addWidget(self.value_lbl)

        self._sub_lbl = QLabel(subtitle)
        self._sub_lbl.setFont(QFont("Tajawal", 8))
        self._sub_lbl.setStyleSheet(f"color:{ts}; background:transparent;")
        lay.addWidget(self._sub_lbl)

        self.setMinimumHeight(100)

    def update_value(self, v):    self.value_lbl.setText(str(v))
    def update_title(self, t):    self._title_lbl.setText(t)
    def update_subtitle(self, s): self._sub_lbl.setText(s)


# ─────────────────────── Type Progress Row ───────────────────────────────────

class TypeProgressRow(QFrame):
    """صف توزيع نوع المعاملات — يتحدث مع الثيم."""

    def __init__(self, label, count, value_str, pct, accent, icon, parent=None):
        super().__init__(parent)
        self._accent = accent
        self.setObjectName("type-progress-row")
        self._bar       = None
        self._count_lbl = None
        self._val_lbl   = None
        self._lbl_w     = None
        self._build(label, count, value_str, pct, icon)
        self._apply_theme()
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(self._apply_theme)
        except Exception:
            pass

    def _apply_theme(self, _=None):
        accent = self._accent
        ts = _c("text_secondary", "#64748B")
        bar_bg = _c("bg_surface_2", "#F4F6F9")
        self.setStyleSheet(f"""
            QFrame#type-progress-row {{ background: transparent; border: none; }}
            QLabel {{ background: transparent; border: none; color: {ts}; }}
            QProgressBar {{
                background  : {bar_bg};
                border-radius: 3px; border: none; max-height: 5px;
            }}
            QProgressBar::chunk {{ background: {accent}; border-radius: 3px; }}
        """)
        if self._count_lbl:
            self._count_lbl.setStyleSheet(f"color:{accent}; background:transparent;")
        if self._val_lbl:
            self._val_lbl.setStyleSheet(f"color:{ts}; background:transparent;")
        if self._lbl_w:
            self._lbl_w.setStyleSheet(f"color:{ts}; background:transparent;")

    def _build(self, label, count, value_str, pct, icon):
        accent = self._accent
        ts = _c("text_secondary", "#64748B")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(10)

        ico = QLabel(icon)
        ico.setFixedSize(28, 28)
        ico.setAlignment(Qt.AlignCenter)
        ico.setStyleSheet(
            f"background:{accent}18; border-radius:14px; font-size:14px; border:none;"
        )
        lay.addWidget(ico)

        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        self._lbl_w = QLabel(label)
        self._lbl_w.setFont(QFont("Tajawal", 9))
        self._lbl_w.setStyleSheet(f"color:{ts};")
        info_col.addWidget(self._lbl_w)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(max(0, min(100, int(pct))))
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(5)
        info_col.addWidget(self._bar)
        lay.addLayout(info_col, 1)

        right_col = QVBoxLayout()
        right_col.setSpacing(2)
        right_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._count_lbl = QLabel(str(count))
        self._count_lbl.setFont(QFont("Tajawal", 14, QFont.Bold))
        self._count_lbl.setStyleSheet(f"color:{accent};")
        self._count_lbl.setAlignment(Qt.AlignRight)
        right_col.addWidget(self._count_lbl)

        self._val_lbl = QLabel(value_str)
        self._val_lbl.setFont(QFont("Tajawal", 8))
        self._val_lbl.setStyleSheet(f"color:{ts};")
        self._val_lbl.setAlignment(Qt.AlignRight)
        right_col.addWidget(self._val_lbl)
        lay.addLayout(right_col)

    def update_data(self, count, value_str, pct):
        if self._count_lbl: self._count_lbl.setText(str(count))
        if self._val_lbl:   self._val_lbl.setText(value_str)
        if self._bar:       self._bar.setValue(max(0, min(100, int(pct))))

    def update_label(self, label):
        if self._lbl_w: self._lbl_w.setText(label)


# ─────────────────────── Quick Action Button ─────────────────────────────────

class QuickActionBtn(QPushButton):
    def __init__(self, icon, label, callback=None, is_primary=False, parent=None):
        super().__init__(parent)
        self._is_primary = is_primary
        self.setFixedSize(110, 80)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._apply_style()
        self._set_text(icon, label)
        if callback:
            self.clicked.connect(callback)

    def _apply_style(self):
        if self._is_primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {GOLD_A};
                    border: 1px solid {GOLD_B};
                    border-radius: 10px;
                    color: {GOLD};
                    font-family: Tajawal; font-size: 10px; font-weight: 600;
                    padding: 6px 4px;
                }}
                QPushButton:hover {{
                    background: {GOLD_B};
                    border-color: {GOLD};
                }}
                QPushButton:pressed {{
                    background: rgba(201,168,76,0.35);
                }}
            """)
        else:
            bg   = _c("bg_hover", "#F8F7F4")
            bdr  = _c("border", "#E0E0E0")
            tp   = _c("text_primary", "#0D1B2A")
            bg_h = _c("bg_active", "#F0E4C0")
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {bg};
                    border: 1px solid {bdr};
                    border-radius: 10px;
                    color: {tp};
                    font-family: Tajawal; font-size: 10px; font-weight: 500;
                    padding: 6px 4px;
                }}
                QPushButton:hover {{
                    background: {bg_h};
                    border-color: {GOLD}88;
                }}
                QPushButton:pressed {{
                    background: {GOLD_A};
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
        color = self._ACT_COLORS.get(action.lower(), GOLD)
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
                "total_transactions", "active_transactions",
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

    # KPI cards (بدون total_value)
    _TOP_CARDS = [
        ("total_transactions", "stat_transactions",  "active_transactions_fmt", "transactions", "📦"),
        ("total_entries",      "entries",             "stat_entries_sub",        "import",       "📥"),
        ("total_clients",      "clients",             "registered_client",       "clients",      "👥"),
        ("total_materials",    "materials",           "available_material",      "materials",    "📋"),
        ("total_documents",    "documents",           "stat_documents",          "documents",    "📄"),
    ]

    _TYPE_CARDS = [
        ("import_count",  "import_value",  "import_type",  GOLD,      "📥"),
        ("export_count",  "export_value",  "export_type",  "#10B981", "📤"),
        ("transit_count", "transit_value", "transit_type", "#EF4444", "🚚"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tm = TranslationManager.get_instance()
        self._ = self._tm.translate
        self.setObjectName("dashboard-tab")
        self._stat_cards   = {}
        self._type_rows    = {}
        self._cached_stats = {}
        self._qa_buttons   = []
        self._tm.language_changed.connect(self.retranslate_ui)
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        container = QWidget()
        container.setObjectName("dashboard-container")
        main = QVBoxLayout(container)
        main.setContentsMargins(20, 14, 20, 20)
        main.setSpacing(12)

        # Header
        main.addWidget(self._build_header())

        # Hero Banner
        self._hero = HeroBanner()
        main.addWidget(self._hero)

        # KPI Cards row
        main.addLayout(self._build_kpi_row())

        # Middle: type overview + quick actions
        main.addLayout(self._build_middle_row())

        # Bottom: activities + transactions
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
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
        w.setObjectName("dashboard-header-bar")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        self._title_lbl = QLabel(self._("dashboard_main_title"))
        self._title_lbl.setFont(QFont("Tajawal", 15, QFont.Bold))
        self._title_lbl.setObjectName("dashboard-title")
        lay.addWidget(self._title_lbl)
        lay.addStretch()

        self._update_lbl = QLabel()
        self._update_lbl.setObjectName("text-muted")
        self._update_lbl.setFont(QFont("Tajawal", 9))
        self._set_update_time()
        lay.addWidget(self._update_lbl)
        lay.addSpacing(8)

        self._refresh_btn = QPushButton(self._("refresh"))
        self._refresh_btn.setObjectName("secondary-btn")
        self._refresh_btn.setMinimumHeight(30)
        self._refresh_btn.setMinimumWidth(80)
        self._refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._refresh_btn.setFont(QFont("Tajawal", 9))
        self._refresh_btn.clicked.connect(self.refresh_all_data)
        lay.addWidget(self._refresh_btn)
        return w

    # ── KPI Row ───────────────────────────────────────────────────────────────

    def _build_kpi_row(self):
        grid = QGridLayout()
        grid.setSpacing(10)
        for col, (stat_key, title_key, sub_key, card_key, icon) in enumerate(self._TOP_CARDS):
            card = KpiCard(
                self._(title_key), 0,
                self._resolve_sub(sub_key, {}),
                card_key, icon
            )
            self._stat_cards[stat_key] = card
            grid.addWidget(card, 0, col)
        return grid

    # ── Middle Row ────────────────────────────────────────────────────────────

    def _build_middle_row(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        # ── Type Overview ───────────────────────────────────────────────
        tf = QFrame()
        tf.setObjectName("card")
        tf_lay = QVBoxLayout(tf)
        tf_lay.setContentsMargins(16, 14, 16, 14)
        tf_lay.setSpacing(4)

        # عنوان + خط ذهبي
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        dot = QFrame()
        dot.setFixedSize(4, 16)
        dot.setStyleSheet(f"background:{GOLD}; border-radius:2px; border:none;")
        title_row.addWidget(dot)
        self._type_section_title = QLabel(self._("transactions_overview"))
        self._type_section_title.setFont(QFont("Tajawal", 11, QFont.Bold))
        self._type_section_title.setObjectName("panel-title")
        title_row.addWidget(self._type_section_title, 1)
        tf_lay.addLayout(title_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        tf_lay.addWidget(sep)
        tf_lay.addSpacing(4)

        for count_key, val_key, label_key, accent, icon in self._TYPE_CARDS:
            row_w = TypeProgressRow(self._(label_key), 0, "$0", 0, accent, icon)
            self._type_rows[count_key] = row_w
            tf_lay.addWidget(row_w)

        tf_lay.addSpacing(6)

        # Tasks strip
        self._tasks_strip_frame = self._build_tasks_strip(0)
        tf_lay.addWidget(self._tasks_strip_frame)

        row.addWidget(tf, stretch=3)

        # ── Quick Actions ───────────────────────────────────────────────
        qa = QFrame()
        qa.setObjectName("card")
        qa_lay = QVBoxLayout(qa)
        qa_lay.setContentsMargins(16, 14, 16, 14)
        qa_lay.setSpacing(10)

        qa_title_row = QHBoxLayout()
        dot2 = QFrame()
        dot2.setFixedSize(4, 16)
        dot2.setStyleSheet(f"background:{GOLD}; border-radius:2px; border:none;")
        qa_title_row.addWidget(dot2)
        self._qa_title = QLabel(self._("quick_actions_title"))
        self._qa_title.setFont(QFont("Tajawal", 11, QFont.Bold))
        self._qa_title.setObjectName("panel-title")
        qa_title_row.addWidget(self._qa_title, 1)
        qa_lay.addLayout(qa_title_row)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("separator")
        qa_lay.addWidget(sep2)

        _actions = [
            ("➕", "add_transaction",  self._navigate_to_add_transaction, True),
            ("📄", "documents",        self._navigate_to_documents,       False),
            ("👥", "clients",          self._navigate_to_clients,         False),
            ("📦", "transactions",     self._navigate_to_transactions,    False),
            ("🚢", "refrigerators",    self._navigate_to_containers,      False),
            ("✅", "tasks",            self._navigate_to_tasks,           False),
        ]
        btns_grid = QGridLayout()
        btns_grid.setSpacing(8)
        self._qa_buttons = []
        for idx, (icon, lkey, cb, primary) in enumerate(_actions):
            btn = QuickActionBtn(icon, self._(lkey), cb, is_primary=primary)
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
        is_ok  = overdue == 0
        color  = _c("success", "#10B981") if is_ok else _c("danger", "#EF4444")
        bg     = _c("bg_card", "#FFFFFF")

        f.setStyleSheet(f"""
            QFrame#tasks-strip {{
                background: {bg};
                border-radius: 7px;
                border: 1px solid {color}35;
                border-right: 3px solid {color};
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
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        title_row = QHBoxLayout()
        dot = QFrame()
        dot.setFixedSize(4, 16)
        dot.setStyleSheet(f"background:{GOLD}; border-radius:2px; border:none;")
        title_row.addWidget(dot)
        self._act_title = QLabel(self._("recent_activities_title"))
        self._act_title.setFont(QFont("Tajawal", 11, QFont.Bold))
        self._act_title.setObjectName("panel-title")
        title_row.addWidget(self._act_title, 1)
        lay.addLayout(title_row)

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
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        title_row = QHBoxLayout()
        dot = QFrame()
        dot.setFixedSize(4, 16)
        dot.setStyleSheet(f"background:{GOLD}; border-radius:2px; border:none;")
        title_row.addWidget(dot)
        self._trx_title = QLabel(self._("latest_transactions_title"))
        self._trx_title.setFont(QFont("Tajawal", 11, QFont.Bold))
        self._trx_title.setObjectName("panel-title")
        title_row.addWidget(self._trx_title, 1)
        lay.addLayout(title_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        self._trans_table = QTableWidget()
        self._trans_table.setObjectName("data-table")
        self._trans_table.setColumnCount(6)
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

    # ── Data Helpers ──────────────────────────────────────────────────────────

    def _resolve_sub(self, sub_key, stats):
        if sub_key == "active_transactions_fmt":
            return self._("active_transactions_fmt").format(count=stats.get("active_transactions", 0))
        if sub_key == "stat_entries_sub":
            return self._("stat_entries_sub")
        return self._(sub_key)

    # ── Activities Feed ───────────────────────────────────────────────────────

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

    # ── Transactions Table ────────────────────────────────────────────────────

    def _update_trans_headers(self):
        self._trans_table.setHorizontalHeaderLabels([
            self._("col_number"), self._("transaction_date"), self._("col_type"),
            self._("col_client"), self._("col_value_usd"), self._("col_status"),
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
                    date_str   = str(t.get("transaction_date", "") or "—")[:10]
                    status     = t.get("status") or ""
                    status_txt = self._(f"status_{status}") if status else "—"
                    vl         = f"${t.get('totals_value', 0) or 0:,.0f}"
                    trx_type   = t.get("transaction_type") or ""
                    type_txt   = TYPE_MAP.get(trx_type, trx_type or "—")

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

                    self._trans_table.setItem(r, 0, _cell(t.get("transaction_no") or "—"))
                    self._trans_table.setItem(r, 1, _cell(date_str))
                    self._trans_table.setItem(r, 2, _cell(type_txt))
                    self._trans_table.setItem(r, 3, _cell(client_name))
                    self._trans_table.setItem(r, 4, _cell(vl, right=True))
                    si = _cell(status_txt)
                    si.setForeground(QColor(STATUS_COLORS.get(status, "#6B7280")))
                    self._trans_table.setItem(r, 5, si)
            finally:
                self._trans_table.setUpdatesEnabled(True)
                self._trans_table.setSortingEnabled(True)
        except Exception as e:
            logger.error(f"Dashboard transactions error: {e}")

    # ── Navigation ────────────────────────────────────────────────────────────

    def _navigate_to(self, tab_key: str):
        try:
            main = self.window()
            if hasattr(main, "switch_section"):
                main.switch_section(tab_key)
        except Exception as e:
            logger.error(f"Dashboard navigate error: {e}")

    def _navigate_to_add_transaction(self):
        try:
            self._navigate_to("transactions")
            main = self.window()
            trx_tab = getattr(main, "tabs", {}).get("transactions")
            if trx_tab and hasattr(trx_tab, "add_new_item"):
                QTimer.singleShot(80, trx_tab.add_new_item)
        except Exception as e:
            logger.error(f"Dashboard add_transaction error: {e}")

    def _navigate_to_documents(self):    self._navigate_to("documents")
    def _navigate_to_clients(self):      self._navigate_to("clients")
    def _navigate_to_transactions(self): self._navigate_to("transactions")
    def _navigate_to_containers(self):   self._navigate_to("container_tracking")
    def _navigate_to_tasks(self):        self._navigate_to("tasks")

    # ── Theme Change ─────────────────────────────────────────────────────────

    def _on_theme_changed(self, _=None):
        """تحديث كل الـ widgets عند تغيير الثيم."""
        # تحديث جدول المعاملات
        self._load_transactions(preloaded=None if not self._cached_stats else
                                [])  # سيُعاد تحميله عند الـ refresh التالي
        # تحديث tasks strip
        overdue = self._cached_stats.get("tasks_overdue", 0)
        is_ok   = overdue == 0
        color   = _c("success", "#10B981") if is_ok else _c("danger", "#EF4444")
        bg      = _c("bg_card", "#FFFFFF")
        self._tasks_strip_frame.setStyleSheet(f"""
            QFrame#tasks-strip {{
                background: {bg};
                border-radius: 7px;
                border: 1px solid {color}35;
                border-right: 3px solid {color};
            }}
            QLabel {{ background: transparent; border: none; }}
        """)

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

        # Hero Banner
        self._hero.update_stats(stats)

        # KPI cards
        for stat_key, _, sub_key, _, _ in self._TOP_CARDS:
            if card := self._stat_cards.get(stat_key):
                card.update_value(stats.get(stat_key, 0))
                card.update_subtitle(self._resolve_sub(sub_key, stats))

        # Type progress rows
        total = max(stats.get("total_transactions", 1), 1)
        for count_key, val_key, _, _, _ in self._TYPE_CARDS:
            if row_w := self._type_rows.get(count_key):
                count = stats.get(count_key, 0)
                val   = stats.get(val_key, 0)
                row_w.update_data(count, f"${val:,.0f}", count / total * 100)

        # Tasks strip
        overdue = stats.get("tasks_overdue", 0)
        is_ok   = overdue == 0
        color   = _c("success", "#10B981") if is_ok else _c("danger", "#EF4444")
        txt = (self._("no_overdue_tasks") if is_ok
               else self._("tasks_overdue_count").format(n=overdue))
        self._tasks_lbl.setText(txt)
        self._tasks_lbl.setStyleSheet(f"color:{color};")
        bg = _c("bg_card", "#FFFFFF")
        self._tasks_strip_frame.setStyleSheet(f"""
            QFrame#tasks-strip {{
                background: {bg};
                border-radius: 7px;
                border: 1px solid {color}35;
                border-right: 3px solid {color};
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
        self._hero.retranslate_ui(self._)

        stats = self._cached_stats
        for stat_key, title_key, sub_key, _, _ in self._TOP_CARDS:
            if card := self._stat_cards.get(stat_key):
                card.update_title(self._(title_key))
                card.update_subtitle(self._resolve_sub(sub_key, stats))

        for count_key, _, label_key, _, _ in self._TYPE_CARDS:
            if row_w := self._type_rows.get(count_key):
                row_w.update_label(self._(label_key))

        for btn, icon, lkey in self._qa_buttons:
            btn.retranslate(icon, self._(lkey))

        self._load_activities()
        self._load_transactions()

    def closeEvent(self, event):
        if hasattr(self, "_refresh_timer"):
            self._refresh_timer.stop()
        event.accept()