from core.base_tab import BaseTab
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
from functools import partial

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
            {"label": "entry_no", "key": "entry_no"},
            {"label": "entry_date", "key": "entry_date"},
            {"label": "transport_unit_type", "key": "transport_unit_label"},
            {"label": "owner_client", "key": "owner_client_name"},
            {"label": "items_count", "key": "items_count"},
            {"label": "total_pcs", "key": "total_pcs"},
            {"label": "total_net", "key": "total_net"},
            {"label": "total_gross", "key": "total_gross"},
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

        self._build_filter_bar()
        self.reload_data()
        self._init_done = True

    # ── Filter bar ──────────────────────────────────────────────────────────

    def _build_filter_bar(self):
        _ = self._
        filter_bar = QWidget()
        filter_bar.setObjectName("filter-bar")
        lay = QHBoxLayout(filter_bar)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(8)

        # حفظ المراجع للترجمة الفورية
        self._lbl_from = QLabel()
        self._lbl_from.setFont(QFont("Tajawal", 9))
        lay.addWidget(self._lbl_from)

        self._date_from = QDateEdit()
        self._date_from.setObjectName("form-input")
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        self._date_from.setDate(QDate.currentDate().addMonths(-3))
        self._date_from.setMinimumWidth(110)
        self._date_from.dateChanged.connect(self._on_filter_changed)
        lay.addWidget(self._date_from)

        self._lbl_to = QLabel()
        self._lbl_to.setFont(QFont("Tajawal", 9))
        lay.addWidget(self._lbl_to)

        self._date_to = QDateEdit()
        self._date_to.setObjectName("form-input")
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setMinimumWidth(110)
        self._date_to.dateChanged.connect(self._on_filter_changed)
        lay.addWidget(self._date_to)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1);
        sep.setFixedHeight(24)
        lay.addWidget(sep)

        # أزرار اليوم / الأسبوع / الشهر / مسح
        self._btn_today = QPushButton()
        self._btn_today.setObjectName("topbar-btn")
        self._btn_today.setMinimumHeight(30)
        self._btn_today.setFont(QFont("Tajawal", 9))
        self._btn_today.setCursor(Qt.PointingHandCursor)
        self._btn_today.clicked.connect(self._preset_today)
        lay.addWidget(self._btn_today)

        self._btn_week = QPushButton()
        self._btn_week.setObjectName("topbar-btn")
        self._btn_week.setMinimumHeight(30)
        self._btn_week.setFont(QFont("Tajawal", 9))
        self._btn_week.setCursor(Qt.PointingHandCursor)
        self._btn_week.clicked.connect(self._preset_week)
        lay.addWidget(self._btn_week)

        self._btn_month = QPushButton()
        self._btn_month.setObjectName("topbar-btn")
        self._btn_month.setMinimumHeight(30)
        self._btn_month.setFont(QFont("Tajawal", 9))
        self._btn_month.setCursor(Qt.PointingHandCursor)
        self._btn_month.clicked.connect(self._preset_month)
        lay.addWidget(self._btn_month)

        self._btn_clear = QPushButton()
        self._btn_clear.setObjectName("topbar-btn")
        self._btn_clear.setMinimumHeight(30)
        self._btn_clear.setFont(QFont("Tajawal", 9))
        self._btn_clear.setCursor(Qt.PointingHandCursor)
        self._btn_clear.clicked.connect(self._preset_clear)
        lay.addWidget(self._btn_clear)

        self._count_lbl = QLabel()
        self._count_lbl.setFont(QFont("Tajawal", 9))
        self._count_lbl.setObjectName("text-muted")
        lay.addWidget(self._count_lbl)

        lay.addStretch()

        try:
            self.layout.insertWidget(1, filter_bar)
        except Exception:
            self.layout.addWidget(filter_bar)

        # الترجمة الفورية لأول مرة
        self._update_filter_bar_texts()

    def _update_filter_bar_texts(self):
        _ = self._
        self._lbl_from.setText("📅 " + _("date_from") + ":")
        self._lbl_to.setText("→ " + _("date_to") + ":")
        self._btn_today.setText("📅 " + _("today"))
        self._btn_week.setText("📅 " + _("this_week"))
        self._btn_month.setText("📅 " + _("this_month"))
        self._btn_clear.setText("✖ " + _("clear"))

    def _preset_today(self):
        today = QDate.currentDate()
        self._date_from.setDate(today); self._date_to.setDate(today)

    def _preset_week(self):
        today = QDate.currentDate()
        self._date_from.setDate(today.addDays(-today.dayOfWeek() + 1))
        self._date_to.setDate(today)

    def _preset_month(self):
        today = QDate.currentDate()
        self._date_from.setDate(QDate(today.year(), today.month(), 1))
        self._date_to.setDate(today)

    def _preset_clear(self):
        self._date_from.setDate(QDate.currentDate().addMonths(-3))
        self._date_to.setDate(QDate.currentDate())
        if hasattr(self, "search_bar"): self.search_bar.clear()

    def _on_filter_changed(self, *_):
        self.reload_data()

    # ---------- data ----------
    def reload_data(self):
        self._skip_base_search = True   # البحث يتم server-side أو بـ _apply_search_filter
        self._skip_base_sort   = True   # الترتيب يتم server-side أو يُدار بـ CRUD
        _ = TranslationManager.get_instance().translate
        lang = TranslationManager.get_instance().get_current_language()

        # قيم الفلاتر
        d_from = self._date_from.date().toString("yyyy-MM-dd") if hasattr(self, "_date_from") else None
        d_to = self._date_to.date().toString("yyyy-MM-dd") if hasattr(self, "_date_to") else None
        search = self.search_bar.text().strip().lower() if hasattr(self, "search_bar") else ""

        # جلب البيانات من CRUD
        try:
            rows = self.crud.list_with_totals(limit=1000, date_from=d_from, date_to=d_to)
        except TypeError:
            rows = self.crud.list_with_totals(limit=1000)

        self.data = []

        for r in rows:
            # ترجمة نوع وسيلة النقل
            transport_type = r.get("transport_unit_type") or "truck"
            unit_label = {
                "truck": _("truck"),
                "container": _("container"),
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
                "created_by_name": "",
                "updated_by_name": "",
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
        self.display_data()

    def display_data(self):
        """
        عرض البيانات في الجدول مع دعم أزرار Edit/Delete وحماية الأعمدة الإدارية
        """
        can_edit = has_perm(self.current_user, "edit_entry")
        can_delete = has_perm(self.current_user, "delete_entry")
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
                        btn_edit.clicked.connect(partial(self._open_edit_dialog, obj))
                        layout.addWidget(btn_edit)

                    if can_delete:
                        btn_delete = QPushButton(self._("delete"))
                        btn_delete.setObjectName("danger-btn")
                        btn_delete.clicked.connect(partial(self._delete_single, obj))
                        layout.addWidget(btn_delete)

                    w = QWidget()
                    w.setLayout(layout)
                    self.table.setCellWidget(row_idx, col_idx, w)
                else:
                    item = QTableWidgetItem(str(row.get(key, "")))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_idx, col_idx, item)

        # إخفاء عمود actions إذا المستخدم لا يملك صلاحية
        try:
            actions_index = next((i for i, c in enumerate(self.columns) if c.get("key") == "actions"), None)
            if actions_index is not None:
                self.table.setColumnHidden(actions_index, not show_actions)
        except Exception:
            pass

        # تطبيق أعمدة admin حسب الصلاحيات
        self._apply_admin_columns()

        # تحديث label للصفوف / pagination
        self.update_pagination_label()

    # ---------- actions ----------
    def add_new_item(self):
        lists = self._load_lists_for_dialog()
        dlg = AddEntryDialog(self, None, **lists)
        if dlg.exec():
            header, items = dlg.get_data()
            user_id = self._user_id()
            new_id = self.crud.create(header, items, user_id=user_id)
            QMessageBox.information(self, self._("added"), self._("entry_added_success"))
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

        # ترجمة الفلاتر وأزرارهم
        self._update_filter_bar_texts()

        # إعادة تحميل البيانات حسب اللغة الجديدة
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