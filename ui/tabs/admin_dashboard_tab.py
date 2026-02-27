from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QGridLayout, QFileDialog, QMessageBox,
    QLineEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from core.permissions import is_admin as _is_admin
from database.db_utils import format_local_dt
from database.models import get_session_local, User, AuditLog, Transaction, Client, Material, Document
from sqlalchemy import func, desc
from datetime import datetime


# ── helpers ──────────────────────────────────────────────────────────────────

def _current_user():
    return SettingsManager.get_instance().get("user")


# ── StatCard ──────────────────────────────────────────────────────────────────

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
        self._val_lbl.setFont(QFont("Tajawal", 28, QFont.Bold))
        self._val_lbl.setStyleSheet(f"color: {color}; background: transparent;")
        lay.addWidget(self._val_lbl)

        self._label_lbl = QLabel(label)
        self._label_lbl.setFont(QFont("Tajawal", 10))
        self._label_lbl.setObjectName("text-muted")
        lay.addWidget(self._label_lbl)

    def update_value(self, v):
        self._val_lbl.setText(str(v))

    def update_label(self, label: str):
        self._label_lbl.setText(label)


# ── Main Tab ──────────────────────────────────────────────────────────────────

class AdminDashboardTab(QWidget):
    """لوحة تحكم الإدارة الكاملة."""

    # مفاتيح البطاقات الأربع — ثابتة ومستقلة عن اللغة
    _CARD_KEYS = ["users", "active_users", "transactions", "db_size"]
    _CARD_ICONS  = ["👥", "✅", "📋", "💾"]
    _CARD_COLORS = ["#4A7EC8", "#2ECC71", "#9B59B6", "#E67E22"]

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

        # header
        main.addWidget(self._build_header())

        # permission warning
        user = _current_user()
        if not _is_admin(user):
            warn = QLabel(self._("admin_only_warning"))
            warn.setStyleSheet("color: #F39C12; font-size: 11px; background: transparent;")
            warn.setFont(QFont("Tajawal", 10))
            main.addWidget(warn)

        # stat cards
        main.addLayout(self._build_stats_row())

        # content: audit log + DB info
        row = QHBoxLayout()
        row.setSpacing(18)
        row.addWidget(self._build_audit_panel(), stretch=3)
        row.addWidget(self._build_db_panel(), stretch=2)
        main.addLayout(row, stretch=1)

        # backup actions
        main.addWidget(self._build_backup_panel())

        main.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # auto-refresh
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start(30000)

    # ── builders ─────────────────────────────────────────────────────────────

    def _build_header(self) -> QFrame:
        f = QFrame()
        lay = QHBoxLayout(f)
        lay.setContentsMargins(0, 0, 0, 0)

        self._title_lbl = QLabel(self._("admin_dashboard_title"))
        self._title_lbl.setFont(QFont("Tajawal", 22, QFont.Bold))
        self._title_lbl.setObjectName("dashboard-title")
        lay.addWidget(self._title_lbl)
        lay.addStretch()

        self._ts_lbl = QLabel()
        self._ts_lbl.setObjectName("text-muted")
        self._ts_lbl.setFont(QFont("Tajawal", 9))
        self._set_ts()
        lay.addWidget(self._ts_lbl)

        self._refresh_btn = QPushButton(f"🔄 {self._('refresh')}")
        self._refresh_btn.setObjectName("btn-primary")
        self._refresh_btn.setMinimumHeight(34)
        self._refresh_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_btn.setFont(QFont("Tajawal", 10))
        self._refresh_btn.clicked.connect(self._refresh_all)
        lay.addWidget(self._refresh_btn)

        return f

    def _build_stats_row(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        self._stats = self._query_stats()
        s = self._stats

        # الربط بمفتاح ثابت (stat_key) بدل نص اللغة
        stat_values = {
            "users":        s.get("users", 0),
            "active_users": s.get("active_users", 0),
            "transactions": s.get("transactions", 0),
            "db_size":      s.get("db_size", "—"),
        }

        self._stat_cards: dict[str, _MiniStat] = {}   # key → card
        for i, key in enumerate(self._CARD_KEYS):
            card = _MiniStat(
                self._CARD_ICONS[i],
                self._(key),
                stat_values[key],
                self._CARD_COLORS[i],
            )
            self._stat_cards[key] = card      # ← الآن المفتاح ثابت دائماً
            grid.addWidget(card, 0, i)

        return grid

    def _build_audit_panel(self) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        top = QHBoxLayout()
        self._audit_title_lbl = QLabel(self._("audit_log_title"))
        self._audit_title_lbl.setFont(QFont("Tajawal", 13, QFont.Bold))
        top.addWidget(self._audit_title_lbl)
        top.addStretch()

        self._audit_search = QLineEdit()
        self._audit_search.setObjectName("form-input")
        self._audit_search.setPlaceholderText(self._("search_placeholder"))
        self._audit_search.setMaximumWidth(180)
        self._audit_search.setMinimumHeight(32)
        self._audit_search.textChanged.connect(self._filter_audit)
        top.addWidget(self._audit_search)

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

        self._load_audit()
        lay.addWidget(self._audit_tbl)

        return f

    def _build_db_panel(self) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        self._db_title_lbl = QLabel(self._("db_info_title"))
        self._db_title_lbl.setFont(QFont("Tajawal", 13, QFont.Bold))
        lay.addWidget(self._db_title_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        lay.addWidget(sep)

        self._db_info_container = QWidget()
        self._db_info_layout = QVBoxLayout(self._db_info_container)
        self._db_info_layout.setSpacing(8)
        self._db_info_layout.setContentsMargins(0, 0, 0, 0)
        self._load_db_info()
        lay.addWidget(self._db_info_container)

        self._sys_title_lbl = QLabel(self._("system_status_title"))
        self._sys_title_lbl.setFont(QFont("Tajawal", 12, QFont.DemiBold))
        self._sys_title_lbl.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(self._sys_title_lbl)

        self._health_container = QWidget()
        self._health_layout = QVBoxLayout(self._health_container)
        self._health_layout.setSpacing(6)
        self._health_layout.setContentsMargins(0, 0, 0, 0)
        self._load_health()
        lay.addWidget(self._health_container)

        lay.addStretch()
        return f

    def _build_backup_panel(self) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        self._backup_title_lbl = QLabel(self._("backups_title"))
        self._backup_title_lbl.setFont(QFont("Tajawal", 13, QFont.Bold))
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
        self._backup_btn.setFont(QFont("Tajawal", 10, QFont.DemiBold))
        self._backup_btn.setCursor(Qt.PointingHandCursor)
        self._backup_btn.clicked.connect(self._do_backup)
        btn_row.addWidget(self._backup_btn)

        self._open_folder_btn = QPushButton(self._("open_backup_folder_btn"))
        self._open_folder_btn.setObjectName("topbar-btn")
        self._open_folder_btn.setMinimumHeight(38)
        self._open_folder_btn.setFont(QFont("Tajawal", 10))
        self._open_folder_btn.setCursor(Qt.PointingHandCursor)
        self._open_folder_btn.clicked.connect(self._open_backup_folder)
        btn_row.addWidget(self._open_folder_btn)

        self._restore_btn = QPushButton(self._("restore_backup_btn"))
        self._restore_btn.setObjectName("btn-warning")
        self._restore_btn.setMinimumHeight(38)
        self._restore_btn.setFont(QFont("Tajawal", 10))
        self._restore_btn.setCursor(Qt.PointingHandCursor)
        self._restore_btn.clicked.connect(self._do_restore)
        btn_row.addWidget(self._restore_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        self._backup_list_lbl = QLabel()
        self._backup_list_lbl.setFont(QFont("Tajawal", 9))
        self._backup_list_lbl.setObjectName("text-muted")
        self._backup_list_lbl.setWordWrap(True)
        self._refresh_backup_list()
        lay.addWidget(self._backup_list_lbl)

        return f

    # ── data loaders ─────────────────────────────────────────────────────────

    def _query_stats(self) -> dict:
        s = {"users": 0, "active_users": 0, "transactions": 0, "db_size": "—"}
        try:
            with get_session_local()() as session:
                s["users"]        = session.query(User).count()
                s["active_users"] = session.query(User).filter(User.is_active == True).count()
                s["transactions"] = session.query(Transaction).count()
            from services.backup_service import get_db_info
            info = get_db_info()
            s["db_size"] = f"{info.get('size_kb', 0)} KB"
        except Exception:
            pass
        return s

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
        COLOR_MAP = {
            "create": "#2ECC71", "insert": "#2ECC71",
            "update": "#F39C12", "delete": "#E74C3C",
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
                tbl    = self._(tbl_trans_key) if tbl_trans_key else (row.table_name or "—")
                act_trans_key = _ACTION_TRANS_KEYS.get(action)
                act_label = self._(act_trans_key) if act_trans_key else action
                act_icon  = _ACTION_ICONS.get(action, "")
                act    = f"{act_icon} {act_label}".strip() if act_icon else act_label
                ts     = format_local_dt(row.timestamp, "%Y-%m-%d %H:%M")
                rid    = str(row.record_id) if row.record_id else "—"
                color  = COLOR_MAP.get(action, "#3498DB")

                self._audit_rows.append((uname, act, tbl, rid, ts, color))

            self._render_audit(self._audit_rows)

        except Exception as e:
            err_row = ("—", f"⚠️ {e}", "—", "—", "—", "#E74C3C")
            self._audit_rows = [err_row]
            self._render_audit(self._audit_rows)

    def _render_audit(self, rows):
        self._audit_tbl.setRowCount(len(rows))
        for r, (uname, act, tbl, rid, ts, color) in enumerate(rows):
            def cell(txt, c=None):
                i = QTableWidgetItem(txt)
                i.setFont(QFont("Tajawal", 9))
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
            if w.widget(): w.widget().deleteLater()

        try:
            from services.backup_service import get_db_info
            info = get_db_info()
            items = [
                (self._("db_path"),          info.get("path", "—")),
                (self._("db_size_label"),    f"{info.get('size_kb', '—')} KB"),
                (self._("db_last_modified"), info.get("modified", "—")),
                (self._("db_status"),        self._("db_available") if info.get("exists") else self._("db_not_found")),
            ]
        except Exception as e:
            items = [(self._("error"), str(e))]

        for label, value in items:
            row = QWidget()
            rlay = QHBoxLayout(row)
            rlay.setContentsMargins(0, 0, 0, 0)

            lbl = QLabel(label + ":")
            lbl.setFont(QFont("Tajawal", 9, QFont.DemiBold))
            lbl.setFixedWidth(110)
            lbl.setObjectName("info-label")
            rlay.addWidget(lbl)

            val = QLabel(value)
            val.setFont(QFont("Tajawal", 9))
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            rlay.addWidget(val, 1)

            self._db_info_layout.addWidget(row)

    def _load_health(self):
        while self._health_layout.count():
            w = self._health_layout.takeAt(0)
            if w.widget(): w.widget().deleteLater()

        # أسماء المكتبات تقنية وليست واجهة مستخدم — لا تُترجم
        from services.healthcheck import check_pdf_runtime
        try:
            report = check_pdf_runtime()
            checks = [
                ("WeasyPrint (PDF)", report.weasyprint_stack),
                ("Cairo",            report.cairo),
                ("Pango",            report.pango),
                ("GDK Pixbuf",       report.gdk_pixbuf),
            ]
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
            lbl.setFont(QFont("Tajawal", 9))
            lbl.setStyleSheet(f"color: {'#2ECC71' if ok else '#E74C3C'}; background:transparent;")
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

    # ── actions ──────────────────────────────────────────────────────────────

    def _do_backup(self):
        try:
            self._backup_btn.setEnabled(False)
            self._backup_btn.setText(self._("backup_in_progress_btn"))
            from services.backup_service import backup as do_backup
            path = do_backup()
            sz = round(path.stat().st_size / 1024, 1)

            from services.notification_service import NotificationService
            NotificationService.get_instance().add_manual(
                self._("backup_success_msg").format(size=sz), level="success", icon="💾"
            )

            QMessageBox.information(self, self._("backup_dialog_title"),
                self._("backup_success_detail") + f"\n\n📂  {path}\n💾  {sz} KB")
            self._refresh_backup_list()
            self._refresh_stats()

        except Exception as e:
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
        # فلتر الملفات: النص التقني لـ Qt — لا يُترجم لأنه معيار نظام الملفات
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
        # البحث بالمفتاح الثابت (key) لا بنص اللغة
        values = {
            "users":        s["users"],
            "active_users": s["active_users"],
            "transactions": s["transactions"],
            "db_size":      s["db_size"],
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
        self._refresh_backup_list()

    def _set_ts(self):
        self._ts_lbl.setText(
            f"{self._('last_update')} {datetime.now().strftime('%H:%M:%S')}"
        )

    def retranslate_ui(self):
        """يُستدعى عند تغيير اللغة لتحديث جميع نصوص الواجهة."""
        # Header
        self._title_lbl.setText(self._("admin_dashboard_title"))
        self._refresh_btn.setText(f"🔄 {self._('refresh')}")
        self._set_ts()

        # Stat cards — نحدّث التسمية فقط، القيمة تبقى كما هي
        for key, card in self._stat_cards.items():
            card.update_label(self._(key))

        # Audit panel
        self._audit_title_lbl.setText(self._("audit_log_title"))
        self._audit_search.setPlaceholderText(self._("search_placeholder"))
        self._audit_tbl.setHorizontalHeaderLabels([
            self._("col_user"), self._("col_action"),
            self._("col_table"), self._("col_record"), self._("col_date"),
        ])
        # أعد تحميل صفوف الـ audit لترجمة أسماء الجداول والأحداث
        self._load_audit()

        # DB panel
        self._db_title_lbl.setText(self._("db_info_title"))
        self._sys_title_lbl.setText(self._("system_status_title"))
        self._load_db_info()

        # Backup panel
        self._backup_title_lbl.setText(self._("backups_title"))
        self._backup_btn.setText(self._("backup_now_btn"))
        self._open_folder_btn.setText(self._("open_backup_folder_btn"))
        self._restore_btn.setText(self._("restore_backup_btn"))
        self._refresh_backup_list()

    def closeEvent(self, event):
        if hasattr(self, "_timer"):
            self._timer.stop()
        event.accept()