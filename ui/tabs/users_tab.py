from core.base_tab import BaseTab
from ui.dialogs.users_dialogs import UserDialog
from ui.dialogs.view_details.view_user_dialog import ViewUserDialog
from database.crud.users_crud import UsersCRUD
from database.crud.permissions_crud import RolesCRUD  # ⬅️ فقط RolesCRUD
from core.translator import TranslationManager
from database.models import get_session_local, User
from core.settings_manager import SettingsManager

# صلاحيات + أعمدة الأدمن
from core.permissions import has_perm, is_admin
from core.admin_columns import apply_admin_columns_to_table

from PySide6.QtWidgets import (
    QTableWidgetItem, QMessageBox, QHBoxLayout, QWidget, QPushButton, QComboBox
)
from PySide6.QtCore import Qt


class UsersTab(BaseTab):
    """
    Users tab:
      - نفس منطق البلدان: صلاحيات موحّدة، أعمدة أدمن، جلسات آمنة.
      - فلتر حسب الدور.
      - CRUD عبر UsersCRUD.
    """

    required_permissions = {
        "view":    "view_users_roles",
        "add":     "add_user",
        "edit":    "edit_user",
        "delete":  "delete_user",
        "import":  "view_users_roles",
        "export":  "view_users_roles",
        "refresh": "view_users_roles",
        "print":   "view_users_roles",
    }

    def __init__(self, parent=None, current_user=None):
        _ = TranslationManager.get_instance().translate

        # وحّد مصدر المستخدم (الممرَّر أو من SettingsManager أو من الأب)
        settings = SettingsManager.get_instance()
        u = current_user or settings.get("user", None) or getattr(parent, "current_user", None)

        super().__init__(title=_("users_tab_title"), parent=parent, user=u)
        self._ = _
        self.users_crud = UsersCRUD()
        self.set_current_user(u)

        # الأعمدة
        self.table.setAlternatingRowColors(True)

        self.set_columns_for_role(
            base_columns=[
                {"label": "username",  "key": "username"},
                {"label": "full_name", "key": "full_name"},
                {"label": "role",      "key": "role"},
                {"label": "status",    "key": "status"},
                {"label": "actions",   "key": "actions"},
            ],
            admin_columns=[
                {"label": "ID",         "key": "id"},
                {"label": "created_by", "key": "created_by_name"},
                {"label": "updated_by", "key": "updated_by_name"},
                {"label": "created_at", "key": "created_at"},
                {"label": "updated_at", "key": "updated_at"},
            ],
        )

        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.verticalHeader().setVisible(False)

        # إشارات
        self.request_edit.connect(self.edit_selected_item)
        self.request_delete.connect(self.delete_selected_items)
        self.request_view.connect(self.on_row_double_clicked)
        self.row_double_clicked.connect(self.on_row_double_clicked)
        if hasattr(self, "request_refresh"):
            self.request_refresh.connect(self.reload_data)

        self.reload_data()
        self._init_done = True

    # -----------------------------
    # Filters
    # -----------------------------
    def setup_filters(self):
        role_filter = QComboBox()
        role_filter.addItem(self._("all_roles"), None)

        lang = TranslationManager.get_instance().get_current_language()
        roles = RolesCRUD().get_all(language=lang)
        for role in roles:
            role_filter.addItem(role["label"], role["name"])  # internal key name
        role_filter.currentIndexChanged.connect(self.reload_data)
        self.role_filter = role_filter
        self.add_filter(role_filter, label="role")

    # -----------------------------
    # Data loading/building
    # -----------------------------
    def reload_data(self):
        admin = is_admin(self.current_user)

        users = self.users_crud.get_all() or []

        # Filter by role if selected
        if hasattr(self, "role_filter") and self.role_filter.currentData():
            selected_role = self.role_filter.currentData()
            users = [u for u in users if u.get("role") == selected_role]

        # paging
        self.total_rows = len(users)
        self.total_pages = max(1, -(-self.total_rows // self.rows_per_page))
        start = (self.current_page - 1) * self.rows_per_page
        end = start + self.rows_per_page
        page_items = users[start:end]

        # map id -> name (admins only)
        id_set = set()
        if admin:
            for u in page_items:
                if u.get("created_by_id"):
                    id_set.add(u["created_by_id"])
                if u.get("updated_by_id"):
                    id_set.add(u["updated_by_id"])
        id_to_name = {}
        if id_set:
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                for (uid, full_name, username) in (
                    s.query(User.id, User.full_name, User.username).filter(User.id.in_(list(id_set)))
                ):
                    id_to_name[uid] = full_name or username or str(uid)

        # Build rows
        self.data = []
        for u in page_items:
            row = {
                "id": u.get("id"),
                "username": u.get("username", ""),
                "full_name": u.get("full_name", ""),
                "role": u.get("role_label", u.get("role", "")),
                "status": self._("active") if u.get("is_active") else self._("inactive"),
                "actions": u,
            }
            if admin:
                created_by_id = u.get("created_by_id")
                updated_by_id = u.get("updated_by_id")
                row.update({
                    "created_by_name": id_to_name.get(created_by_id, str(created_by_id) if created_by_id else ""),
                    "updated_by_name": id_to_name.get(updated_by_id, str(updated_by_id) if updated_by_id else ""),
                    "created_at": str(u.get("created_at", "") or ""),
                    "updated_at": str(u.get("updated_at", "") or ""),
                })
            self.data.append(row)

        self.display_data()

    def display_data(self):
        can_edit = has_perm(self.current_user, "edit_user")
        can_delete = has_perm(self.current_user, "delete_user")
        show_actions = (can_edit or can_delete)

        self.table.setRowCount(0)
        for row_idx, row in enumerate(self.data):
            self.table.insertRow(row_idx)
            for col_idx, col in enumerate(self.columns):
                key = col.get("key")
                if key == "actions":
                    if not show_actions:
                        self.table.setCellWidget(row_idx, col_idx, QWidget())
                        continue

                    user_obj = row["actions"]
                    action_layout = QHBoxLayout()
                    action_layout.setContentsMargins(0, 0, 0, 0)
                    action_layout.setSpacing(12)

                    if can_edit:
                        btn_edit = QPushButton(self._("edit"))
                        btn_edit.setObjectName("primary-btn")
                        btn_edit.clicked.connect(self.make_edit_callback(user_obj))
                        action_layout.addWidget(btn_edit)

                    if can_delete:
                        btn_delete = QPushButton(self._("delete"))
                        btn_delete.setObjectName("danger-btn")
                        btn_delete.clicked.connect(self.make_delete_callback(user_obj))
                        action_layout.addWidget(btn_delete)

                    action_widget = QWidget()
                    action_widget.setLayout(action_layout)
                    self.table.setCellWidget(row_idx, col_idx, action_widget)
                else:
                    item = QTableWidgetItem(str(row.get(key, "")))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_idx, col_idx, item)

        # أخفِ عمود الإجراءات عند عدم وجود صلاحيات
        try:
            actions_index = next((i for i, c in enumerate(self.columns) if c.get("key") == "actions"), None)
            if actions_index is not None:
                self.table.setColumnHidden(actions_index, not show_actions)
        except Exception:
            pass

        # أعمدة الأدمن
        self._apply_admin_columns()

        self.update_pagination_label()

    # -----------------------------
    # Actions
    # -----------------------------
    def add_new_item(self):
        dlg = UserDialog()
        if dlg.exec():
            data = dlg.get_data()
            if not data.get("username") or not data.get("password"):
                QMessageBox.warning(self, self._("error"), self._("must_fill_username_password"))
                return
            if self.users_crud.get_by_username(data["username"]):
                QMessageBox.warning(self, self._("error"), self._("username_already_exists"))
                return
            self.users_crud.add_user(
                username=data["username"],
                password=data["password"],
                full_name=data.get("full_name"),
                role_id=data.get("role"),
                is_active=True,
                user_id=self._user_id(),
            )
            QMessageBox.information(self, self._("added"), self._("user_added_success"))
            self.reload_data()

    def edit_selected_item(self, row=None):
        if row is None:
            rows = self.get_selected_rows()
            if not rows:
                return
            row = rows[0]
        user_obj = self.data[row]["actions"]
        self.open_edit_user(user_obj)

    def delete_selected_items(self, rows=None):
        if rows is None:
            rows = self.get_selected_rows()
        if not rows:
            return
        reply = QMessageBox.question(
            self, self._("delete_user"), self._("are_you_sure_delete"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for row in rows:
                user_obj = self.data[row]["actions"]
                self.users_crud.delete(user_obj["id"] if isinstance(user_obj, dict) else user_obj.id)
            QMessageBox.information(self, self._("deleted"), self._("user_deleted_success"))
            self.reload_data()

    def view_selected_item(self, row=None):
        # لم تعد تُستخدم مباشرة؛ نبقيها للتوافق
        self.on_row_double_clicked(row)

    def open_edit_user(self, user):
        dlg = UserDialog(user)
        if dlg.exec():
            data = dlg.get_data()
            update_data = {}
            if data.get("full_name"):
                update_data["full_name"] = data["full_name"]
            if data.get("role"):
                update_data["role_id"] = data["role"]
            if data.get("password"):
                update_data["password"] = data["password"]

            self.users_crud.update_user(
                user.get("id") if isinstance(user, dict) else user.id,
                update_data,
                user_id=self._user_id(),
            )
            QMessageBox.information(self, self._("updated"), self._("user_updated_success"))
            self.reload_data()

    def delete_user(self, user):
        reply = QMessageBox.question(
            self, self._("delete_user"), self._("are_you_sure_delete"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.users_crud.delete(user.get("id") if isinstance(user, dict) else user.id)
            QMessageBox.information(self, self._("deleted"), self._("user_deleted_success"))
            self.reload_data()

    def make_edit_callback(self, user):
        return lambda checked=False: self.open_edit_user(user)

    def make_delete_callback(self, user):
        return lambda checked=False: self.delete_user(user)

    # -----------------------------
    # Row double-click → View dialog
    # -----------------------------
    def on_row_double_clicked(self, row_index):
        try:
            row = int(row_index)
        except Exception:
            row = getattr(row_index, "row", lambda: -1)()
        if 0 <= row < len(self.data):
            user_obj = self.data[row]["actions"]
            dlg = ViewUserDialog(user_obj, current_user=self.current_user, parent=self)
            dlg.exec()

    # -----------------------------
    # i18n
    # -----------------------------
    def retranslate_ui(self):
        if not getattr(self, "_init_done", False):
            return
        super().retranslate_ui()

        # Rebuild role filter with current language but keep selection
        if hasattr(self, "role_filter"):
            current_data = self.role_filter.currentData()
            self.role_filter.blockSignals(True)
            self.role_filter.clear()
            self.role_filter.addItem(self._("all_roles"), None)

            lang = TranslationManager.get_instance().get_current_language()
            roles = RolesCRUD().get_all(language=lang)
            restore_index = 0
            for r in roles:
                self.role_filter.addItem(r["label"], r["name"])
                if current_data is not None and r["name"] == current_data:
                    restore_index = self.role_filter.count() - 1
            self.role_filter.setCurrentIndex(restore_index)
            self.role_filter.blockSignals(False)

        # Refresh headers and data
        self._apply_columns_for_current_role()
        self.reload_data()

    # -----------------------------
    # Helpers
    # -----------------------------
    def _apply_admin_columns(self):
        admin_keys = ("id", "created_by_name", "updated_by_name", "created_at", "updated_at")
        admin_cols = [idx for idx, col in enumerate(self.columns) if col.get("key") in admin_keys]
        apply_admin_columns_to_table(self.table, self.current_user, admin_cols)

    def _user_id(self):
        u = self.current_user
        if isinstance(u, dict):
            return u.get("id")
        return getattr(u, "id", None)
