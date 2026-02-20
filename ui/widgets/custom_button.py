from PySide6.QtWidgets import QPushButton
from core.theme_manager import ThemeManager
from core.settings_manager import SettingsManager
from core.translator import TranslationManager

class CustomButton(QPushButton):
    def __init__(self, text_key, parent=None):
        super().__init__(parent)
        self.text_key = text_key
        self._ = TranslationManager.get_instance().translate
        self.setObjectName("custom-btn")   # هكذا سيأخذ CSS مباشرة من الثيم
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()
    def retranslate_ui(self):
        self.setText(self._(self.text_key))
