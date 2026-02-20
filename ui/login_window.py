"""
LoginWindow - Fully Responsive Professional Design
===================================================

EVERYTHING is responsive - including dialog size!
Adapts to screen size like modern professional applications.
"""

from PySide6.QtWidgets import (
    QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QComboBox, QFrame, QSizePolicy, QApplication
)
from PySide6.QtGui import QPixmap, QIcon, QScreen
from PySide6.QtCore import Qt, QSize
from core.base_dialog import BaseDialog
from core.settings_manager import SettingsManager
from core.translator import TranslationManager
from database.crud.users_crud import UsersCRUD
import os


class LoginWindow(BaseDialog):
    """
    Fully responsive professional login window.

    Features:
    - Dialog size adapts to screen
    - All elements scale proportionally
    - Professional spacing
    - Clean responsive layout
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoginDialog")
        self._ = TranslationManager.get_instance().translate
        self.user = None

        # ✅ حجم الـ dialog يتناسب مع حجم الشاشة
        self._set_responsive_size()

        self._ui_built = False
        self.init_ui()
        self._ui_built = True
        self.retranslate_ui()
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def _set_responsive_size(self):
        """Set dialog size based on screen size"""
        # Get screen geometry
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # ✅ حجم الـ dialog = نسبة من الشاشة
        # للشاشات الصغيرة: أكبر نسبة
        # للشاشات الكبيرة: نسبة أصغر

        if screen_width < 1366:  # Small screens
            width = min(420, int(screen_width * 0.8))
            height = min(550, int(screen_height * 0.85))
        elif screen_width < 1920:  # Medium screens (HD)
            width = 420
            height = 520
        else:  # Large screens (Full HD+)
            width = 450
            height = 550

        self.setFixedSize(width, height)

        # Center on screen
        self.move(
            (screen_width - width) // 2,
            (screen_height - height) // 2
        )

    def init_ui(self):
        """Initialize fully responsive UI"""

        # Get dialog dimensions for proportional sizing
        dialog_width = self.width()
        dialog_height = self.height()

        # ========== Logo ==========
        logo_label = QLabel()
        logo_label.setObjectName("logo_label")
        from core.paths import icons_path
        logo_path = str(icons_path("logo.png"))

        # ✅ Logo height = نسبة من dialog height
        logo_max_height = int(dialog_height * 0.3)  # 30% of dialog height
        logo_label.setMaximumHeight(logo_max_height)
        logo_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale proportionally
            max_logo_width = int(dialog_width * 0.2)  # 20% of dialog width
            if pixmap.width() > max_logo_width:
                pixmap = pixmap.scaledToWidth(max_logo_width, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignHCenter)
        else:
            logo_label.setText("🛡️")
            logo_label.setAlignment(Qt.AlignHCenter)

        # ========== App Title ==========
        self.title_label = QLabel("LOGIPORT")
        self.title_label.setObjectName("title")
        self.title_label.setAlignment(Qt.AlignHCenter)
        self.title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        # ========== Language Selector ==========
        self.language_box = QComboBox()
        self.language_box.setObjectName("language_box")
        _tm = TranslationManager.get_instance()
        self.language_box.addItem(_tm.translate("arabic"), "ar")
        self.language_box.addItem(_tm.translate("english"), "en")
        self.language_box.addItem(_tm.translate("turkish"), "tr")
        self.language_box.setCurrentIndex(
            ["ar", "en", "tr"].index(TranslationManager.get_instance().get_current_language())
        )
        self.language_box.currentIndexChanged.connect(self.change_language)

        # ✅ Width proportional
        lang_max_width = int(dialog_width * 0.28)  # 28% of dialog width
        self.language_box.setMaximumWidth(lang_max_width)
        self.language_box.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        # ========== Username Field ==========
        self.label_user = QLabel()
        self.label_user.setObjectName("subtitle")

        self.edit_user = QLineEdit()
        self.edit_user.setObjectName("edit_user")
        self.edit_user.setPlaceholderText(self._("username"))
        self.edit_user.setClearButtonEnabled(True)

        # ✅ Input height proportional
        input_min_height = max(36, int(dialog_height * 0.07))  # 7% of dialog height
        self.edit_user.setMinimumHeight(input_min_height)
        self.edit_user.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # ========== Password Field ==========
        self.label_pass = QLabel()
        self.label_pass.setObjectName("subtitle")

        self.edit_pass = QLineEdit()
        self.edit_pass.setObjectName("edit_pass")
        self.edit_pass.setPlaceholderText(self._("password"))
        self.edit_pass.setEchoMode(QLineEdit.Password)
        self.edit_pass.setClearButtonEnabled(True)
        self.edit_pass.setMinimumHeight(input_min_height)
        self.edit_pass.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # ========== Show/Hide Password Button ==========
        self.btn_show_pass = QPushButton()
        self.btn_show_pass.setObjectName("icon-btn")

        from core.paths import icons_path
        eye_icon_path = str(icons_path("eye.png"))
        eye_off_icon_path = str(icons_path("eye_off.png"))

        # ✅ Icon size proportional
        icon_size = max(18, int(dialog_width * 0.045))  # 4.5% of dialog width

        if os.path.exists(eye_icon_path):
            self.eye_icon = QIcon(eye_icon_path)
            self.eye_off_icon = QIcon(eye_off_icon_path) if os.path.exists(eye_off_icon_path) else QIcon()
            self.btn_show_pass.setIcon(self.eye_icon)
            self.btn_show_pass.setIconSize(QSize(icon_size, icon_size))
        else:
            self.btn_show_pass.setText("👁️")

        self.btn_show_pass.setCheckable(True)

        # ✅ Button size = input height (square)
        self.btn_show_pass.setMinimumSize(input_min_height, input_min_height)
        self.btn_show_pass.setMaximumSize(input_min_height, input_min_height)
        self.btn_show_pass.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_show_pass.setFlat(True)
        self.btn_show_pass.setToolTip(self._("show_password"))
        self.btn_show_pass.toggled.connect(self.toggle_password_visibility)

        # ========== Login Button ==========
        self.btn_login = QPushButton()
        self.btn_login.setObjectName("primary-btn")

        # ✅ Button height proportional
        button_min_height = max(40, int(dialog_height * 0.08))  # 8% of dialog height
        self.btn_login.setMinimumHeight(button_min_height)
        self.btn_login.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self.handle_login)

        # ========== Password Layout ==========
        pass_layout = QHBoxLayout()
        pass_layout.addWidget(self.edit_pass, 1)
        pass_layout.addWidget(self.btn_show_pass, 0)
        pass_layout.setContentsMargins(0, 0, 0, 0)

        # ✅ Spacing proportional
        spacing = max(6, int(dialog_width * 0.02))  # 2% of dialog width
        pass_layout.setSpacing(spacing)

        # ========== Copyright ==========
        self.copyright_label = QLabel()
        self.copyright_label.setObjectName("muted")
        self.copyright_label.setAlignment(Qt.AlignHCenter)
        self.copyright_label.setWordWrap(True)
        self.copyright_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        # ========== Card Container ==========
        card_widget = QFrame()
        card_widget.setObjectName("login-card")

        card_layout = QVBoxLayout(card_widget)

        # ✅ Margins proportional
        margin_h = int(dialog_width * 0.08)  # 8% horizontal margin
        margin_v = int(dialog_height * 0.03)  # 3% vertical margin
        card_layout.setContentsMargins(margin_h, margin_v, margin_h, margin_v)
        card_layout.setSpacing(0)

        # ========== Layout Assembly with Proportional Spacing ==========

        # Calculate spacings
        small_spacing = max(4, int(dialog_height * 0.01))   # 1%
        medium_spacing = max(8, int(dialog_height * 0.015)) # 1.5%
        large_spacing = max(12, int(dialog_height * 0.02))  # 2%
        xlarge_spacing = max(16, int(dialog_height * 0.03)) # 3%

        # Language at top right
        lang_row = QHBoxLayout()
        lang_row.addStretch(1)
        lang_row.addWidget(self.language_box, 0)
        card_layout.addLayout(lang_row)

        card_layout.addSpacing(small_spacing)

        # Logo
        card_layout.addWidget(logo_label, 0, Qt.AlignHCenter)
        card_layout.addSpacing(medium_spacing)

        # Title
        card_layout.addWidget(self.title_label)
        card_layout.addSpacing(large_spacing)

        # Username field
        card_layout.addWidget(self.label_user)
        card_layout.addSpacing(small_spacing)
        card_layout.addWidget(self.edit_user)
        card_layout.addSpacing(medium_spacing)

        # Password field
        card_layout.addWidget(self.label_pass)
        card_layout.addSpacing(small_spacing)
        card_layout.addLayout(pass_layout)
        card_layout.addSpacing(xlarge_spacing)

        # Login button
        card_layout.addWidget(self.btn_login)

        # Flexible space
        card_layout.addStretch(1)

        card_layout.addSpacing(medium_spacing)

        # Copyright
        card_layout.addWidget(self.copyright_label)

        # ========== Main Layout ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(card_widget)

        self.setLayout(main_layout)

        # ========== Shortcuts ==========
        self.edit_user.returnPressed.connect(self.handle_login)
        self.edit_pass.returnPressed.connect(self.handle_login)

        # Auto focus
        self.edit_user.setFocus()

    def change_language(self):
        """Change application language"""
        code = self.language_box.currentData()
        TranslationManager.get_instance().set_language(code)

    def toggle_password_visibility(self, checked):
        """Toggle password visibility"""
        if checked:
            self.edit_pass.setEchoMode(QLineEdit.Normal)
            if hasattr(self, "eye_off_icon") and not self.eye_off_icon.isNull():
                self.btn_show_pass.setIcon(self.eye_off_icon)
            else:
                self.btn_show_pass.setText("🚫")
            self.btn_show_pass.setToolTip(self._("hide_password"))
        else:
            self.edit_pass.setEchoMode(QLineEdit.Password)
            if hasattr(self, "eye_icon") and not self.eye_icon.isNull():
                self.btn_show_pass.setIcon(self.eye_icon)
            else:
                self.btn_show_pass.setText("👁️")
            self.btn_show_pass.setToolTip(self._("show_password"))

    def handle_login(self):
        """Handle login with validation"""
        username = self.edit_user.text().strip()
        password = self.edit_pass.text().strip()

        # Validation
        if not username:
            self.show_warning("error", "username_required")
            self.edit_user.setFocus()
            return

        if not password:
            self.show_warning("error", "password_required")
            self.edit_pass.setFocus()
            return

        # Authenticate
        user_crud = UsersCRUD()
        user = user_crud.authenticate(username, password)

        if user:
            self.user = user
            SettingsManager.get_instance().set("user", user)
            self.log_event(f"User login success: {username}")
            self.accept()
        else:
            self.show_warning("error", "invalid_login")
            self.log_event(f"User login failed: {username}", level="warning")
            self.edit_pass.clear()
            self.edit_pass.setFocus()

    def retranslate_ui(self):
        """Update UI text when language changes"""
        if not getattr(self, "_ui_built", False):
            return

        # Window title
        self.set_translated_title("login_title")

        # App title
        if hasattr(self, "title_label") and self.title_label:
            self.title_label.setText(self._("app_title"))

        # Username field
        if hasattr(self, "edit_user"):
            self.label_user.setText(self._("username"))
            self.edit_user.setPlaceholderText(self._("username_placeholder"))

        # Password field
        if hasattr(self, "edit_pass"):
            self.label_pass.setText(self._("password"))
            self.edit_pass.setPlaceholderText(self._("password_placeholder"))

        # Login button
        if hasattr(self, "btn_login"):
            self.btn_login.setText(self._("login"))

        # Show/hide password button
        if hasattr(self, "btn_show_pass"):
            tip_key = "hide_password" if self.btn_show_pass.isChecked() else "show_password"
            self.btn_show_pass.setToolTip(self._(tip_key))

        # Language names
        if hasattr(self, "language_box") and self.language_box:
            self.language_box.setItemText(0, self._("arabic"))
            self.language_box.setItemText(1, self._("english"))
            self.language_box.setItemText(2, self._("turkish"))

        # Copyright
        if hasattr(self, "copyright_label"):
            txt = self._("login_copyright")
            if txt and txt != "login_copyright":
                self.copyright_label.setText(txt)
            else:
                self.copyright_label.setText("© 2025 LOGIPORT — All Rights Reserved")