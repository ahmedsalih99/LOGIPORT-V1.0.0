from core.base_dialog import BaseDialog
from core.translator import TranslationManager

from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QLineEdit, QTextEdit, QComboBox,
    QMessageBox, QTabWidget, QScrollArea, QWidget,
    QGridLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt
from database.crud.countries_crud import CountriesCRUD

# Optional: جلب العملات إن لم تُمرَّر من المستدعي
try:
    from database.crud.currencies_crud import CurrenciesCRUD
except Exception:
    CurrenciesCRUD = None  # type: ignore
from database.crud.clients_crud import ClientsCRUD


def _name_by_lang(row, lang: str, *, ar="name_ar", en="name_en", tr="name_tr"):
    """اختيار نص مناسب حسب لغة الواجهة، مع fallback منطقي."""
    if row is None:
        return ""
    if isinstance(row, dict):
        return row.get({"ar": ar, "en": en, "tr": tr}.get(lang, ar)) or \
               row.get(ar) or row.get(en) or row.get(tr) or ""
    return getattr(row, {"ar": ar, "en": en, "tr": tr}.get(lang, ar), None) or \
           getattr(row, ar, None) or getattr(row, en, None) or getattr(row, tr, None) or ""


class AddCompanyDialog(BaseDialog):
    """
    Add/Edit Company — النسخة المبسّطة (٩ حقول):
      1- name_ar   2- name_en   3- name_tr
      4- address_ar 5- address_en 6- address_tr
      7- default_currency_id
      8- notes
    قواعد التحقق:
      - مطلوب وجود اسم واحد على الأقل (AR/EN/TR).
      - مطلوب وجود عنوان واحد على الأقل (AR/EN/TR).
    """

    def __init__(self, parent=None, company=None, *, currencies=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()

        self.company = company
        self.currencies = list(currencies) if currencies is not None else None

        # Lazy-load currencies if not provided
        if self.currencies is None and CurrenciesCRUD:
            try:
                self.currencies = CurrenciesCRUD().get_all() or []
            except Exception:
                self.currencies = []

        self.countries = None
        if CountriesCRUD:
            try:
                self.countries = CountriesCRUD().get_all() or []
            except Exception:
                self.countries = []

        self.clients = []
        try:
            self.clients = ClientsCRUD().get_all() or []
        except Exception:
            self.clients = []

        self.setWindowTitle(self._("add_company") if not self.company else self._("edit_company"))

        self._init_ui()
        self._prefill_if_edit()

    # ---------- UI ----------

    def _make_form_tab(self) -> dict:
        """راجع أسلوب المشروع: ScrollArea + GridLayout مرتّبة."""
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        scroll.setWidget(w)
        return {"scroll": scroll, "grid": grid}

    def _add_row(self, form: dict, row: int, key: str, widget):
        lbl = QLabel(self._(key))
        lbl.setObjectName("form-label")
        form["grid"].addWidget(lbl, row, 0)
        form["grid"].addWidget(widget, row, 1)

    def _tab_title(self, key: str, fallback: str) -> str:
        try:
            return self._(key)
        except Exception:
            return fallback

    def _init_ui(self):
        main = QVBoxLayout(self)
        tabs = QTabWidget(self)
        title = QLabel(self._("add_company") if not self.company else self._("edit_company"))
        title.setObjectName("title")
        main.addWidget(title)

        # --- Tab: Names ---
        t_names = self._make_form_tab()
        r = 0
        self.name_ar = QLineEdit()
        self._add_row(t_names, r, "arabic_name", self.name_ar); r += 1

        self.name_en = QLineEdit()
        self._add_row(t_names, r, "english_name", self.name_en); r += 1

        self.name_tr = QLineEdit()
        self._add_row(t_names, r, "turkish_name", self.name_tr); r += 1

        tabs.addTab(t_names["scroll"], self._tab_title("names", "Names"))

        # --- Tab: Addresses ---
        t_addr = self._make_form_tab()
        r = 0
        self.address_ar = QTextEdit(); self.address_ar.setFixedHeight(80)
        self._add_row(t_addr, r, "address_ar", self.address_ar); r += 1

        self.address_en = QTextEdit(); self.address_en.setFixedHeight(80)
        self._add_row(t_addr, r, "address_en", self.address_en); r += 1

        self.address_tr = QTextEdit(); self.address_tr.setFixedHeight(80)
        self._add_row(t_addr, r, "address_tr", self.address_tr); r += 1
        tabs.addTab(t_addr["scroll"], self._tab_title("addresses", "Addresses"))

        # --- Tab: Settings (currency + notes) ---
        t_set = self._make_form_tab()
        r = 0
        self.cmb_country = QComboBox()
        self._fill_countries()
        self._add_row(t_set, r, "country", self.cmb_country);
        r += 1
        self.cmb_currency = QComboBox()
        self._fill_currencies()
        self._add_row(t_set, r, "default_currency", self.cmb_currency); r += 1

        self.notes = QTextEdit(); self.notes.setFixedHeight(80)
        self._add_row(t_set, r, "notes", self.notes); r += 1

        self.cmb_owner = QComboBox()
        self._fill_clients()
        self._add_row(t_set, r, "owner_client", self.cmb_owner)
        r += 1

        tabs.addTab(t_set["scroll"], self._tab_title("settings", "Settings"))

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        main.addWidget(tabs)
        main.addWidget(btns)

    def _fill_currencies(self):
        """يملأ قائمة العملات إن توفرت. عنصر أول 'اختر' بقيمة None."""
        self.cmb_currency.clear()
        self.cmb_currency.addItem(self._("select_currency"), None)
        for c in (self.currencies or []):
            if isinstance(c, dict):
                cid = c.get("id")
                code = c.get("code") or ""
                label = (c.get("name_ar") or c.get("name_en") or c.get("name_tr") or code or f"#{cid}")
            else:
                cid = getattr(c, "id", None)
                code = getattr(c, "code", "") or ""
                label = _name_by_lang(c, self._lang) or code or f"#{cid}"
            show = f"{label} ({code})" if code and code not in label else (label or f"#{cid}")
            self.cmb_currency.addItem(show, cid)

    def _fill_countries(self):
        self.cmb_country.clear()
        self.cmb_country.addItem(self._("select_country"), None)
        for c in (self.countries or []):
            if isinstance(c, dict):
                cid = c.get("id")
                n_ar, n_en, n_tr = c.get("name_ar", ""), c.get("name_en", ""), c.get("name_tr", "")
            else:
                cid = getattr(c, "id", None)
                n_ar, n_en, n_tr = getattr(c, "name_ar", ""), getattr(c, "name_en", ""), getattr(c, "name_tr", "")
            # اختيار التسمية حسب لغة الواجهة
            label = {"ar": n_ar, "en": n_en, "tr": n_tr}.get(self._lang) or n_en or n_ar or n_tr or f"#{cid}"
            self.cmb_country.addItem(label, cid)

    def _fill_clients(self):
        self.cmb_owner.clear()
        self.cmb_owner.addItem(self._("select_owner"), None)

        for c in (self.clients or []):
            if isinstance(c, dict):
                cid = c.get("id")
                name = c.get("name_ar") or c.get("name_en") or c.get("name_tr") or f"#{cid}"
            else:
                cid = getattr(c, "id", None)
                name = getattr(c, "name_ar", None) or \
                       getattr(c, "name_en", None) or \
                       getattr(c, "name_tr", None) or f"#{cid}"

            self.cmb_owner.addItem(name, cid)

    # ---------- Prefill on edit ----------

    def _prefill_if_edit(self):
        if not self.company:
            return

        # helper: read from dict OR ORM object
        get = (lambda k, default="": self.company.get(k, default)) if isinstance(self.company, dict) \
            else (lambda k, default="": getattr(self.company, k, default))

        def _norm_id(v):
            try:
                return int(v)
            except Exception:
                return v

        # ===== Names =====
        self.name_ar.setText(get("name_ar", "") or "")
        self.name_en.setText(get("name_en", "") or "")
        self.name_tr.setText(get("name_tr", "") or "")

        # ===== Addresses =====
        self.address_ar.setPlainText(get("address_ar", "") or "")
        self.address_en.setPlainText(get("address_en", "") or "")
        self.address_tr.setPlainText(get("address_tr", "") or "")

        # ===== Country (robust) =====
        country_id = get("country_id", None)
        if country_id is None:
            country_obj = get("country", None)
            if isinstance(country_obj, dict):
                country_id = country_obj.get("id", None)
            elif hasattr(country_obj, "id"):
                country_id = getattr(country_obj, "id", None)

        if country_id is not None:
            want = _norm_id(country_id)
            for i in range(self.cmb_country.count()):
                if _norm_id(self.cmb_country.itemData(i)) == want:
                    self.cmb_country.setCurrentIndex(i)
                    break

        # ===== Default currency =====
        cur_id = get("default_currency_id", None)
        if cur_id is not None:
            want = _norm_id(cur_id)
            for i in range(self.cmb_currency.count()):
                if _norm_id(self.cmb_currency.itemData(i)) == want:
                    self.cmb_currency.setCurrentIndex(i)
                    break

    # ---------- Data & Validation ----------

    def get_data(self) -> dict:
        d = {
            "name_ar": (self.name_ar.text() or "").strip(),
            "name_en": (self.name_en.text() or "").strip(),
            "name_tr": (self.name_tr.text() or "").strip(),
            "address_ar": (self.address_ar.toPlainText() or "").strip(),
            "address_en": (self.address_en.toPlainText() or "").strip(),
            "address_tr": (self.address_tr.toPlainText() or "").strip(),
            "default_currency_id": self.cmb_currency.currentData(),
            "country_id": self.cmb_country.currentData(),  # << جديد
            "notes": (self.notes.toPlainText() or "").strip(),
            "owner_client_id": self.cmb_owner.currentData(),

        }

        # ✅ سطر بسيط أثناء الحفظ
        for k in ("name_ar", "name_en", "name_tr", "address_ar", "address_en", "address_tr"):
            if d[k]:
                d[k] = d[k].upper()

        return d

    def accept(self):
        d = self.get_data()

        # 1) تحقق: اسم واحد على الأقل
        if not (d["name_ar"] or d["name_en"] or d["name_tr"]):
            QMessageBox.warning(self, self._("invalid_data"),
                                self._("at_least_one_name_required"))
            return

        # 2) تحقق: عنوان واحد على الأقل
        if not (d["address_ar"] or d["address_en"] or d["address_tr"]):
            QMessageBox.warning(self, self._("invalid_data"),
                                self._("at_least_one_address_required"))
            return


        if not d["owner_client_id"]:
            QMessageBox.warning(self, self._("invalid_data"),
                                self._("owner_required"))
            return

        super().accept()
