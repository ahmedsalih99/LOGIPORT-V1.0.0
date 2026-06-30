from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QGridLayout, QFileDialog, QMessageBox,
    QLineEdit, QSizePolicy, QProgressBar,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from ui.utils.font_utils import app_font, XS, SM, BODY, MD, BASE, LG, XL, XL2, XL3, XL4, HERO, LOGO

from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from core.permissions import is_admin as _is_admin
from database.db_utils import format_local_dt
from database.models import get_session_local, User, AuditLog, Transaction, Client, Material, Document
from sqlalchemy import func, desc
from datetime import datetime, timedelta

_DB_WARN_MB  = 80    # تحذير عند تجاوز 80 MB
_DB_MAX_MB   = 200   # الحد الأقصى للشريط
_BACKUP_WARN_DAYS = 7  # تحذير إذا آخر نسخة أقدم من 7 أيام


def _current_user():
    return SettingsManager.get_instance().get("user")


# ── _MiniStat ─────────────────────────────────────────────────────────────────

class _MiniStat(QFrame):
    def __init__(self, icon, label, value, color="#4A7EC8", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(6)

        top = QHBoxLayout()
        ico = QLabel(icon)
        ico.setFont(QFont("Segoe UI Emoji", 22))
        top.addWidget(ico)
        top.addStretch()
        lay.addLayout(top)

        self._val_lbl = QLabel(str(value))
        self._val_lbl.setFont(app_font(HERO, bold=True))
        self._val_lbl.setStyleSheet(f"color: {color}; background: transparent;")
        lay.addWidget(self._val_lbl)

        self._label_lbl = QLabel(label)
        self._label_lbl.setFont(app_font(BODY))
        self._label_lbl.setObjectName("text-muted")
        lay.addWidget(self._label_lbl)

    def update_value(self, v):
        self._val_lbl.setText(str(v))

    def update_label(self, label: str):
        self._label_lbl.setText(label)


# ── _ActivityChart — رسم بياني بـ QPainter ───────────────────────────────────

class _ChartCanvas(QWidget):
    """Widget داخلي يرسم الأعمدة بـ QPainter — بدون SVG، يتكيّف مع العرض."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list = []
        self._max_v: int = 1
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set_data(self, data: list):
        self._data  = data
        self._max_v = max((c for _, c in data), default=1) or 1
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont as QF
        if not self._data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W = self.width()
        H = self.height()
        pad_l, pad_r, pad_t, pad_b = 8, 8, 8, 22
        chart_w = W - pad_l - pad_r
        chart_h = H - pad_t - pad_b

        n   = len(self._data)
        gap = 2
        bar_w = max(3, (chart_w - gap * (n - 1)) // n)

        # baseline
        p.setPen(QPen(QColor("#DDDDDD"), 1))
        p.drawLine(pad_l, pad_t + chart_h, W - pad_r, pad_t + chart_h)

        label_font = QF()
        label_font.setPointSize(7)
        p.setFont(label_font)

        step = max(1, n // 8)   # عدد التسميات على المحور

        for i, (lbl, val) in enumerate(self._data):
            x  = pad_l + i * (bar_w + gap)
            bh = int(chart_h * val / self._max_v) if self._max_v else 0
            y  = pad_t + chart_h - bh

            color = QColor("#C9A84C") if val == self._max_v else QColor("#4A7EC8")
            color.setAlphaF(0.85)
            p.setBrush(QBrush(color))
            p.setPen(Qt.NoPen)
            if bh > 0:
                p.drawRoundedRect(x, y, bar_w, bh, 2, 2)

            # قيمة العمود فوقه
            if bh > 14 and val > 0:
                p.setPen(QColor("#555555"))
                p.drawText(x, y - 1, bar_w, 12, Qt.AlignCenter, str(val))

            # تسمية المحور
            if i % step == 0 or i == n - 1:
                p.setPen(QColor("#999999"))
                p.drawText(x - 4, pad_t + chart_h + 2, bar_w + 8, 18,
                           Qt.AlignCenter, lbl)

        p.end()


class _ActivityChart(QFrame):
    """إطار الرسم البياني مع header وعنوان."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(180)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 10)
        lay.setSpacing(8)

        top = QHBoxLayout()
        self._title_lbl = QLabel()
        self._title_lbl.setFont(app_font(LG, bold=True))
        top.addWidget(self._title_lbl)
        top.addStretch()
        self._range_lbl = QLabel()
        self._range_lbl.setFont(app_font(SM))
        self._range_lbl.setObjectName("text-muted")
        top.addWidget(self._range_lbl)
        lay.addLayout(top)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        self._canvas = _ChartCanvas()
        lay.addWidget(self._canvas, 1)

    def load(self, days_data: list, title: str, range_label: str):
        self._title_lbl.setText(title)
        self._range_lbl.setText(range_label)
        self._canvas.set_data(days_data if days_data else [])


# ── AdminDashboardTab ─────────────────────────────────────────────────────────

class AdminDashboardTab(QWidget):

    _CARD_KEYS   = ["users", "active_users", "transactions", "db_size",
                    "stat_clients", "stat_entries", "stat_materials", "stat_last_backup"]
    _CARD_ICONS  = ["👥", "✅", "📋", "💾", "🤝", "📥", "🧱", "🕐"]
    _CARD_COLORS = ["#4A7EC8", "#2ECC71", "#9B59B6", "#E67E22",
                    "#14B8A6", "#F59E0B", "#8B5CF6", "#6B7280"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate
        self.setObjectName("admin-dashboard-tab")
        self._stats: dict = {}
        self._audit_rows: list = []

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

        user = _current_user()
        if not _is_admin(user):
            warn = QLabel(self._("admin_only_warning"))
            warn.setObjectName("text-warning")
            warn.setFont(app_font(BODY))
            main.addWidget(warn)

        # [6] تنبيه النسخ الاحتياطية
        self._backup_warn_lbl = QLabel()
        self._backup_warn_lbl.setObjectName("text-warning")
        self._backup_warn_lbl.setFont(app_font(SM))
        self._backup_warn_lbl.setWordWrap(True)
        self._backup_warn_lbl.hide()
        main.addWidget(self._backup_warn_lbl)

        # [1] 8 بطاقات إحصائية (صفان)
        main.addLayout(self._build_stats_row())

        # [2] رسم بياني
        self._chart = _ActivityChart()
        main.addWidget(self._chart)

        # [5] شريط حجم DB
        main.addWidget(self._build_db_usage_bar())

        # audit + DB info
        row = QHBoxLayout()
        row.setSpacing(18)
        row.addWidget(self._build_audit_panel(), stretch=3)

        right_col = QVBoxLayout()
        right_col.setSpacing(14)
        right_col.addWidget(self._build_db_panel())
        # [4] جدول المستخدمين
        right_col.addWidget(self._build_users_panel())
        row.addLayout(right_col, stretch=2)

        main.addLayout(row, stretch=1)
        main.addWidget(self._build_backup_panel())
        main.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start(30000)

        QTimer.singleShot(0,   self._load_audit)
        QTimer.singleShot(50,  self._load_db_info)
        QTimer.singleShot(80,  self._load_health)
        QTimer.singleShot(100, self._load_chart)
        QTimer.singleShot(120, self._load_users_table)
        QTimer.singleShot(150, self._refresh_backup_list)
        QTimer.singleShot(170, self._check_backup_age)

    # ── builders ─────────────────────────────────────────────────────────────

    def _build_header(self) -> QFrame:
        f = QFrame()
        lay = QHBoxLayout(f)
        lay.setContentsMargins(0, 0, 0, 0)

        self._title_lbl = QLabel(self._("admin_dashboard_title"))
        self._title_lbl.setFont(app_font(XL4, bold=True))
        self._title_lbl.setObjectName("dashboard-title")
        lay.addWidget(self._title_lbl)
        lay.addStretch()

        self._ts_lbl = QLabel()
        self._ts_lbl.setObjectName("text-muted")
        self._ts_lbl.setFont(app_font(SM))
        self._set_ts()
        lay.addWidget(self._ts_lbl)

        self._refresh_btn = QPushButton(f"🔄 {self._('refresh')}")
        self._refresh_btn.setObjectName("btn-primary")
        self._refresh_btn.setMinimumHeight(34)
        self._refresh_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_btn.setFont(app_font(BODY))
        self._refresh_btn.clicked.connect(self._refresh_all)
        lay.addWidget(self._refresh_btn)
        return f

    def _build_stats_row(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        self._stats = self._query_stats()
        stat_values = {
            "users":          self._stats.get("users", 0),
            "active_users":   self._stats.get("active_users", 0),
            "transactions":   self._stats.get("transactions", 0),
            "db_size":        self._stats.get("db_size", "—"),
            "stat_clients":   self._stats.get("clients", 0),
            "stat_entries":   self._stats.get("entries", 0),
            "stat_materials": self._stats.get("materials", 0),
            "stat_last_backup": self._stats.get("last_backup", "—"),
        }

        self._stat_cards: dict = {}
        for i, key in enumerate(self._CARD_KEYS):
            card = _MiniStat(
                self._CARD_ICONS[i],
                self._(key),
                stat_values[key],
                self._CARD_COLORS[i],
            )
            self._stat_cards[key] = card
            grid.addWidget(card, i // 4, i % 4)

        return grid

    # [5] شريط حجم DB
    def _build_db_usage_bar(self) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        lay = QHBoxLayout(f)
        lay.setContentsMargins(18, 10, 18, 10)
        lay.setSpacing(12)

        self._db_usage_lbl = QLabel(self._("db_usage_label"))
        self._db_usage_lbl.setFont(app_font(SM, bold=True))
        self._db_usage_lbl.setFixedWidth(160)
        lay.addWidget(self._db_usage_lbl)

        self._db_progress = QProgressBar()
        self._db_progress.setRange(0, _DB_MAX_MB * 1024)
        self._db_progress.setValue(0)
        self._db_progress.setMinimumHeight(18)
        self._db_progress.setTextVisible(True)
        self._db_progress.setFormat("%v KB / %m KB")
        lay.addWidget(self._db_progress, 1)

        self._db_progress_lbl = QLabel("—")
        self._db_progress_lbl.setFont(app_font(SM))
        self._db_progress_lbl.setObjectName("text-muted")
        lay.addWidget(self._db_progress_lbl)

        return f

    def _build_audit_panel(self) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        top = QHBoxLayout()
        self._audit_title_lbl = QLabel(self._("audit_log_title"))
        self._audit_title_lbl.setFont(app_font(LG, bold=True))
        top.addWidget(self._audit_title_lbl)
        top.addStretch()

        self._audit_search = QLineEdit()
        self._audit_search.setObjectName("form-input")
        self._audit_search.setPlaceholderText(self._("search_placeholder"))
        self._audit_search.setMaximumWidth(180)
        self._audit_search.setMinimumHeight(32)
        self._audit_search.textChanged.connect(self._filter_audit)
        top.addWidget(self._audit_search)

        # [3] زر عرض الكل
        self._view_all_btn = QPushButton(self._("view_all_audit"))
        self._view_all_btn.setObjectName("topbar-btn")
        self._view_all_btn.setMinimumHeight(30)
        self._view_all_btn.setFont(app_font(SM))
        self._view_all_btn.setCursor(Qt.PointingHandCursor)
        self._view_all_btn.clicked.connect(self._open_audit_tab)
        top.addWidget(self._view_all_btn)

        lay.addLayout(top)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        self._audit_tbl = QTableWidget()
        self._audit_tbl.setObjectName("data-table")
        self._audit_tbl.setColumnCount(5)
        self._audit_tbl.setHorizontalHeaderLabels([
            self._("col_user"), self._("col_action"),
            self._("col_table"), self._("col_record"), self._("col_date"),
        ])
        self._audit_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._audit_tbl.verticalHeader().setVisible(False)
        self._audit_tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._audit_tbl.setAlternatingRowColors(True)
        self._audit_tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self._audit_tbl.setMaximumHeight(280)
        lay.addWidget(self._audit_tbl)
        return f

    def _build_db_panel(self) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        self._db_title_lbl = QLabel(self._("db_info_title"))
        self._db_title_lbl.setFont(app_font(LG, bold=True))
        lay.addWidget(self._db_title_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        self._db_info_container = QWidget()
        self._db_info_layout = QVBoxLayout(self._db_info_container)
        self._db_info_layout.setSpacing(8)
        self._db_info_layout.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._db_info_container)

        self._sys_title_lbl = QLabel(self._("system_status_title"))
        self._sys_title_lbl.setFont(app_font(BASE, weight=QFont.DemiBold))
        self._sys_title_lbl.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(self._sys_title_lbl)

        self._health_container = QWidget()
        self._health_layout = QVBoxLayout(self._health_container)
        self._health_layout.setSpacing(6)
        self._health_layout.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._health_container)

        lay.addStretch()
        return f

    # [4] جدول المستخدمين
    def _build_users_panel(self) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        self._users_title_lbl = QLabel(self._("active_users_title"))
        self._users_title_lbl.setFont(app_font(LG, bold=True))
        lay.addWidget(self._users_title_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        self._users_tbl = QTableWidget()
        self._users_tbl.setObjectName("data-table")
        self._users_tbl.setColumnCount(3)
        self._users_tbl.setHorizontalHeaderLabels([
            self._("col_user"),
            self._("col_last_activity"),
            self._("col_status"),
        ])
        self._users_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._users_tbl.verticalHeader().setVisible(False)
        self._users_tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self._users_tbl.setAlternatingRowColors(True)
        self._users_tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self._users_tbl.setMaximumHeight(200)
        lay.addWidget(self._users_tbl)
        return f

    def _build_backup_panel(self) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        self._backup_title_lbl = QLabel(self._("backups_title"))
        self._backup_title_lbl.setFont(app_font(LG, bold=True))
        lay.addWidget(self._backup_title_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._backup_btn = QPushButton(self._("backup_now_btn"))
        self._backup_btn.setObjectName("btn-primary")
        self._backup_btn.setMinimumHeight(38)
        self._backup_btn.setFont(app_font(BODY, weight=QFont.DemiBold))
        self._backup_btn.setCursor(Qt.PointingHandCursor)
        self._backup_btn.clicked.connect(self._do_backup)
        btn_row.addWidget(self._backup_btn)

        self._open_folder_btn = QPushButton(self._("open_backup_folder_btn"))
        self._open_folder_btn.setObjectName("topbar-btn")
        self._open_folder_btn.setMinimumHeight(38)
        self._open_folder_btn.setFont(app_font(BODY))
        self._open_folder_btn.setCursor(Qt.PointingHandCursor)
        self._open_folder_btn.clicked.connect(self._open_backup_folder)
        btn_row.addWidget(self._open_folder_btn)

        self._restore_btn = QPushButton(self._("restore_backup_btn"))
        self._restore_btn.setObjectName("btn-warning")
        self._restore_btn.setMinimumHeight(38)
        self._restore_btn.setFont(app_font(BODY))
        self._restore_btn.setCursor(Qt.PointingHandCursor)
        self._restore_btn.clicked.connect(self._do_restore)
        btn_row.addWidget(self._restore_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        self._backup_list_lbl = QLabel()
        self._backup_list_lbl.setFont(app_font(SM))
        self._backup_list_lbl.setObjectName("text-muted")
        self._backup_list_lbl.setWordWrap(True)
        lay.addWidget(self._backup_list_lbl)
        return f

    # ── data loaders ─────────────────────────────────────────────────────────

    def _query_stats(self) -> dict:
        s = {
            "users": 0, "active_users": 0, "transactions": 0,
            "clients": 0, "entries": 0, "materials": 0,
            "db_size": "—", "last_backup": "—",
        }
        try:
            from database.models.entry import Entry
            with get_session_local()() as session:
                s["users"]        = session.query(User).count()
                s["active_users"] = session.query(User).filter(User.is_active == True).count()
                s["transactions"] = session.query(Transaction).count()
                s["clients"]      = session.query(Client).count()
                s["entries"]      = session.query(Entry).count()
                s["materials"]    = session.query(Material).count()
            from services.backup_service import get_db_info, list_backups
            info = get_db_info()
            s["db_size"] = f"{info.get('size_kb', 0)} KB"
            bk = list_backups()
            if bk:
                ts = datetime.fromtimestamp(bk[0].stat().st_mtime)
                s["last_backup"] = ts.strftime("%m-%d %H:%M")
        except Exception:
            pass
        return s

    # [2] رسم بياني
    def _load_chart(self):
        try:
            from database.models.transaction import Transaction as Trx
            from sqlalchemy import cast, Date as SaDate
            today = datetime.now().date()
            start = today - timedelta(days=29)
            with get_session_local()() as s:
                rows = (
                    s.query(
                        func.date(Trx.transaction_date).label("d"),
                        func.count(Trx.id).label("c"),
                    )
                    .filter(Trx.transaction_date >= str(start))
                    .group_by(func.date(Trx.transaction_date))
                    .all()
                )
            counts = {str(r.d): r.c for r in rows}
            data = []
            for i in range(30):
                d = start + timedelta(days=i)
                label = d.strftime("%m/%d")
                data.append((label, counts.get(str(d), 0)))

            self._chart.load(
                data,
                self._("chart_title"),
                self._("chart_last_30"),
            )
        except Exception as e:
            self._chart._canvas.set_data([])

    # [4] جدول المستخدمين
    def _load_users_table(self):
        try:
            with get_session_local()() as s:
                users = (s.query(User)
                          .order_by(desc(User.updated_at))
                          .all())
            self._users_tbl.setRowCount(len(users))
            for ri, u in enumerate(users):
                name = getattr(u, "full_name", None) or getattr(u, "username", None) or "—"
                upd  = getattr(u, "updated_at", None)
                ts   = format_local_dt(upd, "%Y-%m-%d %H:%M") if upd else self._("no_activity")
                is_active = getattr(u, "is_active", False)
                status_txt = self._("user_active") if is_active else self._("user_inactive")
                status_col = "#2ECC71" if is_active else "#E74C3C"

                def _cell(txt, color=None):
                    item = QTableWidgetItem(str(txt))
                    item.setFont(app_font(SM))
                    item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    if color:
                        item.setForeground(QColor(color))
                    return item

                self._users_tbl.setItem(ri, 0, _cell(name))
                self._users_tbl.setItem(ri, 1, _cell(ts))
                self._users_tbl.setItem(ri, 2, _cell(status_txt, status_col))
        except Exception:
            pass

    def _load_audit(self):
        self._audit_tbl.setRowCount(0)

        _ACTION_TRANS_KEYS = {
            "create": "action_create", "insert": "action_insert",
            "update": "action_update", "delete": "action_delete",
            "import": "action_import", "export": "action_export",
            "print":  "action_print",
        }
        _ACTION_ICONS = {
            "create": "➕", "insert": "➕", "update": "✏️",
            "delete": "🗑️", "import": "📥", "export": "📤", "print": "🖨️",
        }
        _TABLE_TRANS_KEYS = {
            "transactions": "table_transactions", "materials": "table_materials",
            "clients":      "table_clients",      "users":    "table_users",
            "documents":    "table_documents",    "entries":  "table_entries",
        }
        try:
            from core.theme_manager import ThemeManager as _TM
            _tc = _TM.get_instance().current_theme.colors
        except Exception:
            _tc = {}
        COLOR_MAP = {
            "create": _tc.get("success", "#2ECC71"), "insert": _tc.get("success", "#2ECC71"),
            "update": _tc.get("warning", "#F39C12"), "delete": _tc.get("danger",  "#E74C3C"),
        }

        try:
            from sqlalchemy.orm import joinedload as jl
            with get_session_local()() as session:
                rows = (session.query(AuditLog)
                        .options(jl(AuditLog.user))
                        .order_by(desc(AuditLog.id))
                        .limit(50).all())

            self._audit_rows = []
            for row in rows:
                action = (row.action or "").lower()
                uname  = ""
                if row.user:
                    uname = (getattr(row.user, "full_name", None) or
                             getattr(row.user, "username", None) or "—")
                tbl_trans_key = _TABLE_TRANS_KEYS.get(row.table_name or "")
                tbl   = self._(tbl_trans_key) if tbl_trans_key else (row.table_name or "—")
                ak    = _ACTION_TRANS_KEYS.get(action)
                act_l = self._(ak) if ak else action
                icon  = _ACTION_ICONS.get(action, "")
                act   = f"{icon} {act_l}".strip() if icon else act_l
                ts    = format_local_dt(row.timestamp, "%Y-%m-%d %H:%M")
                rid   = str(row.record_id) if row.record_id else "—"
                color = COLOR_MAP.get(action, "#3498DB")
                self._audit_rows.append((uname, act, tbl, rid, ts, color))

            self._render_audit(self._audit_rows)
        except Exception as e:
            self._audit_rows = [("—", f"⚠️ {e}", "—", "—", "—", "#E74C3C")]
            self._render_audit(self._audit_rows)

    def _render_audit(self, rows):
        self._audit_tbl.setRowCount(len(rows))
        for r, (uname, act, tbl, rid, ts, color) in enumerate(rows):
            def cell(txt, c=None):
                i = QTableWidgetItem(txt)
                i.setFont(app_font(SM))
                i.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                if c:
                    i.setForeground(QColor(c))
                return i
            self._audit_tbl.setItem(r, 0, cell(uname))
            self._audit_tbl.setItem(r, 1, cell(act, color))
            self._audit_tbl.setItem(r, 2, cell(tbl))
            self._audit_tbl.setItem(r, 3, cell(rid))
            self._audit_tbl.setItem(r, 4, cell(ts))

    def _filter_audit(self, text: str):
        text = text.strip().lower()
        if not text:
            self._render_audit(self._audit_rows)
            return
        filtered = [r for r in self._audit_rows
                    if any(text in str(col).lower() for col in r[:5])]
        self._render_audit(filtered)

    def _load_db_info(self):
        while self._db_info_layout.count():
            w = self._db_info_layout.takeAt(0)
            if w.widget():
                w.widget().deleteLater()
        try:
            from services.backup_service import get_db_info
            info = get_db_info()
            items = [
                (self._("db_path"),          info.get("path", "—")),
                (self._("db_size_label"),     f"{info.get('size_kb', '—')} KB"),
                (self._("db_last_modified"),  info.get("last_modified", info.get("modified", "—"))),
                (self._("db_status"),
                 self._("db_available") if info.get("exists") else self._("db_not_found")),
            ]
            # [5] حدّث شريط التقدم
            size_kb = info.get("size_kb", 0) or 0
            self._db_progress.setValue(int(size_kb))
            self._db_progress.setFormat(f"{round(size_kb/1024, 1)} MB / {_DB_MAX_MB} MB")
            pct = size_kb / (_DB_MAX_MB * 1024)
            if pct >= 0.9:
                self._db_progress.setStyleSheet("QProgressBar::chunk { background: #E74C3C; }")
            elif pct >= 0.7:
                self._db_progress.setStyleSheet("QProgressBar::chunk { background: #F39C12; }")
            else:
                self._db_progress.setStyleSheet("")
            self._db_progress_lbl.setText(
                f"{round(size_kb / 1024, 1)} {self._('mb_unit')}"
            )
        except Exception as e:
            items = [(self._("error"), str(e))]

        for label, value in items:
            row = QWidget()
            rlay = QHBoxLayout(row)
            rlay.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label + ":")
            lbl.setFont(app_font(SM, weight=QFont.DemiBold))
            lbl.setFixedWidth(110)
            lbl.setObjectName("info-label")
            rlay.addWidget(lbl)
            val = QLabel(value)
            val.setFont(app_font(SM))
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            rlay.addWidget(val, 1)
            self._db_info_layout.addWidget(row)

    def _load_health(self):
        while self._health_layout.count():
            w = self._health_layout.takeAt(0)
            if w.widget():
                w.widget().deleteLater()
        from services.healthcheck import check_pdf_runtime
        try:
            report = check_pdf_runtime()
            checks = [("QtWebEngine (PDF)", report.qtwebengine)]
        except Exception:
            checks = [("PDF Runtime", False)]

        for name, ok in checks:
            row = QWidget()
            rlay = QHBoxLayout(row)
            rlay.setContentsMargins(0, 0, 0, 0)
            dot = QLabel("✅" if ok else "❌")
            dot.setFont(QFont("Segoe UI Emoji", 12))
            dot.setFixedWidth(28)
            rlay.addWidget(dot)
            lbl = QLabel(name)
            lbl.setFont(app_font(SM))
            lbl.setObjectName("text-success" if ok else "text-danger")
            rlay.addWidget(lbl, 1)
            self._health_layout.addWidget(row)

    def _refresh_backup_list(self):
        try:
            from services.backup_service import list_backups
            backups = list_backups()[:5]
            if backups:
                lines = [self._("recent_backups").format(count=len(backups))]
                for b in backups:
                    sz = round(b.stat().st_size / 1024, 1)
                    ts = datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    lines.append(f"  • {b.name}  ({sz} KB) — {ts}")
                self._backup_list_lbl.setText("\n".join(lines))
            else:
                self._backup_list_lbl.setText(self._("no_backups_available"))
        except Exception as e:
            self._backup_list_lbl.setText(f"⚠️ {e}")

    # [6] تنبيه عمر النسخة الاحتياطية
    def _check_backup_age(self):
        try:
            from services.backup_service import list_backups
            backups = list_backups()
            if not backups:
                self._backup_warn_lbl.setText(self._("backup_age_warning").format(days="∞"))
                self._backup_warn_lbl.show()
                return
            latest_mtime = datetime.fromtimestamp(backups[0].stat().st_mtime)
            age_days = (datetime.now() - latest_mtime).days
            if age_days >= _BACKUP_WARN_DAYS:
                self._backup_warn_lbl.setText(
                    self._("backup_age_warning").format(days=age_days)
                )
                self._backup_warn_lbl.show()
            else:
                ts = latest_mtime.strftime("%Y-%m-%d %H:%M")
                self._backup_warn_lbl.setText(self._("backup_ok").format(ts=ts))
                self._backup_warn_lbl.setObjectName("text-success")
                self._backup_warn_lbl.show()
        except Exception:
            self._backup_warn_lbl.hide()

    # [3] فتح تاب سجل العمليات
    def _open_audit_tab(self):
        try:
            from core.data_bus import DataBus
            DataBus.get_instance().publish("navigate_to", "audit_trail")
        except Exception:
            pass

    # ── actions ──────────────────────────────────────────────────────────────

    def _do_backup(self):
        try:
            self._backup_btn.setEnabled(False)
            self._backup_btn.setText(self._("backup_in_progress_btn"))
            from services.backup_service import backup as do_backup
            path = do_backup()
            sz = round(path.stat().st_size / 1024, 1)
            try:
                from services.notification_service import NotificationService
                NotificationService.get_instance().notify_backup(success=True, path=str(path))
            except Exception:
                pass
            QMessageBox.information(self, self._("backup_dialog_title"),
                self._("backup_success_detail") + f"\n\n📂  {path}\n💾  {sz} KB")
            self._refresh_backup_list()
            self._check_backup_age()
            QTimer.singleShot(200, self._refresh_stats)
        except Exception as e:
            try:
                from services.notification_service import NotificationService
                NotificationService.get_instance().notify_backup(success=False, error=str(e))
            except Exception:
                pass
            QMessageBox.critical(self, self._("error"), self._("backup_failed_msg") + f"\n{e}")
        finally:
            self._backup_btn.setEnabled(True)
            self._backup_btn.setText(self._("backup_now_btn"))

    def _open_backup_folder(self):
        try:
            from services.backup_service import _backup_dir
            d = _backup_dir()
            import subprocess, sys
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(d)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(d)])
            else:
                subprocess.Popen(["xdg-open", str(d)])
        except Exception as e:
            QMessageBox.warning(self, self._("warning"), self._("cannot_open_folder") + f"\n{e}")

    def _do_restore(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self._("select_backup_file"), "", "Database Files (*.db);;All Files (*)"
        )
        if not path:
            return
        reply = QMessageBox.warning(
            self, self._("restore_warning_title"),
            self._("restore_warning_msg").format(path=path),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            from services.backup_service import restore as do_restore
            dst = do_restore(path)
            QMessageBox.information(self, self._("success"),
                self._("restore_success_msg").format(path=dst))
        except Exception as e:
            QMessageBox.critical(self, self._("error"), self._("restore_failed_msg") + f"\n{e}")

    # ── refresh ──────────────────────────────────────────────────────────────

    def _refresh_stats(self):
        self._set_ts()
        s = self._query_stats()
        values = {
            "users":          s["users"],
            "active_users":   s["active_users"],
            "transactions":   s["transactions"],
            "db_size":        s["db_size"],
            "stat_clients":   s["clients"],
            "stat_entries":   s["entries"],
            "stat_materials": s["materials"],
            "stat_last_backup": s["last_backup"],
        }
        for key, val in values.items():
            card = self._stat_cards.get(key)
            if card:
                card.update_value(val)

    def _refresh_all(self):
        self._refresh_stats()
        self._load_audit()
        self._load_db_info()
        self._load_health()
        self._load_chart()
        self._load_users_table()
        self._refresh_backup_list()
        self._check_backup_age()

    def _set_ts(self):
        self._ts_lbl.setText(
            f"{self._('last_update')} {datetime.now().strftime('%H:%M:%S')}"
        )

    def retranslate_ui(self):
        self._title_lbl.setText(self._("admin_dashboard_title"))
        self._refresh_btn.setText(f"🔄 {self._('refresh')}")
        self._set_ts()

        for key, card in self._stat_cards.items():
            card.update_label(self._(key))

        self._audit_title_lbl.setText(self._("audit_log_title"))
        self._audit_search.setPlaceholderText(self._("search_placeholder"))
        self._view_all_btn.setText(self._("view_all_audit"))
        self._audit_tbl.setHorizontalHeaderLabels([
            self._("col_user"), self._("col_action"),
            self._("col_table"), self._("col_record"), self._("col_date"),
        ])
        self._load_audit()

        self._db_title_lbl.setText(self._("db_info_title"))
        self._sys_title_lbl.setText(self._("system_status_title"))
        self._db_usage_lbl.setText(self._("db_usage_label"))
        self._load_db_info()

        self._users_title_lbl.setText(self._("active_users_title"))
        self._users_tbl.setHorizontalHeaderLabels([
            self._("col_user"),
            self._("col_last_activity"),
            self._("col_status"),
        ])
        self._load_users_table()

        self._backup_title_lbl.setText(self._("backups_title"))
        self._backup_btn.setText(self._("backup_now_btn"))
        self._open_folder_btn.setText(self._("open_backup_folder_btn"))
        self._restore_btn.setText(self._("restore_backup_btn"))
        self._refresh_backup_list()

    def closeEvent(self, event):
        if hasattr(self, "_timer"):
            self._timer.stop()
        event.accept()