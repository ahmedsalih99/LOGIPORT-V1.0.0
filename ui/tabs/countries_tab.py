from core.base_tab import BaseTab
from ui.dialogs.add_country_dialog import AddCountryDialog
from ui.dialogs.view_details.view_country_dialog import ViewCountryDialog
from database.crud.countries_crud import CountriesCRUD
from core.translator import TranslationManager
from database.models import get_session_local, User
from core.settings_manager import SettingsManager  # ⬅️ جديد

# ✅ البوابة الموحّدة للصلاحيات + أداة أعمدة الأدمن
from core.permissions import has_perm, is_admin
from core.admin_columns import apply_admin_columns_to_table

from PySide6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QHBoxLayout, QWidget, QPushButton
)
from PySide6.QtCore import Qt


class CountriesTab(BaseTab):
    """
    Countries tab with admin-only columns and audit-ready CRUD calls.
    - Normal users: Arabic/English/Turkish names + code + (optional) actions
    - Admins: also see ID, created_by/updated_by names, and timestamps
    Double-click opens a read-only details dialog.
    """

    required_permissions = {
        "view": ["view_values", "view_countries"],
        "add": ["add_country"],
        "edit": ["edit_country"],
        "delete": ["delete_country"],
        "import": ["view_countries"],  # أو خصصها لاحقًا
        "export": ["view_countries"],
        "print": ["view_countries"],
        "refresh": ["view_countries"],
    }

    def __init__(self, parent=None, current_user=None):
        _ = TranslationManager.get_instance().translate

        # ⬅️ وحّدنا مصدر المستخدم: المُمرَّر أو من SettingsManager أو من الأب
        settings = SettingsManager.get_instance()
        u = current_user or settings.get("user", None) or getattr(parent, "current_user", None)

        # مَرِّر المستخدم للـ BaseTab إن كان يدعمه
        super().__init__(title=_("countries"), parent=parent, user=u)
        self._ = _
        self.countries_crud = CountriesCRUD()

        # ثبّت self.current_user داخل التاب
        self.set_current_user(u)

        # ✅ أعمدة الجدول
        self.table.setAlternatingRowColors(True)
        actions_col = {"label": "actions", "key": "actions"}
        base_cols = [
            {"label": "arabic_name", "key": "name_ar"},
            {"label": "english_name", "key": "name_en"},
            {"label": "turkish_name", "key": "name_tr"},
            {"label": "country_code", "key": "code"},
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

        # طبّق صلاحيات التاب
        self.check_permissions()

        # إشارات
        self.request_edit.connect(self.edit_selected_item)
        self.request_delete.connect(self.delete_selected_items)
        self.row_double_clicked.connect(self.on_row_double_clicked)

        self.reload_data()
        self._init_done = True

    # -----------------------------
    # Data loading
    # -----------------------------
    def reload_data(self):
        admin = is_admin(self.current_user)  # ✅ بدلاً من getattr(self, "is_admin", False)

        # 1) اجلب العناصر
        items = self.countries_crud.get_all() or []

        # 2) حضّر مجموعة IDs لمُنشئ/مُحدِّث السجلات (للأدمِن فقط) لتفادي N+1
        id_set = set()
        if admin:
            for c in items:
                cb_id = getattr(c, "created_by", None)
                ub_id = getattr(c, "updated_by", None)
                if isinstance(cb_id, int):
                    id_set.add(cb_id)
                if isinstance(ub_id, int):
                    id_set.add(ub_id)

        # 3) ابنِ خريطة id -> display_name باستعلام واحد
        id_to_name = {}
        if id_set:
            SessionLocal = get_session_local()  # ترجع sessionmaker
            with SessionLocal() as s:  # افتح Session من المصنع
                q = s.query(User.id, User.full_name, User.username).filter(User.id.in_(id_set))
                for uid, full_name, username in q:
                    id_to_name[uid] = (full_name or username or str(uid))

        # 4) ابنِ صفوف الجدول
        self.data = []
        for c in items:
            row = {
                "id": getattr(c, "id", None),
                "name_ar": getattr(c, "name_ar", "") or "",
                "name_en": getattr(c, "name_en", "") or "",
                "name_tr": getattr(c, "name_tr", "") or "",
                "code": getattr(c, "code", "") or "",
                "actions": c,  # للكبس Edit/Delete
            }

            if admin:
                cb_id = getattr(c, "created_by", None)
                ub_id = getattr(c, "updated_by", None)
                row.update({
                    "created_by_name": id_to_name.get(cb_id, str(cb_id or "")),
                    "updated_by_name": id_to_name.get(ub_id, str(ub_id or "")),
                    "created_at": str(getattr(c, "created_at", "") or ""),
                    "updated_at": str(getattr(c, "updated_at", "") or ""),
                })

            self.data.append(row)

        # 5) اعرض البيانات
        self.display_data()

    # -----------------------------
    # Display (with optional action buttons)
    # -----------------------------
    def display_data(self):
        # احسب الصلاحيات مرة واحدة
        can_edit = has_perm(self.current_user, "edit_country")
        can_delete = has_perm(self.current_user, "delete_country")
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

                    country_obj = row["actions"]
                    action_layout = QHBoxLayout()
                    action_layout.setContentsMargins(0, 0, 0, 0)
                    action_layout.setSpacing(12)

                    if can_edit:
                        btn_edit = QPushButton(self._("edit"))
                        btn_edit.setObjectName("primary-btn")
                        btn_edit.clicked.connect(lambda _=False, obj=country_obj: self._open_edit_dialog(obj))
                        action_layout.addWidget(btn_edit)

                    if can_delete:
                        btn_delete = QPushButton(self._("delete"))
                        btn_delete.setObjectName("danger-btn")
                        btn_delete.clicked.connect(lambda _=False, obj=country_obj: self._delete_single(obj))
                        action_layout.addWidget(btn_delete)

                    w = QWidget()
                    w.setLayout(action_layout)
                    self.table.setCellWidget(row_idx, col_idx, w)
                else:
                    item = QTableWidgetItem(str(row.get(key, "")))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_idx, col_idx, item)

        # أخفِ عمود الإجراءات بالكامل إذا لا يوجد صلاحيات
        try:
            actions_index = next((i for i, c in enumerate(self.columns) if c.get("key") == "actions"), None)
            if actions_index is not None:
                self.table.setColumnHidden(actions_index, not show_actions)
        except Exception:
            pass

        # ✅ أعمدة الأدمن فقط: إخفاء/إظهار مركزي
        self._apply_admin_columns()

        self.update_pagination_label()

    # -----------------------------
    # Actions
    # -----------------------------
    def add_new_item(self):
        dlg = AddCountryDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            user_id = getattr(self.current_user, "id", None)
            self.countries_crud.add_country(
                name_ar=data["name_ar"],
                name_en=data["name_en"],
                name_tr=data["name_tr"],
                code=data["code"],
                user_id=user_id,
            )
            QMessageBox.information(self, self._("added"), self._("country_added_success"))
            self.reload_data()

    def edit_selected_item(self, row=None):
        if row is None:
            rows = self.get_selected_rows()
            if not rows:
                return
            row = rows[0]
        country = self.data[row]["actions"]
        self._open_edit_dialog(country)

    def _open_edit_dialog(self, country):
        dlg = AddCountryDialog(self, {
            "name_ar": getattr(country, "name_ar", ""),
            "name_en": getattr(country, "name_en", ""),
            "name_tr": getattr(country, "name_tr", ""),
            "code": getattr(country, "code", ""),
        })
        if dlg.exec():
            data = dlg.get_data()
            user_id = getattr(self.current_user, "id", None)
            self.countries_crud.update_country(country.id, data, user_id=user_id)
            QMessageBox.information(self, self._("updated"), self._("country_updated_success"))
            self.reload_data()

    def delete_selected_items(self, rows=None):
        if rows is None:
            rows = self.get_selected_rows()
        if not rows:
            return
        reply = QMessageBox.question(
            self, self._("delete_country"), self._("are_you_sure_delete"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for row in rows:
                country = self.data[row]["actions"]
                self._delete_single(country, confirm=False)
            QMessageBox.information(self, self._("deleted"), self._("country_deleted_success"))
            self.reload_data()

    def _delete_single(self, country, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, self._("delete_country"), self._("are_you_sure_delete"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.countries_crud.delete(country.id)

    # Double-click → open details dialog (read-only)
    def on_row_double_clicked(self, row_index):
        try:
            row = int(row_index)
        except Exception:
            row = getattr(row_index, "row", lambda: -1)()
        if 0 <= row < len(self.data):
            country = self.data[row]["actions"]
            dlg = ViewCountryDialog(country, current_user=self.current_user, parent=self)
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
                    parent.setTabText(idx, self._("countries"))
        except Exception:
            pass
        # Refresh headers after translation (applies i18n for admin/base columns)
        self._apply_columns_for_current_role()
        # Reload to reflect any translated cell content
        self.reload_data()

    def _apply_admin_columns(self):
        """
        يجمع فهارس أعمدة الأدمن حسب مفاتيحها ثم يطبق الإخفاء/الإظهار مركزيًا.
        """
        # حدّد مفاتيح أعمدة الأدمن كما عرّفتها في set_columns_for_role
        admin_keys = ("id", "created_by_name", "updated_by_name", "created_at", "updated_at")

        # حوّلها إلى فهارس فعلية حسب self.columns
        admin_cols = []
        for idx, col in enumerate(self.columns):
            if col.get("key") in admin_keys:
                admin_cols.append(idx)

        # طبّق الإخفاء/الإظهار حسب صلاحيات الأدمن
        apply_admin_columns_to_table(self.table, self.current_user, admin_cols)

    def _user_id(self):
        if isinstance(self.current_user, dict):
            return self.current_user.get("id")
        return getattr(self.current_user, "id", None)
