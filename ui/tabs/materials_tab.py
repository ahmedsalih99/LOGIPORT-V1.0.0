from core.base_tab import BaseTab
from ui.dialogs.add_material_dialog import AddMaterialDialog
from ui.dialogs.view_details.view_material_dialog import ViewMaterialDialog

from database.crud.materials_crud import MaterialsCRUD
from database.crud.material_types_crud import MaterialTypesCRUD
from database.crud.currencies_crud import CurrenciesCRUD

from core.translator import TranslationManager
from core.settings_manager import SettingsManager

from database.models import get_session_local, User, MaterialType, Currency

from core.permissions import has_perm, is_admin
from core.admin_columns import apply_admin_columns_to_table

from PySide6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QHBoxLayout, QWidget, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon


class MaterialsTab(BaseTab):
    """
    Materials tab (نفس نمط Countries/Currencies)
    - أعمدة أساس للمستخدم العادي + أعمدة أدمن
    - أزرار الإجراءات حسب الصلاحيات
    - نافذة تفاصيل بالدبل-كليك
    """

    required_permissions = {
        "view":    ["view_materials"],
        "add":     ["add_material"],
        "edit":    ["edit_material"],
        "delete":  ["delete_material"],
        "import":  ["view_materials"],
        "export":  ["view_materials"],
        "print":   ["view_materials"],
        "refresh": ["view_materials"],
    }

    def __init__(self, parent=None, current_user=None):
        _ = TranslationManager.get_instance().translate

        # توحيد مصدر المستخدم
        settings = SettingsManager.get_instance()
        u = current_user or settings.get("user", None) or getattr(parent, "current_user", None)

        super().__init__(title=_("materials"), parent=parent, user=u)
        self._ = _
        self.set_current_user(u)

        self.materials_crud = MaterialsCRUD()
        self.mt_crud = MaterialTypesCRUD()
        self.curr_crud = CurrenciesCRUD()
        self.table.setAlternatingRowColors(True)

        # أعمدة الجدول
        actions_col = {"label": "actions", "key": "actions"}
        base_cols = [
            {"label": "code", "key": "code"},
            {"label": "arabic_name", "key": "name_ar"},
            {"label": "english_name", "key": "name_en"},
            {"label": "turkish_name", "key": "name_tr"},
            {"label": "material_type", "key": "material_type_name"},
            {"label": "estimated_price", "key": "estimated_price"},
            {"label": "currency", "key": "currency_code"},
            actions_col,
        ]
        self.set_columns_for_role(
            base_columns=base_cols,
            admin_columns=[
                {"label": "ID", "key": "id"},
                {"label": "created_by", "key": "created_by_name"},
                {"label": "updated_by", "key": "updated_by_name"},
                {"label": "created_at", "key": "created_at"},
                {"label": "updated_at", "key": "updated_at"},
            ],
        )

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

        items = self.materials_crud.get_all() or []

        # اجمع IDs للمستخدمين/الأنواع/العملات لتفادي N+1
        created_ids, updated_ids, type_ids, currency_ids = set(), set(), set(), set()
        for m in items:
            # استخدم *_id إن وُجد، وإلا جرّب العلاقة كـ int
            cb_id = getattr(m, "created_by_id", None)
            ub_id = getattr(m, "updated_by_id", None)
            if cb_id is None:
                rel = getattr(m, "created_by", None)
                if isinstance(rel, int):
                    cb_id = rel
            if ub_id is None:
                rel = getattr(m, "updated_by", None)
                if isinstance(rel, int):
                    ub_id = rel
            if isinstance(cb_id, int):
                created_ids.add(cb_id)
            if isinstance(ub_id, int):
                updated_ids.add(ub_id)

            mt_id = getattr(m, "material_type_id", None)
            if isinstance(mt_id, int):
                type_ids.add(mt_id)
            cur_id = getattr(m, "currency_id", None)
            if isinstance(cur_id, int):
                currency_ids.add(cur_id)

        id_to_user, id_to_type, id_to_currency = {}, {}, {}

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            if admin and (created_ids or updated_ids):
                q = s.query(User.id, User.full_name, User.username).filter(User.id.in_(created_ids | updated_ids))
                for uid, full_name, username in q:
                    id_to_user[uid] = full_name or username or str(uid)

            if type_ids:
                tq = s.query(MaterialType.id, MaterialType.name_ar, MaterialType.name_en, MaterialType.name_tr).filter(
                    MaterialType.id.in_(type_ids)
                )
                for tid, nar, nen, ntr in tq:
                    id_to_type[tid] = {"ar": nar, "en": nen, "tr": ntr}

            if currency_ids:
                cq = s.query(Currency.id, Currency.code).filter(Currency.id.in_(currency_ids))
                for cid, code in cq:
                    id_to_currency[cid] = code

        lang = TranslationManager.get_instance().get_current_language()

        self.data = []
        for m in items:
            mt_id = getattr(m, "material_type_id", None)
            mt_name = ""
            if isinstance(mt_id, int) and mt_id in id_to_type:
                mt_name = (
                        id_to_type[mt_id].get(lang)
                        or id_to_type[mt_id].get("en")
                        or id_to_type[mt_id].get("ar")
                        or id_to_type[mt_id].get("tr")
                        or ""
                )

            cur_id = getattr(m, "currency_id", None)
            cur_code = id_to_currency.get(cur_id, "") if isinstance(cur_id, int) else ""

            row = {
                "id": getattr(m, "id", None),
                "code": getattr(m, "code", "") or "",
                "name_ar": getattr(m, "name_ar", "") or "",
                "name_en": getattr(m, "name_en", "") or "",
                "name_tr": getattr(m, "name_tr", "") or "",
                "material_type_name": mt_name,
                "estimated_price": "" if getattr(m, "estimated_price", None) in (None, "") else str(
                    getattr(m, "estimated_price")),
                "currency_code": cur_code,
                "actions": m,
            }

            if admin:
                cb_rel = getattr(m, "created_by", None)
                ub_rel = getattr(m, "updated_by", None)
                cb_id = getattr(m, "created_by_id", None)
                ub_id = getattr(m, "updated_by_id", None)
                row.update({
                    "created_by_name": self._user_display(cb_rel, id_to_user, cb_id),
                    "updated_by_name": self._user_display(ub_rel, id_to_user, ub_id),
                    "created_at": str(getattr(m, "created_at", "") or ""),
                    "updated_at": str(getattr(m, "updated_at", "") or ""),
                })

            self.data.append(row)

        self.display_data()

    # -----------------------------
    # Display
    # -----------------------------
    def display_data(self):
        can_edit = has_perm(self.current_user, "edit_material")
        can_delete = has_perm(self.current_user, "delete_material")
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

                    obj = row["actions"]
                    action_layout = QHBoxLayout()
                    action_layout.setContentsMargins(0, 0, 0, 0)
                    action_layout.setSpacing(6)

                    if can_edit:
                        btn_edit = QPushButton(self._("edit"))
                        btn_edit.setObjectName("table-edit")
                        btn_edit.clicked.connect(lambda _=False, o=obj: self._open_edit_dialog(o))
                        action_layout.addWidget(btn_edit)
                        btn_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

                    if can_delete:
                        btn_delete = QPushButton(self._("delete"))
                        btn_delete.setObjectName("table-delete")
                        btn_delete.clicked.connect(lambda _=False, o=obj: self._delete_single(o))
                        action_layout.addWidget(btn_delete)
                        btn_delete.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

                    w = QWidget()
                    w.setLayout(action_layout)
                    self.table.setCellWidget(row_idx, col_idx, w)
                else:
                    item = QTableWidgetItem(str(row.get(key, "")))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_idx, col_idx, item)

        # إخفاء عمود الإجراءات إذا ما في صلاحيات
        try:
            actions_index = next((i for i, c in enumerate(self.columns) if c.get("key") == "actions"), None)
            if actions_index is not None:
                self.table.setColumnHidden(actions_index, not show_actions)
        except Exception:
            pass

        self._apply_admin_columns()
        self.update_pagination_label()

    # -----------------------------
    # Actions
    # -----------------------------
    def add_new_item(self):
        # جهّز قوائم النوع/العملة للحوار
        material_types = self.mt_crud.get_all() or []
        currencies = self.curr_crud.get_all() or []
        dlg = AddMaterialDialog(self, None, material_types=material_types, currencies=currencies)
        if dlg.exec():
            data = dlg.get_data()
            user_id = self._user_id()
            self.materials_crud.add_material(
                code=data["code"],
                name_ar=data["name_ar"],
                name_en=data["name_en"],
                name_tr=data["name_tr"],
                material_type_id=data["material_type_id"],
                estimated_price=data["estimated_price"],
                currency_id=data["currency_id"],
                user_id=user_id,
            )
            QMessageBox.information(self, self._("added"), self._("material_added_success"))
            self.reload_data()

    def edit_selected_item(self, row=None):
        if row is None:
            rows = self.get_selected_rows()
            if not rows:
                return
            row = rows[0]
        material = self.data[row]["actions"]
        self._open_edit_dialog(material)

    def _open_edit_dialog(self, material):
        material_types = self.mt_crud.get_all() or []
        currencies = self.curr_crud.get_all() or []
        dlg = AddMaterialDialog(self, material, material_types=material_types, currencies=currencies)
        if dlg.exec():
            data = dlg.get_data()
            user_id = self._user_id()
            self.materials_crud.update_material(material.id, data, user_id=user_id)
            QMessageBox.information(self, self._("updated"), self._("material_updated_success"))
            self.reload_data()

    def delete_selected_items(self, rows=None):
        if rows is None:
            rows = self.get_selected_rows()
        if not rows:
            return
        reply = QMessageBox.question(
            self, self._("delete_material"), self._("are_you_sure_delete"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for row in rows:
                m = self.data[row]["actions"]
                self._delete_single(m, confirm=False)
            QMessageBox.information(self, self._("deleted"), self._("material_deleted_success"))
            self.reload_data()

    def _delete_single(self, material, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, self._("delete_material"), self._("are_you_sure_delete"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.materials_crud.delete(material.id)

    # Double-click → details
    def on_row_double_clicked(self, row_index):
        try:
            row = int(row_index)
        except Exception:
            row = getattr(row_index, "row", lambda: -1)()
        if 0 <= row < len(self.data):
            m = self.data[row]["actions"]
            dlg = ViewMaterialDialog(m, current_user=self.current_user, parent=self)
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
                    parent.setTabText(idx, self._("materials"))
        except Exception:
            pass
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
        if isinstance(self.current_user, dict):
            return self.current_user.get("id")
        return getattr(self.current_user, "id", None)

    def _user_display(self, rel, id_to_name, fallback_id=None) -> str:
        from database.models import User  # يضمن الـtype check بدون استيراد دائري
        if isinstance(rel, User):
            return getattr(rel, "full_name", None) or getattr(rel, "username", None) or str(getattr(rel, "id", fallback_id or ""))
        if isinstance(rel, int):
            return id_to_name.get(rel, str(rel))
        if fallback_id is not None:
            return id_to_name.get(fallback_id, str(fallback_id))
        return ""
