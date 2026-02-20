from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QScrollArea, QGridLayout, QCheckBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QSize

from core.translator import TranslationManager
from core.settings_manager import SettingsManager

from database.crud.permissions_crud import (
    get_all_permissions, get_role_permissions,
    assign_permission_to_role, remove_permission_from_role,
    RolesCRUD
)

from ui.dialogs.add_role_dialog import AddRoleDialog
from ui.widgets.custom_button import CustomButton
from ui.dialogs.view_details.view_role_dialog import ViewRoleDialog


class PermissionsTab(QWidget):
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate

        # موحّد: خذ المستخدم الممرَّر أو من الإعدادات أو من الأب
        settings = SettingsManager.get_instance()
        self.current_user = current_user or settings.get("user", None) or getattr(parent, "current_user", None)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 6, 10, 10)
        main_layout.setSpacing(10)

        # ---------- يسار: الأدوار ----------
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
        self.roles_list.itemDoubleClicked.connect(self._on_role_double_clicked)
        self.roles_list.setObjectName("roles-list")
        self.roles_list.itemSelectionChanged.connect(self.on_role_selected)
        roles_layout.addWidget(self.roles_list)

        main_layout.addWidget(self.roles_box, 1)

        # ---------- يمين: صلاحيات الدور ----------
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

        # شبكة الصلاحيات داخل ScrollArea
        self.scroll = QScrollArea()
        self.scroll.setObjectName("perm-scroll")
        self.scroll.setWidgetResizable(True)

        perm_widget = QWidget()
        perm_widget.setObjectName("perm-grid-container")
        self.perm_grid = QGridLayout(perm_widget)
        self.perm_grid.setContentsMargins(8, 6, 8, 6)
        self.perm_grid.setHorizontalSpacing(14)
        self.perm_grid.setVerticalSpacing(8)

        self.perm_checkboxes = {}  # id: QCheckBox
        self.scroll.setWidget(perm_widget)
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

        # زر إضافة دور
        self.btn_add_role = CustomButton(self._("add_role"))
        self.btn_add_role.clicked.connect(self.show_add_role_dialog)

        self.setLayout(main_layout)

        # حالـة
        self.selected_role = None
        self.permissions = []
        self.roles = []
        self._current_col_count = None  # لتتبّع تغيّر الأعمدة وإعادة توزيع الشبكة

        self.load_roles()
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    # ============================
    # Helpers
    # ============================
    def _user_id(self):
        u = self.current_user
        if isinstance(u, dict):
            return u.get("id")
        return getattr(u, "id", None)

    def _calc_col_count(self) -> int:
        # تقسيم بسيط حسب العرض (يمكن تعديل العتبات لاحقًا)
        w = max(self.width(), 1)
        if w >= 1100:
            return 5
        if w >= 900:
            return 4
        if w >= 700:
            return 3
        return 2

    # ============================
    # Roles
    # ============================
    def load_roles(self):
        lang = TranslationManager.get_instance().get_current_language()
        self.roles = RolesCRUD().get_all(language=lang)
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
            self.clear_permissions()
            return
        role = selected_items[0].data(1000)
        self.selected_role = role
        self.selected_role_label.setText(self._("role") + ": " + role["label"])
        self.selected_role_desc.setText(role.get("description", ""))
        self.load_permissions(role["id"], from_resize=False)

    # ============================
    # Permissions grid
    # ============================
    def clear_permissions(self):
        for cb in self.perm_checkboxes.values():
            cb.setChecked(False)

    def load_permissions(self, role_id: int, *, from_resize: bool = False):
        lang = TranslationManager.get_instance().get_current_language()
        self.permissions = get_all_permissions(language=lang)

        # ✅ نحفظ التحديد فقط أثناء resize
        prev_checked = set()
        if from_resize:
            prev_checked = {
                pid for pid, cb in self.perm_checkboxes.items() if cb.isChecked()
            }

        # تنظيف الشبكة
        for i in reversed(range(self.perm_grid.count())):
            w = self.perm_grid.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.perm_checkboxes.clear()

        col_count = self._calc_col_count()
        self._current_col_count = col_count

        for idx, perm in enumerate(self.permissions):
            cb = QCheckBox(perm["label"])
            cb.setToolTip(perm.get("description", perm["code"]))
            self.perm_checkboxes[perm["id"]] = cb
            row, col = divmod(idx, col_count)
            self.perm_grid.addWidget(cb, row, col)

        # ✔️ صلاحيات الدور من قاعدة البيانات
        role_perms = {p["id"] for p in get_role_permissions(role_id, language=lang)}

        for pid, cb in self.perm_checkboxes.items():
            if from_resize:
                cb.setChecked(pid in prev_checked)
            else:
                cb.setChecked(pid in role_perms)

    # ============================
    # Actions
    # ============================
    def save_permissions(self):
        if not self.selected_role:
            return
        role_id = self.selected_role["id"]

        checked_perm_ids = [pid for pid, cb in self.perm_checkboxes.items() if cb.isChecked()]
        current_perm_ids = [p["id"] for p in get_role_permissions(role_id)]

        to_add = set(checked_perm_ids) - set(current_perm_ids)
        to_remove = set(current_perm_ids) - set(checked_perm_ids)

        uid = self._user_id()
        for perm_id in to_add:
            assign_permission_to_role(role_id, perm_id, user_id=uid)
        for perm_id in to_remove:
            remove_permission_from_role(role_id, perm_id, user_id=uid)

        QMessageBox.information(self, self._("save"), self._("permissions_updated_successfully"))
        self.load_permissions(role_id)

    def reset_to_role_defaults(self):
        if not self.selected_role:
            return
        role_id = self.selected_role["id"]
        uid = self._user_id()
        current_perm_ids = [p["id"] for p in get_role_permissions(role_id)]
        for perm_id in current_perm_ids:
            remove_permission_from_role(role_id, perm_id, user_id=uid)
        self.load_permissions(role_id)
        QMessageBox.information(self, self._("reset_to_role_defaults"), self._("permissions_reset_successfully"))

    def select_all_permissions(self):
        for cb in self.perm_checkboxes.values():
            cb.setChecked(True)

    def unselect_all_permissions(self):
        for cb in self.perm_checkboxes.values():
            cb.setChecked(False)

    # ============================
    # i18n
    # ============================
    def retranslate_ui(self):
        # 1) ترجمة عناصر التحكم
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

        # عناوين القسم يمين تتغير حسب اختيار الدور
        self.selected_role_label.setText("")
        self.selected_role_desc.setText("")

        # 3) الحفاظ على الدور المحدد وإعادة تحميل القوائم والصلاحيات
        selected_id = self.selected_role["id"] if self.selected_role else None

        # أعد تحميل الأدوار حسب اللغة الحالية
        self.load_roles()

        # إذا كان في دور محدد من قبل، أعد اختياره بعد الترجمة
        if selected_id is not None:
            match_index = -1
            for i in range(self.roles_list.count()):
                item = self.roles_list.item(i)
                data = item.data(1000) or {}
                if data.get("id") == selected_id:
                    match_index = i
                    break
            if match_index != -1:
                # هذا سيؤدي لاستدعاء on_role_selected تلقائيًا عبر itemSelectionChanged
                self.roles_list.setCurrentRow(match_index)
            else:
                self.clear_permissions()
        else:
            self.clear_permissions()

    # ============================
    # Layout responsiveness
    # ============================
    def resizeEvent(self, e):
        super().resizeEvent(e)
        new_cols = self._calc_col_count()
        if new_cols != self._current_col_count and self.selected_role:
            # أعد توزيع الشبكة بالحجم الجديد مع الحفاظ على التحديدات
            self.load_permissions(self.selected_role["id"], from_resize=True)

    def _on_role_double_clicked(self, item):
        role = item.data(1000) if item else None
        if not role:
            return
        dlg = ViewRoleDialog(role, current_user=self.current_user, parent=self)
        dlg.exec()

    def show_add_role_dialog(self):
        dlg = AddRoleDialog(self)
        if dlg.exec():
            # أعد تحميل قائمة الأدوار بعد إنشاء دور جديد
            self.load_roles()
