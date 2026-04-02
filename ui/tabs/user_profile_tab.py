"""
ui/tabs/user_profile_tab.py — LOGIPORT
========================================
صفحة معلومات المستخدم — النسخة المطوّرة.

الأقسام:
  1. Hero   — صورة + اسم + دور + مكتب + badge online
  2. Stats  — إجمالي العمليات / اليوم / المعاملات
  3. Info   — معلومات الحساب (display-only)
  4. Edit   — تعديل الاسم الكامل (inline)
  5. Password — تغيير كلمة المرور
  6. Activity — آخر 10 أنشطة مع timeline مرئي
  7. Actions  — تسجيل خروج / إغلاق
"""
from __future__ import annotations

import os
import shutil
from datetime import date

from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QPixmap, QPainter, QBrush, QColor, QPainterPath, QLinearGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QMessageBox, QScrollArea, QSizePolicy,
    QFileDialog, QGraphicsOpacityEffect, QSpacerItem,
)

from core.settings_manager import SettingsManager
from core.translator import TranslationManager
from database.db_utils import format_local_dt
from database.models import get_session_local, AuditLog, Transaction
from sqlalchemy import func, desc


def _current_user():
    return SettingsManager.get_instance().get("user")


def _theme_colors():
    try:
        from core.settings_manager import SettingsManager
        from config.themes.semantic_colors import SemanticColors
        theme_name = SettingsManager.get_instance().get("theme", "light")
        c = SemanticColors.get(theme_name)
        return {
            "primary":    c.get("primary",        "#2563EB"),
            "primary_d":  c.get("primary_active",  "#1D4ED8"),
            "bg":         c.get("background",      "#F8FAFC"),
            "surface":    c.get("surface",         "#FFFFFF"),
            "border":     c.get("border",          "#E2E8F0"),
            "text":       c.get("text_primary",    "#1E293B"),
            "muted":      c.get("text_secondary",  "#64748B"),
            "success":    c.get("success",         "#10B981"),
            "danger":     c.get("danger",          "#EF4444"),
            "warning":    c.get("warning",         "#F59E0B"),
        }
    except Exception:
        return {
            "primary": "#2563EB", "primary_d": "#1D4ED8",
            "bg": "#F8FAFC", "surface": "#FFFFFF",
            "border": "#E2E8F0", "text": "#1E293B",
            "muted": "#64748B", "success": "#10B981",
            "danger": "#EF4444", "warning": "#F59E0B",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

class _Card(QFrame):
    """بطاقة موحّدة مع عنوان اختياري."""
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        if title:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            self._title_lbl = QLabel(title)
            self._title_lbl.setObjectName("card-title")
            f = QFont()
            f.setPointSize(12)
            f.setBold(True)
            self._title_lbl.setFont(f)
            row.addWidget(self._title_lbl)
            row.addStretch()
            lay.addLayout(row)

            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setObjectName("separator")
            lay.addWidget(sep)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(10)
        lay.addLayout(self.body)

    def set_title(self, t: str):
        if hasattr(self, "_title_lbl"):
            self._title_lbl.setText(t)


class _StatCard(QFrame):
    """بطاقة إحصائية صغيرة."""
    def __init__(self, value: str, label: str, accent: str, parent=None):
        super().__init__(parent)
        self.setObjectName("stat-card")
        self._accent = accent
        self._apply_style()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)

        self._val = QLabel(str(value))
        f = QFont()
        f.setPointSize(24)
        f.setBold(True)
        self._val.setFont(f)
        self._val.setStyleSheet(f"color: {accent}; background: transparent;")
        self._val.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._val)

        self._lbl = QLabel(label)
        f2 = QFont()
        f2.setPointSize(9)
        self._lbl.setFont(f2)
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setObjectName("text-muted")
        lay.addWidget(self._lbl)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#stat-card {{
                border: 1px solid transparent;
                border-top: 3px solid {self._accent};
                border-radius: 10px;
                min-width: 120px;
            }}
        """)

    def set_label(self, t: str):
        self._lbl.setText(t)

    def set_value(self, v: str):
        self._val.setText(str(v))


class _Field(QLineEdit):
    def __init__(self, placeholder="", password=False, parent=None):
        super().__init__(parent)
        self.setObjectName("form-input")
        self.setMinimumHeight(40)
        self.setPlaceholderText(placeholder)
        if password:
            self.setEchoMode(QLineEdit.Password)


class _Btn(QPushButton):
    def __init__(self, text: str, style: str = "primary", parent=None):
        super().__init__(text, parent)
        obj = {"primary": "primary-btn", "danger": "danger-btn",
               "secondary": "secondary-btn", "warning": "warning-btn"}.get(style, "primary-btn")
        self.setObjectName(obj)
        self.setMinimumHeight(40)
        self.setCursor(Qt.PointingHandCursor)


class _InfoRow(QWidget):
    def __init__(self, label: str, value: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)

        lbl = QLabel(label)
        lbl.setObjectName("text-muted")
        f = QFont()
        f.setPointSize(10)
        lbl.setFont(f)
        lbl.setFixedWidth(130)
        lay.addWidget(lbl)

        sep = QLabel("·")
        sep.setObjectName("text-muted")
        sep.setFixedWidth(16)
        sep.setAlignment(Qt.AlignCenter)
        lay.addWidget(sep)

        val = QLabel(value or "—")
        f2 = QFont()
        f2.setPointSize(10)
        f2.setBold(True)
        val.setFont(f2)
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(val, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Avatar Widget
# ─────────────────────────────────────────────────────────────────────────────

class _AvatarWidget(QLabel):
    clicked = Signal()

    def __init__(self, size=90, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setAlignment(Qt.AlignCenter)

    def mousePressEvent(self, e):
        self.clicked.emit()

    def set_image(self, path: str | None):
        if path and os.path.isfile(path):
            px = QPixmap(path)
            if not px.isNull():
                s = self._size
                px = px.scaled(s, s, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                out = QPixmap(s, s)
                out.fill(Qt.transparent)
                p = QPainter(out)
                p.setRenderHint(QPainter.Antialiasing)
                path2 = QPainterPath()
                path2.addEllipse(0, 0, s, s)
                p.setClipPath(path2)
                x = (px.width()  - s) // 2
                y = (px.height() - s) // 2
                p.drawPixmap(-x, -y, px)
                p.end()
                self.setPixmap(out)
                self.setStyleSheet(f"""
                    border-radius: {s//2}px;
                    border: 3px solid rgba(255,255,255,0.7);
                """)
                return

        # Default
        self.setPixmap(QPixmap())
        self.setText("👤")
        f = QFont("Segoe UI Emoji")
        f.setPointSize(32)
        self.setFont(f)
        self.setStyleSheet(f"""
            background: rgba(255,255,255,0.25);
            border-radius: {self._size//2}px;
            border: 2px solid rgba(255,255,255,0.45);
        """)


# ─────────────────────────────────────────────────────────────────────────────
# Timeline Activity Item
# ─────────────────────────────────────────────────────────────────────────────

class _ActivityItem(QFrame):
    @staticmethod
    def _get_action_meta():
        """ألوان أحداث النشاط — تقرأ من الثيم."""
        try:
            from core.theme_manager import ThemeManager
            c = ThemeManager.get_instance().current_theme.colors
        except Exception:
            c = {}
        return {
            "create": (c.get("success",       "#10B981"), "＋"),
            "insert": (c.get("success",       "#10B981"), "＋"),
            "update": (c.get("warning",       "#F59E0B"), "✎"),
            "delete": (c.get("danger",        "#EF4444"), "✕"),
            "export": (c.get("accent_indigo", "#6366F1"), "↗"),
            "import": (c.get("accent_violet", "#8B5CF6"), "↙"),
            "print":  (c.get("primary",       "#3B82F6"), "⎙"),
        }

    def __init__(self, action: str, table: str, timestamp: str, is_last=False, parent=None):
        super().__init__(parent)
        action_l = (action or "update").lower()
        accent, symbol = self._get_action_meta().get(action_l, ("#64748B", "●"))

        self.setObjectName("activity-row")
        self.setStyleSheet("QFrame#activity-row { background: transparent; }")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        # ── Dot ──────────────────────────────────────────────
        dot = QLabel(symbol)
        dot.setFixedSize(24, 24)
        dot.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(10)
        f.setBold(True)
        dot.setFont(f)
        dot.setStyleSheet(f"background:{accent}; color:white; border-radius:12px;")
        row.addWidget(dot, 0, Qt.AlignTop)

        # ── Content ───────────────────────────────────────────
        content = QFrame()
        content.setObjectName("card")   # يرث خلفية وبوردر من الـ theme CSS مباشرة
        content.setStyleSheet(f"""
            QFrame#card {{
                border-radius: 8px;
                margin-bottom: {'0' if is_last else '6'}px;
            }}
        """)
        c_lay = QHBoxLayout(content)
        c_lay.setContentsMargins(12, 8, 12, 8)

        msg = QLabel(f"{action.title()} · {table}")
        f2 = QFont()
        f2.setPointSize(10)
        msg.setFont(f2)
        msg.setObjectName("activity-msg")   # يرث لون النص من الـ theme
        c_lay.addWidget(msg, 1)

        ts_lbl = QLabel(timestamp)
        f3 = QFont()
        f3.setPointSize(8)
        ts_lbl.setFont(f3)
        ts_lbl.setObjectName("activity-ts")
        c_lay.addWidget(ts_lbl)

        row.addWidget(content, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Main Tab
# ─────────────────────────────────────────────────────────────────────────────

class UserProfileTab(QWidget):
    logout_requested = Signal()
    close_requested  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tm = TranslationManager.get_instance()
        self._    = self._tm.translate
        self.setObjectName("user-profile-tab")
        self._edit_mode = False
        self._build()
        self._tm.language_changed.connect(self.retranslate_ui)
        # تحديث الألوان عند تغيير الثيم
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setObjectName("profile-container")
        main = QVBoxLayout(container)
        main.setContentsMargins(32, 28, 32, 32)
        main.setSpacing(20)

        main.addWidget(self._build_hero())
        main.addWidget(self._build_stats())
        main.addWidget(self._build_info())
        main.addWidget(self._build_edit_name())
        main.addWidget(self._build_password())
        main.addWidget(self._build_activity())
        main.addWidget(self._build_actions())
        main.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Hero ──────────────────────────────────────────────────────────────────

    def _build_hero(self) -> QFrame:
        tc = _theme_colors()
        frame = QFrame()
        frame.setObjectName("profile-hero")
        frame.setStyleSheet(f"""
            QFrame#profile-hero {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {tc['primary']}, stop:1 {tc['primary_d']}
                );
                border-radius: 16px;
                min-height: 130px;
            }}
            QLabel {{ background: transparent; color: white; }}
            QPushButton {{
                background: rgba(255,255,255,0.18);
                color: white;
                border: 1px solid rgba(255,255,255,0.35);
                border-radius: 8px;
                padding: 4px 14px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.30); }}
        """)

        lay = QHBoxLayout(frame)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(22)

        user = _current_user()

        # Avatar
        self._avatar = _AvatarWidget(size=88)
        self._avatar.clicked.connect(self._pick_avatar)
        self._refresh_avatar()
        lay.addWidget(self._avatar)

        # Info col
        col = QVBoxLayout()
        col.setSpacing(5)

        name = "—"
        role_txt = "—"
        office_txt = "—"
        username_txt = "—"
        if user:
            name = getattr(user, "full_name", None) or getattr(user, "username", "—")
            username_txt = getattr(user, "username", "—")
            role = getattr(user, "role", None)
            role_txt = getattr(role, "name", "—") if role else "—"
            office = getattr(user, "office", None)
            if office:
                lang = SettingsManager.get_instance().get("language") or "ar"
                office_txt = (
                    getattr(office, f"name_{lang}", None)
                    or getattr(office, "name_ar", None)
                    or getattr(office, "name_en", "—")
                )

        self._hero_name = QLabel(name)
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        self._hero_name.setFont(f)
        col.addWidget(self._hero_name)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(16)

        self._hero_role = self._hero_chip(f"◎  {role_txt}")
        self._hero_office = self._hero_chip(f"⊞  {office_txt}")
        meta_row.addWidget(self._hero_role)
        meta_row.addWidget(self._hero_office)
        meta_row.addStretch()
        col.addLayout(meta_row)

        self._hero_username = QLabel(f"@{username_txt}")
        f2 = QFont()
        f2.setPointSize(10)
        self._hero_username.setFont(f2)
        self._hero_username.setStyleSheet("color: rgba(255,255,255,0.7); background: transparent;")
        col.addWidget(self._hero_username)

        lay.addLayout(col, 1)

        # Right buttons
        right = QVBoxLayout()
        right.setSpacing(8)
        right.setAlignment(Qt.AlignTop)

        self._online_badge = QLabel(self._("profile_online_badge"))
        self._online_badge.setStyleSheet(
            "color: #6EE7B7;"
            " background: rgba(0,0,0,0.2);"
            " border-radius: 10px;"
            " padding: 3px 10px;"
            " font-size: 11px;"
        )
        right.addWidget(self._online_badge)

        self._btn_avatar_hero = QPushButton("📷  " + self._("change_avatar"))
        self._btn_avatar_hero.setMinimumHeight(32)
        self._btn_avatar_hero.setCursor(Qt.PointingHandCursor)
        self._btn_avatar_hero.clicked.connect(self._pick_avatar)
        right.addWidget(self._btn_avatar_hero)

        self._btn_delete_avatar = QPushButton(self._("profile_delete_avatar_btn"))
        self._btn_delete_avatar.setMinimumHeight(32)
        self._btn_delete_avatar.setCursor(Qt.PointingHandCursor)
        self._btn_delete_avatar.setStyleSheet("""
            QPushButton {
                background: rgba(239,68,68,0.25);
                color: white;
                border: 1px solid rgba(239,68,68,0.5);
                border-radius: 8px;
                padding: 4px 14px;
                font-size: 11px;
            }
            QPushButton:hover { background: rgba(239,68,68,0.45); }
        """)
        self._btn_delete_avatar.clicked.connect(self._delete_avatar)
        user_has_avatar = bool(getattr(_current_user(), "avatar_path", None))
        self._btn_delete_avatar.setVisible(user_has_avatar)
        right.addWidget(self._btn_delete_avatar)

        lay.addLayout(right)
        return frame

    def _hero_chip(self, text: str) -> QLabel:
        lbl = QLabel(text)
        f = QFont()
        f.setPointSize(9)
        lbl.setFont(f)
        lbl.setStyleSheet("""
            background: rgba(255,255,255,0.15);
            color: white;
            border-radius: 6px;
            padding: 3px 8px;
        """)
        return lbl

    def _refresh_avatar(self):
        user = _current_user()
        path = getattr(user, "avatar_path", None) if user else None
        self._avatar.set_image(path)

    def _pick_avatar(self):
        from database.models import User as UserModel
        file_path, _ = QFileDialog.getOpenFileName(
            self, self._("select_avatar_image"), "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not file_path:
            return
        user = _current_user()
        if not user:
            return

        avatars_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "avatars"
        )
        os.makedirs(avatars_dir, exist_ok=True)
        ext  = os.path.splitext(file_path)[1].lower()
        dest = os.path.join(avatars_dir, f"user_{user.id}{ext}")

        # فكّ lock ويندوز
        self._avatar.setPixmap(QPixmap())

        shutil.copy2(file_path, dest)
        try:
            with get_session_local()() as s:
                db_user = s.get(UserModel, user.id)
                if db_user:
                    db_user.avatar_path = dest
                    s.commit()
            user.avatar_path = dest
            SettingsManager.get_instance().set("user", user)
            self._refresh_avatar()
            self._btn_delete_avatar.setVisible(True)
            QMessageBox.information(self, self._("success"), self._("avatar_updated"))
        except Exception as e:
            QMessageBox.warning(self, self._("error"), str(e))

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _build_stats(self) -> QFrame:
        self._stats_card = _Card(self._("my_stats_title"))
        tc = _theme_colors()
        user = _current_user()
        uid  = getattr(user, "id", None)
        total_actions = today_actions = total_trans = 0
        try:
            with get_session_local()() as s:
                total_actions = s.query(AuditLog).filter(AuditLog.user_id == uid).count()
                today_actions = (s.query(AuditLog)
                                  .filter(AuditLog.user_id == uid,
                                          func.date(AuditLog.timestamp) == date.today()).count())
                total_trans   = s.query(Transaction).count()
        except Exception:
            pass

        row = QHBoxLayout()
        row.setSpacing(14)
        self._stat_total = _StatCard(str(total_actions), self._("total_operations"), tc["primary"])
        self._stat_today = _StatCard(str(today_actions), self._("today_operations"),  tc["success"])
        self._stat_trans = _StatCard(str(total_trans),   self._("transactions"),      "#8B5CF6")
        for w in [self._stat_total, self._stat_today, self._stat_trans]:
            row.addWidget(w)
        row.addStretch()
        self._stats_card.body.addLayout(row)
        return self._stats_card

    # ── Info ─────────────────────────────────────────────────────────────────

    def _build_info(self) -> QFrame:
        self._info_card = _Card(self._("personal_info_title"))
        self._populate_info()
        return self._info_card

    def _populate_info(self):
        while self._info_card.body.count():
            w = self._info_card.body.takeAt(0)
            if w.widget():
                w.widget().deleteLater()

        user = _current_user()
        if not user:
            return

        role      = getattr(user, "role", None)
        role_name = getattr(role, "name", "—") if role else "—"
        office    = getattr(user, "office", None)
        office_name = "—"
        if office:
            lang = SettingsManager.get_instance().get("language") or "ar"
            office_name = (
                getattr(office, f"name_{lang}", None)
                or getattr(office, "name_ar", None)
                or getattr(office, "name_en", "—")
            )
        created   = getattr(user, "created_at", None)
        status    = self._("user_status_active") if getattr(user, "is_active", True) else self._("user_status_suspended")

        rows = [
            (self._("username"),   getattr(user, "username",  "—")),
            (self._("full_name"),  getattr(user, "full_name", "—")),
            (self._("role"),       role_name),
            (self._("profile_office_label"), office_name),
            (self._("status"),     status),
            (self._("created_at"), format_local_dt(created, "%Y-%m-%d") if created else "—"),
        ]
        for label, value in rows:
            self._info_card.body.addWidget(_InfoRow(label, value))

    # ── Edit name ─────────────────────────────────────────────────────────────

    def _build_edit_name(self) -> QFrame:
        self._edit_card = _Card(self._("profile_edit_name_title"))

        user = _current_user()
        self._name_edit = _Field(self._("full_name"))
        self._name_edit.setText(getattr(user, "full_name", "") or "")
        self._edit_card.body.addWidget(self._name_edit)

        btn_row = QHBoxLayout()
        self._save_name_btn = _Btn(self._("profile_save_name_btn"), "primary")
        self._save_name_btn.setMaximumWidth(160)
        self._save_name_btn.clicked.connect(self._save_name)
        btn_row.addWidget(self._save_name_btn)
        btn_row.addStretch()
        self._edit_card.body.addLayout(btn_row)
        return self._edit_card

    def _save_name(self):
        from database.models import User as UserModel
        new_name = self._name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(self, self._("warning"), self._("profile_enter_name_first"))
            return
        user = _current_user()
        if not user:
            return
        try:
            with get_session_local()() as s:
                db_user = s.get(UserModel, user.id)
                if db_user:
                    db_user.full_name = new_name
                    s.commit()
            user.full_name = new_name
            SettingsManager.get_instance().set("user", user)
            self._hero_name.setText(new_name)
            self._populate_info()
            self._flash_success(self._save_name_btn)
        except Exception as e:
            QMessageBox.critical(self, self._("error"), str(e))

    # ── Password ──────────────────────────────────────────────────────────────

    def _build_password(self) -> QFrame:
        self._pw_card = _Card(self._("change_password_title"))
        tc = _theme_colors()

        self._old_pw  = _Field(self._("current_password"), password=True)
        self._new_pw  = _Field(self._("new_password"),     password=True)
        self._conf_pw = _Field(self._("confirm_password"), password=True)

        # strength bar
        self._strength_bar = QFrame()
        self._strength_bar.setFixedHeight(4)
        self._strength_bar.setStyleSheet(f"background: {tc['border']}; border-radius: 2px;")
        self._new_pw.textChanged.connect(self._update_strength)

        for w in [self._old_pw, self._new_pw, self._strength_bar, self._conf_pw]:
            self._pw_card.body.addWidget(w)

        btn_row = QHBoxLayout()
        self._save_pw_btn = _Btn(self._("save_password_btn"), "primary")
        self._save_pw_btn.setMaximumWidth(180)
        self._save_pw_btn.clicked.connect(self._change_password)
        btn_row.addWidget(self._save_pw_btn)
        btn_row.addStretch()
        self._pw_card.body.addLayout(btn_row)
        return self._pw_card

    def _update_strength(self, text: str):
        n = len(text)
        has_upper = any(c.isupper() for c in text)
        has_digit = any(c.isdigit() for c in text)
        has_sym   = any(c in "!@#$%^&*" for c in text)
        score = sum([n >= 6, n >= 10, has_upper, has_digit, has_sym])
        try:
            from core.theme_manager import ThemeManager
            _tc = ThemeManager.get_instance().current_theme.colors
        except Exception:
            _tc = {}
        _colors = [_tc.get("chart_red","#EF4444"), _tc.get("chart_orange","#F97316"),
                   _tc.get("chart_yellow","#F59E0B"), _tc.get("chart_lime","#84CC16"),
                   _tc.get("chart_green","#10B981")]
        widths = [20, 40, 60, 80, 100]
        _bar_color = _colors[min(score, 4)] if text else "#E2E8F0"
        w = widths[min(score, 4)] if text else 100
        self._strength_bar.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {_bar_color}, stop:{w/100:.2f} {_bar_color}, stop:{w/100+0.01:.2f} #E2E8F0, stop:1 #E2E8F0);
            border-radius: 2px;
        """)

    # ── Activity ──────────────────────────────────────────────────────────────

    def _build_activity(self) -> QFrame:
        self._act_card = _Card(self._("recent_activities_mine"))
        self._populate_activity()
        return self._act_card

    def _populate_activity(self):
        while self._act_card.body.count():
            item = self._act_card.body.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        user = _current_user()
        uid  = getattr(user, "id", None)

        TABLE_KEYS = {
            "transactions": "table_transactions", "materials": "table_materials",
            "clients": "table_clients", "users": "table_users",
            "documents": "table_documents", "entries": "table_entries",
        }

        try:
            with get_session_local()() as s:
                rows = (s.query(AuditLog)
                         .filter(AuditLog.user_id == uid)
                         .order_by(desc(AuditLog.id))
                         .limit(10).all())

            if not rows:
                empty = QLabel(self._("no_activity_yet"))
                empty.setAlignment(Qt.AlignCenter)
                empty.setObjectName("empty-label")
                self._act_card.body.addWidget(empty)
                return

            for i, row in enumerate(rows):
                action = row.action or "update"
                tbl_key = TABLE_KEYS.get(row.table_name)
                tbl     = self._(tbl_key) if tbl_key else (row.table_name or "—")
                ts      = format_local_dt(row.timestamp, "%Y-%m-%d %H:%M")
                is_last = (i == len(rows) - 1)
                self._act_card.body.addWidget(
                    _ActivityItem(action, tbl, ts, is_last=is_last)
                )
        except Exception as e:
            err = QLabel(f"⚠  {e}")
            err.setObjectName("text-danger")
            self._act_card.body.addWidget(err)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _build_actions(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(14)

        self._logout_btn = _Btn(self._("logout_btn"), "warning")
        self._logout_btn.setMinimumWidth(150)
        self._logout_btn.clicked.connect(self._confirm_logout)

        self._close_btn = _Btn(self._("close_app_btn"), "danger")
        self._close_btn.setMinimumWidth(150)
        self._close_btn.clicked.connect(self._confirm_close)

        lay.addWidget(self._logout_btn)
        lay.addWidget(self._close_btn)
        lay.addStretch()
        return card

    # ── Logic ─────────────────────────────────────────────────────────────────

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
            return
        try:
            from passlib.hash import bcrypt
            if not bcrypt.verify(old, user.password):
                QMessageBox.warning(self, self._("error"), self._("wrong_password"))
                return
            new_hash = bcrypt.hash(new)
            with get_session_local()() as s:
                from database.models import User as UserModel
                db_user = s.get(UserModel, user.id)
                if db_user:
                    db_user.password = new_hash
                    s.commit()
            self._old_pw.clear()
            self._new_pw.clear()
            self._conf_pw.clear()
            try:
                from services.notification_service import NotificationService
                NotificationService.get_instance().add_manual(
                    self._("password_changed_success"), level="success", icon="🔒"
                )
            except Exception:
                pass
            self._flash_success(self._save_pw_btn)
            QMessageBox.information(self, self._("success"), self._("password_change_success_dialog"))
        except Exception as e:
            QMessageBox.critical(self, self._("error"), self._("password_change_failed") + f"\n{e}")

    def _on_theme_changed(self, _=None):
        """إعادة رسم العناصر المعتمدة على الثيم عند التغيير."""
        self._populate_activity()

    def _delete_avatar(self):
        """حذف الصورة الشخصية والرجوع للافتراضية."""
        from database.models import User as UserModel
        user = _current_user()
        if not user:
            return
        r = QMessageBox.question(
            self, self._("profile_delete_avatar_confirm_title"),
            self._("profile_delete_avatar_confirm_msg"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if r != QMessageBox.Yes:
            return
        try:
            # حرر lock ويندوز أولاً
            self._avatar.setPixmap(QPixmap())
            # حذف الملف
            old_path = getattr(user, "avatar_path", None)
            if old_path and os.path.isfile(old_path):
                os.remove(old_path)
            # تحديث DB
            with get_session_local()() as s:
                db_user = s.get(UserModel, user.id)
                if db_user:
                    db_user.avatar_path = None
                    s.commit()
            user.avatar_path = None
            SettingsManager.get_instance().set("user", user)
            self._refresh_avatar()
            self._btn_delete_avatar.setVisible(False)
        except Exception as e:
            QMessageBox.warning(self, self._("error"), str(e))

    def _confirm_logout(self):
        r = QMessageBox.question(
            self, self._("logout_confirm_title"), self._("logout_confirm_msg"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if r == QMessageBox.Yes:
            self.logout_requested.emit()

    def _confirm_close(self):
        r = QMessageBox.question(
            self, self._("close_app_title"), self._("close_app_msg"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if r == QMessageBox.Yes:
            self.close_requested.emit()

    def _flash_success(self, btn: QPushButton):
        """وميض أخضر لمدة 1.5 ثانية على الزر عند النجاح."""
        original = btn.styleSheet()
        try:
            from core.theme_manager import ThemeManager
            _success = ThemeManager.get_instance().current_theme.colors.get('success', '#10B981')
        except Exception:
            _success = '#10B981'
        btn.setStyleSheet(f"background: {_success}; color: white; border-radius: 8px;")
        btn.setText("✓  " + self._("success"))
        def _restore():
            btn.setStyleSheet(original)
            btn.setText(btn.text().replace("✓  " + self._("success") + "  ", "").lstrip("✓  "))
        QTimer.singleShot(1500, _restore)

    # ── Retranslate ───────────────────────────────────────────────────────────

    def retranslate_ui(self):
        self._ = TranslationManager.get_instance().translate
        user = _current_user()
        lang = SettingsManager.get_instance().get("language") or "ar"

        # Hero
        if hasattr(self, "_btn_avatar_hero"):
            self._btn_avatar_hero.setText("📷  " + self._("change_avatar"))
        if hasattr(self, "_btn_delete_avatar"):
            self._btn_delete_avatar.setText(self._("profile_delete_avatar_btn"))
        self._online_badge.setText("● " + self._("user_online"))

        role_txt = "—"
        office_txt = "—"
        if user:
            role = getattr(user, "role", None)
            role_txt = getattr(role, "name", "—") if role else "—"
            office = getattr(user, "office", None)
            if office:
                office_txt = (
                    getattr(office, f"name_{lang}", None)
                    or getattr(office, "name_ar", None)
                    or "—"
                )
        self._hero_role.setText(f"◎  {role_txt}")
        self._hero_office.setText(f"⊞  {office_txt}")

        # Stats
        self._stats_card.set_title(self._("my_stats_title"))
        self._stat_total.set_label(self._("total_operations"))
        self._stat_today.set_label(self._("today_operations"))
        self._stat_trans.set_label(self._("transactions"))

        # Info
        self._info_card.set_title(self._("personal_info_title"))
        self._populate_info()

        # Edit name
        self._edit_card.set_title(self._("profile_edit_name_title"))
        self._save_name_btn.setText(self._("profile_save_name_btn"))
        self._name_edit.setPlaceholderText(self._("full_name"))

        # Password
        self._pw_card.set_title(self._("change_password_title"))
        self._old_pw.setPlaceholderText(self._("current_password"))
        self._new_pw.setPlaceholderText(self._("new_password"))
        self._conf_pw.setPlaceholderText(self._("confirm_password"))
        self._save_pw_btn.setText(self._("save_password_btn"))

        # Activity
        self._act_card.set_title(self._("recent_activities_mine"))
        self._populate_activity()

        # Actions
        self._logout_btn.setText(self._("logout_btn"))
        self._close_btn.setText(self._("close_app_btn"))