"""
ui/main_window.py — LOGIPORT
==============================
Lazy Loading محسّن:
- التبويبات تُستورد وتُنشأ فقط عند أول ضغطة عليها
- Dashboard فقط يُبنى فوراً
- وقت بدء التشغيل ينخفض من ~10 ثوانٍ إلى ~3 ثوانٍ
"""
from core.base_window import BaseWindow
from PySide6.QtWidgets import (
    QStackedWidget, QWidget, QHBoxLayout, QVBoxLayout, QApplication, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

# ── الاستيرادات الضرورية فقط عند بدء التشغيل ─────────────────────────────
from ui.widgets.sidebar import Sidebar
from ui.widgets.topbar import TopBar
from ui.tabs.dashboard_tab import DashboardTab        # أول تبويب — يُحمَّل فوراً
from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from services.notification_service import NotificationService
from core.data_bus import DataBus
from services.alert_service import AlertService
from services.backup_service import backup
import logging

logger = logging.getLogger(__name__)

# ── خريطة التبويبات: مسار الاستيراد الكامل (lazy) ────────────────────────
_TAB_IMPORT_MAP = {
    "users":             ("ui.tabs.users_tab",            "UsersTab"),
    "permissions":       ("ui.tabs.permissions_tab",      "PermissionsTab"),
    "users_permissions": ("ui.tabs.users_permissions_tab","UsersPermissionsTab"),
    "values":            ("ui.tabs.values_tab",           "ValuesTab"),
    "materials":         ("ui.tabs.materials_tab",        "MaterialsTab"),
    "clients":           ("ui.tabs.clients_tab",          "ClientsTab"),
    "companies":         ("ui.tabs.companies_tab",        "CompaniesTab"),
    "pricing":           ("ui.tabs.pricing_tab",          "PricingTab"),
    "entries":           ("ui.tabs.entries_tab",          "EntriesTab"),
    "transactions":      ("ui.tabs.transactions_tab",     "TransactionsTab"),
    "container_tracking":("ui.tabs.container_tracking_tab","ContainerTrackingTab"),
    "tasks":             ("ui.tabs.tasks_tab",             "TasksTab"),
    "documents":         ("ui.tabs.documents_tab",        "DocumentsTab"),
    "control_panel":     ("ui.tabs.admin_dashboard_tab",  "AdminDashboardTab"),
    "audit_trail":       ("ui.tabs.audit_trail_tab",      "AuditTrailTab"),
    "offices":           ("ui.tabs.offices_tab",            "OfficesTab"),
}

_TABS_NEEDING_USER = {"users", "users_permissions", "offices", "container_tracking", "tasks"}


class MainWindow(BaseWindow):
    """النافذة الرئيسية مع Lazy Loading للتبويبات."""

    def __init__(self, current_user=None):
        super().__init__()

        # يجب أن تُعرَّف قبل super().__init__() لأنه يُنادي retranslate_ui()
        self.tabs = {}
        self._tab_placeholders = {}
        self._profile_tab = None

        self.setObjectName("MainWindow")
        self.current_user = current_user
        self.set_translated_title("app_title")

        TranslationManager.get_instance().language_changed.connect(
            self._on_language_change
        )

        # بعد كل تغيير ثيم، Qt قد يُعيد توريث direction من QApplication
        # نُصحّح الاتجاه فوراً بناءً على اللغة الفعلية
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(
                lambda _: self.update_layout_direction()
            )
        except Exception:
            pass

        self._init_ui()
        self.update_layout_direction()   # تأكد من اتجاه الـ Sidebar عند أول تشغيل
        self._restore_window_geometry()
        self.retranslate_ui()

        self._notif_svc = NotificationService.get_instance()
        self._notif_svc.start()
        DataBus.get_instance()   # تهيئة مبكرة للـ event bus

        self._alert_svc = AlertService.get_instance()
        self._alert_svc.start()

        user_name = ""
        if current_user:
            user_name = (
                getattr(current_user, "full_name", None)
                or getattr(current_user, "username", None)
                or ""
            )
        _t = TranslationManager.get_instance().translate
        self._notif_svc.add_manual(
            _t("welcome_message").format(name=user_name),
            level="success",
            icon="🎉",
        )
        self._notif_svc.notify_login(user_name)

        # ── التحقق من التحديثات بعد 5 ثوانٍ (في الخلفية) ──────────────────
        from PySide6.QtCore import QTimer
        QTimer.singleShot(5000, self._check_for_updates)

        # ── تشغيل المزامنة التلقائية عند بدء التطبيق (بعد 3 ثوانٍ) ─────────
        QTimer.singleShot(3000, self._start_sync_if_configured)

    # ─── update check ────────────────────────────────────────────────────────

    def _check_for_updates(self):
        """يتحقق من التحديثات في الخلفية — لا يُجمّد الواجهة."""
        try:
            from services.updater_service import UpdaterService
            UpdaterService.get_instance().check_async(
                on_update_found=self._on_update_found,
            )
        except Exception as e:
            logger.debug(f"Update check skipped: {e}")

    def _on_update_found(self, update_info):
        """يُظهر نافذة التحديث في الـ main thread."""
        from PySide6.QtCore import QMetaObject, Qt
        # نستخدم QTimer للتشغيل في الـ main thread
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._show_update_dialog(update_info))

    def _show_update_dialog(self, update_info):
        try:
            from ui.dialogs.update_dialog import UpdateDialog
            dlg = UpdateDialog(update_info, parent=self)
            dlg.exec()
        except Exception as e:
            logger.error(f"Failed to show update dialog: {e}")

    # ─── geometry ────────────────────────────────────────────────────────────

    def _set_responsive_size(self):
        screen = QApplication.primaryScreen()
        sg = screen.availableGeometry()
        sw, sh = sg.width(), sg.height()
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.move(
            sg.left() + (sw - self.width()) // 2,
            sg.top() + (sh - self.height()) // 2,
        )

    def _restore_window_geometry(self):
        settings = SettingsManager.get_instance()
        saved_geometry = settings.get("window_geometry", None)
        from PySide6.QtCore import QByteArray
        try:
            if saved_geometry:
                return self.restoreGeometry(
                    QByteArray.fromHex(saved_geometry.encode())
                )
        except Exception:
            pass
        return False

    # ─── UI init ─────────────────────────────────────────────────────────────

    def _init_ui(self):
        # ═══════════════════════════════════════════════════
        # الهيكل الجديد — Floating Pill:
        #   VBox:
        #     TopBar (اسم المستخدم + بحث + لوغو)
        #     FloatingPillNav (أيقونة + نص — pill مُعلَّق)
        #     QStackedWidget (المحتوى يملأ الباقي)
        # ═══════════════════════════════════════════════════
        main_widget = QWidget()
        main_widget.setObjectName("main-widget")

        lang   = SettingsManager.get_instance().get("language", "ar")
        is_rtl = (lang == "ar")

        root_layout = QVBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── TopBar ────────────────────────────────────────
        self.top_bar = TopBar()
        self.top_bar.setLayoutDirection(Qt.RightToLeft if is_rtl else Qt.LeftToRight)
        self.top_bar.profile_requested.connect(self._open_profile)
        self.top_bar.logout_requested.connect(self._do_logout)
        try:
            self.top_bar.about_requested.connect(self._open_about)
        except Exception:
            pass
        try:
            self.top_bar.search_requested.connect(self._open_global_search)
        except Exception:
            pass
        try:
            self.top_bar.sync_settings_requested.connect(self._open_sync_settings)
        except Exception:
            pass
        root_layout.addWidget(self.top_bar)

        # ── Floating Pill Nav ─────────────────────────────
        self.sidebar = Sidebar()
        self.sidebar.section_changed.connect(self.switch_section)
        # مهم: نمنع الـ pill من تحديد minimum width للنافذة الرئيسية
        self.sidebar.setMinimumWidth(0)
        root_layout.addWidget(self.sidebar)

        # ── Content Stack ─────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setObjectName("content-stack")
        root_layout.addWidget(self.stack, 1)

        # Ctrl+F و Ctrl+K — البحث العام
        self._search_shortcut   = QShortcut(QKeySequence("Ctrl+F"), self)
        self._search_shortcut.activated.connect(self._open_global_search)
        self._search_shortcut_k = QShortcut(QKeySequence("Ctrl+K"), self)
        self._search_shortcut_k.activated.connect(self._open_global_search)

        # بناء التبويبات
        dashboard = DashboardTab()
        self.tabs["dashboard"] = dashboard
        self.stack.addWidget(dashboard)

        for tab_key in self.sidebar.btn_keys:
            if tab_key == "dashboard":
                continue
            if tab_key in _TAB_IMPORT_MAP:
                placeholder = QWidget()
                placeholder.setObjectName(f"placeholder_{tab_key}")
                self._tab_placeholders[tab_key] = placeholder
                self.stack.addWidget(placeholder)

        self.center_widget = main_widget   # backward compat
        self.setCentralWidget(main_widget)

        if self.sidebar.btn_keys:
            self.switch_section(self.sidebar.btn_keys[0])

    # ─── Lazy Tab Builder ─────────────────────────────────────────────────────

    def _build_tab(self, tab_key: str):
        """يبني التبويب عند أول طلب ويستبدل الـ placeholder."""
        if tab_key in self.tabs:
            return self.tabs[tab_key]

        module_path, class_name = _TAB_IMPORT_MAP[tab_key]
        try:
            import importlib
            module = importlib.import_module(module_path)
            tab_class = getattr(module, class_name)

            if tab_key in _TABS_NEEDING_USER:
                tab_instance = tab_class(current_user=self.current_user)
            else:
                tab_instance = tab_class()

            placeholder = self._tab_placeholders.get(tab_key)
            if placeholder:
                idx = self.stack.indexOf(placeholder)
                if idx >= 0:
                    self.stack.removeWidget(placeholder)
                    self.stack.insertWidget(idx, tab_instance)
                    placeholder.deleteLater()
                    del self._tab_placeholders[tab_key]
                else:
                    self.stack.addWidget(tab_instance)
            else:
                self.stack.addWidget(tab_instance)

            self.tabs[tab_key] = tab_instance
            logger.debug(f"Lazy loaded tab: {tab_key}")
            # تطبيق الاتجاه الحالي على التبويبة المُنشأة حديثاً
            lang = SettingsManager.get_instance().get("language", "ar")
            direction = Qt.RightToLeft if lang == "ar" else Qt.LeftToRight
            tab_instance.setLayoutDirection(direction)
            self._apply_direction_recursive(tab_instance, direction)
            # استدعاء retranslate_ui إذا كانت التبويبة تدعمه
            if hasattr(tab_instance, "retranslate_ui"):
                try:
                    tab_instance.retranslate_ui()
                except Exception:
                    pass
            return tab_instance

        except Exception as e:
            logger.error(f"Failed to build tab '{tab_key}': {e}", exc_info=True)
            return None

    def _get_or_build_profile_tab(self):
        if self._profile_tab is None:
            from ui.tabs.user_profile_tab import UserProfileTab
            self._profile_tab = UserProfileTab()
            self._profile_tab.logout_requested.connect(self._do_logout)
            self._profile_tab.close_requested.connect(self._do_close)
            self.stack.addWidget(self._profile_tab)
        return self._profile_tab

    # ─── navigation ──────────────────────────────────────────────────────────

    def switch_section(self, section_name: str):
        if section_name == "dashboard":
            self.stack.setCurrentWidget(self.tabs["dashboard"])
            return
        if section_name in self.tabs:
            self.stack.setCurrentWidget(self.tabs[section_name])
            return
        if section_name in _TAB_IMPORT_MAP:
            tab = self._build_tab(section_name)
            if tab:
                self.stack.setCurrentWidget(tab)

    # ─── dialogs ─────────────────────────────────────────────────────────────

    def _open_global_search(self):
        """يفتح نافذة البحث العام."""
        try:
            from ui.dialogs.global_search_dialog import GlobalSearchDialog
            dlg = GlobalSearchDialog(self)
            dlg.navigate_to.connect(self._navigate_to_result)
            dlg.exec()
        except Exception as e:
            logger.error(f"Global search error: {e}", exc_info=True)

    def _navigate_to_result(self, entity_key: str, record_id: int):
        """
        ينتقل للتاب المناسب ويحدد السجل.
        يُستدعى عند الضغط على نتيجة في البحث العام.
        """
        # 1) انتقل للتاب
        self.switch_section(entity_key)
        if hasattr(self.sidebar, "change_section"):
            self.sidebar.change_section(entity_key)

        # 2) اطلب من التاب تحديد السجل
        tab = self.tabs.get(entity_key)
        if tab and hasattr(tab, "select_record_by_id"):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, lambda: tab.select_record_by_id(record_id))

    def _open_about(self):
        try:
            from ui.dialogs.about_dialog import AboutDialog
            dlg = AboutDialog(self)
            dlg.exec()
        except Exception as e:
            QMessageBox.information(self, "LOGIPORT", f"v3.2.0\n{e}")

    def _open_sync_settings(self):
        try:
            from ui.dialogs.sync_settings_dialog import SyncSettingsDialog
            dlg = SyncSettingsDialog(self)
            dlg.exec()
        except Exception as e:
            logger.error(f"Failed to open sync settings: {e}")

    def _start_sync_if_configured(self):
        """يُشغَّل بعد 3 ثوانٍ من بدء التطبيق — يبدأ auto sync إذا كانت الإعدادات مكتملة."""
        try:
            from services.sync_service import get_sync_service
            from core.settings_manager import SettingsManager
            sm  = SettingsManager.get_instance()
            url = sm.get("sync_supabase_url", "")
            key = sm.get("sync_anon_key", "")
            office_raw = sm.get("sync_office_id", "")
            enabled = sm.get("sync_enabled", "false").lower() == "true"

            if not (url and key and office_raw and enabled):
                logger.info("Sync: auto-start skipped — not fully configured")
                return

            try:
                office_id = int(office_raw)
            except (ValueError, TypeError):
                logger.warning("Sync: invalid office_id '%s' — skipping auto-start", office_raw)
                return

            interval = int(sm.get("sync_interval_min", "5") or "5") * 60
            svc = get_sync_service()
            svc.configure(office_id=office_id, interval_seconds=interval)
            svc.start_auto_sync()
            logger.info("Sync: auto-sync started on app launch (office=%d, interval=%ds)", office_id, interval)
        except Exception as e:
            logger.error("Sync: failed to auto-start: %s", e)

    def _open_profile(self):
        self.stack.setCurrentWidget(self._get_or_build_profile_tab())

    # ─── logout / close ──────────────────────────────────────────────────────

    def _do_logout(self):
        """
        تسجيل الخروج — النهج: إعادة تهيئة نفس الـ instance بدل إنشاء نافذة جديدة.
        هذا يتجنب كل مشاكل setQuitOnLastWindowClosed وإغلاق الـ event loop.
        """
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QDialog
        from ui.login_window import LoginWindow

        # إشعار تسجيل الخروج قبل إيقاف الخدمة
        try:
            user_name = (
                getattr(self.current_user, "full_name", None)
                or getattr(self.current_user, "username", None)
                or ""
            )
            self._notif_svc.notify_logout(user_name)
        except Exception:
            pass

        self._notif_svc.stop()
        if hasattr(self, '_alert_svc'): self._alert_svc.stop()
        SettingsManager.get_instance().set("user", None)

        # مسح سياق المكتب
        try:
            from core.office_context import OfficeContext
            OfficeContext.clear()
        except Exception:
            pass

        # أخفي النافذة مؤقتاً
        self.hide()

        # افتح نافذة تسجيل الدخول (exec() يُبقي الـ event loop حياً)
        login = LoginWindow()
        result = login.exec()

        if result == QDialog.Accepted:
            new_user = getattr(login, "user", None)
            SettingsManager.get_instance().set("user", new_user)
            # أعد تهيئة نفس النافذة بدل إنشاء نافذة جديدة
            self._reinitialize(new_user)
        else:
            # المستخدم أغلق نافذة الدخول → اخرج
            QApplication.instance().quit()

    def _reinitialize(self, new_user):
        """
        إعادة تهيئة النافذة الحالية بمستخدم جديد.
        نُعيد استخدام نفس الـ QMainWindow instance لتجنب مشاكل event loop.
        """
        # 1) أوقف الإشعارات
        if hasattr(self, "_notif_svc") and self._notif_svc:
            try:
                self._notif_svc.stop()
                if hasattr(self, '_alert_svc'): self._alert_svc.stop()
            except Exception:
                pass

        # 2) امسح الـ stack widget كاملاً
        while self.stack.count() > 0:
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        # 3) أعد تعيين المتغيرات
        self.tabs = {}
        self._tab_placeholders = {}
        self._profile_tab = None
        self.current_user = new_user
        SettingsManager.get_instance().set("user", new_user)

        # 4) أعد بناء الـ UI (يعيد بناء sidebar + stack + dashboard)
        self._init_ui()
        self.update_layout_direction()  # تأكد من موضع Sidebar باللغة الصحيحة
        self.retranslate_ui()

        # 5) أعد تشغيل الإشعارات
        self._notif_svc = NotificationService.get_instance()
        self._notif_svc.start()

        self._alert_svc = AlertService.get_instance()
        self._alert_svc.start()

        user_name = (
            getattr(new_user, "full_name", None)
            or getattr(new_user, "username", None)
            or ""
        )
        _t = TranslationManager.get_instance().translate
        self._notif_svc.add_manual(
            _t("welcome_message").format(name=user_name),
            level="success",
            icon="🎉",
        )
        self._notif_svc.notify_login(user_name)

        # 6) أظهر النافذة
        self.show()
        self.raise_()
        self.activateWindow()

    def _do_close(self):
        self._notif_svc.stop()
        if hasattr(self, '_alert_svc'): self._alert_svc.stop()
        QApplication.instance().quit()

    def closeEvent(self, event):
        try:
            settings = SettingsManager.get_instance()
            geometry_hex = self.saveGeometry().toHex().data().decode()
            settings.set("window_geometry", geometry_hex)

            if settings.get("auto_backup", False):
                try:
                    backup()
                    logger.info("Automatic backup completed successfully.")
                except Exception as e:
                    logger.error(f"Automatic backup failed: {e}")
        except Exception as e:
            logger.error(f"Error saving window geometry: {e}")

        if hasattr(self, "_notif_svc") and self._notif_svc:
            self._notif_svc.stop()
        if hasattr(self, '_alert_svc'): self._alert_svc.stop()
        event.accept()

    # ─── language ────────────────────────────────────────────────────────────

    def update_layout_direction(self):
        lang      = SettingsManager.get_instance().get("language", "ar")
        direction = Qt.RightToLeft if lang == "ar" else Qt.LeftToRight

        # الـ pill أفقي — الاتجاه يتحكم في ترتيب التابات (RTL: يمين → يسار)
        for widget in [
            getattr(self, "center_widget", None),
            getattr(self, "top_bar",       None),
            getattr(self, "stack",         None),
            getattr(self, "sidebar",       None),
        ]:
            if widget is not None:
                widget.setLayoutDirection(direction)

        for tab in getattr(self, "tabs", {}).values():
            if tab is not None:
                tab.setLayoutDirection(direction)
                self._apply_direction_recursive(tab, direction)

        profile = getattr(self, "_profile_tab", None)
        if profile:
            profile.setLayoutDirection(direction)
            self._apply_direction_recursive(profile, direction)

    def _reposition_sidebar(self):
        """لا لزوم لها مع الـ Floating Pill — محفوظة للتوافق."""
        pass

    @staticmethod
    def _apply_direction_recursive(widget, direction):
        """تطبيق الاتجاه على كل الـ widgets الداخلية (جداول، lists، إلخ)."""
        from PySide6.QtWidgets import QTableWidget, QTableView, QListWidget, QListView, QHeaderView
        for child in widget.findChildren(QTableWidget):
            child.setLayoutDirection(direction)
            hdr = child.horizontalHeader()
            if hdr:
                hdr.setLayoutDirection(direction)
        for child in widget.findChildren(QTableView):
            child.setLayoutDirection(direction)
        for child in widget.findChildren(QListWidget):
            child.setLayoutDirection(direction)
        for child in widget.findChildren(QListView):
            child.setLayoutDirection(direction)

    def retranslate_ui(self):
        self.set_translated_title("app_title")
        if hasattr(self, "top_bar"):
            self.top_bar.retranslate_ui()
        if hasattr(self, "sidebar"):
            self.sidebar.retranslate_ui()
        for tab in getattr(self, "tabs", {}).values():
            if hasattr(tab, "retranslate_ui"):
                tab.retranslate_ui()
        profile = getattr(self, "_profile_tab", None)
        if profile and hasattr(profile, "retranslate_ui"):
            profile.retranslate_ui()

    def _on_language_change(self):
        # الاتجاه أولاً قبل retranslate لأن بعض الـ widgets تُعاد بناؤها
        self.update_layout_direction()
        self.retranslate_ui()