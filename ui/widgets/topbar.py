"""
TopBar - LOGIPORT v3.1
=========================

محدّث:
- NotificationBell مع badge حقيقي
- زر المستخدم يفتح صفحة البروفايل
- زر تسجيل خروج سريع
- ساعة + لغة + ثيم + إعدادات
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSpacerItem,
    QSizePolicy, QLabel, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from ui.settings_window import SettingsWindow
from ui.widgets.notification_bell import NotificationBell
import datetime


class TopBar(QWidget):
    """Responsive top bar with notifications and user menu."""

    # ── signals ──────────────────────────────────────────────────────────────
    profile_requested = Signal()   # فتح صفحة البروفايل
    logout_requested  = Signal()   # تسجيل الخروج
    about_requested   = Signal()   # نافذة عن التطبيق

    def __init__(self):
        super().__init__()
        self.setObjectName("TopBar")
        self._  = TranslationManager.get_instance().translate
        self.settings = SettingsManager.get_instance()

        self._set_responsive_height()
        self._init_ui()

    def _set_responsive_height(self):
        screen = QApplication.primaryScreen()
        screen_height = screen.availableGeometry().height()

        if screen_height < 768:
            height = max(48, int(screen_height * 0.06))
        elif screen_height < 1080:
            height = 54
        else:
            height = max(56, int(screen_height * 0.05))

        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        self.topbar_height = height

    def _init_ui(self):
        layout = QHBoxLayout(self)
        margin_h = max(16, int(self.topbar_height * 0.4))
        layout.setContentsMargins(margin_h, 0, margin_h, 0)
        layout.setSpacing(max(8, int(self.topbar_height * 0.2)))

        # ─── LEFT: Settings / Language / Theme ───────────────────────────────
        self.settings_btn = QPushButton(f"⚙ {self._('settings')}")
        self.settings_btn.setObjectName("topbar-btn")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(self.settings_btn)

        self.lang_btn = QPushButton(f"🌐 {self._('language')}")
        self.lang_btn.setObjectName("topbar-btn")
        self.lang_btn.setCursor(Qt.PointingHandCursor)
        self.lang_btn.clicked.connect(self.toggle_language)
        layout.addWidget(self.lang_btn)

        self.theme_btn = QPushButton(f"🌗 {self._('theme')}")
        self.theme_btn.setObjectName("topbar-btn")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_btn)

        self.about_btn = QPushButton("ℹ️")
        self.about_btn.setObjectName("topbar-btn")
        self.about_btn.setFixedWidth(36)
        self.about_btn.setCursor(Qt.PointingHandCursor)
        self.about_btn.setToolTip(self._("about_app"))
        self.about_btn.setFont(QFont("Segoe UI Emoji", 13))
        self.about_btn.clicked.connect(self.about_requested.emit)
        layout.addWidget(self.about_btn)

        # ─── CENTER: Clock ────────────────────────────────────────────────────
        layout.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.time_label = QLabel(datetime.datetime.now().strftime("%H:%M"))
        self.time_label.setObjectName("topbar-clock")
        self.time_label.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        layout.addWidget(self.time_label)

        layout.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # ─── RIGHT: Notification Bell ─────────────────────────────────────────
        self.notif_bell = NotificationBell()
        layout.addWidget(self.notif_bell)

        # ─── RIGHT: User button (opens profile) ───────────────────────────────
        self.user_btn = QPushButton()
        self.user_btn.setObjectName("topbar-btn")
        self.user_btn.setCursor(Qt.PointingHandCursor)
        self.user_btn.setToolTip(self._("profile"))
        self.user_btn.clicked.connect(self.profile_requested.emit)
        self._refresh_user_btn()
        layout.addWidget(self.user_btn)

        # ─── RIGHT: Logout ────────────────────────────────────────────────────
        self.logout_btn = QPushButton("🚪")
        self.logout_btn.setObjectName("topbar-btn")
        self.logout_btn.setFixedWidth(36)
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.setToolTip(self._("logout"))
        self.logout_btn.setFont(QFont("Segoe UI Emoji", 14))
        self.logout_btn.clicked.connect(self.logout_requested.emit)
        layout.addWidget(self.logout_btn)

        # ─── Clock timer ──────────────────────────────────────────────────────
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(60000)

    def _refresh_user_btn(self):
        user = self.settings.get("user")
        name = "👤"
        if user:
            display = (getattr(user, "full_name", None) or
                       getattr(user, "username", None) or "")
            if display:
                name = f"👤  {display}"
        self.user_btn.setText(name)
        self.user_btn.setFont(QFont("Tajawal", 10))

    def update_time(self):
        self.time_label.setText(datetime.datetime.now().strftime("%H:%M"))

    def toggle_language(self):
        lang = self.settings.get("language")
        new_lang = "en" if lang == "ar" else ("tr" if lang == "en" else "ar")
        self.settings.set_language(new_lang)
        self.lang_btn.setText(f"🌐 {self._('language')}")
        self.settings_btn.setText(f"⚙ {self._('settings')}")
        self.theme_btn.setText(f"🌗 {self._('theme')}")

    def toggle_theme(self):
        theme = self.settings.get("theme")
        new_theme = "dark" if theme == "light" else "light"
        self.settings.set("theme", new_theme)
        self.theme_btn.setText(f"🌗 {self._('theme')}")

    def open_settings(self):
        dlg = SettingsWindow(self)
        dlg.exec_()

    def retranslate_ui(self):
        self._ = TranslationManager.get_instance().translate
        self.lang_btn.setText(f"🌐 {self._('language')}")
        self.theme_btn.setText(f"🌗 {self._('theme')}")
        self.settings_btn.setText(f"⚙ {self._('settings')}")
        self.lang_btn.setToolTip(self._("language"))
        self.theme_btn.setToolTip(self._("theme"))
        self.settings_btn.setToolTip(self._("settings"))
        self.about_btn.setToolTip(self._("about_app"))
        self.user_btn.setToolTip(self._("profile"))
        self.logout_btn.setToolTip(self._("logout"))
        self._refresh_user_btn()
