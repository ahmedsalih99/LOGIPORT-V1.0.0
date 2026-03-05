"""
ui/tabs/offices_tab.py
=======================
تبويب إدارة المكاتب — عرض / إضافة / تعديل / تفعيل وتعطيل
"""
from core.base_tab import BaseTab
from core.permissions import has_perm, is_admin
from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from core.admin_columns import apply_admin_columns_to_table
from database.crud.offices_crud import OfficesCRUD

from PySide6.QtWidgets import QMessageBox, QTableWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class OfficesTab(BaseTab):
    """
    تبويب المكاتب.
    - Admin فقط يرى زر الإضافة والتعديل والحذف
    - كل المستخدمين يشوفون قائمة المكاتب
    """

    required_permissions = {
        "view":    ["view_offices"],
        "add":     ["add_office"],
        "edit":    ["edit_office"],
        "delete":  ["delete_office"],
        "refresh": ["view_offices"],
    }

    def __init__(self, parent=None, current_user=None):
        _ = TranslationManager.get_instance().translate
        settings = SettingsManager.get_instance()
        u = current_user or settings.get("user", None) or getattr(parent, "current_user", None)

        super().__init__(title=_("offices"), parent=parent, user=u)
        self._ = _
        self.crud = OfficesCRUD()
        self.set_current_user(u)

        # ── أعمدة الجدول ──────────────────────────────────────────────────────
        self.table.setAlternatingRowColors(True)
        actions_col = {"label": "actions", "key": "actions"}

        self.set_columns_for_role(
            base_columns=[
                {"label": "office_code",    "key": "code"},
                {"label": "arabic_name",    "key": "name_ar"},
                {"label": "english_name",   "key": "name_en"},
                {"label": "turkish_name",   "key": "name_tr"},
                {"label": "country",        "key": "country"},
                {"label": "city",           "key": "city"},
                {"label": "status",         "key": "status"},
                actions_col,
            ],
            admin_columns=[
                {"label": "ID",             "key": "id"},
                {"label": "sort_order",     "key": "sort_order"},
                {"label": "notes",          "key": "notes"},
            ],
        )

        self.check_permissions()

        # ── إشارات ────────────────────────────────────────────────────────────
        self.request_edit.connect(self.edit_selected_item)
        self.request_delete.connect(self.delete_selected_items)
        self.row_double_clicked.connect(self.on_row_double_clicked)

        self.reload_data()
        self._init_done = True

    # ── تحميل البيانات ────────────────────────────────────────────────────────

    def reload_data(self):
        items = self.crud.get_all() or []
        self.data = []
        for o in items:
            row = {
                "id":         o.get("id"),
                "code":       o.get("code", ""),
                "name_ar":    o.get("name_ar", ""),
                "name_en":    o.get("name_en", "") or "",
                "name_tr":    o.get("name_tr", "") or "",
                "country":    o.get("country", "") or "",
                "city":       o.get("city", "") or "",
                "status":     self._("active") if o.get("is_active") else self._("inactive"),
                "sort_order": str(o.get("sort_order", 0)),
                "notes":      o.get("notes", "") or "",
                "is_active":  o.get("is_active", True),
                "actions":    o,  # القاموس الكامل للتعديل
            }
            self.data.append(row)
        self.display_data()

    # ── عرض البيانات ──────────────────────────────────────────────────────────

    def display_data(self):
        self._display_with_actions("edit_office", "delete_office")
        self._color_inactive_rows()

    def _color_inactive_rows(self):
        """يُلوّن صفوف المكاتب المعطلة بلون رمادي خفيف."""
        for row_idx, row_data in enumerate(self.data):
            if not row_data.get("is_active", True):
                for col in range(self.table.columnCount()):
                    item = self.table.item(row_idx, col)
                    if item:
                        item.setForeground(QColor("#9CA3AF"))

    # ── إضافة مكتب ────────────────────────────────────────────────────────────

    def add_new_item(self):
        from ui.dialogs.add_office_dialog import AddOfficeDialog
        dlg = AddOfficeDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            user_id = getattr(self.current_user, "id", None)
            try:
                self.crud.add(
                    code=data["code"],
                    name_ar=data["name_ar"],
                    name_en=data.get("name_en") or "",
                    name_tr=data.get("name_tr") or "",
                    country=data.get("country") or "",
                    city=data.get("city") or "",
                    notes=data.get("notes") or "",
                    sort_order=data.get("sort_order", 0),
                    user_id=user_id,
                )
                QMessageBox.information(self, self._("added"), self._("office_added_success"))
                self.reload_data()
            except Exception as exc:
                QMessageBox.critical(self, self._("error"), str(exc))

    # ── تعديل مكتب ────────────────────────────────────────────────────────────

    def edit_selected_item(self, row=None):
        if row is None:
            rows = self.get_selected_rows()
            if not rows:
                return
            row = rows[0]
        office_dict = self.data[row]["actions"]
        self._open_edit_dialog(office_dict)

    def _open_edit_dialog(self, office_dict: dict):
        from ui.dialogs.add_office_dialog import AddOfficeDialog
        dlg = AddOfficeDialog(self, office_dict)
        if dlg.exec():
            data = dlg.get_data()
            user_id = getattr(self.current_user, "id", None)
            try:
                self.crud.update(office_dict["id"], data, user_id=user_id)
                QMessageBox.information(self, self._("updated"), self._("office_updated_success"))
                self.reload_data()
            except Exception as exc:
                QMessageBox.critical(self, self._("error"), str(exc))

    # ── حذف مكتب ──────────────────────────────────────────────────────────────

    def delete_selected_items(self, rows=None):
        if rows is None:
            rows = self.get_selected_rows()
        if not rows:
            return
        reply = QMessageBox.question(
            self, self._("delete_office"), self._("are_you_sure_delete"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        user_id = getattr(self.current_user, "id", None)
        for row in rows:
            office_dict = self.data[row]["actions"]
            try:
                self.crud.delete(office_dict["id"], user_id=user_id)
            except Exception as exc:
                QMessageBox.warning(self, self._("error"), str(exc))
        QMessageBox.information(self, self._("deleted"), self._("office_deleted_success"))
        self.reload_data()

    # ── دابل كليك → تفعيل / تعطيل ────────────────────────────────────────────

    def on_row_double_clicked(self, row_index):
        try:
            row = int(row_index)
        except Exception:
            row = getattr(row_index, "row", lambda: -1)()
        if not (0 <= row < len(self.data)):
            return

        office_dict = self.data[row]["actions"]
        is_active = office_dict.get("is_active", True)
        action = self._("deactivate") if is_active else self._("activate")
        name = office_dict.get("name_ar", "")

        reply = QMessageBox.question(
            self,
            action,
            f"{action} — {name}؟",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            user_id = getattr(self.current_user, "id", None)
            self.crud.toggle_active(office_dict["id"], user_id=user_id)
            self.reload_data()

    # ── i18n ──────────────────────────────────────────────────────────────────

    def retranslate_ui(self):
        super().retranslate_ui()
        parent = self.parent()
        try:
            if parent and hasattr(parent, "indexOf") and hasattr(parent, "setTabText"):
                idx = parent.indexOf(self)
                if idx != -1:
                    parent.setTabText(idx, self._("offices"))
        except Exception:
            pass
        self._apply_columns_for_current_role()
        self.reload_data()

    def _apply_admin_columns(self):
        admin_keys = ("id", "sort_order", "notes")
        admin_cols = [
            idx for idx, col in enumerate(self.columns)
            if col.get("key") in admin_keys
        ]
        apply_admin_columns_to_table(self.table, self.current_user, admin_cols)