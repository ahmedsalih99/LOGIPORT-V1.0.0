from core.base_tab import BaseTab
from ui.dialogs.add_packaging_type_dialog import AddPackagingTypeDialog
from ui.dialogs.view_details.view_packaging_type_dialog import ViewPackagingTypeDialog
from database.crud.packaging_types_crud import PackagingTypesCRUD
from core.translator import TranslationManager
from database.models import get_session_local, User
from core.settings_manager import SettingsManager

# ✅ بوابة الصلاحيات + أعمدة الأدمن
from core.permissions import has_perm, is_admin
from core.admin_columns import apply_admin_columns_to_table

from PySide6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QHBoxLayout, QWidget, QPushButton
)
from PySide6.QtCore import Qt


class PackagingTypesTab(BaseTab):
    """
    Packaging Types tab with admin-only columns and audit-ready CRUD calls.
    - Normal users see Arabic/English/Turkish names + actions.
    - Admins additionally see ID + created_by/updated_by + created_at/updated_at.
    """

    required_permissions = {
        "view":    "view_values",           # ضمن تبويب القِيَم
        "add":     "add_packaging_type",
        "edit":    "edit_packaging_type",
        "delete":  "delete_packaging_type",
        "import":  "view_values",
        "export":  "view_values",
        "refresh": "view_values",           # لتفعيل زر التحديث
        "print":   "view_values",
    }

    def __init__(self, parent=None, current_user=None):
        _ = TranslationManager.get_instance().translate

        # وحّد مصدر المستخدم (الممرَّر أو المخزَّن أو من الأب)
        settings = SettingsManager.get_instance()
        u = current_user or settings.get("user", None) or getattr(parent, "current_user", None)

        super().__init__(title=_("packaging_types"), parent=parent, user=u)
        self._ = _
        self.packaging_types_crud = PackagingTypesCRUD()

        # ثبّت current_user داخل التاب
        self.set_current_user(u)

        # تعريف الأعمدة
        self.table.setAlternatingRowColors(True)

        self.set_columns_for_role(
            base_columns=[
                {"label": "arabic_name",  "key": "name_ar"},
                {"label": "english_name", "key": "name_en"},
                {"label": "turkish_name", "key": "name_tr"},
                {"label": "actions",      "key": "actions"},
            ],
            admin_columns=[
                {"label": "ID",          "key": "id"},
                {"label": "created_by",  "key": "created_by_name"},
                {"label": "updated_by",  "key": "updated_by_name"},
                {"label": "created_at",  "key": "created_at"},
                {"label": "updated_at",  "key": "updated_at"},
            ],
        )

        # طبّق صلاحيات التاب
        self.check_permissions()

        # إشارات
        self.request_edit.connect(self.edit_selected_item)
        self.request_delete.connect(self.delete_selected_items)
        self.row_double_clicked.connect(self.on_row_double_clicked)
        if hasattr(self, "request_refresh"):
            self.request_refresh.connect(self.reload_data)

        self.reload_data()
        self._init_done = True

    # -----------------------------
    # Data loading
    # -----------------------------
    def reload_data(self):
        admin = is_admin(self.current_user)

        items = self.packaging_types_crud.get_all() or []

        # خريطة id->name لمرة واحدة (للأدمِن لتفادي N+1)
        id_set = set()
        if admin:
            for pt in items:
                cb_id = getattr(pt, "created_by_id", None)
                ub_id = getattr(pt, "updated_by_id", None)
                cb_fallback = getattr(pt, "created_by", None)
                ub_fallback = getattr(pt, "updated_by", None)
                if not cb_id and isinstance(cb_fallback, int):
                    cb_id = cb_fallback
                if not ub_id and isinstance(ub_fallback, int):
                    ub_id = ub_fallback
                if isinstance(cb_id, int):
                    id_set.add(cb_id)
                if isinstance(ub_id, int):
                    id_set.add(ub_id)

        id_to_name = {}
        if id_set:
            # get_session_local -> sessionmaker، افتح Session منه
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                q = s.query(User.id, User.full_name, User.username).filter(User.id.in_(id_set))
                for uid, full_name, username in q:
                    id_to_name[uid] = (full_name or username or str(uid))

        # إبني صفوف الجدول
        self.data = []
        for pt in items:
            row = {
                "id":      getattr(pt, "id", None),
                "name_ar": getattr(pt, "name_ar", "") or "",
                "name_en": getattr(pt, "name_en", "") or "",
                "name_tr": getattr(pt, "name_tr", "") or "",
                "actions": pt,
            }
            if admin:
                created_by_rel = getattr(pt, "created_by", None)
                updated_by_rel = getattr(pt, "updated_by", None)
                created_by_id  = getattr(pt, "created_by_id", None)
                updated_by_id  = getattr(pt, "updated_by_id", None)

                if isinstance(created_by_rel, User):
                    created_by_name = getattr(created_by_rel, "full_name", None) or getattr(created_by_rel, "username", None) or str(created_by_rel.id)
                else:
                    key = created_by_id or (created_by_rel if isinstance(created_by_rel, int) else None)
                    created_by_name = id_to_name.get(key, str(key or ""))

                if isinstance(updated_by_rel, User):
                    updated_by_name = getattr(updated_by_rel, "full_name", None) or getattr(updated_by_rel, "username", None) or str(updated_by_rel.id)
                else:
                    key = updated_by_id or (updated_by_rel if isinstance(updated_by_rel, int) else None)
                    updated_by_name = id_to_name.get(key, str(key or ""))

                row.update({
                    "created_by_name": created_by_name or "",
                    "updated_by_name": updated_by_name or "",
                    "created_at": str(getattr(pt, "created_at", "") or ""),
                    "updated_at": str(getattr(pt, "updated_at", "") or ""),
                })

            self.data.append(row)

        self.display_data()

    # -----------------------------
    # Display with action buttons
    # -----------------------------
    def display_data(self):
        can_edit = has_perm(self.current_user, "edit_packaging_type")
        can_delete = has_perm(self.current_user, "delete_packaging_type")
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

                    pt = row["actions"]
                    action_layout = QHBoxLayout()
                    action_layout.setContentsMargins(0, 0, 0, 0)
                    action_layout.setSpacing(12)

                    if can_edit:
                        btn_edit = QPushButton(self._("edit"))
                        btn_edit.setObjectName("primary-btn")
                        btn_edit.clicked.connect(lambda _=False, obj=pt: self._open_edit_dialog(obj))
                        action_layout.addWidget(btn_edit)

                    if can_delete:
                        btn_delete = QPushButton(self._("delete"))
                        btn_delete.setObjectName("danger-btn")
                        btn_delete.clicked.connect(lambda _=False, obj=pt: self._delete_single(obj))
                        action_layout.addWidget(btn_delete)

                    w = QWidget()
                    w.setLayout(action_layout)
                    self.table.setCellWidget(row_idx, col_idx, w)
                else:
                    item = QTableWidgetItem(str(row.get(key, "")))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_idx, col_idx, item)

        # أخفِ عمود الإجراءات إن لم توجد صلاحيات
        try:
            actions_index = next((i for i, c in enumerate(self.columns) if c.get("key") == "actions"), None)
            if actions_index is not None:
                self.table.setColumnHidden(actions_index, not show_actions)
        except Exception:
            pass

        # ✅ أعمدة الأدمن فقط
        self._apply_admin_columns()

        self.update_pagination_label()

    # -----------------------------
    # Actions
    # -----------------------------
    def add_new_item(self):
        dlg = AddPackagingTypeDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            user_id = self._user_id()
            self.packaging_types_crud.add_packaging_type(
                name_ar=data["name_ar"],
                name_en=data["name_en"],
                name_tr=data["name_tr"],
                user_id=user_id,
            )
            QMessageBox.information(self, self._("added"), self._("packaging_type_added_success"))
            self.reload_data()

    def edit_selected_item(self, row=None):
        if row is None:
            rows = self.get_selected_rows()
            if not rows:
                return
            row = rows[0]
        pt = self.data[row]["actions"]
        self._open_edit_dialog(pt)

    def _open_edit_dialog(self, pt):
        dlg = AddPackagingTypeDialog(self, {
            "name_ar": getattr(pt, "name_ar", ""),
            "name_en": getattr(pt, "name_en", ""),
            "name_tr": getattr(pt, "name_tr", ""),
        })
        if dlg.exec():
            data = dlg.get_data()
            user_id = self._user_id()
            self.packaging_types_crud.update_packaging_type(pt.id, data, user_id=user_id)
            QMessageBox.information(self, self._("updated"), self._("packaging_type_updated_success"))
            self.reload_data()

    def delete_selected_items(self, rows=None):
        if rows is None:
            rows = self.get_selected_rows()
        if not rows:
            return
        reply = QMessageBox.question(
            self, self._("delete_packaging_type"), self._("are_you_sure_delete"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for row in rows:
                pt = self.data[row]["actions"]
                self._delete_single(pt, confirm=False)
            QMessageBox.information(self, self._("deleted"), self._("packaging_type_deleted_success"))
            self.reload_data()

    def _delete_single(self, pt, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, self._("delete_packaging_type"), self._("are_you_sure_delete"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.packaging_types_crud.delete(pt.id)

    # -----------------------------
    # Double-click → view dialog
    # -----------------------------
    def on_row_double_clicked(self, row_index):
        try:
            row = int(row_index)
        except Exception:
            row = getattr(row_index, "row", lambda: -1)()
        if 0 <= row < len(self.data):
            pt = self.data[row]["actions"]
            dlg = ViewPackagingTypeDialog(pt, current_user=self.current_user, parent=self)
            dlg.exec()

    # -----------------------------
    # i18n / Tab title
    # -----------------------------
    def retranslate_ui(self):
        super().retranslate_ui()
        parent = self.parent()
        try:
            if parent and hasattr(parent, "indexOf") and hasattr(parent, "setTabText"):
                idx = parent.indexOf(self)
                if idx != -1:
                    parent.setTabText(idx, self._("packaging_types"))
        except Exception:
            pass
        # Refresh headers after translation (applies i18n for admin/base columns)
        self._apply_columns_for_current_role()
        # Reload to reflect any translated cell content
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
