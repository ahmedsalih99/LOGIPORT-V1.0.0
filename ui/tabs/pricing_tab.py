from core.base_tab import BaseTab
from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from core.permissions import has_perm, is_admin
from core.admin_columns import apply_admin_columns_to_table
from database.crud.delivery_methods_crud import DeliveryMethodsCRUD

from database.crud.pricing_crud import PricingCRUD
from database.models import get_session_local, User
from database.models.company import Company
from database.models.material import Material
from database.models.currency import Currency
try:
    from database.models.pricing_type import PricingType
except Exception:
    PricingType = None

from ui.dialogs.add_pricing_dialog import AddPricingDialog
from ui.dialogs.view_details.view_pricing_dialog import ViewPricingDialog

from PySide6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QHBoxLayout, QWidget, QPushButton
)
from PySide6.QtCore import Qt


class PricingTab(BaseTab):
    required_permissions = {
        "view":    ["view_pricing"],
        "add":     ["add_pricing"],
        "edit":    ["edit_pricing"],
        "delete":  ["delete_pricing"],
        "import":  ["view_pricing"],
        "export":  ["view_pricing"],
        "print":   ["view_pricing"],
        "refresh": ["view_pricing"],
    }

    def __init__(self, parent=None, current_user=None):
        _ = TranslationManager.get_instance().translate
        settings = SettingsManager.get_instance()
        u = current_user or settings.get("user", None) or getattr(parent, "current_user", None)

        super().__init__(title=_("pricing"), parent=parent, user=u)
        self._ = _
        self.set_current_user(u)

        self.pricing_crud = PricingCRUD()
        self.table.setAlternatingRowColors(True)

        actions_col = {"label": "actions", "key": "actions"}
        base_cols = [
            {"label": "seller_company",  "key": "seller_company_name"},
            {"label": "buyer_company",   "key": "buyer_company_name"},
            {"label": "material",        "key": "material_name"},
            {"label": "pricing_type",    "key": "pricing_type_name"},
            {"label": "price",           "key": "price"},
            {"label": "currency",        "key": "currency_code"},
            {"label": "delivery_method", "key": "delivery_method_label"},
            {"label": "is_active",       "key": "is_active_label"},
            actions_col,
        ]
        self.set_columns_for_role(
            base_columns=base_cols,
            admin_columns=[
                {"label": "ID",         "key": "id"},
                {"label": "created_by", "key": "created_by_name"},
                {"label": "updated_by", "key": "updated_by_name"},
                {"label": "created_at", "key": "created_at"},
                {"label": "updated_at", "key": "updated_at"},
            ],
        )

        self.check_permissions()

        self.request_edit.connect(self.edit_selected_item)
        self.request_delete.connect(self.delete_selected_items)
        self.row_double_clicked.connect(self.on_row_double_clicked)
        if hasattr(self, "request_refresh"):
            self.request_refresh.connect(self.reload_data)

        self.reload_data()
        self._init_done = True

    # ---------- data loading ----------
    def reload_data(self):
        admin = is_admin(self.current_user)
        items = self.pricing_crud.list() or []

        # اجمع كل الـ IDs المطلوبة لاستعلام واحد سريع
        seller_ids, buyer_ids, material_ids, currency_ids, ptype_ids = set(), set(), set(), set(), set()
        created_ids, updated_ids, dm_ids = set(), set(), set()

        for p in items:
            if isinstance(getattr(p, "seller_company_id", None), int):
                seller_ids.add(p.seller_company_id)
            if isinstance(getattr(p, "buyer_company_id", None), int):
                buyer_ids.add(p.buyer_company_id)
            if isinstance(getattr(p, "material_id", None), int):
                material_ids.add(p.material_id)
            if isinstance(getattr(p, "currency_id", None), int):
                currency_ids.add(p.currency_id)
            if isinstance(getattr(p, "pricing_type_id", None), int):
                ptype_ids.add(p.pricing_type_id)
            cb_id = getattr(p, "created_by_id", None)
            ub_id = getattr(p, "updated_by_id", None)
            if isinstance(cb_id, int):
                created_ids.add(cb_id)
            if isinstance(ub_id, int):
                updated_ids.add(ub_id)
            dm_id = getattr(p, "delivery_method_id", None)
            if isinstance(dm_id, int):
                dm_ids.add(dm_id)

        id_to_company = {}
        id_to_material = {}
        id_to_currency = {}
        id_to_ptype = {}
        id_to_user = {}

        lang = TranslationManager.get_instance().get_current_language()

        def _pick_lang_map(d):
            if not d:
                return ""
            return d.get(lang) or d.get("en") or d.get("ar") or d.get("tr") or ""

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            if seller_ids or buyer_ids:
                q = s.query(Company.id, Company.name_ar, Company.name_en, Company.name_tr).filter(
                    Company.id.in_(seller_ids | buyer_ids))
                for cid, nar, nen, ntr in q:
                    id_to_company[cid] = {"ar": nar, "en": nen, "tr": ntr}
            if material_ids:
                q = s.query(Material.id, Material.name_ar, Material.name_en, Material.name_tr).filter(
                    Material.id.in_(material_ids))
                for mid, nar, nen, ntr in q:
                    id_to_material[mid] = {"ar": nar, "en": nen, "tr": ntr}
            if currency_ids:
                q = s.query(Currency.id, Currency.code).filter(Currency.id.in_(currency_ids))
                for cid, code in q:
                    id_to_currency[cid] = code or ""
            if PricingType is not None and ptype_ids:
                q = s.query(PricingType.id, PricingType.name_ar, PricingType.name_en, PricingType.name_tr,
                            PricingType.code).filter(PricingType.id.in_(ptype_ids))
                for pid, nar, nen, ntr, code in q:
                    id_to_ptype[pid] = {"ar": nar, "en": nen, "tr": ntr, "code": code}
            if admin and (created_ids or updated_ids):
                q = s.query(User.id, User.full_name, User.username).filter(User.id.in_(created_ids | updated_ids))
                for uid, full_name, username in q:
                    id_to_user[uid] = full_name or username or str(uid)

        # ✅ أسماء طرق التسليم من CRUD
        id_to_dm_label = self._load_delivery_labels(dm_ids)

        self.data = []
        for p in items:
            sc = id_to_company.get(getattr(p, "seller_company_id", None), {})
            bc = id_to_company.get(getattr(p, "buyer_company_id", None), {})
            mm = id_to_material.get(getattr(p, "material_id", None), {})
            pt = id_to_ptype.get(getattr(p, "pricing_type_id", None), {})
            cur_code = id_to_currency.get(getattr(p, "currency_id", None), "")

            pricing_type_name = _pick_lang_map(pt) or (pt.get("code", "") if isinstance(pt, dict) else "")

            dm_id = getattr(p, "delivery_method_id", None)
            if isinstance(dm_id, int) and dm_id in id_to_dm_label:
                dm_label = id_to_dm_label[dm_id]
            else:
                dm_label = self._("not_set") if dm_id is None else str(dm_id)

            is_active_label = self._("active") if getattr(p, "is_active", True) else self._("inactive")

            row = {
                "id": getattr(p, "id", None),
                "seller_company_name": _pick_lang_map(sc),
                "buyer_company_name": _pick_lang_map(bc),
                "material_name": _pick_lang_map(mm),
                "pricing_type_name": pricing_type_name,
                "price": str(getattr(p, "price", "") or ""),
                "currency_code": cur_code,
                "delivery_method_label": dm_label,
                "is_active_label": is_active_label,
                "actions": p,
            }

            if admin:
                row.update({
                    "created_by_name": self._user_display(getattr(p, "created_by", None), id_to_user,
                                                          getattr(p, "created_by_id", None)),
                    "updated_by_name": self._user_display(getattr(p, "updated_by", None), id_to_user,
                                                          getattr(p, "updated_by_id", None)),
                    "created_at": str(getattr(p, "created_at", "") or ""),
                    "updated_at": str(getattr(p, "updated_at", "") or ""),
                })

            self.data.append(row)

        self.display_data()

    def display_data(self):
        can_edit = has_perm(self.current_user, "edit_pricing")
        can_delete = has_perm(self.current_user, "delete_pricing")
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
                    layout = QHBoxLayout()
                    layout.setContentsMargins(0, 0, 0, 0)
                    layout.setSpacing(12)

                    if can_edit:
                        btn_edit = QPushButton(self._("edit"))
                        btn_edit.setObjectName("primary-btn")
                        btn_edit.clicked.connect(lambda _=False, o=obj: self._open_edit_dialog(o))
                        layout.addWidget(btn_edit)

                    if can_delete:
                        btn_delete = QPushButton(self._("delete"))
                        btn_delete.setObjectName("danger-btn")
                        btn_delete.clicked.connect(lambda _=False, o=obj: self._delete_single(o))
                        layout.addWidget(btn_delete)

                    w = QWidget(); w.setLayout(layout)
                    self.table.setCellWidget(row_idx, col_idx, w)
                else:
                    item = QTableWidgetItem(str(row.get(key, "")))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_idx, col_idx, item)

        try:
            actions_index = next((i for i, c in enumerate(self.columns) if c.get("key") == "actions"), None)
            if actions_index is not None:
                self.table.setColumnHidden(actions_index, not show_actions)
        except Exception:
            pass

        self._apply_admin_columns()
        self.update_pagination_label()

    # ---------- actions ----------
    def add_new_item(self):
        # جهّز قوائم الاختيار من الـ DB مباشرة (نفس أسلوب clients_tab)
        sellers, buyers, materials, currencies, ptypes = [], [], [], [], []
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            sellers = s.query(Company).order_by(Company.name_ar.asc()).all()
            buyers = sellers
            materials = s.query(Material).order_by(Material.name_ar.asc()).all()
            currencies = s.query(Currency).order_by(Currency.code.asc()).all()
            if PricingType is not None:
                order1 = getattr(PricingType, "sort_order", None)
                ptypes = s.query(PricingType).order_by(
                    order1.asc() if order1 is not None else PricingType.id.asc(),
                    PricingType.id.asc()
                ).all()

        dlg = AddPricingDialog(self, None,
                               sellers=sellers, buyers=buyers,
                               materials=materials, currencies=currencies, pricing_types=ptypes)
        if dlg.exec():
            data = dlg.get_data()
            user_id = self._user_id()
            self.pricing_crud.add_pricing(data, user_id=user_id)
            QMessageBox.information(self, self._("added"), self._("pricing_added_success"))
            self.reload_data()

    def edit_selected_item(self, row=None):
        if row is None:
            rows = self.get_selected_rows()
            if not rows:
                return
            row = rows[0]
        p = self.data[row]["actions"]
        self._open_edit_dialog(p)

    def _open_edit_dialog(self, pricing):
        sellers, buyers, materials, currencies, ptypes = [], [], [], [], []
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            sellers   = s.query(Company).order_by(Company.name_ar.asc()).all()
            buyers    = sellers
            materials = s.query(Material).order_by(Material.name_ar.asc()).all()
            currencies= s.query(Currency).order_by(Currency.code.asc()).all()
            if PricingType is not None:
                ptypes = s.query(PricingType).order_by(
                    getattr(PricingType, "sort_order", None).asc() if hasattr(PricingType, "sort_order") else PricingType.id.asc(),
                    PricingType.id.asc()
                ).all()

        dlg = AddPricingDialog(self, pricing,
                               sellers=sellers, buyers=buyers,
                               materials=materials, currencies=currencies, pricing_types=ptypes)
        if dlg.exec():
            data = dlg.get_data()
            user_id = self._user_id()
            self.pricing_crud.update_pricing(pricing.id, data, user_id=user_id)
            QMessageBox.information(self, self._("updated"), self._("pricing_updated_success"))
            self.reload_data()

    def delete_selected_items(self, rows=None):
        if rows is None:
            rows = self.get_selected_rows()
        if not rows:
            return
        reply = QMessageBox.question(
            self, self._("delete_pricing"), self._("are_you_sure_delete"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for row in rows:
                p = self.data[row]["actions"]
                self._delete_single(p, confirm=False)
            QMessageBox.information(self, self._("deleted"), self._("pricing_deleted_success"))
            self.reload_data()

    def _delete_single(self, pricing, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, self._("delete_pricing"), self._("are_you_sure_delete"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.pricing_crud.delete_pricing(pricing.id)

    def on_row_double_clicked(self, row_index):
        try:
            row = int(row_index)
        except Exception:
            row = getattr(row_index, "row", lambda: -1)()
        if 0 <= row < len(self.data):
            p = self.data[row]["actions"]
            dlg = ViewPricingDialog(p, current_user=self.current_user, parent=self)
            dlg.exec()

    # ---------- utils ----------
    def retranslate_ui(self):
        super().retranslate_ui()
        parent = self.parent()
        try:
            if parent and hasattr(parent, "indexOf") and hasattr(parent, "setTabText"):
                idx = parent.indexOf(self)
                if idx != -1:
                    parent.setTabText(idx, self._("pricing"))
        except Exception:
            pass
        self._apply_columns_for_current_role()
        self.reload_data()

    def _apply_admin_columns(self):
        admin_keys = ("id", "created_by_name", "updated_by_name", "created_at", "updated_at")
        admin_cols = [idx for idx, col in enumerate(self.columns) if col.get("key") in admin_keys]
        apply_admin_columns_to_table(self.table, self.current_user, admin_cols)

    def _user_id(self):
        if isinstance(self.current_user, dict):
            return self.current_user.get("id")
        return getattr(self.current_user, "id", None)

    def _user_display(self, rel, id_to_name, fallback_id=None) -> str:
        if isinstance(rel, User):
            return getattr(rel, "full_name", None) or getattr(rel, "username", None) or str(getattr(rel, "id", fallback_id or ""))
        if isinstance(rel, int):
            return id_to_name.get(rel, str(rel))
        if fallback_id is not None:
            return id_to_name.get(fallback_id, str(fallback_id))
        return ""

    def _load_delivery_labels(self, dm_ids: set) -> dict:
        """
        إرجاع قاموس {delivery_method_id: localized_label} باستخدام DeliveryMethodsCRUD.
        إذا ما في دوال تصفية بالـCRUD، منجيب الكل ونفلتر محليًا.
        """
        labels = {}
        if not dm_ids:
            return labels
        try:
            lang = TranslationManager.get_instance().get_current_language()
            crud = DeliveryMethodsCRUD()

            # حاول تستخدم get_all بترتيب منطقي
            methods = []
            try:
                methods = crud.get_all(order_by=["sort_order", "id"]) or []
            except Exception:
                methods = crud.get_all() or []

            for dm in methods:
                did = getattr(dm, "id", None)
                if did in dm_ids:
                    # اختيار التسمية حسب اللغة
                    if lang == "ar" and getattr(dm, "name_ar", None):
                        labels[did] = dm.name_ar
                    elif lang == "tr" and getattr(dm, "name_tr", None):
                        labels[did] = dm.name_tr
                    else:
                        labels[did] = getattr(dm, "name_en", None) or getattr(dm, "name_ar", None) or getattr(dm,
                                                                                                              "name_tr",
                                                                                                              None) or f"#{did}"
        except Exception:
            # في حال أي خطأ، منرجع قاموس فاضي وباقي الكود يعمل fallback للـID/Not set
            pass
        return labels
