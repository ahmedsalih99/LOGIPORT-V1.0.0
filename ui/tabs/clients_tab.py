from core.base_tab import BaseTab
from ui.dialogs.add_client_dialog import AddClientDialog
from ui.dialogs.view_details.view_client_dialog import ViewClientDialog

from database.crud.clients_crud import ClientsCRUD
from database.crud.countries_crud import CountriesCRUD
from database.crud.currencies_crud import CurrenciesCRUD

from core.translator import TranslationManager
from core.settings_manager import SettingsManager

from database.models import get_session_local, User, Country

from core.permissions import has_perm, is_admin
from core.admin_columns import apply_admin_columns_to_table

from PySide6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QHBoxLayout, QWidget, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt


class ClientsTab(BaseTab):
    required_permissions = {
        "view":    ["view_clients"],
        "add":     ["add_client"],
        "edit":    ["edit_client"],
        "delete":  ["delete_client"],
        "import":  ["view_clients"],
        "export":  ["view_clients"],
        "print":   ["view_clients"],
        "refresh": ["view_clients"],
    }

    def __init__(self, parent=None, current_user=None):
        _ = TranslationManager.get_instance().translate
        settings = SettingsManager.get_instance()
        u = current_user or settings.get("user", None) or getattr(parent, "current_user", None)

        super().__init__(title=_("clients"), parent=parent, user=u)
        self._ = _
        self.set_current_user(u)

        self.clients_crud = ClientsCRUD()
        self.countries_crud = CountriesCRUD()
        self.curr_crud = CurrenciesCRUD()
        self.table.setAlternatingRowColors(True)

        actions_col = {"label": "actions", "key": "actions"}
        base_cols = [
            {"label": "name", "key": "name_local"},          # ← اسم واحد حسب لغة الواجهة
            {"label": "country", "key": "country_name"},
            {"label": "city", "key": "city"},
            {"label": "address", "key": "address_local"},   # ← عنوان محلي حسب اللغة
            {"label": "phone", "key": "phone"},
            {"label": "notes", "key": "notes"},
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

        self.request_edit.connect(self.edit_selected_item)
        self.request_delete.connect(self.delete_selected_items)
        self.row_double_clicked.connect(self.on_row_double_clicked)
        if hasattr(self, "request_refresh"):
            self.request_refresh.connect(self.reload_data)

        self.reload_data()
        self._init_done = True

    def reload_data(self):
        self._skip_base_search = True   # البحث يتم server-side أو بـ _apply_search_filter
        self._skip_base_sort   = True   # الترتيب يتم server-side أو يُدار بـ CRUD
        admin = is_admin(self.current_user)

        # 1) اجلب السجلات
        items = self.clients_crud.get_all() or []

        # 2) طبّق الفلترة والفرز داخل الذاكرة
        items = self._apply_search_filter(items)
        items = self._apply_order(items)

        # 3) جهّز مراجع المستخدمين والبلدان
        created_ids, updated_ids, country_ids = set(), set(), set()
        for c in items:
            cb_id = getattr(c, "created_by_id", None)
            ub_id = getattr(c, "updated_by_id", None)
            if isinstance(cb_id, int):
                created_ids.add(cb_id)
            if isinstance(ub_id, int):
                updated_ids.add(ub_id)
            if isinstance(getattr(c, "country_id", None), int):
                country_ids.add(c.country_id)

        id_to_user, id_to_country = {}, {}

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            if admin and (created_ids or updated_ids):
                q = s.query(User.id, User.full_name, User.username).filter(
                    User.id.in_(created_ids | updated_ids)
                )
                for uid, full_name, username in q:
                    id_to_user[uid] = full_name or username or str(uid)

            if country_ids:
                cq = s.query(Country.id, Country.name_ar, Country.name_en, Country.name_tr).filter(
                    Country.id.in_(country_ids)
                )
                for cid, nar, nen, ntr in cq:
                    id_to_country[cid] = {"ar": nar, "en": nen, "tr": ntr}

        lang = TranslationManager.get_instance().get_current_language()

        # 4) ابنِ بيانات الجدول
        self.data = []
        for c in items:
            # country label by lang
            co_id = getattr(c, "country_id", None)
            country_name = ""
            if isinstance(co_id, int) and co_id in id_to_country:
                country_name = (
                        id_to_country[co_id].get(lang)
                        or id_to_country[co_id].get("en")
                        or id_to_country[co_id].get("ar")
                        or id_to_country[co_id].get("tr")
                        or ""
                )

            # localized client name (fallbacks)
            if lang == "ar":
                name_local = (
                        getattr(c, "name_ar", None)
                        or getattr(c, "name_en", None)
                        or getattr(c, "name_tr", None)
                        or ""
                )
            elif lang == "tr":
                name_local = (
                        getattr(c, "name_tr", None)
                        or getattr(c, "name_en", None)
                        or getattr(c, "name_ar", None)
                        or ""
                )
            else:
                name_local = (
                        getattr(c, "name_en", None)
                        or getattr(c, "name_ar", None)
                        or getattr(c, "name_tr", None)
                        or ""
                )

            # localized address with legacy fallback
            if lang == "ar":
                address_local = (getattr(c, "address_ar", "") or getattr(c, "address", "") or "")
            elif lang == "tr":
                address_local = (getattr(c, "address_tr", "") or getattr(c, "address", "") or "")
            else:
                address_local = (getattr(c, "address_en", "") or getattr(c, "address", "") or "")

            row = {
                "id": getattr(c, "id", None),
                "name_local": name_local,
                "country_name": country_name,
                "city": getattr(c, "city", "") or "",
                "address_local": address_local,
                "phone": getattr(c, "phone", "") or "",
                "notes": getattr(c, "notes", "") or "",
                "actions": c,
            }

            if admin:
                row.update({
                    "created_by_name": self._user_display(
                        getattr(c, "created_by", None), id_to_user, getattr(c, "created_by_id", None)
                    ),
                    "updated_by_name": self._user_display(
                        getattr(c, "updated_by", None), id_to_user, getattr(c, "updated_by_id", None)
                    ),
                    "created_at": str(getattr(c, "created_at", "") or ""),
                    "updated_at": str(getattr(c, "updated_at", "") or ""),
                })

            self.data.append(row)

        # 5) اعرض النتائج
        self.display_data()

    def display_data(self):
        can_edit = has_perm(self.current_user, "edit_client")
        can_delete = has_perm(self.current_user, "delete_client")
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
                        btn_edit.setObjectName("primary-btn")
                        btn_edit.clicked.connect(lambda _=False, o=obj: self._open_edit_dialog(o))
                        action_layout.addWidget(btn_edit)
                        btn_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)


                    if can_delete:
                        btn_delete = QPushButton(self._("delete"))
                        btn_delete.setObjectName("danger-btn")
                        btn_delete.clicked.connect(lambda _=False, o=obj: self._delete_single(o))
                        action_layout.addWidget(btn_delete)
                        btn_delete.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)


                    w = QWidget(); w.setLayout(action_layout)
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

    def add_new_item(self):
        countries = self.countries_crud.get_all() or []
        currencies = self.curr_crud.get_all() or []
        dlg = AddClientDialog(self, None, countries=countries, currencies=currencies)
        if dlg.exec():
            data = dlg.get_data()
            user_id = self._user_id()
            self.clients_crud.add_client(
                name_ar=data["name_ar"],
                name_en=data["name_en"],
                name_tr=data["name_tr"],
                country_id=data["country_id"],
                city=data["city"],
                address_ar=data["address_ar"],
                address_en=data["address_en"],
                address_tr=data["address_tr"],
                default_currency_id=data["default_currency_id"],
                phone=data["phone"],
                email=data["email"],
                website=data["website"],
                tax_id=data["tax_id"],
                notes=data["notes"],
                user_id=user_id,
            )
            QMessageBox.information(self, self._("added"), self._("client_added_success"))
            self.reload_data()

    def edit_selected_item(self, row=None):
        if row is None:
            rows = self.get_selected_rows()
            if not rows:
                return
            row = rows[0]
        client = self.data[row]["actions"]
        self._open_edit_dialog(client)

    def _open_edit_dialog(self, client):
        countries = self.countries_crud.get_all() or []
        currencies = self.curr_crud.get_all() or []
        dlg = AddClientDialog(self, client, countries=countries, currencies=currencies)
        if dlg.exec():
            data = dlg.get_data()
            user_id = self._user_id()
            self.clients_crud.update_client(client.id, data, user_id=user_id)
            QMessageBox.information(self, self._("updated"), self._("client_updated_success"))
            self.reload_data()

    def delete_selected_items(self, rows=None):
        if rows is None:
            rows = self.get_selected_rows()
        if not rows:
            return
        reply = QMessageBox.question(
            self, self._("delete_client"), self._("are_you_sure_delete"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for row in rows:
                c = self.data[row]["actions"]
                self._delete_single(c, confirm=False)
            QMessageBox.information(self, self._("deleted"), self._("client_deleted_success"))
            self.reload_data()

    def _delete_single(self, client, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, self._("delete_client"), self._("are_you_sure_delete"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.clients_crud.delete_client(client.id)

    def on_row_double_clicked(self, row_index):
        try:
            row = int(row_index)
        except Exception:
            row = getattr(row_index, "row", lambda: -1)()
        if 0 <= row < len(self.data):
            c = self.data[row]["actions"]
            dlg = ViewClientDialog(c, current_user=self.current_user, parent=self)
            dlg.exec()

    def retranslate_ui(self):
        super().retranslate_ui()
        parent = self.parent()
        try:
            if parent and hasattr(parent, "indexOf") and hasattr(parent, "setTabText"):
                idx = parent.indexOf(self)
                if idx != -1:
                    parent.setTabText(idx, self._("clients"))
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
        from database.models import User
        if isinstance(rel, User):
            return getattr(rel, "full_name", None) or getattr(rel, "username", None) or str(getattr(rel, "id", fallback_id or ""))
        if isinstance(rel, int):
            return id_to_name.get(rel, str(rel))
        if fallback_id is not None:
            return id_to_name.get(fallback_id, str(fallback_id))
        return ""

    def _read_search_text(self) -> str:
        for attr in ("get_search_text", "get_search_query"):
            if hasattr(self, attr) and callable(getattr(self, attr)):
                try:
                    return str(getattr(self, attr)() or "").strip()
                except Exception:
                    pass
        for name in ("search_bar", "search_input", "txt_search", "search_line_edit"):
            w = getattr(self, name, None)
            if w is not None and hasattr(w, "text"):
                try:
                    return str(w.text() or "").strip()
                except Exception:
                    pass
        return ""

    def _read_order_key(self) -> str:
        # default ordering
        key = "created_at_desc"
        for name in ("order_combobox", "cmb_order", "order_by", "cmb_sort"):
            w = getattr(self, name, None)
            if w is None:
                continue
            for fn in ("currentData", "currentText"):
                if hasattr(w, fn):
                    try:
                        v = getattr(w, fn)()
                        if v:
                            txt = str(v).strip().lower()
                            if "name" in txt:
                                return "name_asc"
                            if "creation" in txt or "created" in txt or "date" in txt:
                                return "created_at_desc"
                            return txt
                    except Exception:
                        pass
        return key

    def _apply_search_filter(self, items):
        q = self._read_search_text().casefold()
        if not q:
            return list(items)

        def hit(c):
            try:
                fields = [
                    getattr(c, "name_ar", ""), getattr(c, "name_en", ""), getattr(c, "name_tr", ""),
                    getattr(c, "city", ""), getattr(c, "phone", ""), getattr(c, "email", ""), getattr(c, "website", ""),
                    getattr(c, "tax_id", ""), getattr(c, "address_ar", ""), getattr(c, "address_en", ""),
                    getattr(c, "address_tr", ""), getattr(c, "address", ""),
                ]
                if any(q in str(f or "").casefold() for f in fields):
                    return True
                co = getattr(c, "country", None)
                if co is not None:
                    for n in (getattr(co, "name_ar", None), getattr(co, "name_en", None), getattr(co, "name_tr", None)):
                        if q in str(n or "").casefold():
                            return True
                return False
            except Exception:
                return False

        return [c for c in items if hit(c)]

    def _apply_order(self, items):
        key = self._read_order_key()
        if not items:
            return items
        try:
            if key.startswith("name"):
                return sorted(items, key=lambda c: (
                    str(getattr(c, "name_en", "") or getattr(c, "name_ar", "") or getattr(c, "name_tr",
                                                                                          "")).casefold()))
            # default: created_at desc then id desc
            return sorted(items, key=lambda c: (getattr(c, "created_at", None) or 0, getattr(c, "id", 0)), reverse=False)
        except Exception:
            return items