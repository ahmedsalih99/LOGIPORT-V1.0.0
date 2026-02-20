from PySide6.QtGui import QIntValidator
from PySide6.QtGui import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QLineEdit, QFrame, QMessageBox,
    QSizePolicy, QApplication, QFileDialog
)
from core.base_dialog import BaseDialog
from core.settings_manager import SettingsManager
from core.translator import TranslationManager
from database.db_utils import get_db_path


def get_combo_index(value, code_map, fallback_map=None, default_code=None):
    """Helper function to get combo box index"""
    fallback_map = fallback_map or {}
    default_code = default_code or code_map[0]
    val = str(value)
    if val not in code_map:
        val = fallback_map.get(val, default_code)
    return code_map.index(val)


class SettingsWindow(BaseDialog):
    """
    Fully responsive settings window.

    Dialog size and all components scale based on screen size.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsDialog")
        self.settings = SettingsManager.get_instance()
        self._ = TranslationManager.get_instance().translate

        # ✅ حجم Dialog responsive
        self._set_responsive_size()

        self.init_ui()
        self.retranslate_ui()
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def _set_responsive_size(self):
        """Set dialog size based on screen size"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # ⭐ أحجام أكبر
        if screen_width < 1366:  # Small screens
            width = min(550, int(screen_width * 0.85))
            height = min(650, int(screen_height * 0.9))
        elif screen_width < 1920:  # Medium screens (HD)
            width = 640
            height = 700  # ⭐ زدت الارتفاع
        else:  # Large screens (Full HD+)
            width = 680
            height = 750  # ⭐ زدت الارتفاع

        self.setFixedSize(width, height)

        # Center on screen
        self.move(
            (screen_width - width) // 2,
            (screen_height - height) // 2
        )

        self.dialog_width = width
        self.dialog_height = height

    def init_ui(self):
        """Initialize responsive UI"""

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ========== Card Container ==========
        card = QFrame()
        card.setObjectName("settings-card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        card_layout = QVBoxLayout(card)

        # ✅ Margins proportional
        margin_h = max(12, int(self.dialog_width * 0.025))  # 2.5% horizontal
        margin_v = max(8, int(self.dialog_height * 0.018))  # 1.8% vertical
        card_layout.setContentsMargins(margin_h, margin_v, margin_h, margin_h)

        # ✅ Spacing proportional
        spacing = max(8, int(self.dialog_height * 0.018))  # 1.8% of height
        card_layout.setSpacing(spacing)

        # ========== Color Bar ==========
        color_bar = QFrame()
        color_bar.setObjectName("settings-card-bar")
        color_bar.setFixedHeight(4)
        card_layout.addWidget(color_bar)

        # ========== Title ==========
        title = QLabel(self._("settings"))
        title.setObjectName("settings-title")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        # ========== General Settings Section ==========
        section1 = QLabel(self._("general_settings"))
        section1.setObjectName("settings-section-title")
        card_layout.addWidget(section1)

        # ✅ Combo box width proportional
        combo_min_width = max(160, int(self.dialog_width * 0.33))  # 33% of width

        # Language row
        row = QHBoxLayout()
        row.setSpacing(max(6, int(self.dialog_width * 0.015)))  # 1.5% spacing
        self.lang_label = QLabel(self._("language"))
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("settings-combo")
        self.lang_combo.setMinimumWidth(combo_min_width)
        row.addWidget(self.lang_label)
        row.addWidget(self.lang_combo)
        card_layout.addLayout(row)

        # Theme row
        row = QHBoxLayout()
        row.setSpacing(max(6, int(self.dialog_width * 0.015)))
        self.theme_label = QLabel(self._("theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("settings-combo")
        self.theme_combo.setMinimumWidth(combo_min_width)
        row.addWidget(self.theme_label)
        row.addWidget(self.theme_combo)
        card_layout.addLayout(row)

        # Font size row
        row = QHBoxLayout()
        row.setSpacing(max(6, int(self.dialog_width * 0.015)))
        self.font_size_label = QLabel(self._("font_size"))
        self.font_size_combo = QComboBox()
        self.font_size_combo.setObjectName("settings-combo")
        self.font_size_combo.setMinimumWidth(combo_min_width)
        row.addWidget(self.font_size_label)
        row.addWidget(self.font_size_combo)
        card_layout.addLayout(row)

        # ========== Separator ==========
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setObjectName("settings-separator")
        card_layout.addWidget(sep1)

        # ========== Documents Settings Section ==========
        section2 = QLabel(self._("documents_settings"))
        section2.setObjectName("settings-section-title")
        card_layout.addWidget(section2)

        # Documents language row
        row = QHBoxLayout()
        row.setSpacing(max(6, int(self.dialog_width * 0.015)))
        self.docs_lang_label = QLabel(self._("documents_language"))
        self.docs_lang_combo = QComboBox()
        self.docs_lang_combo.setObjectName("settings-combo")
        self.docs_lang_combo.setMinimumWidth(combo_min_width)
        row.addWidget(self.docs_lang_label)
        row.addWidget(self.docs_lang_combo)
        card_layout.addLayout(row)

        # Documents output path row
        docs_path_row = QHBoxLayout()
        docs_path_row.setSpacing(max(6, int(self.dialog_width * 0.015)))
        self.docs_path_label = QLabel(self._("documents_path"))
        self.docs_path_input = QLineEdit()
        self.docs_path_input.setObjectName("settings-input")
        self.docs_path_input.setReadOnly(True)
        self.docs_path_input.setPlaceholderText(self._("choose_folder"))
        self.docs_path_browse_btn = QPushButton("...")
        self.docs_path_browse_btn.setObjectName("secondary-btn")
        self.docs_path_browse_btn.setFixedWidth(36)
        self.docs_path_browse_btn.setCursor(Qt.PointingHandCursor)
        self.docs_path_browse_btn.clicked.connect(self._browse_documents_folder)
        self.docs_path_clear_btn = QPushButton("✕")
        self.docs_path_clear_btn.setObjectName("secondary-btn")
        self.docs_path_clear_btn.setFixedWidth(30)
        self.docs_path_clear_btn.setToolTip(self._("choose_folder"))
        self.docs_path_clear_btn.setCursor(Qt.PointingHandCursor)
        self.docs_path_clear_btn.clicked.connect(self._clear_documents_folder)
        docs_path_row.addWidget(self.docs_path_label, 0)
        docs_path_row.addWidget(self.docs_path_input, 1)
        docs_path_row.addWidget(self.docs_path_browse_btn, 0)
        docs_path_row.addWidget(self.docs_path_clear_btn, 0)
        card_layout.addLayout(docs_path_row)

        # ========== Separator ==========
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("settings-separator")
        card_layout.addWidget(sep2)

        # ========== Database Settings Section ==========
        section3 = QLabel(self._("database_settings"))
        section3.setObjectName("settings-section-title")
        card_layout.addWidget(section3)

        # Database path
        db_row = QHBoxLayout()
        db_row.setSpacing(max(6, int(self.dialog_width * 0.015)))
        self.db_path_label = QLabel(self._("database_path"))
        self.db_path_input = QLineEdit()
        self.db_path_input.setObjectName("settings-input")
        self.db_path_input.setReadOnly(True)
        db_row.addWidget(self.db_path_label, 0)
        db_row.addWidget(self.db_path_input, 1)
        card_layout.addLayout(db_row)

        # Backup checkbox
        self.auto_backup_check = QCheckBox(self._("auto_backup"))
        self.auto_backup_check.setObjectName("settings-checkbox")
        card_layout.addWidget(self.auto_backup_check)

        # ========== Separator ==========
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        sep3.setObjectName("settings-separator")
        card_layout.addWidget(sep3)

        # ========== Separator 4 ==========
        sep4 = QFrame()
        sep4.setFrameShape(QFrame.HLine)
        sep4.setObjectName("settings-separator")
        card_layout.addWidget(sep4)

        # ========== Transaction Numbering Section ==========
        section_numbering = QLabel(self._("transaction_numbering"))
        section_numbering.setObjectName("settings-section-title")
        card_layout.addWidget(section_numbering)

        # Last transaction number
        row = QHBoxLayout()
        row.setSpacing(max(6, int(self.dialog_width * 0.015)))
        self.last_tx_label = QLabel(self._("last_transaction_number"))
        self.last_tx_input = QLineEdit()
        self.last_tx_input.setObjectName("settings-input")
        self.last_tx_input.setPlaceholderText("26000")
        from PySide6.QtGui import QIntValidator
        self.last_tx_input.setValidator(QIntValidator(0, 999999999))
        row.addWidget(self.last_tx_label, 0)
        row.addWidget(self.last_tx_input, 1)
        card_layout.addLayout(row)

        # Prefix
        row = QHBoxLayout()
        row.setSpacing(max(6, int(self.dialog_width * 0.015)))
        self.prefix_label = QLabel(self._("transaction_prefix"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setObjectName("settings-input")
        self.prefix_input.setPlaceholderText(self._("prefix_placeholder"))
        self.prefix_input.setMaxLength(10)
        row.addWidget(self.prefix_label, 0)
        row.addWidget(self.prefix_input, 1)
        card_layout.addLayout(row)

        # Preview
        row = QHBoxLayout()
        row.setSpacing(max(6, int(self.dialog_width * 0.015)))
        self.preview_label = QLabel(self._("next_transaction_preview"))
        self.preview_value = QLineEdit()
        self.preview_value.setObjectName("settings-input")
        self.preview_value.setReadOnly(True)
        self.preview_value.setStyleSheet("background-color: #f5f5f5; color: #666;")
        row.addWidget(self.preview_label, 0)
        row.addWidget(self.preview_value, 1)
        card_layout.addLayout(row)

        # Connect signals
        self.last_tx_input.textChanged.connect(self._update_transaction_preview)
        self.prefix_input.textChanged.connect(self._update_transaction_preview)

        # ========== Buttons ==========
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(max(8, int(self.dialog_width * 0.015)))

        # ✅ Button height proportional
        btn_height = max(36, int(self.dialog_height * 0.07))  # 7% of height

        self.save_btn = QPushButton(self._("save"))
        self.save_btn.setObjectName("primary-btn")
        self.save_btn.setMinimumHeight(btn_height)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_settings)

        self.cancel_btn = QPushButton(self._("cancel"))
        self.cancel_btn.setObjectName("secondary-btn")
        self.cancel_btn.setMinimumHeight(btn_height)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)

        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.cancel_btn)
        card_layout.addLayout(buttons_layout)

        # ========== Main Layout ==========
        main_layout.addWidget(card)
        self.setLayout(main_layout)

        # ========== Load Settings ==========
        self.load_settings()

    def load_settings(self):
        """Load current settings into UI"""
        # Language combo
        self.lang_combo.clear()
        self.lang_combo.addItem(self._("arabic"), "ar")
        self.lang_combo.addItem(self._("english"), "en")
        self.lang_combo.addItem(self._("turkish"), "tr")
        current_lang = self.settings.get("language", "ar")
        idx = get_combo_index(current_lang, ["ar", "en", "tr"])
        self.lang_combo.setCurrentIndex(idx)

        # Theme combo
        self.theme_combo.clear()
        self.theme_combo.addItem(self._("light"), "light")
        self.theme_combo.addItem(self._("dark"), "dark")
        current_theme = self.settings.get("theme", "dark")
        idx = get_combo_index(current_theme, ["light", "dark"])
        self.theme_combo.setCurrentIndex(idx)

        # Font size combo
        self.font_size_combo.clear()
        self.font_size_combo.addItem(self._("small"), "small")
        self.font_size_combo.addItem(self._("medium"), "medium")
        self.font_size_combo.addItem(self._("large"), "large")
        current_font = self.settings.get("font_size", "medium")
        idx = get_combo_index(current_font, ["small", "medium", "large"])
        self.font_size_combo.setCurrentIndex(idx)

        # Documents output path
        docs_out_path = self.settings.get_documents_output_path()
        self.docs_path_input.setText(docs_out_path)

        # Documents language combo
        self.docs_lang_combo.clear()
        self.docs_lang_combo.addItem(self._("arabic"), "ar")
        self.docs_lang_combo.addItem(self._("english"), "en")
        self.docs_lang_combo.addItem(self._("turkish"), "tr")
        current_docs_lang = self.settings.get("documents_language", "ar")
        idx = get_combo_index(current_docs_lang, ["ar", "en", "tr"])
        self.docs_lang_combo.setCurrentIndex(idx)

        # Database path
        db_path = str(get_db_path())
        self.db_path_input.setText(db_path)

        # Auto backup
        auto_backup = self.settings.get("auto_backup", True)
        self.auto_backup_check.setChecked(auto_backup)

        # Transaction numbering
        last_tx_number = self.settings.get_transaction_last_number()
        self.last_tx_input.setText(str(last_tx_number))

        tx_prefix = self.settings.get_transaction_prefix()
        self.prefix_input.setText(tx_prefix)

        self._update_transaction_preview()

    def save_settings(self):
        """Save settings and apply changes"""
        try:
            # ⭐ 1. حفظ الترقيم أولاً (قبل كل شي!)
            try:
                last_tx_text = self.last_tx_input.text().strip()
                if last_tx_text:
                    last_tx_number = int(last_tx_text)
                    self.settings.set_transaction_last_number(last_tx_number)

                tx_prefix = self.prefix_input.text().strip()
                self.settings.set_transaction_prefix(tx_prefix)
            except ValueError:
                self.show_error(self._("error"), self._("invalid_transaction_number"))
                return

            # 2. Get values
            new_lang = self.lang_combo.currentData()
            new_theme = self.theme_combo.currentData()
            new_font = self.font_size_combo.currentData()
            new_docs_lang = self.docs_lang_combo.currentData()
            auto_backup = self.auto_backup_check.isChecked()

            # Check if language changed
            lang_changed = new_lang != self.settings.get("language")

            # Check if theme changed
            theme_changed = new_theme != self.settings.get("theme")

            # Save settings
            self.settings.set("language", new_lang)
            self.settings.set("theme", new_theme)
            self.settings.set("font_size", new_font)
            self.settings.set("documents_language", new_docs_lang)
            self.settings.set("auto_backup", auto_backup)

            # Documents output path
            docs_out_path = self.docs_path_input.text().strip()
            self.settings.set_documents_output_path(docs_out_path)

            # Apply language if changed
            if lang_changed:
                self.settings.set_language(new_lang)

            # Apply theme if changed
            if theme_changed:
                from core.theme_manager import ThemeManager
                ThemeManager.get_instance().apply_theme()

            # Show success message
            self.show_info(self._("success"), self._("settings_saved_successfully"))

            # ⭐ في النهاية فقط
            self.accept()

        except Exception as e:
            self.show_error(self._("error"), str(e))

    def retranslate_ui(self):
        """Update UI text when language changes"""
        self._ = TranslationManager.get_instance().translate
        self.set_translated_title("settings")

        # Update labels
        if hasattr(self, 'lang_label'):
            self.lang_label.setText(self._("language"))
        if hasattr(self, 'theme_label'):
            self.theme_label.setText(self._("theme"))
        if hasattr(self, 'font_size_label'):
            self.font_size_label.setText(self._("font_size"))
        if hasattr(self, 'docs_lang_label'):
            self.docs_lang_label.setText(self._("documents_language"))
        if hasattr(self, 'db_path_label'):
            self.db_path_label.setText(self._("database_path"))
        if hasattr(self, 'auto_backup_check'):
            self.auto_backup_check.setText(self._("auto_backup"))

        # Update buttons
        if hasattr(self, 'save_btn'):
            self.save_btn.setText(self._("save"))
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.setText(self._("cancel"))

        # Reload combo boxes with translated items
        if hasattr(self, 'lang_combo'):
            self.load_settings()

        # Transaction numbering labels
        if hasattr(self, 'last_tx_label'):
            self.last_tx_label.setText(self._("last_transaction_number"))
        if hasattr(self, 'prefix_label'):
            self.prefix_label.setText(self._("transaction_prefix"))
        if hasattr(self, 'prefix_input'):
            self.prefix_input.setPlaceholderText(self._("prefix_placeholder"))
        if hasattr(self, 'preview_label'):
            self.preview_label.setText(self._("next_transaction_preview"))

    def _browse_documents_folder(self):
        """فتح نافذة اختيار مجلد حفظ المستندات"""
        current = self.docs_path_input.text().strip() or ""
        folder = QFileDialog.getExistingDirectory(
            self,
            self._("select_documents_folder"),
            current,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if folder:
            self.docs_path_input.setText(folder)

    def _clear_documents_folder(self):
        """إعادة المسار للافتراضي (داخل التطبيق)"""
        self.docs_path_input.clear()

    def _update_transaction_preview(self):
        """تحديث معاينة رقم المعاملة القادم"""
        try:
            last_number_text = self.last_tx_input.text().strip()
            if not last_number_text:
                self.preview_value.setText("---")
                return

            last_number = int(last_number_text)
            next_number = last_number + 1

            prefix = self.prefix_input.text().strip()
            preview = f"{prefix}{next_number}" if prefix else str(next_number)
            self.preview_value.setText(preview)
        except ValueError:
            self.preview_value.setText("---")