"""
LoginWindow - Fully Responsive Professional Design
===================================================

EVERYTHING is responsive - including dialog size!
Adapts to screen size like modern professional applications.
"""

from PySide6.QtWidgets import (
    QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QComboBox, QFrame, QSizePolicy, QApplication, QCheckBox,
    QGraphicsDropShadowEffect
)
from PySide6.QtGui import QPixmap, QIcon, QScreen, QColor
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer
from core.base_dialog import BaseDialog
from core.settings_manager import SettingsManager
from core.translator import TranslationManager
from database.crud.users_crud import UsersCRUD, AccountLockedError
import os
import sys
from ui.utils.wheel_blocker import block_wheel_in


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
        super().__init__(parent)   # BaseDialog يستدعي _restore_geometry هنا
        self.setObjectName("LoginDialog")
        self._ = TranslationManager.get_instance().translate
        self.user = None

        # أيقونة + عنوان الـ titlebar
        try:
            from core.paths import icons_path
            from PySide6.QtGui import QIcon
            icon_file = str(icons_path("logo.ico"))
            if not __import__("os").path.exists(icon_file):
                icon_file = str(icons_path("logo.png"))
            self.setWindowIcon(QIcon(icon_file))
        except Exception:
            pass
        self.setWindowTitle(self._("login_title"))

        # إذا لم تكن هناك geometry محفوظة، نضع الحجم الافتراضي
        if not self.settings.get("dialog_geometry_LoginWindow"):
            self._set_responsive_size()

        self._ui_built = False
        self.init_ui()
        block_wheel_in(self)
        self._ui_built = True
        self.retranslate_ui()
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)


    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not getattr(self, "_field_ux_installed", False):
            try:
                from ui.utils.field_navigation import setup_field_ux
                setup_field_ux(self)
                self._field_ux_installed = True
            except Exception:
                pass

        # ✅ Fade-in animation — مرة وحدة فقط عند أول ظهور
        if not getattr(self, "_fade_in_played", False):
            self._fade_in_played = True
            try:
                self.setWindowOpacity(0.0)
                self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
                self._fade_anim.setDuration(220)
                self._fade_anim.setStartValue(0.0)
                self._fade_anim.setEndValue(1.0)
                self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
                self._fade_anim.start()
            except Exception:
                self.setWindowOpacity(1.0)

        # ✅ فحص دوري لحالة Caps Lock (يلتقط الحالة حتى لو كانت مفعّلة
        # من قبل ما يفتح المستخدم النافذة أصلاً)
        if not getattr(self, "_caps_lock_timer", None):
            self._caps_lock_timer = QTimer(self)
            self._caps_lock_timer.setInterval(400)
            self._caps_lock_timer.timeout.connect(self._poll_caps_lock)
            self._caps_lock_timer.start()
            self._poll_caps_lock()  # فحص فوري بدون انتظار أول tick

    def closeEvent(self, event):
        try:
            if getattr(self, "_caps_lock_timer", None):
                self._caps_lock_timer.stop()
        except Exception:
            pass
        super().closeEvent(event)

    def _set_responsive_size(self):
        """Set dialog initial size based on screen — resizable by user"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # الحجم الافتراضي حسب الشاشة
        if screen_width < 1366:
            width = min(420, int(screen_width * 0.8))
            height = min(550, int(screen_height * 0.85))
        elif screen_width < 1920:
            width = 420
            height = 520
        else:
            width = 450
            height = 550

        # حد أدنى للقياس — لا fixed
        self.setMinimumSize(340, 460)
        self.resize(width, height)

        # توسيط
        self.move(
            screen_geometry.left() + (screen_width - width) // 2,
            screen_geometry.top() + (screen_height - height) // 2
        )

    def init_ui(self):
        """Initialize fully responsive UI"""

        # Get dialog dimensions for proportional sizing
        dialog_width = self.width()
        dialog_height = self.height()

        # ========== Logo ==========
        logo_label = QLabel()
        logo_label.setObjectName("logo_label")
        self.logo_label = logo_label
        from core.paths import icons_path
        logo_path = str(icons_path("logo.png"))

        # ✅ Logo height = نسبة من dialog height
        logo_max_height = int(dialog_height * 0.3)  # 30% of dialog height
        self._logo_max_height_ratio = 0.3
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
        # الاسم التجاري ثابت دائماً — لا يُترجم
        self.title_label = QLabel("LOGIPORT")
        self.title_label.setObjectName("login-brand-title")
        self.title_label.setAlignment(Qt.AlignHCenter)
        self.title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.title_label.setStyleSheet(
            "font-size: 22px; font-weight: 800; letter-spacing: 4px;"
            "color: #0D1B2A; background: transparent;"
        )

        # Subtitle — يُترجم
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("login-brand-subtitle")
        self.subtitle_label.setAlignment(Qt.AlignHCenter)
        self.subtitle_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.subtitle_label.setStyleSheet(
            "font-size: 11px; color: #C9A84C; background: transparent; letter-spacing: 1px;"
        )

        # Gold divider under title
        self.title_divider = QFrame()
        self.title_divider.setFixedSize(40, 2)
        self.title_divider.setStyleSheet("background: #C9A84C; border-radius: 1px;")

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
        # عرض كافي لعرض "العربية" / "English" / "Türkçe" بالكامل
        self.language_box.setMinimumWidth(110)
        self.language_box.setMaximumWidth(130)
        self.language_box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # ========== Username Field ==========
        self.label_user = QLabel()
        self.label_user.setObjectName("subtitle")

        self.edit_user = QLineEdit()
        self.edit_user.setObjectName("username")
        self.edit_user.setPlaceholderText(self._("username"))
        self.edit_user.setClearButtonEnabled(True)

        # أيقونة المستخدم داخل الحقل
        try:
            from core.paths import icons_path
            user_icon_path = str(icons_path("user.png"))
            if os.path.exists(user_icon_path):
                self.edit_user.addAction(QIcon(user_icon_path), QLineEdit.LeadingPosition)
        except Exception:
            pass

        # تعبئة آخر يوزرنيم محفوظ (إذا كان "تذكرني" مفعّلاً بالمرة السابقة)
        try:
            if self.settings.get("login_remember_me", False):
                last_username = self.settings.get("login_last_username", "") or ""
                if last_username:
                    self.edit_user.setText(last_username)
        except Exception:
            pass

        # ✅ Input height proportional
        input_min_height = max(36, int(dialog_height * 0.07))  # 7% of dialog height
        self._input_min_height = input_min_height
        self.edit_user.setMinimumHeight(input_min_height)
        self.edit_user.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # ========== Password Field ==========
        self.label_pass = QLabel()
        self.label_pass.setObjectName("subtitle")

        self.edit_pass = QLineEdit()
        self.edit_pass.setObjectName("password")
        self.edit_pass.setPlaceholderText(self._("password"))
        self.edit_pass.setEchoMode(QLineEdit.Password)
        self.edit_pass.setClearButtonEnabled(True)
        self.edit_pass.setMinimumHeight(input_min_height)
        self.edit_pass.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # تحذير Caps Lock — مخفي افتراضياً، يظهر فقط أثناء الكتابة بالباسوورد
        self.caps_lock_label = QLabel()
        self.caps_lock_label.setObjectName("caps-lock-warning")
        self.caps_lock_label.setStyleSheet(
            "color: #B45309; font-size: 10.5px; font-weight: 600; background: transparent;"
        )
        self.caps_lock_label.setVisible(False)
        self._caps_lock_on = False

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
        self._button_min_height = button_min_height
        self.btn_login.setMinimumHeight(button_min_height)
        self.btn_login.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self.handle_login)

        # ========== Remember Me + Forgot Password ==========
        self.chk_remember = QCheckBox()
        self.chk_remember.setObjectName("chk_remember")
        self.chk_remember.setCursor(Qt.PointingHandCursor)
        try:
            self.chk_remember.setChecked(bool(self.settings.get("login_remember_me", False)))
        except Exception:
            pass

        self.btn_forgot = QPushButton()
        self.btn_forgot.setObjectName("link-btn")
        self.btn_forgot.setFlat(True)
        self.btn_forgot.setCursor(Qt.PointingHandCursor)
        self.btn_forgot.setStyleSheet(
            "QPushButton#link-btn { border: none; background: transparent;"
            " color: #0D1B2A; font-size: 11px; text-decoration: underline; }"
            "QPushButton#link-btn:hover { color: #C9A84C; }"
        )
        self.btn_forgot.clicked.connect(self._show_forgot_password)

        remember_row = QHBoxLayout()
        remember_row.setContentsMargins(0, 0, 0, 0)
        remember_row.addWidget(self.chk_remember)
        remember_row.addStretch(1)
        remember_row.addWidget(self.btn_forgot)

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
        self.card_widget = card_widget

        # ظل ناعم لإحساس "عائم" بدل لوحة مسطحة
        try:
            shadow = QGraphicsDropShadowEffect(card_widget)
            shadow.setBlurRadius(36)
            shadow.setXOffset(0)
            shadow.setYOffset(8)
            shadow.setColor(QColor(13, 27, 42, 70))  # Navy بشفافية
            card_widget.setGraphicsEffect(shadow)
        except Exception:
            pass

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

        # Title block
        card_layout.addWidget(self.title_label)
        card_layout.addSpacing(4)
        card_layout.addWidget(self.title_divider, 0, Qt.AlignHCenter)
        card_layout.addSpacing(4)
        card_layout.addWidget(self.subtitle_label)
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
        card_layout.addWidget(self.caps_lock_label)
        card_layout.addSpacing(small_spacing)
        card_layout.addLayout(remember_row)
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
        # احفظ في SettingsManager حتى يبدأ MainWindow باللغة الصحيحة
        SettingsManager.get_instance().set("language", code)

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

        # ✅ تعطيل الزر أثناء المعالجة لمنع النقر المزدوج + إظهار حالة تحميل
        original_btn_text = self.btn_login.text()
        self.btn_login.setEnabled(False)
        self.btn_login.setText(self._("logging_in"))
        QApplication.processEvents()

        try:
            user_crud = UsersCRUD()
            user = user_crud.authenticate(username, password)
        except AccountLockedError as locked:
            minutes = max(1, (locked.retry_after_seconds + 59) // 60)
            title = self._("error")
            message = self._("account_locked_message").format(minutes=minutes)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, title, message)
            self.log_event(f"Login blocked (account locked): {username}", level="warning")
            self.edit_pass.clear()
            self.edit_pass.setFocus()
            return
        finally:
            self.btn_login.setEnabled(True)
            self.btn_login.setText(original_btn_text)

        if user:
            self.user = user
            SettingsManager.get_instance().set("user", user)

            # ── تذكرني: حفظ/مسح آخر يوزرنيم بحسب حالة الـ checkbox ──────────
            try:
                remember = self.chk_remember.isChecked()
                self.settings.set("login_remember_me", remember)
                self.settings.set("login_last_username", username if remember else "")
            except Exception:
                pass

            # ── تحميل المكتب وتفعيل OfficeContext ──────────────────────────
            try:
                from core.office_context import OfficeContext
                office_id = getattr(user, "office_id", None)
                # office محمّل الآن بـ joinedload في authenticate()
                office    = getattr(user, "office", None)
                # fallback: إذا لم يُحمَّل لأي سبب، نجلبه يدوياً
                if office_id and office is None:
                    from database.crud.offices_crud import OfficesCRUD
                    office = OfficesCRUD().get_by_id(office_id)
                OfficeContext.set(office_id, office)
                import logging
                logging.getLogger(__name__).debug(
                    f"OfficeContext set: id={office_id}, name={office.get_name() if office else None}"
                )
            except Exception as _oc_err:
                import logging
                logging.getLogger(__name__).warning(f"OfficeContext load failed: {_oc_err}")

            self.log_event(f"User login success: {username}")
            self.accept()
        else:
            self.show_warning("error", "invalid_login")
            self.log_event(f"User login failed: {username}", level="warning")
            self.edit_pass.clear()
            self.edit_pass.setFocus()

    def _show_forgot_password(self):
        """رسالة توجيهية بسيطة — لا يوجد إعادة تعيين تلقائي حالياً"""
        self.show_info("forgot_password_title", "forgot_password_message")

    @staticmethod
    def _query_caps_lock_state() -> bool:
        """
        يفحص الحالة الفعلية لمفتاح Caps Lock من نظام التشغيل مباشرة
        (وليس فقط عند ضغطه وهو مركّز بحقل معيّن) — يعمل على Windows.
        على أنظمة أخرى يرجع False دائماً (best-effort).
        """
        if sys.platform != "win32":
            return False
        try:
            import ctypes
            VK_CAPITAL = 0x14
            return bool(ctypes.windll.user32.GetKeyState(VK_CAPITAL) & 1)
        except Exception:
            return False

    def _poll_caps_lock(self):
        """يُستدعى دورياً (QTimer) لتحديث ظهور تحذير Caps Lock"""
        try:
            is_on = self._query_caps_lock_state()
            if is_on != getattr(self, "_caps_lock_on", False):
                self._caps_lock_on = is_on
                self._update_caps_lock_label()
        except Exception:
            pass

    def _update_caps_lock_label(self):
        if getattr(self, "_caps_lock_on", False):
            self.caps_lock_label.setText("⚠ " + self._("caps_lock_warning"))
            self.caps_lock_label.setVisible(True)
        else:
            self.caps_lock_label.setVisible(False)

    def resizeEvent(self, event):
        """إعادة ضبط القياسات النسبية الأساسية عند تغيير حجم النافذة يدوياً"""
        super().resizeEvent(event)
        if not getattr(self, "_ui_built", False):
            return
        try:
            h = self.height()
            w = self.width()

            input_h = max(36, int(h * 0.07))
            if hasattr(self, "edit_user"):
                self.edit_user.setMinimumHeight(input_h)
            if hasattr(self, "edit_pass"):
                self.edit_pass.setMinimumHeight(input_h)
            if hasattr(self, "btn_show_pass"):
                self.btn_show_pass.setMinimumSize(input_h, input_h)
                self.btn_show_pass.setMaximumSize(input_h, input_h)

            if hasattr(self, "btn_login"):
                self.btn_login.setMinimumHeight(max(40, int(h * 0.08)))

            if hasattr(self, "logo_label"):
                self.logo_label.setMaximumHeight(int(h * 0.3))
        except Exception:
            pass

    def retranslate_ui(self):
        """Update UI text when language changes"""
        if not getattr(self, "_ui_built", False):
            return

        # Window title
        self.set_translated_title("login_title")

        # Brand title ثابت دائماً
        if hasattr(self, "title_label") and self.title_label:
            self.title_label.setText("LOGIPORT")

        # Subtitle يتترجم
        if hasattr(self, "subtitle_label") and self.subtitle_label:
            self.subtitle_label.setText(self._("app_subtitle"))

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

        # Remember me + Forgot password
        if hasattr(self, "chk_remember"):
            self.chk_remember.setText(self._("remember_me"))
        if hasattr(self, "btn_forgot"):
            self.btn_forgot.setText(self._("forgot_password"))

        # Caps lock label (إن كان ظاهراً حالياً، حدّث نصه باللغة الجديدة)
        if hasattr(self, "caps_lock_label"):
            self._update_caps_lock_label()

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