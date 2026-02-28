from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QTableWidgetItem, QMessageBox, QSizePolicy
)

# ========== Core ==========
from core.base_tab import BaseTab
from core.translator import TranslationManager
from core.settings_manager import SettingsManager

# صلاحيات وأعمدة الأدمن (نفس countries_tab)
from core.permissions import has_perm, is_admin
from core.admin_columns import apply_admin_columns_to_table

# ========== CRUD / Models ==========
from database.crud.companies_crud import CompaniesCRUD
from database.models import get_session_local, User
from database.models.currency import Currency
from database.models.company import Company
try:
    from database.models.country import Country
except Exception:
    Country = None
try:
    from database.models.client import Client
except Exception:
    Client = None

# Dialogs
from ui.dialogs.add_company_dialog import AddCompanyDialog
from ui.dialogs.view_details.view_company_dialog import ViewCompanyDialog


# ---------- Helpers ----------
def _pick_by_lang(obj, lang: str, ar_key: str, en_key: str, tr_key: str) -> str:
    def _get(o, k):
        if isinstance(o, dict):
            return o.get(k) or ""
        return getattr(o, k, "") or ""
    pref = {"ar": ar_key, "en": en_key, "tr": tr_key}.get(lang, ar_key)
    val = (_get(obj, pref) or "").strip()
    if val:
        return val
    for k in (ar_key, en_key, tr_key):
        v = (_get(obj, k) or "").strip()
        if v:
            return v
    return ""


class CompaniesTab(BaseTab):
    """
    تبويب الشركات — مطابق لنمط countries_tab:
    - أعمدة أساسية: الاسم (مُلخّص لغة الواجهة) | العنوان | العملة | الملاحظات | الإجراءات
    - أعمدة الأدمن: ID, created/updated by/at
    - صلاحيات موحّدة
    """

    required_permissions = {
        "view":    ["view_values", "view_companies"],
        "add":     ["add_company"],
        "edit":    ["edit_company"],
        "delete":  ["delete_company"],
        "import":  ["view_companies"],
        "export":  ["view_companies"],
        "print":   ["view_companies"],
        "refresh": ["view_companies"],
    }

    def __init__(self, parent=None, current_user=None):
        _ = TranslationManager.get_instance().translate

        settings = SettingsManager.get_instance()
        u = current_user or settings.get("user", None) or getattr(parent, "current_user", None)

        super().__init__(title=_("companies"), parent=parent, user=u)
        self._ = _
        self.set_current_user(u)
        self._lang = TranslationManager.get_instance().get_current_language()

        # ✅ أنشئ CRUD مع توافق رجعي
        try:
            self.companies_crud = CompaniesCRUD()
        except TypeError:
            # في حال BaseCRUD يتطلّب model و session_factory
            self.companies_crud = CompaniesCRUD(model=Company, session_factory=get_session_local)
        self.table.setAlternatingRowColors(True)

        actions_col = {"label": "actions", "key": "actions"}
        base_cols = [
            {"label": "name",          "key": "name_local"},
            {"label": "country",       "key": "country_name"},
            {"label": "owner_client",  "key": "owner_name"},
            {"label": "phone",         "key": "phone"},
            {"label": "currency",      "key": "currency_code"},
            {"label": "is_active",     "key": "is_active_label"},
            actions_col,
        ]
        self.set_columns_for_role(
            base_columns=base_cols,
            admin_columns=[
                {"label": "ID",          "key": "id"},
                {"label": "created_by",  "key": "created_by_name"},
                {"label": "updated_by",  "key": "updated_by_name"},
                {"label": "created_at",  "key": "created_at"},
                {"label": "updated_at",  "key": "updated_at"},
            ],
        )

        self.check_permissions()
        self.request_edit.connect(self.edit_selected_item)
        self.request_delete.connect(self.delete_selected_items)
        self.row_double_clicked.connect(self.on_row_double_clicked)

        self.reload_data()
        self._init_done = True

    # =========================
    # Data loading
    # =========================
    def reload_data(self):
        admin = is_admin(self.current_user)
        lang  = self._lang   # نعرّف lang مبكراً لأن country_map يحتاجه

        items = self.companies_crud.get_all() or []

        # خريطة رموز العملات والدول وأصحاب الشركات
        currency_map = {}
        country_map  = {}   # country_id → name
        owner_map    = {}   # owner_client_id → name
        SessionLocal = get_session_local()
        try:
            with SessionLocal() as s:
                for cid, code in s.query(Currency.id, Currency.code).all():
                    currency_map[cid] = (code or "").strip()
                if Country is not None:
                    for row in s.query(Country).all():
                        name = (getattr(row, f"name_{lang}", None) or
                                getattr(row, "name_ar", None) or
                                getattr(row, "name_en", None) or "")
                        country_map[row.id] = name
                if Client is not None:
                    for row in s.query(Client).all():
                        name = (getattr(row, f"name_{lang}", None) or
                                getattr(row, "name_ar", None) or
                                getattr(row, "name_en", None) or
                                getattr(row, "full_name", None) or "")
                        owner_map[row.id] = name
        except Exception:
            pass

        # دوال صغيرة لسحب الـID والاسم من أي قيمة (int أو كائن User)
        def _extract_user_id(val):
            if val is None:
                return None
            if isinstance(val, int):
                return val
            # كائن User أو شبيه
            uid = getattr(val, "id", None)
            if isinstance(uid, int):
                return uid
            try:
                return int(val)
            except Exception:
                return None

        def _extract_user_display(val):
            """اسم للعرض مباشرة إن كان لدينا relationship محمّل."""
            if val is None:
                return ""
            name = getattr(val, "full_name", None) or getattr(val, "username", None)
            return name or ""

        # جهّز مجموعة IDs للمستخدمين (للأدمن)
        id_set = set()
        created_rel = {}  # company_id -> display-from-rel (لو وجد)
        updated_rel = {}

        if admin:
            for c in items:
                cb = getattr(c, "created_by", None)
                ub = getattr(c, "updated_by", None)

                # لو relationship موجود ومحمّل، خزّن اسم العرض المباشر
                crel = _extract_user_display(cb)
                urel = _extract_user_display(ub)
                if crel:
                    created_rel[getattr(c, "id", None)] = crel
                if urel:
                    updated_rel[getattr(c, "id", None)] = urel

                # التقط الـID من int أو من relationship
                cb_id = _extract_user_id(cb)
                ub_id = _extract_user_id(ub)
                if isinstance(cb_id, int):
                    id_set.add(cb_id)
                if isinstance(ub_id, int):
                    id_set.add(ub_id)

        # ابنِ خريطة id -> name باستعلام واحد
        id_to_name = {}
        if id_set:
            with SessionLocal() as s:
                q = s.query(User.id, User.full_name, User.username).filter(User.id.in_(id_set))
                for uid, full_name, username in q:
                    id_to_name[uid] = (full_name or username or str(uid))

        # تجهيز الصفوف
        self.data = []
        for c in items:
            cid = getattr(c, "id", None)
            is_active = getattr(c, "is_active", True)
            row = {
                "id":            cid,
                "name_local":    _pick_by_lang(c, lang, "name_ar", "name_en", "name_tr"),
                "country_name":  country_map.get(getattr(c, "country_id", None), ""),
                "owner_name":    owner_map.get(getattr(c, "owner_client_id", None), ""),
                "phone":         getattr(c, "phone", "") or "",
                "currency_code": currency_map.get(getattr(c, "default_currency_id", None), ""),
                "is_active_label": self._("active") if is_active else self._("inactive"),
                "actions":       c,
            }

            if admin:
                # حاول أولاً الاسم من العلاقة المحمّلة، وإلا من الخريطة، وإلا فرّغ
                cb_id = _extract_user_id(getattr(c, "created_by", None))
                ub_id = _extract_user_id(getattr(c, "updated_by", None))
                row.update({
                    "created_by_name": created_rel.get(cid) or (id_to_name.get(cb_id, "") if cb_id else ""),
                    "updated_by_name": updated_rel.get(cid) or (id_to_name.get(ub_id, "") if ub_id else ""),
                    "created_at": str(getattr(c, "created_at", "") or ""),
                    "updated_at": str(getattr(c, "updated_at", "") or ""),
                })

            self.data.append(row)

        self.display_data()

    # =========================
    # Display
    # =========================
    def display_data(self):
        self._display_with_actions("edit_company", "delete_company")

    def add_new_item(self):
        dlg = AddCompanyDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            user_id = getattr(self.current_user, "id", None)

            owner_client_id = data.get("owner_client_id")
            if not owner_client_id:
                QMessageBox.warning(self, self._("invalid_data"),
                                    self._("owner_required"))
                return

            self.companies_crud.add_company(
                data,
                owner_client_id=owner_client_id,
                user_id=user_id
            )

            QMessageBox.information(self, self._("added"),
                                    self._("company_added_success"))
            self.reload_data()

    def edit_selected_item(self, row=None):
        if row is None:
            rows = self.get_selected_rows()
            if not rows:
                return
            row = rows[0]
        company = self.data[row]["actions"]
        self._open_edit_dialog(company)

    def _open_edit_dialog(self, company):
        # نمرر الـ ORM object مباشرة - _prefill_if_edit تقرأ منه كل الحقول
        dlg = AddCompanyDialog(self, company)
        if dlg.exec():
            data = dlg.get_data()
            user_id = getattr(self.current_user, "id", None)
            self.companies_crud.update_company(company.id, data, user_id=user_id)
            QMessageBox.information(self, self._("updated"), self._("company_updated_success"))
            self.reload_data()

    def delete_selected_items(self, rows=None):
        if rows is None:
            rows = self.get_selected_rows()
        if not rows:
            return
        reply = QMessageBox.question(
            self, self._("delete_company"), self._("are_you_sure_delete"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for row in rows:
                company = self.data[row]["actions"]
                self._delete_single(company, confirm=False)
            QMessageBox.information(self, self._("deleted"), self._("company_deleted_success"))
            self.reload_data()

    def _delete_single(self, company, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, self._("delete_company"), self._("are_you_sure_delete"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.companies_crud.delete_company(company.id)

    def on_row_double_clicked(self, row_index):
        """
        Open company details dialog using ViewCompanyDialog
        instead of QMessageBox.
        """

        # تحديد رقم الصف سواء كان int أو QModelIndex
        try:
            row = int(row_index)
        except Exception:
            row = getattr(row_index, "row", lambda: -1)()

        if not (0 <= row < len(self.data)):
            return

        # الحصول على كائن الشركة الحقيقي
        company = self.data[row].get("actions")
        if not company:
            return

        # فتح Dialog عرض التفاصيل
        dlg = ViewCompanyDialog(parent=self, company=company)

        # إذا بدك يكون فقط عرض بدون تعديل
        dlg.setModal(True)
        dlg.exec()

    # =========================
    # i18n / title
    # =========================
    def retranslate_ui(self):
        super().retranslate_ui()
        parent = self.parent()
        try:
            if parent and hasattr(parent, "indexOf") and hasattr(parent, "setTabText"):
                idx = parent.indexOf(self)
                if idx != -1:
                    parent.setTabText(idx, self._("companies"))
        except Exception:
            pass
        self._apply_columns_for_current_role()
        self._lang = TranslationManager.get_instance().get_current_language()
        self.reload_data()

    def _apply_admin_columns(self):
        admin_keys = ("id", "created_by_name", "updated_by_name", "created_at", "updated_at")
        admin_cols = []
        for idx, col in enumerate(self.columns):
            if col.get("key") in admin_keys:
                admin_cols.append(idx)
        apply_admin_columns_to_table(self.table, self.current_user, admin_cols)