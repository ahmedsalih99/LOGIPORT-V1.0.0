"""
DashboardTab - LOGIPORT v3.2
==============================
Clean, theme-aware dashboard with stat cards, activities, and transactions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QGridLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from database.models import get_session_local
from database.db_utils import format_local_dt
from database.models import Transaction, Material, Client, AuditLog, User, Document, Entry
from config.themes.semantic_colors import SemanticColors
from sqlalchemy import func, desc
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# StatCard — بطاقة إحصائية ملونة
# ─────────────────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    PALETTES = {
        "transactions": ("#4A7EC8", "#2C5AA0"),
        "value":        ("#2ECC71", "#1A9A50"),
        "clients":      ("#9B59B6", "#6C3483"),
        "materials":    ("#E74C3C", "#A93226"),
        "import":       ("#3498DB", "#1F6FA4"),
        "export":       ("#1ABC9C", "#0E8C6F"),
        "transit":      ("#F39C12", "#B7770D"),
        "documents":    ("#64748B", "#475569"),
    }

    def __init__(self, title, value, subtitle, card_key="transactions", icon="📊", parent=None):
        super().__init__(parent)
        c1, c2 = self.PALETTES.get(card_key, ("#4A7EC8", "#2C5AA0"))
        self.setObjectName("stat-card-gradient")
        self.setStyleSheet(f"""
            QFrame#stat-card-gradient {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {c1},stop:1 {c2});
                border-radius: 14px;
                min-height: 110px;
                border: none;
            }}
            QLabel {{ color: white; background: transparent; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)

        # ── الصف العلوي: أيقونة + عنوان ──
        top = QHBoxLayout()
        top.setSpacing(0)
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "background: rgba(255,255,255,0.18); border-radius: 16px; font-size: 15px;"
        )
        top.addWidget(icon_lbl)
        top.addSpacing(10)
        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(QFont("Tajawal", 10, QFont.DemiBold))
        self._title_lbl.setStyleSheet("color: rgba(255,255,255,0.88);")
        top.addWidget(self._title_lbl, 1)
        lay.addLayout(top)

        lay.addSpacing(2)

        # ── القيمة الرئيسية — مصغّرة من 30 → 22 ──
        self.value_lbl = QLabel(str(value))
        self.value_lbl.setFont(QFont("Tajawal", 22, QFont.Bold))
        self.value_lbl.setStyleSheet("color: white; letter-spacing: 0.5px;")
        lay.addWidget(self.value_lbl)

        # ── الـ subtitle ──
        self._sub_lbl = QLabel(subtitle)
        self._sub_lbl.setFont(QFont("Tajawal", 8))
        self._sub_lbl.setStyleSheet("color: rgba(255,255,255,0.70);")
        lay.addWidget(self._sub_lbl)

    def update_value(self, v):    self.value_lbl.setText(str(v))
    def update_title(self, t):    self._title_lbl.setText(t)
    def update_subtitle(self, s): self._sub_lbl.setText(s)


# ─────────────────────────────────────────────────────────────────────────────
# ActivityItem — عنصر نشاط واحد
# ─────────────────────────────────────────────────────────────────────────────

class ActivityItem(QFrame):
    ICONS = {
        "create": ("➕", "#2ECC71"),
        "insert": ("➕", "#2ECC71"),
        "update": ("✏️", "#F39C12"),
        "delete": ("🗑️", "#E74C3C"),
    }

    def __init__(self, action: str, message: str, timestamp: str, parent=None):
        super().__init__(parent)
        self.setObjectName("activity-item")
        icon, color = self.ICONS.get(action.lower(), ("📝", "#3498DB"))

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)

        # دائرة الأيقونة
        ico = QLabel(icon)
        ico.setFixedSize(30, 30)
        ico.setAlignment(Qt.AlignCenter)
        ico.setStyleSheet(
            f"background: {color}; border-radius: 15px; color: white; font-size: 13px;"
        )
        lay.addWidget(ico)

        # النص والوقت
        col = QVBoxLayout()
        col.setSpacing(1)
        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont("Tajawal", 9, QFont.DemiBold))
        msg_lbl.setObjectName("activity-msg")
        col.addWidget(msg_lbl)

        ts_lbl = QLabel(f"🕒 {timestamp}")
        ts_lbl.setFont(QFont("Tajawal", 8))
        ts_lbl.setObjectName("activity-ts")
        col.addWidget(ts_lbl)

        lay.addLayout(col, 1)

        # خط ملون على الجانب
        self._color = color


# ─────────────────────────────────────────────────────────────────────────────
# DashboardTab
# ─────────────────────────────────────────────────────────────────────────────

class DashboardTab(QWidget):

    _ROW1_DEFS = [
        ("total_transactions", "total_transactions",  "active_transactions_fmt", "transactions", "📦"),
        ("total_value",        "total_value",         "active_transactions_lbl", "value",        "💰"),
        ("total_clients",      "clients",             "registered_client",       "clients",      "👥"),
        ("total_materials",    "materials",           "available_material",      "materials",    "📋"),
    ]
    _ROW2_DEFS = [
        ("import_count",    "transaction_type.import", "import_value_fmt",  "import",    "📥"),
        ("export_count",    "transaction_type.export", "export_value_fmt",  "export",    "📤"),
        ("transit_count",   "transit_type",            "transit_value_fmt", "transit",   "🚚"),
        ("total_documents", "documents",               "stat_documents",    "documents", "📄"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tm = TranslationManager.get_instance()
        self._ = self._tm.translate
        self.setObjectName("dashboard-tab")
        self._stat_cards  = {}
        self._cached_stats = {}
        self._tm.language_changed.connect(self.retranslate_ui)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setObjectName("dashboard-container")

        main = QVBoxLayout(container)
        main.setContentsMargins(28, 24, 28, 24)
        main.setSpacing(20)

        main.addWidget(self._build_header())
        main.addLayout(self._build_stat_grid())

        bottom = QHBoxLayout()
        bottom.setSpacing(18)
        bottom.addWidget(self._build_activities_panel(), stretch=2)
        bottom.addWidget(self._build_transactions_panel(), stretch=3)
        main.addLayout(bottom, stretch=1)

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_all_data)
        self._refresh_timer.start(30_000)

    # ── builders ──────────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setObjectName("dashboard-header-bar")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 4)

        self._title_lbl = QLabel(self._("dashboard_main_title"))
        self._title_lbl.setFont(QFont("Tajawal", 22, QFont.Bold))
        self._title_lbl.setObjectName("dashboard-title")
        lay.addWidget(self._title_lbl)
        lay.addStretch()

        self._update_lbl = QLabel()
        self._update_lbl.setObjectName("text-muted")
        self._set_update_time()
        lay.addWidget(self._update_lbl)

        lay.addSpacing(12)

        self._refresh_btn = QPushButton(self._("refresh"))
        self._refresh_btn.setObjectName("primary-btn")
        self._refresh_btn.setMinimumHeight(36)
        self._refresh_btn.setMinimumWidth(100)
        self._refresh_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_btn.clicked.connect(self.refresh_all_data)
        lay.addWidget(self._refresh_btn)

        return w

    def _build_stat_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)
        stats = self._get_stats()
        self._cached_stats.update(stats)

        all_defs = self._ROW1_DEFS + self._ROW2_DEFS
        for idx, (stat_key, title_key, sub_key, card_key, icon) in enumerate(all_defs):
            card = StatCard(
                self._(title_key),
                stats.get(stat_key, 0),
                self._resolve_sub(sub_key, stats),
                card_key, icon
            )
            self._stat_cards[stat_key] = card
            row, col = divmod(idx, 4)
            grid.addWidget(card, row, col)

        return grid

    def _build_activities_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        self._act_title = QLabel(self._("recent_activities_title"))
        self._act_title.setFont(QFont("Tajawal", 13, QFont.Bold))
        self._act_title.setObjectName("panel-title")
        lay.addWidget(self._act_title)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setObjectName("separator")
        lay.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._act_container = QWidget()
        self._act_container.setObjectName("activities-container")
        self._act_layout = QVBoxLayout(self._act_container)
        self._act_layout.setSpacing(5)
        self._act_layout.setContentsMargins(0, 0, 0, 0)
        self._load_activities()

        scroll.setWidget(self._act_container)
        lay.addWidget(scroll)
        return frame

    def _build_transactions_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        self._trx_title = QLabel(self._("latest_transactions_title"))
        self._trx_title.setFont(QFont("Tajawal", 13, QFont.Bold))
        self._trx_title.setObjectName("panel-title")
        lay.addWidget(self._trx_title)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setObjectName("separator")
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
        self._trans_table.verticalHeader().setDefaultSectionSize(38)
        self._update_trans_headers()
        self._load_transactions()

        lay.addWidget(self._trans_table)
        return frame

    # ── data ──────────────────────────────────────────────────────────────────

    def _get_stats(self) -> dict:
        s = {k: 0 for k in [
            "total_transactions", "active_transactions", "total_value",
            "total_clients", "total_materials",
            "import_count", "import_value", "export_count", "export_value",
            "transit_count", "transit_value", "total_documents",
        ]}
        try:
            with get_session_local()() as session:
                s["total_transactions"]  = session.query(Transaction).count()
                s["active_transactions"] = (
                    session.query(Transaction)
                    .filter(Transaction.status == "active").count()
                )
                v = session.query(func.sum(Transaction.totals_value)).scalar() or 0
                s["total_value"] = f"${float(v):,.0f}"

                for t in ("import", "export", "transit"):
                    s[f"{t}_count"] = (
                        session.query(Transaction)
                        .filter(Transaction.transaction_type == t).count()
                    )
                    s[f"{t}_value"] = float(
                        session.query(func.sum(Transaction.totals_value))
                        .filter(Transaction.transaction_type == t).scalar() or 0
                    )

                s["total_clients"]   = session.query(Client).count()
                s["total_materials"] = session.query(Material).count()
                s["total_documents"] = session.query(Document).count()
        except Exception as e:
            print(f"Dashboard stats error: {e}")
        return s

    def _resolve_sub(self, sub_key: str, stats: dict) -> str:
        if sub_key == "active_transactions_fmt":
            return self._("active_transactions").format(count=stats.get("active_transactions", 0))
        if sub_key == "import_value_fmt":  return f"${stats.get('import_value', 0):,.0f}"
        if sub_key == "export_value_fmt":  return f"${stats.get('export_value', 0):,.0f}"
        if sub_key == "transit_value_fmt": return f"${stats.get('transit_value', 0):,.0f}"
        return self._(sub_key)

    def _load_activities(self):
        # مسح العناصر القديمة
        while self._act_layout.count():
            item = self._act_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        TABLE_KEYS = {
            "transactions": "table_transactions", "materials": "table_materials",
            "clients": "table_clients", "users": "table_users",
            "documents": "table_documents", "entries": "table_entries",
            "companies": "table_companies",
        }
        ACTION_KEYS = {
            "create": "action_create", "insert": "action_insert",
            "update": "action_update", "delete": "action_delete",
        }

        try:
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
                    uname = getattr(row.user, "full_name", None) or getattr(row.user, "username", None) or self._("system_user")
                msg = self._("activity_message").format(user=uname, action=act, table=tbl)
                ts  = format_local_dt(row.timestamp)

                item = ActivityItem(action, msg, ts)
                item.setObjectName("activity-item")
                self._act_layout.addWidget(item)

        except Exception as e:
            err = QLabel(f"⚠️ {e}")
            err.setObjectName("activity-ts")
            self._act_layout.addWidget(err)

        self._act_layout.addStretch()

    def _update_trans_headers(self):
        self._trans_table.setHorizontalHeaderLabels([
            self._("col_number"), self._("transaction_date"), self._("col_type"),
            self._("col_client"), self._("col_weight_kg"), self._("col_value_usd"),
            self._("col_status"),
        ])

    def _load_transactions(self):
        self._trans_table.setRowCount(0)
        TYPE_MAP = {
            "import":  self._("import_type"),
            "export":  self._("export_type"),
            "transit": self._("transit_type"),
        }
        STATUS_COLORS = {
            "active":   "#2ECC71",
            "draft":    "#F39C12",
            "closed":   "#95A5A6",
            "archived": "#7F8C8D",
        }
        try:
            from sqlalchemy.orm import joinedload as jl
            with get_session_local()() as session:
                rows = (session.query(Transaction)
                        .options(jl(Transaction.client))
                        .order_by(desc(Transaction.id))
                        .limit(10).all())

            self._trans_table.setRowCount(len(rows))
            for r, t in enumerate(rows):
                def cell(txt, right=False):
                    i = QTableWidgetItem(txt)
                    i.setTextAlignment((Qt.AlignRight if right else Qt.AlignCenter) | Qt.AlignVCenter)
                    return i

                date_str = t.transaction_date.strftime("%Y-%m-%d") if t.transaction_date else "—"
                status_txt = self._(f"status_{t.status}") if t.status else "—"
                wt = f"{t.totals_net_kg:,.1f}" if t.totals_net_kg else "—"
                vl = f"{t.totals_value:,.2f}"  if t.totals_value  else "—"

                self._trans_table.setItem(r, 0, cell(t.transaction_no or "—"))
                self._trans_table.setItem(r, 1, cell(date_str))
                self._trans_table.setItem(r, 2, cell(TYPE_MAP.get(t.transaction_type, t.transaction_type or "—")))
                # اختيار اسم العميل حسب اللغة الحالية
                lang = TranslationManager.get_instance().get_current_language()
                if t.client:
                    if lang == "en":
                        client_display = t.client.name_en or t.client.name_ar or "—"
                    elif lang == "tr":
                        client_display = t.client.name_tr or t.client.name_ar or "—"
                    else:
                        client_display = t.client.name_ar or "—"
                else:
                    client_display = "—"
                self._trans_table.setItem(r, 3, cell(client_display))
                self._trans_table.setItem(r, 4, cell(wt, right=True))
                self._trans_table.setItem(r, 5, cell(vl, right=True))

                si = cell(status_txt)
                color = STATUS_COLORS.get(t.status or "", "#95A5A6")
                si.setForeground(QColor(color))
                self._trans_table.setItem(r, 6, si)

        except Exception as e:
            print(f"Dashboard transactions error: {e}")

    # ── refresh ───────────────────────────────────────────────────────────────

    def refresh_all_data(self):
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText(self._("refreshing"))
        self._set_update_time()

        stats = self._get_stats()
        self._cached_stats.update(stats)

        for key, val in {
            "total_transactions": stats["total_transactions"],
            "total_value":        stats["total_value"],
            "total_clients":      stats["total_clients"],
            "total_materials":    stats["total_materials"],
            "import_count":       stats["import_count"],
            "export_count":       stats["export_count"],
            "transit_count":      stats["transit_count"],
            "total_documents":    stats["total_documents"],
        }.items():
            if card := self._stat_cards.get(key):
                card.update_value(val)

        card = self._stat_cards.get("total_transactions")
        if card:
            card.update_subtitle(
                self._("active_transactions").format(count=stats.get("active_transactions", 0))
            )

        self._load_activities()
        self._load_transactions()

        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText(self._("refresh"))

    def _set_update_time(self):
        self._update_lbl.setText(
            f'{self._("last_update")} {datetime.now().strftime("%H:%M:%S")}'
        )

    def retranslate_ui(self):
        self._ = TranslationManager.get_instance().translate
        self._title_lbl.setText(self._("dashboard_main_title"))
        self._refresh_btn.setText(self._("refresh"))
        self._act_title.setText(self._("recent_activities_title"))
        self._trx_title.setText(self._("latest_transactions_title"))
        self._set_update_time()
        self._update_trans_headers()

        stats = self._cached_stats
        for stat_key, title_key, sub_key, _, _ in self._ROW1_DEFS + self._ROW2_DEFS:
            if card := self._stat_cards.get(stat_key):
                card.update_title(self._(title_key))
                card.update_subtitle(self._resolve_sub(sub_key, stats))

        self._load_activities()
        self._load_transactions()

    def closeEvent(self, event):
        if hasattr(self, "_refresh_timer"):
            self._refresh_timer.stop()
        event.accept()