"""
ui/dialogs/add_company_dialog.py
==================================
Add/Edit Company — ترث BaseDialog مباشرةً (لأنها تحتوي على QTabWidget).
هيكل: Header (primary) → QTabWidget (stretch) → Footer (حفظ/إلغاء)
Tabs: Names / Details / Addresses / Finance / Settings
"""
from core.base_dialog import BaseDialog
from core.translator import TranslationManager

from PySide6.QtWidgets import (
    QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QTabWidget, QScrollArea, QWidget,
    QFormLayout, QLabel, QFrame,
    QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.utils.wheel_blocker import block_wheel_in

from database.crud.countries_crud import CountriesCRUD
from database.crud.clients_crud import ClientsCRUD

try:
    from database.crud.currencies_crud import CurrenciesCRUD
except Exception:
    CurrenciesCRUD = None

try:
    from ui.widgets.searchable_combo import SearchableComboBox
    _HAS_SEARCHABLE = True
except Exception:
    _HAS_SEARCHABLE = False


def _name_by_lang(row, lang: str, *, ar="name_ar", en="name_en", tr="name_tr"):
    if row is None:
        return ""
    if isinstance(row, dict):
        key = {"ar": ar, "en": en, "tr": tr}.get(lang, ar)
        return row.get(key) or row.get(ar) or row.get(en) or row.get(tr) or ""
    key = {"ar": ar, "en": en, "tr": tr}.get(lang, ar)
    return (getattr(row, key, None) or getattr(row, ar, None)
            or getattr(row, en, None) or getattr(row, tr, None) or "")


class AddCompanyDialog(BaseDialog):
    """
    Add/Edit Company.
    Tab 1 - الأسماء:   name_ar, name_en, name_tr
    Tab 2 - التفاصيل: owner_client, country, city, phone, email, website
    Tab 3 - العناوين: address_ar, address_en, address_tr
    Tab 4 - المالية:  default_currency, tax_id, registration_number
    Tab 5 - الإعدادات: is_active, notes
    """

    def __init__(self, parent=None, company=None, *, currencies=None):
        super().__init__(parent)
        self._company = company
        self._lang = TranslationManager.get_instance().get_current_language()

        self._currencies = list(currencies) if currencies is not None else None
        if self._currencies is None and CurrenciesCRUD:
            try:
                self._currencies = CurrenciesCRUD().get_all() or []
            except Exception:
                self._currencies = []

        try:
            self._countries = CountriesCRUD().get_all() or []
        except Exception:
            self._countries = []

        try:
            self._clients = ClientsCRUD().get_all() or []
        except Exception:
            self._clients = []

        title_key = "add_company" if not company else "edit_company"
        self.set_translated_title(title_key)
        self.setMinimumWidth(560)
        self.setSizeGripEnabled(True)

        self._build_ui()
        self._populate()
        block_wheel_in(self)

    # ─────────────────────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        header, sep = self._build_primary_header(
            title=self._("add_company" if not self._company else "edit_company")
        )
        root.addWidget(header)
        root.addWidget(sep)

        # ── Tabs (stretch=1 يأخذ كل المساحة) ────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        # Tab 1: Names
        tab1, f1 = self._make_tab()
        self.name_ar = QLineEdit()
        self._row(f1, "arabic_name",  self.name_ar,  required=True)
        self.name_en = QLineEdit()
        self._row(f1, "english_name", self.name_en)
        self.name_tr = QLineEdit()
        self._row(f1, "turkish_name", self.name_tr)
        self._tabs.addTab(tab1, self._("names"))

        # Tab 2: Details
        tab2, f2 = self._make_tab()
        if _HAS_SEARCHABLE:
            self.cmb_owner = SearchableComboBox(parent=self)
            self.cmb_owner.set_loader(
                loader=self._search_clients,
                display=self._client_display,
                value=lambda c: c.id if not isinstance(c, dict) else c.get("id"),
            )
        else:
            self.cmb_owner = QComboBox()
            for cl in self._clients:
                cid = cl.get("id") if isinstance(cl, dict) else getattr(cl, "id", None)
                self.cmb_owner.addItem(_name_by_lang(cl, self._lang) or f"#{cid}", cid)
        self._row(f2, "owner_client", self.cmb_owner, required=True)

        self.cmb_country = QComboBox()
        self._fill_countries()
        self._row(f2, "country", self.cmb_country)

        self.city = QLineEdit()
        self._row(f2, "city", self.city)

        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+90 ...")
        self._row(f2, "phone", self.phone)

        self.email = QLineEdit()
        self.email.setPlaceholderText("example@email.com")
        self._row(f2, "email", self.email)

        self.website = QLineEdit()
        self.website.setPlaceholderText("https://...")
        self._row(f2, "website", self.website)
        self._tabs.addTab(tab2, self._("details"))

        # Tab 3: Addresses
        tab3, f3 = self._make_tab()
        self.address_ar = _AutoTextEdit()
        self._row(f3, "address_ar", self.address_ar)
        self.address_en = _AutoTextEdit()
        self._row(f3, "address_en", self.address_en)
        self.address_tr = _AutoTextEdit()
        self._row(f3, "address_tr", self.address_tr)
        self._tabs.addTab(tab3, self._("addresses"))

        # Tab 4: Finance
        tab4, f4 = self._make_tab()
        self.cmb_currency = QComboBox()
        self._fill_currencies()
        self._row(f4, "default_currency", self.cmb_currency)
        self.tax_id = QLineEdit()
        self._row(f4, "tax_id", self.tax_id)
        self.registration_number = QLineEdit()
        self._row(f4, "registration_number", self.registration_number)
        self._tabs.addTab(tab4, self._("finance"))

        # Tab 5: Settings
        tab5, f5 = self._make_tab()
        self.chk_active = QCheckBox(self._("active"))
        self.chk_active.setChecked(True)
        f5.addRow(self.chk_active)
        self.notes = _AutoTextEdit()
        self._row(f5, "notes", self.notes)
        self._tabs.addTab(tab5, self._("settings"))

        root.addWidget(self._tabs, 1)   # stretch=1 → يأخذ كل المساحة المتاحة

        # ── Footer ────────────────────────────────────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("form-dialog-sep")
        sep2.setFixedHeight(1)

        footer = QWidget()
        footer.setObjectName("form-dialog-footer")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(24, 14, 24, 14)
        f_lay.setSpacing(10)
        f_lay.addStretch()

        self.btn_cancel = QPushButton(self._("cancel"))
        self.btn_cancel.setObjectName("secondary-btn")
        self.btn_cancel.setMinimumWidth(90)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton(self._("save"))
        self.btn_save.setObjectName("primary-btn")
        self.btn_save.setMinimumWidth(90)
        self.btn_save.clicked.connect(self.accept)

        f_lay.addWidget(self.btn_cancel)
        f_lay.addWidget(self.btn_save)

        root.addWidget(sep2)
        root.addWidget(footer)

    # ─────────────────────────────────────────────────────────────────────────
    # Tab / row helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _make_tab(self):
        """يعيد (scroll_widget, QFormLayout)."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        form = QFormLayout(body)
        form.setContentsMargins(16, 14, 16, 14)
        form.setSpacing(12)
        form.setRowWrapPolicy(QFormLayout.WrapAllRows)
        scroll.setWidget(body)
        return scroll, form

    def _row(self, form: QFormLayout, key: str, widget, required: bool = False):
        lbl = QLabel()
        lbl.setObjectName("form-dialog-label")
        f = lbl.font()
        f.setWeight(QFont.DemiBold)
        lbl.setFont(f)
        text = self._(key)
        if required:
            lbl.setText(f'{text} <span style="color:#EF4444;">*</span>')
            lbl.setTextFormat(Qt.RichText)
        else:
            lbl.setText(text)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow(lbl, widget)

    # ─────────────────────────────────────────────────────────────────────────
    # Combo fillers
    # ─────────────────────────────────────────────────────────────────────────

    def _fill_countries(self):
        self.cmb_country.clear()
        self.cmb_country.addItem(self._("select_country"), None)
        for c in self._countries:
            cid   = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
            label = _name_by_lang(c, self._lang) or f"#{cid}"
            self.cmb_country.addItem(label, cid)

    def _fill_currencies(self):
        self.cmb_currency.clear()
        self.cmb_currency.addItem(self._("select_currency"), None)
        for c in (self._currencies or []):
            cid  = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
            code = (c.get("code") if isinstance(c, dict) else getattr(c, "code", "")) or ""
            name = _name_by_lang(c, self._lang) or code
            label = f"{name} ({code})" if code and code not in name else name or f"#{cid}"
            self.cmb_currency.addItem(label, cid)

    def _search_clients(self, q: str = "") -> list:
        clients = self._clients or []
        if not q:
            return clients[:60]
        q = q.casefold()
        def _has(c, attr):
            v = c.get(attr) if isinstance(c, dict) else getattr(c, attr, "")
            return q in (v or "").casefold()
        return [c for c in clients if _has(c, "name_ar") or _has(c, "name_en") or _has(c, "name_tr")][:60]

    def _client_display(self, c, lang: str) -> str:
        if isinstance(c, dict):
            return (c.get(f"name_{lang}") or c.get("name_ar") or c.get("name_en")
                    or f"#{c.get('id', '?')}")
        return _name_by_lang(c, lang) or f"#{getattr(c, 'id', '?')}"

    # ─────────────────────────────────────────────────────────────────────────
    # Populate (edit mode)
    # ─────────────────────────────────────────────────────────────────────────

    def _populate(self):
        if not self._company:
            return
        g = self._get

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

        self.name_ar.setText(g("name_ar") or "")
        self.name_en.setText(g("name_en") or "")
        self.name_tr.setText(g("name_tr") or "")

        owner_id = g("owner_client_id")
        if owner_id is None:
            oc = g("owner_client")
            if oc is not None:
                owner_id = oc.get("id") if isinstance(oc, dict) else getattr(oc, "id", None)
        if owner_id and _HAS_SEARCHABLE and hasattr(self.cmb_owner, "set_value"):
            objs = self._search_clients("")
            obj = next((c for c in objs if
                        (c.get("id") if isinstance(c, dict) else getattr(c, "id", None)) == owner_id
                        ), None)
            if obj:
                self.cmb_owner.set_value(owner_id, display_text=self._client_display(obj, self._lang))

        country_id = g("country_id")
        if country_id is None:
            co = g("country")
            if co is not None:
                country_id = co.get("id") if isinstance(co, dict) else getattr(co, "id", None)
        _set_combo(self.cmb_country, country_id)

        self.city.setText(g("city") or "")
        self.phone.setText(g("phone") or "")
        self.email.setText(g("email") or "")
        self.website.setText(g("website") or "")

        self.address_ar.setPlainText(g("address_ar") or "")
        self.address_en.setPlainText(g("address_en") or "")
        self.address_tr.setPlainText(g("address_tr") or "")

        _set_combo(self.cmb_currency, g("default_currency_id"))
        self.tax_id.setText(g("tax_id") or "")
        self.registration_number.setText(g("registration_number") or "")

        is_active = g("is_active")
        self.chk_active.setChecked(bool(is_active) if is_active is not None else True)
        self.notes.setPlainText(g("notes") or "")

    def _get(self, key, default=None):
        if isinstance(self._company, dict):
            return self._company.get(key, default)
        return getattr(self._company, key, default)

    # ─────────────────────────────────────────────────────────────────────────
    # Data & Validation
    # ─────────────────────────────────────────────────────────────────────────

    def get_data(self) -> dict:
        owner_val = None
        if _HAS_SEARCHABLE and hasattr(self.cmb_owner, "current_value"):
            owner_val = self.cmb_owner.current_value()
        elif isinstance(self.cmb_owner, QComboBox):
            owner_val = self.cmb_owner.currentData()

        return {
            "name_ar":             (self.name_ar.text() or "").strip().upper(),
            "name_en":             (self.name_en.text() or "").strip().upper(),
            "name_tr":             (self.name_tr.text() or "").strip().upper(),
            "owner_client_id":     owner_val,
            "country_id":          self.cmb_country.currentData(),
            "city":                (self.city.text() or "").strip(),
            "phone":               (self.phone.text() or "").strip(),
            "email":               (self.email.text() or "").strip().lower(),
            "website":             (self.website.text() or "").strip(),
            "address_ar":          (self.address_ar.toPlainText() or "").strip().upper() or None,
            "address_en":          (self.address_en.toPlainText() or "").strip().upper() or None,
            "address_tr":          (self.address_tr.toPlainText() or "").strip().upper() or None,
            "default_currency_id": self.cmb_currency.currentData(),
            "tax_id":              (self.tax_id.text() or "").strip(),
            "registration_number": (self.registration_number.text() or "").strip(),
            "is_active":           self.chk_active.isChecked(),
            "notes":               (self.notes.toPlainText() or "").strip(),
        }

    def accept(self):
        d = self.get_data()
        ok = True
        errors = []

        if not (d["name_ar"] or d["name_en"] or d["name_tr"]):
            errors.append(self._("at_least_one_name_required"))
            self._tabs.setCurrentIndex(0)
            ok = False

        if not d["owner_client_id"]:
            errors.append(self._("owner_required"))
            if ok:
                self._tabs.setCurrentIndex(1)
            ok = False

        email = d["email"]
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            errors.append(self._("invalid_email"))
            if ok:
                self._tabs.setCurrentIndex(1)
            ok = False

        if not ok:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, self._("invalid_data"), "\n".join(errors))
            return

        super().accept()


# ─────────────────────────────────────────────────────────────────────────────
# Helper widget
# ─────────────────────────────────────────────────────────────────────────────

class _AutoTextEdit(QTextEdit):
    """
    QTextEdit يتمدد تلقائياً مع محتواه.
    - حد أدنى: 72px (سطرين تقريباً)
    - حد أقصى: 35% من ارتفاع الشاشة المتاحة
    - يُحدَّث عند كل تغيير في النص
    """

    _MIN_H = 72

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(self._MIN_H)
        self.document().contentsChanged.connect(self._adjust)

    def _max_h(self) -> int:
        try:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                return int(screen.availableGeometry().height() * 0.35)
        except Exception:
            pass
        return 300

    def _adjust(self):
        doc_h = int(self.document().size().height()) + 8   # 8px padding
        new_h = max(self._MIN_H, min(doc_h, self._max_h()))
        if self.height() != new_h:
            self.setFixedHeight(new_h)

    def sizeHint(self):
        from PySide6.QtCore import QSize
        doc_h = int(self.document().size().height()) + 8
        h = max(self._MIN_H, min(doc_h, self._max_h()))
        return QSize(super().sizeHint().width(), h)