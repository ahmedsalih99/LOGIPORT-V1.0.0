"""
UserProfileTab - LOGIPORT
==========================
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QMessageBox, QScrollArea, QGridLayout,
    QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.settings_manager import SettingsManager
from core.translator import TranslationManager
from database.db_utils import format_local_dt
from database.models import get_session_local, AuditLog, Transaction
from sqlalchemy import func, desc


def _current_user():
    return SettingsManager.get_instance().get("user")


class _SectionFrame(QFrame):
    """بطاقة قسم مع عنوان."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(12)

        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(QFont("Tajawal", 13, QFont.Bold))
        self._title_lbl.setObjectName("section-title-lbl")
        outer.addWidget(self._title_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        outer.addWidget(sep)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        outer.addWidget(self.content)

    def set_title(self, title: str):
        self._title_lbl.setText(title)


class _InfoRow(QWidget):
    def __init__(self, label: str, value: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label + ":")
        lbl.setFont(QFont("Tajawal", 10, QFont.DemiBold))
        lbl.setObjectName("info-label")
        lbl.setFixedWidth(140)
        lay.addWidget(lbl)

        val = QLabel(value or "—")
        val.setFont(QFont("Tajawal", 10))
        val.setObjectName("info-value")
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(val, 1)


class _StatMini(QFrame):
    def __init__(self, icon, value, label, color, parent=None):
        super().__init__(parent)
        self.setObjectName("stat-mini")
        self.setStyleSheet(f"""
            QFrame#stat-mini {{
                background: {color};
                border-radius: 10px;
                min-width: 110px;
                min-height: 80px;
            }}
            QLabel {{ background: transparent; color: white; }}
        """)
        lay = QVBoxLayout(self)
        lay.setSpacing(4)
        lay.setContentsMargins(14, 12, 14, 12)

        ico = QLabel(icon)
        ico.setFont(QFont("Segoe UI Emoji", 20))
        ico.setAlignment(Qt.AlignCenter)
        lay.addWidget(ico)

        self._val_lbl = QLabel(str(value))
        self._val_lbl.setFont(QFont("Tajawal", 22, QFont.Bold))
        self._val_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._val_lbl)

        self._label_lbl = QLabel(label)
        self._label_lbl.setFont(QFont("Tajawal", 9))
        self._label_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._label_lbl)

    def set_label(self, label: str):
        self._label_lbl.setText(label)


class UserProfileTab(QWidget):
    logout_requested = Signal()
    close_requested  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tm = TranslationManager.get_instance()
        self._ = self._tm.translate
        self.setObjectName("user-profile-tab")
        self._tm.language_changed.connect(self.retranslate_ui)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setObjectName("profile-container")

        main = QVBoxLayout(container)
        main.setContentsMargins(32, 28, 32, 28)
        main.setSpacing(22)

        main.addWidget(self._build_hero())
        main.addWidget(self._build_stats())
        main.addWidget(self._build_info())
        main.addWidget(self._build_password())
        main.addWidget(self._build_activity())
        main.addWidget(self._build_actions())
        main.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ─── builders ────────────────────────────────────────────────────────────

    def _build_hero(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("profile-hero")
        frame.setStyleSheet("""
            QFrame#profile-hero {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4A7EC8, stop:1 #2C5AA0
                );
                border-radius: 16px;
                min-height: 120px;
            }
            QLabel { background: transparent; color: white; }
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(20)

        user = _current_user()

        avatar = QLabel("👤")
        avatar.setFont(QFont("Segoe UI Emoji", 36))
        avatar.setFixedSize(80, 80)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            background: rgba(255,255,255,0.2);
            border-radius: 40px;
            border: 2px solid rgba(255,255,255,0.4);
        """)
        lay.addWidget(avatar)

        col = QVBoxLayout()
        col.setSpacing(4)

        display  = "—"
        role_txt = "—"
        if user:
            display  = getattr(user, "full_name", None) or getattr(user, "username", None) or "—"
            role     = getattr(user, "role", None)
            role_txt = getattr(role, "name", "—") if role else "—"

        self._hero_name_lbl = QLabel(display)
        self._hero_name_lbl.setFont(QFont("Tajawal", 22, QFont.Bold))
        col.addWidget(self._hero_name_lbl)

        self._hero_role_lbl = QLabel(self._("user_role").format(role=role_txt))
        self._hero_role_lbl.setFont(QFont("Tajawal", 11))
        self._hero_role_lbl.setStyleSheet("color: rgba(255,255,255,0.85); background: transparent;")
        col.addWidget(self._hero_role_lbl)

        lay.addLayout(col, 1)

        self._hero_badge = QLabel(self._("user_online"))
        self._hero_badge.setFont(QFont("Tajawal", 10, QFont.DemiBold))
        self._hero_badge.setStyleSheet("""
            color: #2ECC71;
            background: rgba(0,0,0,0.25);
            border-radius: 12px;
            padding: 4px 12px;
        """)
        lay.addWidget(self._hero_badge, 0, Qt.AlignTop)

        return frame

    def _build_stats(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        self._stats_title_lbl = QLabel(self._("my_stats_title"))
        self._stats_title_lbl.setFont(QFont("Tajawal", 13, QFont.Bold))
        lay.addWidget(self._stats_title_lbl)

        user = _current_user()
        uid  = getattr(user, "id", None)
        total_actions = today_actions = total_trans = 0

        try:
            from datetime import date
            with get_session_local()() as session:
                total_actions = session.query(AuditLog).filter(AuditLog.user_id == uid).count()
                today_actions = (session.query(AuditLog)
                                 .filter(AuditLog.user_id == uid,
                                         func.date(AuditLog.timestamp) == date.today()).count())
                total_trans   = session.query(Transaction).count()
        except Exception:
            pass

        grid = QHBoxLayout()
        grid.setSpacing(12)

        self._stat_total  = _StatMini("📋", total_actions, self._("total_operations"), "#4A7EC8")
        self._stat_today  = _StatMini("📅", today_actions, self._("today_operations"),  "#2ECC71")
        self._stat_trans  = _StatMini("📦", total_trans,   self._("transactions"),      "#9B59B6")

        for w in [self._stat_total, self._stat_today, self._stat_trans]:
            grid.addWidget(w)
        grid.addStretch()
        lay.addLayout(grid)

        return frame

    def _build_info(self) -> QFrame:
        self._info_sec = _SectionFrame(self._("personal_info_title"))
        self._populate_info()
        return self._info_sec

    def _populate_info(self):
        """يملأ (أو يعيد ملء) قسم المعلومات الشخصية."""
        # حذف المحتوى القديم
        while self._info_sec.content_layout.count():
            w = self._info_sec.content_layout.takeAt(0)
            if w.widget():
                w.widget().deleteLater()

        user = _current_user()
        if user:
            role       = getattr(user, "role", None)
            role_name  = getattr(role, "name", "—") if role else "—"
            created    = getattr(user, "created_at", None)
            created_str = format_local_dt(created, "%Y-%m-%d")
            status     = self._("user_status_active") if getattr(user, "is_active", True) else self._("user_status_suspended")
            rows = [
                (self._("username"),   getattr(user, "username",  "—")),
                (self._("full_name"),  getattr(user, "full_name", "—")),
                (self._("role"),       role_name),
                (self._("status"),     status),
                (self._("created_at"), created_str),
            ]
        else:
            rows = [(self._("username"), "—")]

        for label, value in rows:
            self._info_sec.content_layout.addWidget(_InfoRow(label, value))

    def _build_password(self) -> QFrame:
        self._pw_sec = _SectionFrame(self._("change_password_title"))

        def make_field(ph):
            f = QLineEdit()
            f.setEchoMode(QLineEdit.Password)
            f.setPlaceholderText(ph)
            f.setObjectName("form-input")
            f.setMinimumHeight(38)
            return f

        self._old_pw  = make_field(self._("current_password"))
        self._new_pw  = make_field(self._("new_password"))
        self._conf_pw = make_field(self._("confirm_password"))

        for w in [self._old_pw, self._new_pw, self._conf_pw]:
            self._pw_sec.content_layout.addWidget(w)

        self._save_pw_btn = QPushButton(self._("save_password_btn"))
        self._save_pw_btn.setObjectName("btn-primary")
        self._save_pw_btn.setMinimumHeight(38)
        self._save_pw_btn.setCursor(Qt.PointingHandCursor)
        self._save_pw_btn.setFont(QFont("Tajawal", 10, QFont.DemiBold))
        self._save_pw_btn.clicked.connect(self._change_password)
        self._pw_sec.content_layout.addWidget(self._save_pw_btn)

        return self._pw_sec

    def _build_activity(self) -> QFrame:
        self._act_sec = _SectionFrame(self._("recent_activities_mine"))
        self._populate_activity()
        return self._act_sec

    def _populate_activity(self):
        """يملأ (أو يعيد ملء) قسم الأنشطة الأخيرة."""
        while self._act_sec.content_layout.count():
            w = self._act_sec.content_layout.takeAt(0)
            if w.widget():
                w.widget().deleteLater()

        user = _current_user()
        uid  = getattr(user, "id", None)

        TABLE_KEYS = {
            "transactions": "table_transactions", "materials": "table_materials",
            "clients": "table_clients", "users": "table_users",
            "documents": "table_documents", "entries": "table_entries",
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
            with get_session_local()() as session:
                rows = (session.query(AuditLog)
                        .filter(AuditLog.user_id == uid)
                        .order_by(desc(AuditLog.id))
                        .limit(8).all())

            if not rows:
                empty = QLabel(self._("no_activity_yet"))
                empty.setAlignment(Qt.AlignCenter)
                empty.setStyleSheet("color: #9CA3AF; padding: 12px;")
                self._act_sec.content_layout.addWidget(empty)
                return

            for row in rows:
                action   = (row.action or "update").lower()
                icon, color = ICONS.get(action, ("📝", "#3498DB"))
                tbl_key  = TABLE_KEYS.get(row.table_name)
                tbl      = self._(tbl_key) if tbl_key else (row.table_name or "—")
                act_key  = ACTION_KEYS.get(action)
                act      = self._(act_key) if act_key else action
                ts       = format_local_dt(row.timestamp, "%Y-%m-%d %H:%M")

                item = QFrame()
                item.setStyleSheet(f"""
                    QFrame {{
                        background: rgba(0,0,0,0.03);
                        border-radius: 8px;
                        border-right: 3px solid {color};
                    }}
                """)
                row_lay = QHBoxLayout(item)
                row_lay.setContentsMargins(10, 6, 10, 6)

                ico = QLabel(icon)
                ico.setFont(QFont("Segoe UI Emoji", 14))
                ico.setFixedWidth(24)
                row_lay.addWidget(ico)

                msg = QLabel(self._("activity_in").format(action=act, table=tbl))
                msg.setFont(QFont("Tajawal", 10))
                row_lay.addWidget(msg, 1)

                ts_lbl = QLabel(ts)
                ts_lbl.setFont(QFont("Tajawal", 8))
                ts_lbl.setStyleSheet("color: #9CA3AF;")
                row_lay.addWidget(ts_lbl)

                self._act_sec.content_layout.addWidget(item)

        except Exception as e:
            err = QLabel(f"⚠️ {e}")
            err.setStyleSheet("color: #E74C3C;")
            self._act_sec.content_layout.addWidget(err)

    def _build_actions(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(16)

        self._logout_btn = QPushButton(self._("logout_btn"))
        self._logout_btn.setObjectName("btn-warning")
        self._logout_btn.setMinimumSize(160, 42)
        self._logout_btn.setFont(QFont("Tajawal", 11, QFont.DemiBold))
        self._logout_btn.setCursor(Qt.PointingHandCursor)
        self._logout_btn.clicked.connect(self._confirm_logout)

        self._close_btn = QPushButton(self._("close_app_btn"))
        self._close_btn.setObjectName("btn-danger")
        self._close_btn.setMinimumSize(160, 42)
        self._close_btn.setFont(QFont("Tajawal", 11, QFont.DemiBold))
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.clicked.connect(self._confirm_close)

        lay.addWidget(self._logout_btn)
        lay.addWidget(self._close_btn)
        lay.addStretch()

        return frame

    # ─── handlers ────────────────────────────────────────────────────────────

    def _change_password(self):
        old  = self._old_pw.text().strip()
        new  = self._new_pw.text().strip()
        conf = self._conf_pw.text().strip()

        if not old or not new or not conf:
            QMessageBox.warning(self, self._("warning"), self._("fill_all_password_fields"))
            return
        if new != conf:
            QMessageBox.warning(self, self._("warning"), self._("passwords_dont_match"))
            return
        if len(new) < 6:
            QMessageBox.warning(self, self._("warning"), self._("password_too_short"))
            return

        user = _current_user()
        if not user:
            QMessageBox.critical(self, self._("error"), self._("no_user_logged_in"))
            return

        try:
            from passlib.hash import bcrypt
            if not bcrypt.verify(old, user.password):
                QMessageBox.warning(self, self._("error"), self._("wrong_password"))
                return

            new_hash = bcrypt.hash(new)
            with get_session_local()() as session:
                db_user = session.get(type(user), user.id)
                if db_user:
                    db_user.password = new_hash
                    session.commit()

            self._old_pw.clear()
            self._new_pw.clear()
            self._conf_pw.clear()

            from services.notification_service import NotificationService
            NotificationService.get_instance().add_manual(
                self._("password_changed_success"), level="success", icon="🔒"
            )
            QMessageBox.information(self, self._("success"), self._("password_change_success_dialog"))

        except Exception as e:
            QMessageBox.critical(self, self._("error"), self._("password_change_failed") + f"\n{e}")

    def _confirm_logout(self):
        reply = QMessageBox.question(
            self, self._("logout_confirm_title"), self._("logout_confirm_msg"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.logout_requested.emit()

    def _confirm_close(self):
        reply = QMessageBox.question(
            self, self._("close_app_title"), self._("close_app_msg"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close_requested.emit()

    # ─── retranslate ─────────────────────────────────────────────────────────

    def retranslate_ui(self):
        """يُستدعى عند تغيير اللغة — يُحدّث جميع نصوص الواجهة."""
        self._ = TranslationManager.get_instance().translate

        user = _current_user()
        role_txt = "—"
        if user:
            role = getattr(user, "role", None)
            role_txt = getattr(role, "name", "—") if role else "—"

        # Hero
        self._hero_role_lbl.setText(self._("user_role").format(role=role_txt))
        self._hero_badge.setText(self._("user_online"))

        # Stats section title + card labels
        self._stats_title_lbl.setText(self._("my_stats_title"))
        self._stat_total.set_label(self._("total_operations"))
        self._stat_today.set_label(self._("today_operations"))
        self._stat_trans.set_label(self._("transactions"))

        # Info section
        self._info_sec.set_title(self._("personal_info_title"))
        self._populate_info()

        # Password section
        self._pw_sec.set_title(self._("change_password_title"))
        self._old_pw.setPlaceholderText(self._("current_password"))
        self._new_pw.setPlaceholderText(self._("new_password"))
        self._conf_pw.setPlaceholderText(self._("confirm_password"))
        self._save_pw_btn.setText(self._("save_password_btn"))

        # Activity section
        self._act_sec.set_title(self._("recent_activities_mine"))
        self._populate_activity()

        # Action buttons
        self._logout_btn.setText(self._("logout_btn"))
        self._close_btn.setText(self._("close_app_btn"))