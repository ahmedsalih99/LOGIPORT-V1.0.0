"""
TopBar - LOGIPORT
==================
الهيكل:
  [أدوات + لغة]  [← spacer →]  [🔍 بحث]  [← spacer →]  [⏰]  [🔔]  [👤 اسم]  [⬡ logout]
"""

import datetime
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSpacerItem,
    QSizePolicy, QLabel, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QRect
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPainterPath

from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from ui.widgets.notification_bell import NotificationBell
from ui.utils.svg_icons import set_icon
from ui.widgets.sync_widget import SyncWidget
from core.permissions import has_perm, is_admin


# ─── Avatar دائرة ملوّنة ────────────────────────────────────────────────────

class _AvatarLabel(QLabel):
    SIZE = 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._letter  = "U"
        self._color   = "#2563EB"
        self._img     = None

    def set_user(self, name: str, avatar_path: str | None = None):
        self._letter = (name[0].upper() if name else "U")
        palette = ["#2563EB", "#7C3AED", "#059669", "#DC2626", "#D97706", "#0891B2"]
        self._color = palette[ord(self._letter) % len(palette)]

        self._img = None
        if avatar_path:
            try:
                pm = QPixmap(avatar_path)
                if not pm.isNull():
                    self._img = pm.scaled(
                        self.SIZE, self.SIZE,
                        Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation
                    )
            except Exception:
                pass
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        r = self.SIZE
        path.addEllipse(0, 0, r, r)
        p.setClipPath(path)
        if self._img:
            p.drawPixmap(0, 0, self._img)
        else:
            p.fillRect(0, 0, r, r, QColor(self._color))
            p.setPen(QColor("#FFFFFF"))
            p.setFont(QFont("Tajawal", 11, QFont.Bold))
            p.drawText(QRect(0, 0, r, r), Qt.AlignCenter, self._letter)
        p.end()


# ─── User Widget: QFrame قابل للضغط ─────────────────────────────────────────

class _UserChip(QFrame):
    """QFrame يحمل avatar + اسم، ويصدر clicked عند الضغط."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topbar-user-chip")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 12, 0)
        lay.setSpacing(8)

        self.avatar = _AvatarLabel()
        lay.addWidget(self.avatar)

        self.name_lbl = QLabel()
        self.name_lbl.setObjectName("topbar-username-lbl")
        lay.addWidget(self.name_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_user(self, name: str, avatar_path: str | None = None):
        display = name or "User"
        self.avatar.set_user(display, avatar_path)
        self.name_lbl.setText(display)
        self.name_lbl.setFont(QFont("Tajawal", 10, QFont.DemiBold))


# ─── OfficeBadge ─────────────────────────────────────────────────────────────

class _OfficeBadge(QFrame):
    """Badge صغير يعرض اسم المكتب الحالي في TopBar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topbar-office-badge")
        self.setFixedHeight(28)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(4)

        icon = QLabel("🏢")
        icon.setFixedWidth(16)
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)

        self._lbl = QLabel()
        self._lbl.setObjectName("topbar-office-lbl")
        lay.addWidget(self._lbl)

    def set_office(self, name: str):
        """يحدّث اسم المكتب — يُخفي الـ badge إذا لم يكن هناك مكتب."""
        self._lbl.setText(name)
        self.setVisible(bool(name))


# ─── TopBar ──────────────────────────────────────────────────────────────────

class TopBar(QWidget):

    profile_requested = Signal()
    logout_requested  = Signal()
    about_requested   = Signal()
    search_requested  = Signal()
    sync_settings_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("TopBar")
        self._       = TranslationManager.get_instance().translate
        self.settings = SettingsManager.get_instance()
        self.setFixedHeight(52)
        self._build()

    # ── بناء الواجهة ─────────────────────────────────────────────────────────

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(4)

        # ══ LEFT: أدوات ══════════════════════════════════════════════════════
        self.settings_btn = self._icon_btn("settings", self.open_settings)
        self.theme_btn    = self._icon_btn("theme",    self.toggle_theme)
        self.about_btn    = self._icon_btn("info",     self.about_requested.emit)

        # إخفاء زر الإعدادات إذا لم يملك المستخدم صلاحية manage_settings
        _u = self.settings.get("user")
        self.settings_btn.setVisible(is_admin(_u) or has_perm(_u, "manage_settings"))

        lay.addWidget(self.settings_btn)
        lay.addWidget(self.theme_btn)
        lay.addWidget(self.about_btn)

        # زر اللغة — نص فقط
        self.lang_btn = QPushButton()
        self.lang_btn.setObjectName("topbar-lang-btn")
        self.lang_btn.setFixedHeight(28)
        self.lang_btn.setCursor(Qt.PointingHandCursor)
        self.lang_btn.clicked.connect(self.toggle_language)
        self._refresh_lang_btn()
        lay.addWidget(self.lang_btn)

        # ══ CENTER: بحث ══════════════════════════════════════════════════════
        lay.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.search_btn = QPushButton()
        self.search_btn.setObjectName("topbar-search-bar")
        self.search_btn.setFixedHeight(34)
        self.search_btn.setMinimumWidth(260)
        self.search_btn.setMaximumWidth(400)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setLayoutDirection(Qt.RightToLeft)
        self.search_btn.clicked.connect(self.search_requested.emit)
        set_icon(self.search_btn, "search", 15)
        self._refresh_search_text()
        lay.addWidget(self.search_btn)

        lay.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # ══ RIGHT: ساعة ══════════════════════════════════════════════════════
        self.time_label = QLabel(datetime.datetime.now().strftime("%H:%M"))
        self.time_label.setObjectName("topbar-clock")
        self.time_label.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        lay.addWidget(self.time_label)

        lay.addWidget(self._vline())

        # ══ RIGHT: جرس إشعارات ════════════════════════════════════════════════
        self.notif_bell = NotificationBell()
        lay.addWidget(self.notif_bell)

        lay.addWidget(self._vline())

        # ══ RIGHT: badge المكتب ════════════════════════════════════════════════
        self.office_badge = _OfficeBadge()
        lay.addWidget(self.office_badge)

        # ══ RIGHT: مؤشر المزامنة ══════════════════════════════════════════════
        self.sync_widget = SyncWidget()
        self.sync_widget.sync_settings_requested.connect(
            self.sync_settings_requested.emit
        )
        lay.addWidget(self.sync_widget)

        # ══ RIGHT: User chip (avatar + اسم) ══════════════════════════════════
        self.user_chip = _UserChip()
        self.user_chip.clicked.connect(self.profile_requested.emit)
        self.user_chip.setToolTip(self._("profile"))
        lay.addWidget(self.user_chip)

        # ══ RIGHT: logout ═════════════════════════════════════════════════════
        self.logout_btn = self._icon_btn("logout", self.logout_requested.emit)
        lay.addWidget(self.logout_btn)

        # ── تحديث بيانات المستخدم ─────────────────────────────────────────────
        self._refresh_user()

        # ── Timer الساعة ──────────────────────────────────────────────────────
        timer = QTimer(self)
        timer.timeout.connect(lambda: self.time_label.setText(
            datetime.datetime.now().strftime("%H:%M")
        ))
        timer.start(1000)

        # ── إعادة رسم الأيقونات عند تغيير الثيم ──────────────────────────────
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

        # تحديث الصورة فوراً عند تغيير user في الـ settings
        self.settings.setting_changed.connect(self._on_setting_changed)

        # ── بدء polling مؤشر المزامنة ─────────────────────────────────────────
        self.sync_widget.start()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _icon_btn(self, icon_name: str, slot) -> QPushButton:
        btn = QPushButton()
        btn.setObjectName("topbar-tool-btn")
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.PointingHandCursor)
        set_icon(btn, icon_name, 17)
        btn.clicked.connect(slot)
        return btn

    def _vline(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.VLine)
        f.setObjectName("topbar-sep")
        return f

    def _refresh_lang_btn(self):
        lang   = self.settings.get("language") or "ar"
        labels = {"ar": "ع", "en": "EN", "tr": "TR"}
        self.lang_btn.setText(labels.get(lang, lang.upper()))

    def _refresh_search_text(self):
        self.search_btn.setText(f"  {self._('search')}...        Ctrl+K")

    def _refresh_user(self):
        user        = self.settings.get("user")
        name        = ""
        avatar_path = None
        if user:
            name        = getattr(user, "full_name", None) or getattr(user, "username", None) or ""
            avatar_path = getattr(user, "avatar_path", None)
        self.user_chip.set_user(name, avatar_path)
        self._refresh_office()
        # تحديث رؤية زر الإعدادات بناءً على صلاحية المستخدم الحالي
        self.settings_btn.setVisible(is_admin(user) or has_perm(user, "manage_settings"))

    def _refresh_office(self):
        """يحدّث badge المكتب من OfficeContext."""
        try:
            from core.office_context import OfficeContext
            lang = self.settings.get("language") or "ar"
            office_name = OfficeContext.get_name(lang)
            self.office_badge.set_office(office_name)
        except Exception:
            self.office_badge.set_office("")

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_setting_changed(self, key, value):
        if key == "user":
            self._refresh_user()
        elif key == "language":
            self._refresh_office()

    def _on_theme_changed(self, _=None):
        set_icon(self.settings_btn, "settings", 17)
        set_icon(self.theme_btn,    "theme",    17)
        set_icon(self.about_btn,    "info",     17)
        set_icon(self.logout_btn,   "logout",   17)
        set_icon(self.search_btn,   "search",   15)
        # أيقونة الإشعارات
        try:
            set_icon(self.notif_bell._btn, "bell", 18)
        except Exception:
            pass
        # أيقونة المزامنة
        try:
            set_icon(self.sync_widget._btn, "sync", 17)
        except Exception:
            pass

    def toggle_language(self):
        lang     = self.settings.get("language")
        new_lang = "en" if lang == "ar" else ("tr" if lang == "en" else "ar")
        self.settings.set_language(new_lang)
        self._refresh_lang_btn()

    def toggle_theme(self):
        theme     = self.settings.get("theme")
        new_theme = "dark" if theme == "light" else "light"
        self.settings.set("theme", new_theme)

    def open_settings(self):
        from ui.settings_window import SettingsWindow
        SettingsWindow(self).exec_()

    # ── public API ────────────────────────────────────────────────────────────

    def update_time(self):
        self.time_label.setText(datetime.datetime.now().strftime("%H:%M"))

    def retranslate_ui(self):
        self._       = TranslationManager.get_instance().translate
        self._refresh_lang_btn()
        self._refresh_search_text()
        self._refresh_user()  # يستدعي _refresh_office داخلياً
        self.settings_btn.setToolTip(self._("settings"))
        self.theme_btn.setToolTip(self._("theme"))
        self.about_btn.setToolTip(self._("about_app"))
        self.logout_btn.setToolTip(self._("logout"))
        self.user_chip.setToolTip(self._("profile"))

    # backward compat — بعض الأماكن تستدعي هذه الأسماء
    @property
    def user_btn(self):
        return self.user_chip

    @property
    def user_widget(self):
        return self.user_chip