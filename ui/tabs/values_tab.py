from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PySide6.QtCore import QTimer, Qt
from ui.tabs.countries_tab import CountriesTab
from ui.tabs.packaging_types_tab import PackagingTypesTab
from ui.tabs.delivery_methods_tab import DeliveryMethodsTab
from ui.tabs.currencies_tab import CurrenciesTab
from ui.tabs.material_types_tab import MaterialTypesTab
from core.translator import TranslationManager

class ValuesTab(QWidget):
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)

        # ترجمة
        self._tm = TranslationManager.get_instance()
        self._ = self._tm.translate

        # فلاغات
        self._ui_built = False
        self._lang_connected = False

        # Debounce للترجمة (تفادي نداءات متتالية سريعة)
        self._rt_timer = QTimer(self)
        self._rt_timer.setSingleShot(True)
        self._rt_timer.timeout.connect(self._do_retranslate)

        # UI
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("MainTabs")
        self.tabs.tabBar().setObjectName("MainTabBar")
        self.tabs.setTabPosition(QTabWidget.North)

        # التابات الفرعية (مرّر المستخدم الحالي)
        self.countries_tab = CountriesTab(parent=self.tabs, current_user=current_user)
        # أو أي متغيّر يحمل المستخدم بعد تسجيل الدخول
        self.packaging_types_tab = PackagingTypesTab(self, current_user=current_user)
        self.delivery_methods_tab = DeliveryMethodsTab(self, current_user=current_user)
        self.currencies_tab = CurrenciesTab(self, current_user=current_user)
        self.material_types_tab = MaterialTypesTab(self, current_user=current_user)

        # أضف التابات (النصوص ستُترجم في retranslate_ui)
        self.tabs.addTab(self.countries_tab, "")
        self.tabs.addTab(self.packaging_types_tab, "")
        self.tabs.addTab(self.delivery_methods_tab, "")
        self.tabs.addTab(self.currencies_tab, "")
        self.tabs.addTab(self.material_types_tab, "")

        main_layout.addWidget(self.tabs)

        # خلصنا البناء
        self._ui_built = True

        # ترجمة أولية + ربط إشارة تغيير اللغة مرة واحدة
        self.retranslate_ui()
        if not self._lang_connected:
            self._tm.language_changed.connect(self.retranslate_ui)
            self._lang_connected = True

    # ======================================================
    # Public: ترجمة الواجهة (Debounced)
    # ======================================================
    def retranslate_ui(self):
        if not self._ui_built:
            return
        # حدّث المرجع حتى لو تغيّرت instance داخليًا
        self._ = self._tm.translate
        self._rt_timer.start(0)

    # ======================================================
    # Private: الترجمة الفعلية
    # ======================================================
    def _do_retranslate(self):
        # 1) نصوص عناوين التابات
        self._set_tab_texts()

        # 2) إبلاغ التابات الفرعية تترجم حالها
        self._retranslate_children()

        # 3) اتجاه الواجهة بحسب اللغة
        self._apply_direction()

    def _set_tab_texts(self):
        titles = [
            self._("countries"),
            self._("packaging_types"),
            self._("delivery_methods"),
            self._("currencies"),
            self._("material_types"),
        ]
        for i, title in enumerate(titles):
            # امنع إعادة التعيين إذا النص نفسه (تقليل وميض)
            if self.tabs.tabText(i) != title:
                self.tabs.setTabText(i, title)

    def _retranslate_children(self):
        # استدعِ retranslate_ui على كل تاب فرعي إن وُجدت
        for tab in (
            self.countries_tab,
            self.packaging_types_tab,
            self.delivery_methods_tab,
            self.currencies_tab,
            self.material_types_tab,
        ):
            if hasattr(tab, "retranslate_ui"):
                tab.retranslate_ui()

    def _apply_direction(self):
        lang = self._tm.get_current_language()
        rtl = (lang == "ar")
        self.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
        # من الجيد ضبط اتجاه شريط التابات أيضاً
        self.tabs.setLayoutDirection(Qt.RightToLeft if rtl else Qt.LeftToRight)
