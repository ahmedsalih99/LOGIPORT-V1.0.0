"""
DashboardTab - LOGIPORT v3.1
==============================
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
from database.models import Transaction, Material, Client, AuditLog, User, Document, Entry
from config.themes.semantic_colors import SemanticColors
from sqlalchemy import func, desc
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# StatCard
# ─────────────────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    CARD_PALETTES = {
        "transactions": ("#4A7EC8", "#2C5AA0"),
        "value":        ("#2ECC71", "#1A9A50"),
        "clients":      ("#9B59B6", "#6C3483"),
        "materials":    ("#E74C3C", "#A93226"),
        "import":       ("#3498DB", "#1F6FA4"),
        "export":       ("#1ABC9C", "#0E8C6F"),
        "transit":      ("#F39C12", "#B7770D"),
        "documents":    ("#7F8C8D", "#4D6364"),
    }

    def __init__(self, title, value, subtitle, card_key="transactions", icon="📊", parent=None):
        super().__init__(parent)
        self.setObjectName("stat-card-gradient")
        colors = self.CARD_PALETTES.get(card_key, ("#4A7EC8", "#2C5AA0"))
        c1, c2 = colors
        self.setStyleSheet(f"""
            QFrame#stat-card-gradient {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {c1}, stop:1 {c2}
                );
                border-radius: 14px;
                min-height: 130px;
                border: 1px solid rgba(255,255,255,0.15);
            }}
            QLabel {{ color: white; background: transparent; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 26))
        header.addWidget(icon_lbl)
        header.addStretch()
        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(QFont("Tajawal", 11))
        self._title_lbl.setStyleSheet("color: rgba(255,255,255,0.92); background: transparent;")
        header.addWidget(self._title_lbl)
        layout.addLayout(header)
        layout.addSpacing(4)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setFont(QFont("Tajawal", 34, QFont.Bold))
        self.value_lbl.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(self.value_lbl)

        self._sub_lbl = QLabel(subtitle) if subtitle else None
        if self._sub_lbl:
            self._sub_lbl.setFont(QFont("Tajawal", 9))
            self._sub_lbl.setStyleSheet("color: rgba(255,255,255,0.82); background: transparent;")
            layout.addWidget(self._sub_lbl)

        layout.addStretch()

    def update_value(self, value):
        self.value_lbl.setText(str(value))

    def update_title(self, title: str):
        self._title_lbl.setText(title)

    def update_subtitle(self, subtitle: str):
        if self._sub_lbl:
            self._sub_lbl.setText(subtitle)


# ─────────────────────────────────────────────────────────────────────────────
# DashboardTab
# ─────────────────────────────────────────────────────────────────────────────

class DashboardTab(QWidget):

    # تعريف البطاقات كـ class-level لإعادة الاستخدام في retranslate
    _ROW1_DEFS = [
        # (stat_key,            title_key,              sub_key,                  card_key,      icon)
        ("total_transactions", "total_transactions",   "active_transactions_fmt", "transactions","📦"),
        ("total_value",        "total_value",          "active_transactions_lbl", "value",       "💰"),
        ("total_clients",      "clients",              "registered_client",       "clients",     "👥"),
        ("total_materials",    "materials",            "available_material",      "materials",   "📋"),
    ]
    _ROW2_DEFS = [
        ("import_count",    "transaction_type.import",  "import_value_fmt",  "import",    "📥"),
        ("export_count",    "transaction_type.export",  "export_value_fmt",  "export",    "📤"),
        ("transit_count",   "transit_type",             "transit_value_fmt", "transit",   "🚚"),
        ("total_documents", "documents",                "stat_documents",    "documents", "📄"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tm = TranslationManager.get_instance()
        self._ = self._tm.translate
        self.setObjectName("dashboard-tab")
        self._stat_cards = {}       # stat_key → StatCard
        self._cached_stats = {}     # آخر إحصاء لاستخدامه في retranslate
        self._tm.language_changed.connect(self.retranslate_ui)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setObjectName("dashboard-container")

        main = QVBoxLayout(container)
        main.setContentsMargins(24, 24, 24, 24)
        main.setSpacing(20)

        main.addWidget(self._build_header())
        main.addLayout(self._build_stat_row1())
        main.addLayout(self._build_stat_row2())

        content = QHBoxLayout()
        content.setSpacing(18)
        content.addWidget(self._build_activities_panel(), stretch=2)
        content.addWidget(self._build_transactions_panel(), stretch=3)
        main.addLayout(content, stretch=1)

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_all_data)
        self._refresh_timer.start(30000)

    # ─── builders ─────────────────────────────────────────────────────────────

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("dashboard-header")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(0, 0, 0, 0)

        self._title_lbl = QLabel(self._("dashboard_main_title"))
        self._title_lbl.setFont(QFont("Tajawal", 24, QFont.Bold))
        self._title_lbl.setObjectName("dashboard-title")
        lay.addWidget(self._title_lbl)
        lay.addStretch()

        self._update_lbl = QLabel()
        self._update_lbl.setObjectName("text-muted")
        self._update_lbl.setFont(QFont("Tajawal", 9))
        self._set_update_time()
        lay.addWidget(self._update_lbl)

        self._refresh_btn_ref = QPushButton(self._("refresh"))
        self._refresh_btn_ref.setObjectName("btn-primary")
        self._refresh_btn_ref.setFont(QFont("Tajawal", 10))
        self._refresh_btn_ref.setMinimumHeight(34)
        self._refresh_btn_ref.setCursor(Qt.PointingHandCursor)
        self._refresh_btn_ref.clicked.connect(self.refresh_all_data)
        lay.addWidget(self._refresh_btn_ref)

        return header

    def _build_stat_row1(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)
        stats = self._get_stats()
        self._cached_stats.update(stats)

        for i, (stat_key, title_key, sub_key, card_key, icon) in enumerate(self._ROW1_DEFS):
            title = self._(title_key)
            sub   = self._resolve_sub(sub_key, stats)
            card  = StatCard(title, stats.get(stat_key, 0), sub, card_key, icon)
            self._stat_cards[stat_key] = card
            grid.addWidget(card, 0, i)

        return grid

    def _build_stat_row2(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)
        stats = self._get_stats()
        self._cached_stats.update(stats)

        for i, (stat_key, title_key, sub_key, card_key, icon) in enumerate(self._ROW2_DEFS):
            title = self._(title_key)
            sub   = self._resolve_sub(sub_key, stats)
            card  = StatCard(title, stats.get(stat_key, 0), sub, card_key, icon)
            self._stat_cards[stat_key] = card
            grid.addWidget(card, 0, i)

        return grid

    def _resolve_sub(self, sub_key: str, stats: dict) -> str:
        """يحوّل مفتاح الـ subtitle إلى نص مترجم مع دعم القيم الديناميكية."""
        if sub_key == "active_transactions_fmt":
            return self._("active_transactions").format(count=stats.get("active_transactions", 0))
        if sub_key == "import_value_fmt":
            return f"${stats.get('import_value', 0):,.0f}"
        if sub_key == "export_value_fmt":
            return f"${stats.get('export_value', 0):,.0f}"
        if sub_key == "transit_value_fmt":
            return f"${stats.get('transit_value', 0):,.0f}"
        return self._(sub_key)

    def _build_activities_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        self._activities_title = QLabel(self._("recent_activities_title"))
        self._activities_title.setFont(QFont("Tajawal", 14, QFont.Bold))
        lay.addWidget(self._activities_title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._activities_container = QWidget()
        self._activities_container.setStyleSheet("background: transparent;")
        self._activities_layout = QVBoxLayout(self._activities_container)
        self._activities_layout.setSpacing(6)
        self._activities_layout.setContentsMargins(0, 0, 0, 0)

        self._load_activities()
        scroll.setWidget(self._activities_container)
        lay.addWidget(scroll)
        return frame

    def _build_transactions_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        self._transactions_title = QLabel(self._("latest_transactions_title"))
        self._transactions_title.setFont(QFont("Tajawal", 14, QFont.Bold))
        lay.addWidget(self._transactions_title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        self._trans_table = QTableWidget()
        self._trans_table.setObjectName("data-table")
        self._trans_table.setColumnCount(7)
        self._trans_table.setHorizontalHeaderLabels([
            self._("col_number"), self._("transaction_date"), self._("col_type"),
            self._("col_client"), self._("col_weight_kg"), self._("col_value_usd"),
            self._("col_status"),
        ])
        self._trans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._trans_table.verticalHeader().setVisible(False)
        self._trans_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._trans_table.setAlternatingRowColors(True)
        self._trans_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self._load_transactions()
        lay.addWidget(self._trans_table)
        return frame

    # ─── data loaders ─────────────────────────────────────────────────────────

    def _get_stats(self) -> dict:
        stats = {
            "total_transactions": 0, "active_transactions": 0,
            "total_value": 0, "total_clients": 0, "total_materials": 0,
            "import_count": 0, "import_value": 0,
            "export_count": 0, "export_value": 0,
            "transit_count": 0, "transit_value": 0,
            "total_documents": 0,
        }
        try:
            with get_session_local()() as session:
                stats["total_transactions"] = session.query(Transaction).count()
                stats["active_transactions"] = (
                    session.query(Transaction)
                    .filter(Transaction.status == "active").count()
                )
                v = (session.query(func.sum(Transaction.totals_value))
                     .filter(Transaction.status == "active").scalar() or 0)
                stats["total_value"] = f"${float(v):,.0f}"

                for t in ["import", "export", "transit"]:
                    c = session.query(Transaction).filter(Transaction.transaction_type == t).count()
                    v2 = (session.query(func.sum(Transaction.totals_value))
                          .filter(Transaction.transaction_type == t).scalar() or 0)
                    stats[f"{t}_count"] = c
                    stats[f"{t}_value"] = float(v2)

                stats["total_clients"]   = session.query(Client).count()
                stats["total_materials"] = session.query(Material).count()
                stats["total_documents"] = session.query(Document).count()
        except Exception as e:
            print(f"Dashboard stats error: {e}")
        return stats

    def _load_activities(self):
        while self._activities_layout.count():
            item = self._activities_layout.takeAt(0)
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
        ICONS = {
            "create": ("➕", "#2ECC71"), "insert": ("➕", "#2ECC71"),
            "update": ("✏️", "#F39C12"), "delete": ("🗑️", "#E74C3C"),
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
                icon, color = ICONS.get(action, ("📝", "#3498DB"))
                tbl_key = TABLE_KEYS.get(row.table_name)
                tbl = self._(tbl_key) if tbl_key else (row.table_name or "—")
                act_key = ACTION_KEYS.get(action)
                act = self._(act_key) if act_key else action
                uname = ""
                if row.user:
                    uname = (getattr(row.user, "full_name", None) or
                             getattr(row.user, "username", None) or self._("system_user"))
                ts = row.timestamp.strftime("%Y-%m-%d %H:%M") if row.timestamp else "—"

                item = QFrame()
                item.setStyleSheet(f"""
                    QFrame {{
                        background: rgba(0,0,0,0.02);
                        border-radius: 8px;
                        border-right: 3px solid {color};
                    }}
                    QFrame:hover {{ background: rgba(74,126,200,0.06); }}
                """)
                row_lay = QHBoxLayout(item)
                row_lay.setContentsMargins(8, 6, 8, 6)

                ico_lbl = QLabel(icon)
                ico_lbl.setFont(QFont("Segoe UI Emoji", 14))
                ico_lbl.setFixedSize(28, 28)
                ico_lbl.setAlignment(Qt.AlignCenter)
                ico_lbl.setStyleSheet(f"background: {color}; border-radius: 14px; color: white;")
                row_lay.addWidget(ico_lbl)

                col = QVBoxLayout()
                col.setSpacing(1)
                msg = QLabel(self._("activity_message").format(user=uname, action=act, table=tbl))
                msg.setFont(QFont("Tajawal", 9, QFont.DemiBold))
                col.addWidget(msg)
                ts_lbl = QLabel(f"🕒 {ts}")
                ts_lbl.setFont(QFont("Tajawal", 8))
                ts_lbl.setStyleSheet("color: #9CA3AF;")
                col.addWidget(ts_lbl)
                row_lay.addLayout(col, 1)

                self._activities_layout.addWidget(item)

        except Exception as e:
            err = QLabel(f"⚠️ {e}")
            err.setStyleSheet("color: #E74C3C;")
            self._activities_layout.addWidget(err)

        self._activities_layout.addStretch()

    def _load_transactions(self):
        self._trans_table.setRowCount(0)
        TYPE_MAP = {
            "import":  self._("import_type"),
            "export":  self._("export_type"),
            "transit": self._("transit_type"),
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
                    i.setFont(QFont("Tajawal", 9))
                    i.setTextAlignment(
                        (Qt.AlignRight if right else Qt.AlignCenter) | Qt.AlignVCenter
                    )
                    return i

                self._trans_table.setItem(r, 0, cell(t.transaction_no or "—"))
                ds = t.transaction_date.strftime("%Y-%m-%d") if t.transaction_date else "—"
                self._trans_table.setItem(r, 1, cell(ds))
                self._trans_table.setItem(r, 2, cell(TYPE_MAP.get(t.transaction_type, t.transaction_type or "—")))
                cname = t.client.name_ar if t.client else "—"
                self._trans_table.setItem(r, 3, cell(cname))
                wt = f"{t.totals_net_kg:,.1f}" if t.totals_net_kg else "—"
                self._trans_table.setItem(r, 4, cell(wt, right=True))
                vl = f"{t.totals_value:,.2f}" if t.totals_value else "—"
                self._trans_table.setItem(r, 5, cell(vl, right=True))
                status_txt = self._("status_active") if t.status == "active" else (t.status or "—")
                si = cell(status_txt)
                if t.status == "active":
                    si.setForeground(QColor("#2ECC71"))
                self._trans_table.setItem(r, 6, si)

        except Exception as e:
            print(f"Dashboard transactions error: {e}")

    # ─── refresh ──────────────────────────────────────────────────────────────

    def refresh_all_data(self):
        if hasattr(self, "_refresh_btn_ref"):
            self._refresh_btn_ref.setEnabled(False)
            self._refresh_btn_ref.setText(self._("refreshing"))

        self._set_update_time()
        stats = self._get_stats()
        self._cached_stats.update(stats)

        updates = {
            "total_transactions": stats["total_transactions"],
            "total_value":        stats["total_value"],
            "total_clients":      stats["total_clients"],
            "total_materials":    stats["total_materials"],
            "import_count":       stats["import_count"],
            "export_count":       stats["export_count"],
            "transit_count":      stats["transit_count"],
            "total_documents":    stats["total_documents"],
        }
        for key, val in updates.items():
            card = self._stat_cards.get(key)
            if card:
                card.update_value(val)

        # تحديث subtitles الديناميكية
        active_count = stats.get("active_transactions", 0)
        card = self._stat_cards.get("total_transactions")
        if card:
            card.update_subtitle(self._("active_transactions").format(count=active_count))

        self._load_activities()
        self._load_transactions()

        if hasattr(self, "_refresh_btn_ref"):
            self._refresh_btn_ref.setEnabled(True)
            self._refresh_btn_ref.setText(self._("refresh"))

        print(f"Dashboard refreshed at {datetime.now().strftime('%H:%M:%S')}")

    def _set_update_time(self):
        self._update_lbl.setText(
            f'{self._("last_update")} {datetime.now().strftime("%H:%M:%S")}'
        )

    def retranslate_ui(self):
        """يُستدعى عند تغيير اللغة — يُحدّث جميع نصوص الواجهة."""
        self._ = TranslationManager.get_instance().translate

        # Header
        self._title_lbl.setText(self._("dashboard_main_title"))
        self._refresh_btn_ref.setText(self._("refresh"))
        self._set_update_time()

        # Panel titles
        self._activities_title.setText(self._("recent_activities_title"))
        self._transactions_title.setText(self._("latest_transactions_title"))

        # Table headers
        self._trans_table.setHorizontalHeaderLabels([
            self._("col_number"), self._("transaction_date"), self._("col_type"),
            self._("col_client"), self._("col_weight_kg"), self._("col_value_usd"),
            self._("col_status"),
        ])

        # Stat card titles وsubtitles (بدون إعادة بناء البطاقات)
        stats = self._cached_stats
        all_defs = self._ROW1_DEFS + self._ROW2_DEFS
        for stat_key, title_key, sub_key, _, _ in all_defs:
            card = self._stat_cards.get(stat_key)
            if card:
                card.update_title(self._(title_key))
                card.update_subtitle(self._resolve_sub(sub_key, stats))

        # إعادة تحميل البيانات لترجمة المحتوى
        self._load_activities()
        self._load_transactions()

    def closeEvent(self, event):
        if hasattr(self, "_refresh_timer"):
            self._refresh_timer.stop()
        event.accept()