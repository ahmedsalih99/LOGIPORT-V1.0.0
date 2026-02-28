from core.base_dialog import BaseDialog
from core.translator import TranslationManager

from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QMessageBox, QTabWidget, QScrollArea, QWidget,
    QGridLayout, QDialogButtonBox
)
from PySide6.QtGui import QGuiApplication

from database.crud.countries_crud import CountriesCRUD

try:
    from database.crud.currencies_crud import CurrenciesCRUD
except Exception:
    CurrenciesCRUD = None

from database.crud.clients_crud import ClientsCRUD


def _name_by_lang(row, lang: str, *, ar="name_ar", en="name_en", tr="name_tr"):
    if row is None:
        return ""
    if isinstance(row, dict):
        key = {"ar": ar, "en": en, "tr": tr}.get(lang, ar)
        return row.get(key) or row.get(ar) or row.get(en) or row.get(tr) or ""
    key = {"ar": ar, "en": en, "tr": tr}.get(lang, ar)
    return getattr(row, key, None) or getattr(row, ar, None) or getattr(row, en, None) or getattr(row, tr, None) or ""


class AddCompanyDialog(BaseDialog):
    """
    Add/Edit Company - يعكس جميع اعمدة companies:
      Tab 1 - الاسماء : name_ar, name_en, name_tr
      Tab 2 - التفاصيل : owner_client, country, city, phone, email, website
      Tab 3 - العناوين : address_ar, address_en, address_tr
      Tab 4 - المالية : default_currency, tax_id, registration_number
      Tab 5 - الاعدادات : is_active, notes
    """

    def __init__(self, parent=None, company=None, *, currencies=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()

        self.company = company
        self.currencies = list(currencies) if currencies is not None else None

        if self.currencies is None and CurrenciesCRUD:
            try:
                self.currencies = CurrenciesCRUD().get_all() or []
            except Exception:
                self.currencies = []

        try:
            self.countries = CountriesCRUD().get_all() or []
        except Exception:
            self.countries = []

        try:
            self.clients = ClientsCRUD().get_all() or []
        except Exception:
            self.clients = []

        self.setWindowTitle(self._("add_company") if not self.company else self._("edit_company"))
        self.setSizeGripEnabled(True)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.setMinimumWidth(520)
        self.setMaximumHeight(int(screen.height() * 0.92))

        self._init_ui()
        self._prefill_if_edit()

    # ──────────────────────────────────────────────
    # UI helpers
    # ──────────────────────────────────────────────
    def _make_tab(self) -> dict:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        scroll.setWidget(w)
        return {"scroll": scroll, "grid": grid}

    def _row(self, tab: dict, row: int, key: str, widget, required=False):
        lbl_text = self._(key) + (" *" if required else "")
        lbl = QLabel(lbl_text)
        lbl.setObjectName("form-label")
        tab["grid"].addWidget(lbl, row, 0)
        tab["grid"].addWidget(widget, row, 1)

    # ──────────────────────────────────────────────
    # Build UI
    # ──────────────────────────────────────────────
    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 8)
        root.setSpacing(8)

        title = QLabel(self._("add_company") if not self.company else self._("edit_company"))
        title.setObjectName("dialog-title")
        root.addWidget(title)

        tabs = QTabWidget(self)

        # ── Tab 1: Names ──
        t1 = self._make_tab()
        r = 0
        self.name_ar = QLineEdit()
        self._row(t1, r, "arabic_name", self.name_ar, required=True); r += 1
        self.name_en = QLineEdit()
        self._row(t1, r, "english_name", self.name_en); r += 1
        self.name_tr = QLineEdit()
        self._row(t1, r, "turkish_name", self.name_tr); r += 1
        tabs.addTab(t1["scroll"], self._("names"))

        # ── Tab 2: Details ──
        t2 = self._make_tab()
        r = 0
        self.cmb_owner = QComboBox()
        self._fill_clients()
        self._row(t2, r, "owner_client", self.cmb_owner, required=True); r += 1

        self.cmb_country = QComboBox()
        self._fill_countries()
        self._row(t2, r, "country", self.cmb_country); r += 1

        self.city = QLineEdit()
        self._row(t2, r, "city", self.city); r += 1

        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+90 ...")
        self._row(t2, r, "phone", self.phone); r += 1

        self.email = QLineEdit()
        self.email.setPlaceholderText("example@email.com")
        self._row(t2, r, "email", self.email); r += 1

        self.website = QLineEdit()
        self.website.setPlaceholderText("https://...")
        self._row(t2, r, "website", self.website); r += 1
        tabs.addTab(t2["scroll"], self._("details"))

        # ── Tab 3: Addresses ──
        t3 = self._make_tab()
        r = 0
        self.address_ar = QTextEdit()
        self.address_ar.setFixedHeight(80)
        self._row(t3, r, "address_ar", self.address_ar); r += 1
        self.address_en = QTextEdit()
        self.address_en.setFixedHeight(80)
        self._row(t3, r, "address_en", self.address_en); r += 1
        self.address_tr = QTextEdit()
        self.address_tr.setFixedHeight(80)
        self._row(t3, r, "address_tr", self.address_tr); r += 1
        tabs.addTab(t3["scroll"], self._("addresses"))

        # ── Tab 4: Finance ──
        t4 = self._make_tab()
        r = 0
        self.cmb_currency = QComboBox()
        self._fill_currencies()
        self._row(t4, r, "default_currency", self.cmb_currency); r += 1

        self.tax_id = QLineEdit()
        self._row(t4, r, "tax_id", self.tax_id); r += 1

        self.registration_number = QLineEdit()
        self._row(t4, r, "registration_number", self.registration_number); r += 1
        tabs.addTab(t4["scroll"], self._("finance"))

        # ── Tab 5: Settings ──
        t5 = self._make_tab()
        r = 0
        self.chk_active = QCheckBox(self._("active"))
        self.chk_active.setChecked(True)
        self._row(t5, r, "is_active", self.chk_active); r += 1

        self.notes = QTextEdit()
        self.notes.setFixedHeight(100)
        self._row(t5, r, "notes", self.notes); r += 1
        tabs.addTab(t5["scroll"], self._("settings"))

        root.addWidget(tabs)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    # ──────────────────────────────────────────────
    # Combo fillers
    # ──────────────────────────────────────────────
    def _fill_currencies(self):
        self.cmb_currency.clear()
        self.cmb_currency.addItem(self._("select_currency"), None)
        for c in (self.currencies or []):
            cid  = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
            code = (c.get("code") if isinstance(c, dict) else getattr(c, "code", "")) or ""
            name = _name_by_lang(c, self._lang) or code
            label = f"{name} ({code})" if code and code not in name else name or f"#{cid}"
            self.cmb_currency.addItem(label, cid)

    def _fill_countries(self):
        self.cmb_country.clear()
        self.cmb_country.addItem(self._("select_country"), None)
        for c in (self.countries or []):
            cid   = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
            label = _name_by_lang(c, self._lang) or f"#{cid}"
            self.cmb_country.addItem(label, cid)

    def _fill_clients(self):
        self.cmb_owner.clear()
        self.cmb_owner.addItem(self._("select_owner"), None)
        for c in (self.clients or []):
            cid = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
            if isinstance(c, dict):
                name = c.get("name_ar") or c.get("name_en") or c.get("name_tr") or f"#{cid}"
            else:
                name = (getattr(c, "name_ar", None) or getattr(c, "name_en", None) or
                        getattr(c, "name_tr", None) or getattr(c, "name", None) or f"#{cid}")
            self.cmb_owner.addItem(name, cid)

    # ──────────────────────────────────────────────
    # Prefill (edit mode)
    # ──────────────────────────────────────────────
    def _prefill_if_edit(self):
        if not self.company:
            return

        get = (lambda k, d=None: self.company.get(k, d)) if isinstance(self.company, dict) \
            else (lambda k, d=None: getattr(self.company, k, d))

        def _norm(v):
            try:
                return int(v)
            except Exception:
                return v

        def _set_combo(combo, value):
            if value is None:
                return
            want = _norm(value)
            for i in range(combo.count()):
                if _norm(combo.itemData(i)) == want:
                    combo.setCurrentIndex(i)
                    return

        # Tab 1 – Names
        self.name_ar.setText(get("name_ar") or "")
        self.name_en.setText(get("name_en") or "")
        self.name_tr.setText(get("name_tr") or "")

        # Tab 2 – Details
        # owner: من العمود المباشر او من relationship
        owner_id = get("owner_client_id") or None
        if owner_id is None:
            oc = get("owner_client")
            if oc is not None:
                owner_id = (oc.get("id") if isinstance(oc, dict) else getattr(oc, "id", None))
        _set_combo(self.cmb_owner, owner_id)

        # country: من العمود المباشر او من relationship
        country_id = get("country_id") or None
        if country_id is None:
            co = get("country")
            if co is not None:
                country_id = (co.get("id") if isinstance(co, dict) else getattr(co, "id", None))
        _set_combo(self.cmb_country, country_id)

        self.city.setText(get("city") or "")
        self.phone.setText(get("phone") or "")
        self.email.setText(get("email") or "")
        self.website.setText(get("website") or "")

        # Tab 3 – Addresses
        self.address_ar.setPlainText(get("address_ar") or "")
        self.address_en.setPlainText(get("address_en") or "")
        self.address_tr.setPlainText(get("address_tr") or "")

        # Tab 4 – Finance
        _set_combo(self.cmb_currency, get("default_currency_id"))
        self.tax_id.setText(get("tax_id") or "")
        self.registration_number.setText(get("registration_number") or "")

        # Tab 5 – Settings
        is_active = get("is_active")
        self.chk_active.setChecked(bool(is_active) if is_active is not None else True)
        self.notes.setPlainText(get("notes") or "")

    # ──────────────────────────────────────────────
    # Data & Validation
    # ──────────────────────────────────────────────
    def get_data(self) -> dict:
        d = {
            "name_ar":             (self.name_ar.text() or "").strip().upper(),
            "name_en":             (self.name_en.text() or "").strip().upper(),
            "name_tr":             (self.name_tr.text() or "").strip().upper(),
            "owner_client_id":     self.cmb_owner.currentData(),
            "country_id":          self.cmb_country.currentData(),
            "city":                (self.city.text() or "").strip(),
            "phone":               (self.phone.text() or "").strip(),
            "email":               (self.email.text() or "").strip().lower(),
            "website":             (self.website.text() or "").strip(),
            "address_ar":          (self.address_ar.toPlainText() or "").strip().upper(),
            "address_en":          (self.address_en.toPlainText() or "").strip().upper(),
            "address_tr":          (self.address_tr.toPlainText() or "").strip().upper(),
            "default_currency_id": self.cmb_currency.currentData(),
            "tax_id":              (self.tax_id.text() or "").strip(),
            "registration_number": (self.registration_number.text() or "").strip(),
            "is_active":           self.chk_active.isChecked(),
            "notes":               (self.notes.toPlainText() or "").strip(),
        }
        return d

    def accept(self):
        d = self.get_data()
        errors = []

        if not (d["name_ar"] or d["name_en"] or d["name_tr"]):
            errors.append(self._("at_least_one_name_required"))

        if not d["owner_client_id"]:
            errors.append(self._("owner_required"))

        email = d["email"]
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            errors.append(self._("invalid_email"))

        if errors:
            QMessageBox.warning(self, self._("invalid_data"), "\n".join(errors))
            return

        super().accept()
