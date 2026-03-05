from PySide6.QtWidgets import QTableWidget, QHeaderView
from core.theme_manager import ThemeManager
from core.settings_manager import SettingsManager
from core.translator import TranslationManager

class CustomTable(QTableWidget):
    def __init__(self, rows=0, columns=0, parent=None, header_keys=None):
        super().__init__(rows, columns, parent)
        self.header_keys = header_keys or []
        self._ = TranslationManager.get_instance().translate
        self.setObjectName("custom-table")
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()
    def retranslate_ui(self):
        if self.header_keys and self.columnCount() == len(self.header_keys):
            self.setHorizontalHeaderLabels([self._(key) for key in self.header_keys])
