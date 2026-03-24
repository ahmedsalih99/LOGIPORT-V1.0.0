"""
sidebar.py — LOGIPORT  (Floating Pill Navigation)
===================================================
شريط تنقل أفقي عائم يحل محل السايدبار الجانبي.
- كل تاب: أيقونة كبيرة + اسم تحتها
- التاب النشط: خلفية primary + نص وأيقونة بيضاء
- يحتفظ بنفس الـ API: section_changed Signal + change_section()
- الـ pill لا يتجاوز عرض الشاشة أبداً (أزرار تتقلص أو تختبئ)
"""

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QToolButton, QSizePolicy, QApplication,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon

from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from database.crud.permissions_crud import allowed_tabs
from ui.utils.svg_icons import get_sidebar_icon, refresh_sidebar_icons

ICON_PATHS = {
    "dashboard":          "icons/dashboard.png",
    "materials":          "icons/materials.png",
    "clients":            "icons/clients.png",
    "companies":          "icons/companies.png",
    "pricing":            "icons/pricing.png",
    "entries":            "icons/entries.png",
    "transactions":       "icons/transactions.png",
    "container_tracking": "icons/container.png",
    "tasks":              "icons/tasks.png",
    "documents":          "icons/documents.png",
    "values":             "icons/values.png",
    "offices":            "icons/settings.png",
    "audit_trail":        "icons/audit_trail.png",
    "control_panel":      "icons/settings.png",
    "users_permissions":  "icons/users.png",
}

_EMOJI_FALLBACK = {
    "dashboard":          "🏠",
    "materials":          "📦",
    "clients":            "👥",
    "companies":          "🏢",
    "pricing":            "💱",
    "entries":            "📥",
    "transactions":       "📋",
    "container_tracking": "🚢",
    "tasks":              "✅",
    "documents":          "📄",
    "values":             "💰",
    "offices":            "🏬",
    "audit_trail":        "🕵️",
    "control_panel":      "⚙️",
    "users_permissions":  "🔑",
}


class FloatingPillNav(QFrame):
    """شريط تنقل أفقي عائم."""

    section_changed = Signal(str)
    sidebar_toggled = Signal(bool)   # backward compat

    def __init__(self):
        super().__init__()
        self.setObjectName("FloatingPill")

        self._        = TranslationManager.get_instance().translate
        self.settings = SettingsManager.get_instance()
        self.buttons: dict = {}
        self.btn_keys: list = []
        self._active_key = ""

        self._build()

        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)
        self.settings.setting_changed.connect(self._on_setting_changed)

        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(
                lambda _: refresh_sidebar_icons(self)
            )
        except Exception:
            pass

        self.retranslate_ui()
        if self.btn_keys:
            self.change_section(self.btn_keys[0])

    # ─── Build ────────────────────────────────────────────────────────────────

    def _build(self):
        # الـ FloatingPillNav يمتد أفقياً — ارتفاع ثابت
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(106)
        # مهم: لا يُسبّب minimum width على النافذة
        self.setMinimumWidth(0)

        # Layout خارجي يُمركز الـ pill
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(0)
        outer.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        # الـ pill — frame مستدير يحمل الأزرار مباشرة
        self._pill = QFrame()
        self._pill.setObjectName("pill-inner")
        # Preferred: يأخذ ما يحتاج لكن لا يتجاوز الـ outer
        self._pill.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._pill.setFixedHeight(90)
        self._pill.setMinimumWidth(0)

        self._pill_layout = QHBoxLayout(self._pill)
        self._pill_layout.setContentsMargins(6, 3, 6, 3)
        self._pill_layout.setSpacing(2)

        # نضيف الـ pill للـ outer بدون stretch — يتمركز طبيعياً
        outer.addWidget(self._pill)

        self._build_buttons()

    def _build_buttons(self):
        for btn in self.buttons.values():
            try:
                btn.setParent(None)
                btn.deleteLater()
            except Exception:
                pass
        self.buttons = {}
        self.btn_keys = []

        user         = self.settings.get("user", None)
        allowed_list = allowed_tabs(user) or []
        allowed_set  = set(allowed_list)
        ordered_keys = [k for k in ICON_PATHS if k in allowed_set]

        for key in ordered_keys:
            self._add_pill_btn(key)

        self.btn_keys = ordered_keys

        # بعد بناء الأزرار: احسب الحجم الطبيعي ثم اضبط maximum width
        self._pill.adjustSize()
        try:
            screen_w = QApplication.primaryScreen().availableGeometry().width()
            # الـ pill لا يتجاوز عرض الشاشة - 40px هامش
            self._pill.setMaximumWidth(screen_w - 40)
        except Exception:
            self._pill.setMaximumWidth(1600)

    def _add_pill_btn(self, key: str):
        btn = QToolButton()
        btn.setObjectName("pill-tab-btn")
        btn.setCheckable(True)
        btn.setAutoRaise(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        btn.setMinimumWidth(0)
        # Force text visible under icon
        try:
            from PySide6.QtGui import QFont
            f = QFont()
            f.setPointSize(8)
            btn.setFont(f)
        except Exception:
            pass

        icon_size = 48
        svg_icon  = get_sidebar_icon(key, icon_size)
        if not svg_icon.isNull():
            btn.setIcon(svg_icon)
        else:
            btn.setIcon(QIcon())
        btn.setIconSize(QSize(icon_size, icon_size))
        btn.setText(self._(key))
        btn.setToolTip(self._(key))

        btn.clicked.connect(lambda _=False, k=key: self.change_section(k))
        self._pill_layout.addWidget(btn)
        self.buttons[key] = btn

    # ─── Navigation ───────────────────────────────────────────────────────────

    def change_section(self, key: str):
        for k, b in self.buttons.items():
            b.setChecked(k == key)
            b.setProperty("active", k == key)
            b.style().unpolish(b)
            b.style().polish(b)
        self._active_key = key
        self.section_changed.emit(key)
        try:
            refresh_sidebar_icons(self)
        except Exception:
            pass

    # ─── backward compat ──────────────────────────────────────────────────────

    def toggle_sidebar(self):
        pass

    def refresh_stylesheet(self):
        self.setStyleSheet("")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    # ─── i18n ─────────────────────────────────────────────────────────────────

    def retranslate_ui(self):
        self._ = TranslationManager.get_instance().translate
        for key, btn in self.buttons.items():
            btn.setText(self._(key))
            btn.setToolTip(self._(key))
        refresh_sidebar_icons(self)
        self.refresh_stylesheet()

    def _on_setting_changed(self, key, value):
        if key in ("language", "direction"):
            self._build_buttons()
            self.retranslate_ui()
            if self._active_key and self._active_key in self.buttons:
                self.change_section(self._active_key)


# backward compat alias
Sidebar = FloatingPillNav