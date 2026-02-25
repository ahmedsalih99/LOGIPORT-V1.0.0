"""
Sidebar - Fully Responsive Professional Design
===============================================

Features:
- Width adapts to screen size
- All elements scale proportionally
- Smooth animations
- New theme system compatible
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QPushButton, QSizePolicy, QLabel,
    QHBoxLayout, QSpacerItem, QWidget, QToolButton, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation
from PySide6.QtGui import QIcon, QPixmap
from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from database.crud.permissions_crud import allowed_tabs
from core.paths import resource_path
from ui.utils.svg_icons import get_sidebar_icon, refresh_sidebar_icons, get_icon, QSize as _QSize

ICON_PATHS = {
    "dashboard": "icons/dashboard.png",
    "materials": "icons/materials.png",
    "clients": "icons/clients.png",
    "companies": "icons/companies.png",
    "pricing": "icons/pricing.png",
    "entries": "icons/entries.png",
    "transactions": "icons/transactions.png",
    "documents": "icons/documents.png",
    "values": "icons/values.png",
    "audit_trail": "icons/audit_trail.png",
    "control_panel": "icons/settings.png",
    "users_permissions": "icons/users.png",
}


class Sidebar(QFrame):
    """
    Fully responsive sidebar.

    Width and all components scale based on screen size.
    """

    section_changed = Signal(str)
    sidebar_toggled = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")

        self._ = TranslationManager.get_instance().translate
        self.settings = SettingsManager.get_instance()

        # ✅ حالة التوسيع - الأحجام responsive
        self._set_responsive_widths()

        self.expanded = True
        self.setMinimumWidth(self.expanded_width)
        self.setMaximumWidth(self.expanded_width)

        # لياوت رئيسي
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)

        # ✅ Margins proportional
        margin_bottom = max(10, int(self.expanded_width * 0.06))  # 6% of width
        self.main_layout.setContentsMargins(0, 0, 0, margin_bottom)

        # شعـار + اسم
        self._build_header()

        # الأزرار حسب الصلاحيات
        self.main_layout.addStretch(1)   # مسافة مرنة فوق الأزرار
        self._build_buttons_from_permissions()
        self.main_layout.addStretch(1)   # مسافة مرنة تحت الأزرار

        self._build_footer_toggle()

        # إشعارات الترجمة/الإعدادات
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)
        self.settings.setting_changed.connect(self._on_setting_changed)

        # Theme change → أعد رسم أيقونات السايدبار فور تطبيق الثيم الجديد
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(
                lambda _: refresh_sidebar_icons(self)
            )
        except Exception:
            pass

        # اتجاه أولي حسب اللغة
        self.retranslate_ui()

        # اختر أول تبويب
        if self.btn_keys:
            self.change_section(self.btn_keys[0])

        self._sidebar_animation = None

    def _set_responsive_widths(self):
        """Set sidebar widths based on screen size"""
        screen = QApplication.primaryScreen()
        screen_width = screen.availableGeometry().width()

        # ✅ Sidebar widths = نسبة من الشاشة
        if screen_width < 1366:  # Small screens
            self.expanded_width = max(180, int(screen_width * 0.15))  # 15%
            self.collapsed_width = max(50, int(screen_width * 0.04))  # 4%
        elif screen_width < 1920:  # Medium screens (HD)
            self.expanded_width = 210
            self.collapsed_width = 54
        else:  # Large screens (Full HD+)
            self.expanded_width = max(220, int(screen_width * 0.12))  # 12%
            self.collapsed_width = max(60, int(screen_width * 0.03))  # 3%

        # Store for children
        self.screen_width = screen_width

    # ==================== UI Parts ====================

    def _build_header(self):
        """Build logo and app name header"""

        self.logo_box = QFrame(self)
        self.logo_box.setObjectName("SidebarLogoBox")

        # ✅ Logo box height proportional
        logo_height = max(60, int(self.expanded_width * 0.35))  # 35% of width
        self.logo_box.setFixedHeight(logo_height)

        logo_layout = QVBoxLayout(self.logo_box)

        # ✅ Margins proportional
        margin_top = max(8, int(logo_height * 0.15))  # 15% of logo box height
        logo_layout.setContentsMargins(0, margin_top, 0, 0)
        logo_layout.setSpacing(2)

        # Logo image
        self.logo_img = QLabel()
        self.logo_img.setObjectName("sidebar-logo-img")
        pix = QPixmap(resource_path("icons", "logo.png"))

        # ✅ Logo size proportional
        logo_img_size = max(40, int(self.expanded_width * 0.23))  # 23% of width

        if not pix.isNull():
            self.logo_img.setPixmap(
                pix.scaled(
                    logo_img_size, logo_img_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
        self.logo_img.setAlignment(Qt.AlignHCenter)
        logo_layout.addWidget(self.logo_img)

        # App name
        self.logo_label = QLabel(self._("app_name"))
        self.logo_label.setObjectName("sidebar-app-name")
        self.logo_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        logo_layout.addWidget(self.logo_label)

        self.main_layout.addWidget(self.logo_box)

        # Separator
        self.main_layout.addSpacing(6)
        line = QFrame()
        line.setObjectName("sidebar-separator")
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        self.main_layout.addWidget(line)
        self.main_layout.addSpacing(5)

    def _build_footer_toggle(self):
        """Build toggle button at bottom"""

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.toggle_btn = QPushButton()
        self.toggle_btn.setObjectName("sidebar-toggle-btn")

        # ✅ Toggle button size proportional
        toggle_size = max(36, int(self.expanded_width * 0.19))  # 19% of width
        self.toggle_btn.setFixedSize(toggle_size, toggle_size)

        self.toggle_btn.setCursor(Qt.PointingHandCursor)

        # ✅ Icon size proportional — يجب تعريفها قبل الاستخدام
        icon_size = max(20, int(toggle_size * 0.6))  # 60% of button size
        _toggle_svg = get_icon("menu_burger", icon_size)
        if not _toggle_svg.isNull():
            self.toggle_btn.setIcon(_toggle_svg)
        else:
            self.toggle_btn.setIcon(QIcon(resource_path("icons", "menu_burger.png")))
        self.toggle_btn.setIconSize(QSize(icon_size, icon_size))

        self.toggle_btn.setToolTip(self._("toggle_sidebar"))
        self.toggle_btn.clicked.connect(self.toggle_sidebar)

        row.addWidget(self.toggle_btn)
        row.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.main_layout.addLayout(row)

    # ==================== Behavior ====================

    def add_button(self, key, label, icon_path=None):
        """Add a button to the sidebar"""

        btn = QToolButton()
        btn.setObjectName("sidebar-btn")
        btn.setCheckable(True)
        btn.setAutoRaise(True)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(label)

        # ✅ Button height proportional
        btn_height = max(38, int(self.expanded_width * 0.18))  # 18% of width
        btn.setMinimumHeight(btn_height)

        # ✅ Icon size proportional
        icon_size = max(18, int(btn_height * 0.6))  # 60% of button height
        btn.setIconSize(QSize(icon_size, icon_size))

        if self.expanded:
            btn.setText(label)

        # SVG icon — fallback to PNG if not available
        svg_icon = get_sidebar_icon(key, icon_size)
        if not svg_icon.isNull():
            btn.setIcon(svg_icon)
        elif icon_path:
            btn.setIcon(QIcon(resource_path(*icon_path.split("/"))))

        lang = self.settings.get("language", "ar")
        is_rtl = (lang == "ar")
        btn.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        btn.clicked.connect(lambda checked=False, k=key: self.change_section(k))
        self.main_layout.addWidget(btn)

        if not hasattr(self, 'buttons'):
            self.buttons = {}

        self.buttons[key] = btn

    def change_section(self, key):
        """Change active section"""
        for k, b in self.buttons.items():
            b.setChecked(k == key)
        self.section_changed.emit(key)

    def toggle_sidebar(self):
        """Toggle sidebar expanded/collapsed with safe width animation"""

        self.expanded = not self.expanded

        target_width = (
            self.expanded_width if self.expanded
            else self.collapsed_width
        )

        # نوقف أي أنيميشن سابق
        if self._sidebar_animation and self._sidebar_animation.state():
            self._sidebar_animation.stop()

        # نحرر القيود قبل بدء الحركة
        self.setMinimumWidth(0)

        # أنيميشن آمن على maximumWidth فقط
        self._sidebar_animation = QPropertyAnimation(self, b"maximumWidth")
        self._sidebar_animation.setDuration(220)
        self._sidebar_animation.setStartValue(self.width())
        self._sidebar_animation.setEndValue(target_width)

        # بعد انتهاء الأنيميشن نثبت العرض بشكل نظيف
        def finalize_width():
            self.setFixedWidth(target_width)

        self._sidebar_animation.finished.connect(finalize_width)
        self._sidebar_animation.start()

        # تحديث عناصر الواجهة
        self.logo_label.setVisible(self.expanded)
        self._apply_expand_state_to_buttons()

        # إشعار المين ويندو
        self.sidebar_toggled.emit(self.expanded)

    def _apply_expand_state_to_buttons(self):
        """Update button appearance when expanding/collapsing"""

        lang = self.settings.get("language", "ar")
        is_rtl = (lang == "ar")

        for key, btn in self.buttons.items():
            label = self._(key)

            if self.expanded:
                btn.setText(label)
                btn.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
                btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            else:
                btn.setText("")

            # ✅ Icon size stays proportional
            btn_height = btn.minimumHeight()
            icon_size = max(18, int(btn_height * 0.6))
            btn.setIconSize(QSize(icon_size, icon_size))

            # Dynamic property for theme
            btn.setProperty("layout_dir", "rtl" if is_rtl else "ltr")

            # Refresh style
            btn.style().unpolish(btn)
            btn.style().polish(btn)

            btn.setToolTip(label)

    # ==================== Direction / i18n ====================

    def retranslate_ui(self):
        """Update UI text when language changes"""

        # Update translations
        self._ = TranslationManager.get_instance().translate
        self.logo_label.setText(self._("app_name"))
        self.toggle_btn.setToolTip(self._("toggle_sidebar"))

        if hasattr(self, 'buttons'):
            for key, btn in self.buttons.items():
                btn.setToolTip(self._(key))

        # Update layout direction
        lang = self.settings.get("language", "ar")
        self.setLayoutDirection(Qt.RightToLeft if lang == "ar" else Qt.LeftToRight)

        self._apply_expand_state_to_buttons()

        # Refresh icons with current theme color
        refresh_sidebar_icons(self)

        # Refresh stylesheet
        self.refresh_stylesheet()

    def _on_setting_changed(self, key, value):
        """Handle settings changes"""
        if key in ("language", "direction"):
            self.retranslate_ui()

    def refresh_stylesheet(self):
        """Refresh theme stylesheet"""
        self.setStyleSheet("")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _build_buttons_from_permissions(self):
        """Build sidebar buttons based on user permissions"""

        # Clear old buttons
        if hasattr(self, 'buttons'):
            for btn in self.buttons.values():
                try:
                    btn.setParent(None)
                except Exception:
                    pass

        self.buttons = {}

        # Get current user
        user = self.settings.get("user", None)

        # Get allowed tabs
        allowed_list = allowed_tabs(user) or []
        try:
            allowed_set = set(allowed_list)
        except Exception:
            allowed_set = set()

        # Order by ICON_PATHS and filter allowed
        ordered_keys = [k for k in ICON_PATHS.keys() if k in allowed_set]

        # Create buttons
        for key in ordered_keys:
            self.add_button(key, self._(key), ICON_PATHS.get(key))

        # Store visible keys
        self.btn_keys = ordered_keys