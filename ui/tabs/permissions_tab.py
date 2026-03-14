from collections import defaultdict

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLineEdit, QListWidget,
    QListWidgetItem, QLabel, QScrollArea, QGridLayout, QCheckBox, QPushButton,
    QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt

from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from core.permissions import has_perm, is_admin

from database.crud.permissions_crud import (
    get_all_permissions, get_role_permissions,
    assign_permission_to_role, remove_permission_from_role,
    RolesCRUD
)

from ui.dialogs.add_role_dialog import AddRoleDialog
from ui.widgets.custom_button import CustomButton
from ui.dialogs.view_details.view_role_dialog import ViewRoleDialog


# ترتيب ثابت لعرض المجموعات (الأكثر أهمية أولاً)
_CATEGORY_ORDER = [
    "DASHBOARD", "TRANSACTIONS", "ENTRIES", "DOCUMENTS",
    "CLIENTS", "COMPANIES", "MATERIALS", "PRICING",
    "CONTAINERS", "VALUES", "OFFICES", "USERS", "AUDIT", "SETTINGS", "ADMIN",
]

# ترجمة اسم الـ category إلى تسمية بالثلاث لغات
_CATEGORY_LABELS = {
    "DASHBOARD":     {"ar": "لوحة التحكم",      "en": "Dashboard",    "tr": "Kontrol Paneli"},
    "TRANSACTIONS":  {"ar": "المعاملات",          "en": "Transactions", "tr": "İşlemler"},
    "ENTRIES":       {"ar": "الإدخالات",          "en": "Entries",      "tr": "Girişler"},
    "DOCUMENTS":     {"ar": "المستندات",          "en": "Documents",    "tr": "Belgeler"},
    "CLIENTS":       {"ar": "العملاء",            "en": "Clients",      "tr": "Müşteriler"},
    "COMPANIES":     {"ar": "الشركات",            "en": "Companies",    "tr": "Şirketler"},
    "MATERIALS":     {"ar": "المواد",             "en": "Materials",    "tr": "Malzemeler"},
    "PRICING":       {"ar": "التسعير",            "en": "Pricing",      "tr": "Fiyatlandırma"},
    "VALUES":        {"ar": "القيم والإعدادات",   "en": "Values",       "tr": "Değerler"},
    "OFFICES":       {"ar": "المكاتب",            "en": "Offices",      "tr": "Ofisler"},
    "USERS":         {"ar": "المستخدمون والأدوار","en": "Users & Roles","tr": "Kullanıcılar"},
    "AUDIT":         {"ar": "سجل التدقيق",        "en": "Audit Log",    "tr": "Denetim"},
    "SETTINGS":      {"ar": "الإعدادات",          "en": "Settings",     "tr": "Ayarlar"},
    "CONTAINERS":    {"ar": "تتبع الحاويات",      "en": "Containers",   "tr": "Konteynerler"},
    "ADMIN":         {"ar": "لوحة الإدارة",       "en": "Admin Panel",  "tr": "Yönetim Paneli"},
}


class PermissionsTab(QWidget):
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate

        settings = SettingsManager.get_instance()
        self.current_user = (
            current_user or settings.get("user", None) or getattr(parent, "current_user", None)
        )

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 6, 10, 10)
        main_layout.setSpacing(10)

        # ── يسار: الأدوار ─────────────────────────────────────────────────
        self.roles_box = QGroupBox(self._("roles"))
        self.roles_box.setObjectName("perm-side-card")
        roles_layout = QVBoxLayout(self.roles_box)
        roles_layout.setContentsMargins(12, 10, 12, 12)
        roles_layout.setSpacing(8)

        self.role_search = QLineEdit()
        self.role_search.setObjectName("search-field")
        self.role_search.setPlaceholderText(self._("search_role"))
        self.role_search.textChanged.connect(self.filter_roles)
        roles_layout.addWidget(self.role_search)

        self.roles_list = QListWidget()
        self.roles_list.setObjectName("roles-list")
        self.roles_list.itemSelectionChanged.connect(self.on_role_selected)
        self.roles_list.itemDoubleClicked.connect(self._on_role_double_clicked)
        roles_layout.addWidget(self.roles_list)

        self.btn_add_role = CustomButton(self._("add_role"))
        self.btn_add_role.clicked.connect(self.show_add_role_dialog)
        roles_layout.addWidget(self.btn_add_role)

        main_layout.addWidget(self.roles_box, 1)

        # ── يمين: صلاحيات الدور ───────────────────────────────────────────
        self.right_box = QGroupBox(self._("role_permissions"))
        self.right_box.setObjectName("perm-main-card")
        right_layout = QVBoxLayout(self.right_box)
        right_layout.setContentsMargins(12, 10, 12, 12)
        right_layout.setSpacing(10)

        self.selected_role_label = QLabel()
        self.selected_role_label.setObjectName("section-title")
        right_layout.addWidget(self.selected_role_label)

        self.selected_role_desc = QLabel()
        self.selected_role_desc.setObjectName("muted-text")
        right_layout.addWidget(self.selected_role_desc)

        # أزرار تحديد/إلغاء التحديد
        check_btns_layout = QHBoxLayout()
        check_btns_layout.setSpacing(8)
        self.btn_select_all = QPushButton(self._("select_all_permissions"))
        self.btn_select_all.setObjectName("action-btn")
        self.btn_unselect_all = QPushButton(self._("unselect_all_permissions"))
        self.btn_unselect_all.setObjectName("action-btn")
        self.btn_select_all.clicked.connect(self.select_all_permissions)
        self.btn_unselect_all.clicked.connect(self.unselect_all_permissions)
        check_btns_layout.addStretch()
        check_btns_layout.addWidget(self.btn_unselect_all)
        check_btns_layout.addWidget(self.btn_select_all)
        right_layout.addLayout(check_btns_layout)

        # ScrollArea تحتوي على مجموعات الصلاحيات
        self.scroll = QScrollArea()
        self.scroll.setObjectName("perm-scroll")
        self.scroll.setWidgetResizable(True)

        self._scroll_content = QWidget()
        self._scroll_content.setObjectName("perm-grid-container")
        self._scroll_layout = QVBoxLayout(self._scroll_content)
        self._scroll_layout.setContentsMargins(8, 6, 8, 6)
        self._scroll_layout.setSpacing(12)
        self._scroll_layout.addStretch()

        self.scroll.setWidget(self._scroll_content)
        right_layout.addWidget(self.scroll)

        # أزرار الحفظ/إعادة التعيين
        btns_layout = QHBoxLayout()
        btns_layout.addStretch()
        self.btn_reset = QPushButton(self._("reset_to_role_defaults"))
        self.btn_reset.setObjectName("secondary-btn")
        self.btn_reset.clicked.connect(self.reset_to_role_defaults)
        self.btn_save = QPushButton(self._("save"))
        self.btn_save.setObjectName("primary-btn")
        self.btn_save.clicked.connect(self.save_permissions)
        btns_layout.addWidget(self.btn_reset)
        btns_layout.addWidget(self.btn_save)
        right_layout.addLayout(btns_layout)

        main_layout.addWidget(self.right_box, 3)

        self.setLayout(main_layout)

        # الحالة
        self.selected_role = None
        self.permissions = []
        self.roles = []
        self.perm_checkboxes: dict[int, QCheckBox] = {}

        self._apply_permission_visibility()
        self.load_roles()
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────
        try:
            from core.data_bus import DataBus
            DataBus.get_instance().subscribe('users', self._load_data)
        except Exception:
            pass

    def _apply_permission_visibility(self):
        u = self.current_user
        can_add_role  = is_admin(u) or has_perm(u, "add_role")
        can_save_perm = is_admin(u) or has_perm(u, "edit_permission")
        self.btn_add_role.setVisible(can_add_role)
        self.btn_save.setVisible(can_save_perm)
        self.btn_reset.setVisible(can_save_perm)
        self.btn_select_all.setVisible(can_save_perm)
        self.btn_unselect_all.setVisible(can_save_perm)

    def _user_id(self):
        u = self.current_user
        if isinstance(u, dict):
            return u.get("id")
        return getattr(u, "id", None)

    def _current_lang(self) -> str:
        return TranslationManager.get_instance().get_current_language()

    def _category_label(self, cat: str) -> str:
        lang = self._current_lang()
        labels = _CATEGORY_LABELS.get(cat, {})
        return labels.get(lang, labels.get("en", cat))

    # ──────────────────────────────────────────────────────────────────────
    # Roles
    # ──────────────────────────────────────────────────────────────────────
    def load_roles(self):
        self.roles = RolesCRUD().get_all(language=self._current_lang())
        self.roles_list.clear()
        for role in self.roles:
            item = QListWidgetItem(role["label"])
            item.setData(1000, role)
            self.roles_list.addItem(item)

    def filter_roles(self, text):
        t = (text or "").strip().lower()
        for i in range(self.roles_list.count()):
            item = self.roles_list.item(i)
            item.setHidden(t not in item.text().lower())

    def on_role_selected(self):
        selected_items = self.roles_list.selectedItems()
        if not selected_items:
            self.selected_role_label.setText("")
            self.selected_role_desc.setText("")
            self._clear_scroll_content()
            return
        role = selected_items[0].data(1000)
        self.selected_role = role
        self.selected_role_label.setText(self._("role") + ": " + role["label"])
        self.selected_role_desc.setText(role.get("description", "") or "")
        self.load_permissions(role["id"])

    def _on_role_double_clicked(self, item):
        role = item.data(1000) if item else None
        if not role:
            return
        dlg = ViewRoleDialog(role, current_user=self.current_user, parent=self)
        dlg.exec()

    def show_add_role_dialog(self):
        dlg = AddRoleDialog(self)
        if dlg.exec():
            self.load_roles()

    # ──────────────────────────────────────────────────────────────────────
    # Responsive layout — يُعيد توزيع الأعمدة عند تغيير حجم النافذة
    # ──────────────────────────────────────────────────────────────────────
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.selected_role:
            self.load_permissions(self.selected_role["id"])

    # ──────────────────────────────────────────────────────────────────────
    # Permissions — عرض مجمّع بـ categories
    # ──────────────────────────────────────────────────────────────────────
    def _clear_scroll_content(self):
        """يمسح كل widgets داخل الـ scroll content."""
        layout = self._scroll_layout
        # احذف كل شيء ما عدا الـ stretch في الآخر
        while layout.count() > 1:
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.perm_checkboxes.clear()

    def load_permissions(self, role_id: int):
        lang = self._current_lang()
        self.permissions = get_all_permissions(language=lang)

        # مسح المحتوى القديم
        self._clear_scroll_content()

        # تجميع الصلاحيات بـ category
        by_cat: dict[str, list] = defaultdict(list)
        for perm in self.permissions:
            cat = (perm.get("category") or "OTHER").upper()
            by_cat[cat].append(perm)

        # صلاحيات الدور الحالية من DB
        role_perm_ids = {p["id"] for p in get_role_permissions(role_id, language=lang)}

        # رتّب المجموعات حسب الترتيب المحدد ثم الباقية أبجدياً
        ordered_cats = []
        for cat in _CATEGORY_ORDER:
            if cat in by_cat:
                ordered_cats.append(cat)
        for cat in sorted(by_cat.keys()):
            if cat not in ordered_cats:
                ordered_cats.append(cat)

        insert_pos = self._scroll_layout.count() - 1  # قبل الـ stretch

        for cat in ordered_cats:
            perms_in_cat = by_cat[cat]
            cat_label = self._category_label(cat)

            # GroupBox لكل category
            grp = QGroupBox(cat_label)
            grp.setObjectName("perm-category-group")
            grp_layout = QGridLayout(grp)
            grp_layout.setContentsMargins(10, 8, 10, 8)
            grp_layout.setHorizontalSpacing(14)
            grp_layout.setVerticalSpacing(6)

            # عدد الأعمدة حسب عرض التطبيق الفعلي
            # نأخذ عرض النافذة الكلية ونطرح عرض يسار (الأدوار ~220px) + margins
            main_win = self.window()
            total_w = main_win.width() if main_win else 1200
            right_w = int(total_w * 0.75) - 60   # 75% للجهة اليمين تقريباً
            if right_w >= 1100:
                col_count = 5
            elif right_w >= 800:
                col_count = 4
            elif right_w >= 550:
                col_count = 3
            else:
                col_count = 2
            for idx, perm in enumerate(perms_in_cat):
                cb = QCheckBox(perm["label"])
                cb.setToolTip(perm.get("description") or perm["code"])
                cb.setChecked(perm["id"] in role_perm_ids)
                self.perm_checkboxes[perm["id"]] = cb
                row, col = divmod(idx, col_count)
                grp_layout.addWidget(cb, row, col)

            # stretch في آخر الصف لمنع امتداد العمود الأخير
            grp_layout.setColumnStretch(col_count, 1)

            self._scroll_layout.insertWidget(insert_pos, grp)
            insert_pos += 1

    def clear_permissions(self):
        for cb in self.perm_checkboxes.values():
            cb.setChecked(False)

    # ──────────────────────────────────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────────────────────────────────
    def save_permissions(self):
        if not self.selected_role:
            return
        role_id = self.selected_role["id"]
        uid = self._user_id()

        checked_ids = {pid for pid, cb in self.perm_checkboxes.items() if cb.isChecked()}
        current_ids = {p["id"] for p in get_role_permissions(role_id)}

        for perm_id in checked_ids - current_ids:
            assign_permission_to_role(role_id, perm_id, user_id=uid)
        for perm_id in current_ids - checked_ids:
            remove_permission_from_role(role_id, perm_id, user_id=uid)

        try:
            from core.permissions import clear_permission_cache
            clear_permission_cache()
        except Exception:
            pass

        QMessageBox.information(self, self._("save"), self._("permissions_updated_successfully"))
        self.load_permissions(role_id)

    def reset_to_role_defaults(self):
        if not self.selected_role:
            return
        role_id = self.selected_role["id"]
        uid = self._user_id()

        for perm_id in [p["id"] for p in get_role_permissions(role_id)]:
            remove_permission_from_role(role_id, perm_id, user_id=uid)

        try:
            from core.permissions import clear_permission_cache
            clear_permission_cache()
        except Exception:
            pass

        self.load_permissions(role_id)
        QMessageBox.information(
            self, self._("reset_to_role_defaults"), self._("permissions_reset_successfully")
        )

    def select_all_permissions(self):
        for cb in self.perm_checkboxes.values():
            cb.setChecked(True)

    def unselect_all_permissions(self):
        for cb in self.perm_checkboxes.values():
            cb.setChecked(False)

    # ──────────────────────────────────────────────────────────────────────
    # i18n
    # ──────────────────────────────────────────────────────────────────────
    def retranslate_ui(self):
        self.role_search.setPlaceholderText(self._("search_role"))
        self.btn_save.setText(self._("save"))
        self.btn_reset.setText(self._("reset_to_role_defaults"))
        self.btn_select_all.setText(self._("select_all_permissions"))
        self.btn_unselect_all.setText(self._("unselect_all_permissions"))
        if hasattr(self, "btn_add_role"):
            self.btn_add_role.setText(self._("add_role"))
        if hasattr(self, "roles_box"):
            self.roles_box.setTitle(self._("roles"))
        if hasattr(self, "right_box"):
            self.right_box.setTitle(self._("role_permissions"))

        self.selected_role_label.setText("")
        self.selected_role_desc.setText("")

        selected_id = self.selected_role["id"] if self.selected_role else None
        self.load_roles()

        if selected_id is not None:
            for i in range(self.roles_list.count()):
                item = self.roles_list.item(i)
                if (item.data(1000) or {}).get("id") == selected_id:
                    self.roles_list.setCurrentRow(i)
                    break
            else:
                self._clear_scroll_content()
        else:
            self._clear_scroll_content()