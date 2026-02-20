from PySide6.QtWidgets import QWidget, QTabWidget, QVBoxLayout
from core.translator import TranslationManager
from ui.tabs.users_tab import UsersTab
from ui.tabs.permissions_tab import PermissionsTab

class UsersPermissionsTab(QWidget):
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")
        self.tabs.tabBar().setObjectName("MainTabBar")
        self.tabs.setTabPosition(QTabWidget.North)

        self.users_tab = UsersTab(current_user=current_user)
        self.perms_tab = PermissionsTab()

        # لا تحفظ فهارس
        self.tabs.addTab(self.users_tab, self._("users_tab_title"))
        self.tabs.addTab(self.perms_tab, self._("permissions_tab_title"))

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # ✅ اربط بعد البناء
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self):
        users_idx = self.tabs.indexOf(self.users_tab)
        if users_idx != -1:
            self.tabs.setTabText(users_idx, self._("users_tab_title"))

        perms_idx = self.tabs.indexOf(self.perms_tab)
        if perms_idx != -1:
            self.tabs.setTabText(perms_idx, self._("permissions_tab_title"))

        # أعِد ترجمة التابات الداخلية
        hasattr(self.users_tab, "retranslate_ui") and self.users_tab.retranslate_ui()
        hasattr(self.perms_tab, "retranslate_ui") and self.perms_tab.retranslate_ui()
