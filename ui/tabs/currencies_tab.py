from core.base_tab import BaseTab
from ui.dialogs.add_currency_dialog import AddCurrencyDialog
from database.crud.currencies_crud import CurrenciesCRUD
from core.translator import TranslationManager
from database.models import get_session_local, User
from core.settings_manager import SettingsManager
from ui.dialogs.view_details.view_currency_dialog import ViewCurrencyDialog

# ✅ بوابة الصلاحيات والأعمدة الإدارية
from core.permissions import has_perm, is_admin
from core.admin_columns import apply_admin_columns_to_table

from PySide6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QHBoxLayout, QWidget, QPushButton
)
from PySide6.QtCore import Qt


class CurrenciesTab(BaseTab):
    """
    Currencies tab with admin-only columns and audit-ready CRUD calls.
    - Normal users: see Arabic/English/Turkish names + symbol + code + actions.
    - Admins: also see ID, created_by/updated_by names, and timestamps.
    """

    required_permissions = {
        "view": "view_values",   # لأنه ضمن تبويب القِيَم
        "add": "add_currency",
        "edit": "edit_currency",
        "delete": "delete_currency",
        "import": "view_values",
        "export": "view_values",
        "refresh": "view_values",  # مهم لتفعيل زر التحديث
        "print": "view_values",
    }

    def __init__(self, parent=None, current_user=None):
        _ = TranslationManager.get_instance().translate

        # وحّد مصدر المستخدم (الممرَّر أو المخزَّن أو من الأب)
        settings = SettingsManager.get_instance()
        u = current_user or settings.get("user", None) or getattr(parent, "current_user", None)

        super().__init__(title=_("currencies"), parent=parent, user=u)
        self._ = _
        self.currencies_crud = CurrenciesCRUD()

        # ثبّت current_user داخل التاب
        self.set_current_user(u)

        # تعريف أعمدة الجدول
        self.table.setAlternatingRowColors(True)

        self.set_columns_for_role(
            base_columns=[
                {"label": "arabic_name",  "key": "name_ar"},
                {"label": "english_name", "key": "name_en"},
                {"label": "turkish_name", "key": "name_tr"},
                {"label": "currency_symbol", "key": "symbol"},
                {"label": "currency_code",   "key": "code"},
                {"label": "actions", "key": "actions"},
            ],
            admin_columns=[
                {"label": "ID",          "key": "id"},
                {"label": "created_by",  "key": "created_by_name"},
                {"label": "updated_by",  "key": "updated_by_name"},
                {"label": "created_at",  "key": "created_at"},
                {"label": "updated_at",  "key": "updated_at"},
            ],
        )

        # طبّق صلاحيات التاب (مثل إظهار/إخفاء الأزرار العليا)
        self.check_permissions()

        # إشارات أساسية
        self.row_double_clicked.connect(self.on_row_double_clicked)
        self.request_edit.connect(self.edit_selected_item)
        self.request_delete.connect(self.delete_selected_items)
        if hasattr(self, "request_refresh"):
            self.request_refresh.connect(self.reload_data)

        self.reload_data()
        self._init_done = True

    # -----------------------------
    # Data loading
    # -----------------------------
    def reload_data(self):
        admin = is_admin(self.current_user)

        items = self.currencies_crud.get_all() or []

        # خريطة id->name لمرة واحدة (للأدمِن فقط لتفادي N+1)
        id_set = set()
        if admin:
            for curr in items:
                # دعم created_by_id/updated_by_id أو created_by/updated_by كـ int
                cb_id = getattr(curr, "created_by_id", None)
                ub_id = getattr(curr, "updated_by_id", None)
                cb_fallback = getattr(curr, "created_by", None)
                ub_fallback = getattr(curr, "updated_by", None)
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
            # ✅ get_session_local يرجع sessionmaker، افتح منه Session
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                q = s.query(User.id, User.full_name, User.username).filter(User.id.in_(id_set))
                for uid, full_name, username in q:
                    id_to_name[uid] = (full_name or username or str(uid))

        # إبني صفوف الجدول
        self.data = []
        for curr in items:
            row = {
                "id": getattr(curr, "id", None),
                "name_ar": getattr(curr, "name_ar", "") or "",
                "name_en": getattr(curr, "name_en", "") or "",
                "name_tr": getattr(curr, "name_tr", "") or "",
                "symbol": getattr(curr, "symbol", "") or "",
                "code": getattr(curr, "code", "") or "",
                "actions": curr,
            }
            if admin:
                # دعم علاقة User أو أرقام IDs
                created_by_rel = getattr(curr, "created_by", None)
                updated_by_rel = getattr(curr, "updated_by", None)
                created_by_id = getattr(curr, "created_by_id", None)
                updated_by_id = getattr(curr, "updated_by_id", None)

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
                    "created_at": str(getattr(curr, "created_at", "") or ""),
                    "updated_at": str(getattr(curr, "updated_at", "") or ""),
                })

            self.data.append(row)

        self.display_data()

    # -----------------------------
    # Display with action buttons
    # -----------------------------
    def display_data(self):
        can_edit = has_perm(self.current_user, "edit_currency")
        can_delete = has_perm(self.current_user, "delete_currency")
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

                    curr = row["actions"]
                    action_layout = QHBoxLayout()
                    action_layout.setContentsMargins(0, 0, 0, 0)
                    action_layout.setSpacing(12)

                    if can_edit:
                        btn_edit = QPushButton(self._("edit"))
                        btn_edit.setObjectName("primary-btn")
                        btn_edit.clicked.connect(lambda _=False, obj=curr: self._open_edit_dialog(obj))
                        action_layout.addWidget(btn_edit)

                    if can_delete:
                        btn_delete = QPushButton(self._("delete"))
                        btn_delete.setObjectName("danger-btn")
                        btn_delete.clicked.connect(lambda _=False, obj=curr: self._delete_single(obj))
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
        dlg = AddCurrencyDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            user_id = self._user_id()
            self.currencies_crud.add_currency(
                name_ar=data["name_ar"],
                name_en=data["name_en"],
                name_tr=data["name_tr"],
                symbol=data["symbol"],
                code=data["code"],
                user_id=user_id,
            )
            QMessageBox.information(self, self._("added"), self._("currency_added_success"))
            self.reload_data()

    def edit_selected_item(self, row=None):
        if row is None:
            rows = self.get_selected_rows()
            if not rows:
                return
            row = rows[0]
        curr = self.data[row]["actions"]
        self._open_edit_dialog(curr)

    def _open_edit_dialog(self, curr):
        dlg = AddCurrencyDialog(self, {
            "name_ar": getattr(curr, "name_ar", ""),
            "name_en": getattr(curr, "name_en", ""),
            "name_tr": getattr(curr, "name_tr", ""),
            "symbol": getattr(curr, "symbol", ""),
            "code": getattr(curr, "code", ""),
        })
        if dlg.exec():
            data = dlg.get_data()
            user_id = self._user_id()
            self.currencies_crud.update_currency(curr.id, data, user_id=user_id)
            QMessageBox.information(self, self._("updated"), self._("currency_updated_success"))
            self.reload_data()

    def delete_selected_items(self, rows=None):
        if rows is None:
            rows = self.get_selected_rows()
        if not rows:
            return
        reply = QMessageBox.question(
            self, self._("delete_currency"), self._("are_you_sure_delete"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for row in rows:
                curr = self.data[row]["actions"]
                self._delete_single(curr, confirm=False)
            QMessageBox.information(self, self._("deleted"), self._("currency_deleted_success"))
            self.reload_data()

    def _delete_single(self, curr, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, self._("delete_currency"), self._("are_you_sure_delete"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.currencies_crud.delete(curr.id)

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
                    parent.setTabText(idx, self._("currencies"))
        except Exception:
            pass
        # Refresh headers after translation (applies i18n for admin/base columns)
        self._apply_columns_for_current_role()
        # Reload to reflect any translated cell content
        self.reload_data()

    def _apply_admin_columns(self):
        admin_keys = ("id", "created_by_name", "updated_by_name", "created_at", "updated_at")
        admin_cols = [idx for idx, col in enumerate(self.columns) if col.get("key") in admin_keys]
        apply_admin_columns_to_table(self.table, self.current_user, admin_cols)

    def _user_id(self):
        u = self.current_user
        if isinstance(u, dict):
            return u.get("id")
        return getattr(u, "id", None)

    def on_row_double_clicked(self, row_index):
        try:
            row = int(row_index)
        except Exception:
            row = getattr(row_index, "row", lambda: -1)()
        if 0 <= row < len(self.data):
            curr = self.data[row]["actions"]
            dlg = ViewCurrencyDialog(curr, current_user=self.current_user, parent=self)
            dlg.exec()
