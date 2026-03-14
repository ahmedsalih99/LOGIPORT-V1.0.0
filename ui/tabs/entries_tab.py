from core.base_tab import BaseTab
from core.data_bus import DataBus
from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from core.permissions import has_perm, is_admin
from core.admin_columns import apply_admin_columns_to_table
from PySide6.QtWidgets import QHeaderView

from database.crud.entries_crud import EntriesCRUD
from database.models import get_session_local, User
from database.models.entry import Entry
from database.models.entry_item import EntryItem
from database.models.client import Client
from database.models.material import Material
from database.models.packaging_type import PackagingType
from database.models.country import Country

from ui.dialogs.add_entry_dialog import AddEntryDialog
from ui.dialogs.view_details.view_entry_dialog import ViewEntryDialog


from PySide6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QHBoxLayout, QWidget, QPushButton,
    QDateEdit, QLabel, QFrame
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

def _align_center(item: QTableWidgetItem):
    item.setTextAlignment(Qt.AlignCenter)
    return item

def pick_name_by_lang(obj, lang: str, ar="name_ar", en="name_en", tr="name_tr"):
    if not obj:
        return ""

    # إذا كان dict (وهو حالتك الحالية)
    if isinstance(obj, dict):
        if lang == "ar" and obj.get(ar):
            return obj.get(ar)
        if lang == "tr" and obj.get(tr):
            return obj.get(tr)
        return obj.get(en) or obj.get(ar) or obj.get(tr) or ""

    # إذا كان ORM object
    if lang == "ar" and getattr(obj, ar, None):
        return getattr(obj, ar)
    if lang == "tr" and getattr(obj, tr, None):
        return getattr(obj, tr)

    return (
        getattr(obj, en, None)
        or getattr(obj, ar, None)
        or getattr(obj, tr, None)
        or ""
    )


class EntriesTab(BaseTab):
    required_permissions = {
        "view":    ["view_entries"],
        "add":     ["add_entry"],
        "edit":    ["edit_entry"],
        "delete":  ["delete_entry"],
        "import":  ["view_entries"],
        "export":  ["view_entries"],
        "print":   ["view_entries"],
        "refresh": ["view_entries"],
    }

    def __init__(self, parent=None, current_user=None):
        _ = TranslationManager.get_instance().translate
        settings = SettingsManager.get_instance()
        u = current_user or settings.get("user", None) or getattr(parent, "current_user", None)

        super().__init__(title=_("entries"), parent=parent, user=u)
        self._ = _
        self.set_current_user(u)

        self.crud = EntriesCRUD()
        self.table.setAlternatingRowColors(True)

        actions_col = {"label": "actions", "key": "actions"}
        base_cols = [
            {"label": "entry_no",           "key": "entry_no"},
            {"label": "entry_date",         "key": "entry_date"},
            {"label": "transport_unit_type","key": "transport_unit_label"},
            {"label": "owner_client",       "key": "owner_client_name"},
            {"label": "items_count",        "key": "items_count"},
            {"label": "total_pcs",          "key": "total_pcs"},
            {"label": "total_net",          "key": "total_net"},
            {"label": "total_gross",        "key": "total_gross"},
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

        # زر "ربط بكونتينر" في toolbar
        self._btn_link_container = QPushButton(f"🚢  {self._('link_container')}")
        self._btn_link_container.setObjectName("secondary-btn")
        self._btn_link_container.setToolTip(self._("link_container_tooltip"))
        self._btn_link_container.clicked.connect(self._link_container)
        self.top_bar.addWidget(self._btn_link_container)

        self._build_filter_bar()
        self.reload_data()
        DataBus.get_instance().subscribe('entries', self.reload_data)
        DataBus.get_instance().subscribe('clients', self.reload_data)
        self._init_done = True

    # ── Filter bar ──────────────────────────────────────────────────────────

    def _build_filter_bar(self):
        from core.base_tab import DateRangeBar
        self._date_bar = DateRangeBar(self, default_months=3)
        self._date_bar.changed.connect(self._on_filter_changed)
        # alias للتوافق مع reload_data
        self._date_from = self._date_bar._date_from
        self._date_to   = self._date_bar._date_to
        try:
            self.layout.insertWidget(1, self._date_bar)
        except Exception:
            self.layout.addWidget(self._date_bar)

    def _on_filter_changed(self, *_):
        self.reload_data()

    # ---------- data ----------
    def reload_data(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._skip_base_search = True   # البحث يتم server-side أو بـ _apply_search_filter
        self._skip_base_sort   = True   # الترتيب يتم server-side أو يُدار بـ CRUD
        _ = TranslationManager.get_instance().translate
        lang = TranslationManager.get_instance().get_current_language()

        # قيم الفلاتر
        d_from = self._date_from.date().toString("yyyy-MM-dd") if hasattr(self, "_date_from") else None
        d_to = self._date_to.date().toString("yyyy-MM-dd") if hasattr(self, "_date_to") else None
        search = self.search_bar.text().strip().lower() if hasattr(self, "search_bar") else ""

        # pagination server-side
        try:
            self.total_rows = self.crud.count_with_totals(date_from=d_from, date_to=d_to)
        except Exception:
            self.total_rows = 0
        self.total_pages  = max(1, -(-self.total_rows // self.rows_per_page))
        self.current_page = min(self.current_page, self.total_pages)

        # جلب البيانات من CRUD
        try:
            rows = self.crud.list_with_totals(
                limit  = self.rows_per_page,
                offset = (self.current_page - 1) * self.rows_per_page,
                date_from=d_from,
                date_to=d_to,
            )
        except TypeError:
            rows = self.crud.list_with_totals(limit=self.rows_per_page)

        self.data = []

        for r in rows:
            # ترجمة نوع وسيلة النقل
            transport_type = r.get("transport_unit_type") or "truck"
            unit_label = {
                "truck": _("truck"),
                "other": _("other")
            }.get(transport_type, _("truck"))

            # اسم العميل حسب لغة التطبيق
            client_obj = r.get("owner_client_obj")  # يحتوي على name_ar, name_en, name_tr
            if client_obj:
                client_name = pick_name_by_lang(client_obj, lang)
            else:
                client_name = r.get("owner_client_name") or ""

            entry_no = r.get("entry_no") or r.get("transport_ref") or ""

            self.data.append({
                "entry_no": entry_no,
                "entry_date": str(r.get("entry_date") or ""),
                "transport_unit_label": unit_label,
                "owner_client_name": client_name,
                "items_count": int(r.get("items_count") or 0),
                "total_pcs": f"{float(r.get('total_pcs') or 0):.0f}",
                "total_net": f"{float(r.get('total_net') or 0):.2f}",
                "total_gross": f"{float(r.get('total_gross') or 0):.2f}",
                "id": r.get("id"),
                "created_by_name": r.get("created_by_name") or "",
                "updated_by_name": r.get("updated_by_name") or "",
                "created_at": str(r.get("created_at") or ""),
                "updated_at": str(r.get("updated_at") or ""),
                "actions": r.get("id"),
                "_raw_entry_no": entry_no,
                "_raw_client": client_name,
            })


        # فلترة البحث على العميل أو رقم الإدخال
        if search:
            self.data = [
                r for r in self.data
                if search in str(r.get("_raw_entry_no", "")).lower()
                   or search in str(r.get("_raw_client", "")).lower()
            ]

        # تحديث عداد الصفوف
        if hasattr(self, "_count_lbl"):
            self._count_lbl.setText(f"({len(self.data)} " + _("total_rows") + ")")

        # عرض البيانات في الجدول
        QApplication.restoreOverrideCursor()
        self.display_data()

    def display_data(self):
        self._display_with_actions("edit_entry", "delete_entry")



    # ---------- actions ----------
    def add_new_item(self):
        lists = self._load_lists_for_dialog()
        dlg = AddEntryDialog(self, None, **lists)
        if dlg.exec():
            header, items = dlg.get_data()
            user_id = self._user_id()
            new_id = self.crud.create(header, items, user_id=user_id)
            QMessageBox.information(self, self._("added"), self._("entry_added_success"))
            DataBus.get_instance().emit('entries')
            self.reload_data()

    def edit_selected_item(self, row=None):
        if row is None:
            rows = self.get_selected_rows()
            if not rows:
                return
            row = rows[0]
        e = self.data[row]["actions"]
        self._open_edit_dialog(e)

    def _open_edit_dialog(self, entry_id):
        # حمّل Entry object من ID
        entry_obj = self.crud.get(entry_id)
        if not entry_obj:
            QMessageBox.warning(self, self._("error"), self._("entry_not_found"))
            return

        lists = self._load_lists_for_dialog()
        dlg = AddEntryDialog(self, entry_obj, **lists)  # ✅ مرر object
        if dlg.exec():
            header, items = dlg.get_data()
            user_id = self._user_id()
            ok = self.crud.update(entry_obj.id, header, items, user_id=user_id)  # ✅
            if ok:
                QMessageBox.information(self, self._("updated"), self._("entry_updated_success"))
            DataBus.get_instance().emit('entries')
            self.reload_data()


    def delete_selected_items(self, rows=None):
        if rows is None:
            rows = self.get_selected_rows()
        if not rows:
            return
        reply = QMessageBox.question(
            self, self._("delete_entry"), self._("are_you_sure_delete"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for row in rows:
                e = self.data[row]["actions"]
                self._delete_single(e, confirm=False)
            QMessageBox.information(self, self._("deleted"), self._("entry_deleted_success"))
            DataBus.get_instance().emit('entries')
            self.reload_data()

    def _delete_single(self, entry_obj, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, self._("delete_entry"), self._("are_you_sure_delete"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.crud.delete(entry_obj.id)

    def on_row_double_clicked(self, row_index):
        try:
            row = int(row_index)
        except Exception:
            row = getattr(row_index, "row", lambda: -1)()

        if not (0 <= row < len(self.data)):
            return

        # خذ الـ id بأمان سواء مخزّن بالـ row أو من كائن actions
        entry_id = self.data[row].get("id")
        if not entry_id:
            obj = self.data[row].get("actions")
            entry_id = getattr(obj, "id", None)

        if not entry_id:
            return

        # ⚠️ هنا الأهم: رجّع الإدخال مُحمّلًا بكل التفاصيل
        e_full = self.crud.get_with_details(entry_id)
        if not e_full:
            return

        from ui.dialogs.view_details.view_entry_dialog import ViewEntryDialog
        dlg = ViewEntryDialog(e_full, current_user=self.current_user, parent=self)
        dlg.exec()

    # ---------- utils ----------
    def retranslate_ui(self):
        super().retranslate_ui()
        parent = self.parent()
        try:
            if parent and hasattr(parent, "indexOf") and hasattr(parent, "setTabText"):
                idx = parent.indexOf(self)
                if idx != -1:
                    parent.setTabText(idx, self._("entries"))
        except Exception:
            pass

        if hasattr(self, "_date_bar"): self._date_bar.retranslate()
        self.reload_data()

    def _apply_admin_columns(self):
        admin_keys = ("id", "created_by_name", "updated_by_name", "created_at", "updated_at")
        admin_cols = [idx for idx, col in enumerate(self.columns) if col.get("key") in admin_keys]
        apply_admin_columns_to_table(self.table, self.current_user, admin_cols)

    def _user_id(self):
        if isinstance(self.current_user, dict):
            return self.current_user.get("id")
        return getattr(self.current_user, "id", None)

    def _user_display(self, rel, id_to_name=None, fallback_id=None) -> str:
        if isinstance(rel, User):
            return getattr(rel, "full_name", None) or getattr(rel, "username", None) or str(getattr(rel, "id", fallback_id or ""))
        if isinstance(rel, int):
            return str(rel)
        if fallback_id is not None:
            return str(fallback_id)
        return ""

    def _load_lists_for_dialog(self):
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            clients = s.query(Client).order_by(Client.name_ar.asc()).all()
            materials = s.query(Material).order_by(Material.name_ar.asc()).all()
            packs = s.query(PackagingType).order_by(PackagingType.sort_order.asc() if hasattr(PackagingType, "sort_order") else PackagingType.id.asc()).all()
            countries = s.query(Country).order_by(Country.name_ar.asc()).all()
        return dict(clients=clients, materials=materials, packaging_types=packs, countries=countries)