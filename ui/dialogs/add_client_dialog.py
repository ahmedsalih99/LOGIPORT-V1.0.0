from core.base_dialog import BaseDialog
from core.translator import TranslationManager

from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QLineEdit, QTextEdit, QComboBox,
    QMessageBox, QTabWidget, QScrollArea, QWidget,
    QGridLayout, QDialogButtonBox
)
from PySide6.QtGui import QGuiApplication


def _name_by_lang(obj, lang: str) -> str:
    if not obj:
        return ""
    if lang == "ar" and getattr(obj, "name_ar", None):
        return obj.name_ar
    if lang == "tr" and getattr(obj, "name_tr", None):
        return obj.name_tr
    return getattr(obj, "name_en", None) or getattr(obj, "name_ar", None) or getattr(obj, "name_tr", None) or ""


class AddClientDialog(BaseDialog):
    """Add/Edit Client dialog — slimmer, three-language names & addresses, single city; no status."""

    def __init__(self, parent=None, client=None, *, countries=None, currencies=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()

        self.client = client
        self.countries = countries or []
        self.currencies = currencies or []

        self.set_translated_title("add_client" if client is None else "edit_client")
        self.init_ui()

    def init_ui(self):
        self.setSizeGripEnabled(True)
        screen_rect = QGuiApplication.primaryScreen().availableGeometry()
        self.setMaximumHeight(int(screen_rect.height() * 0.9))
        self.setMaximumWidth(int(screen_rect.width() * 0.9))

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        tabs = QTabWidget(self)

        # ---------- General ----------
        general = self._make_form_tab()
        r = 0
        self.name_ar = QLineEdit();                  self._add_row(general, r, "arabic_name", self.name_ar); r += 1
        self.name_en = QLineEdit();                  self._add_row(general, r, "english_name", self.name_en); r += 1
        self.name_tr = QLineEdit();                  self._add_row(general, r, "turkish_name", self.name_tr); r += 1
        tabs.addTab(general["scroll"], self._tab_title("tab_general", self._("tab_general")))

        # ---------- Location ----------
        location = self._make_form_tab()
        r = 0
        self.cmb_country = QComboBox(); self._fill_countries()
        self._add_row(location, r, "country", self.cmb_country); r += 1
        self.city = QLineEdit();        self._add_row(location, r, "city", self.city); r += 1
        # 3-language addresses
        self.address_ar = QTextEdit(); self.address_ar.setFixedHeight(56)
        self._add_row(location, r, "address_ar", self.address_ar); r += 1
        self.address_en = QTextEdit(); self.address_en.setFixedHeight(56)
        self._add_row(location, r, "address_en", self.address_en); r += 1
        self.address_tr = QTextEdit(); self.address_tr.setFixedHeight(56)
        self._add_row(location, r, "address_tr", self.address_tr); r += 1
        tabs.addTab(location["scroll"], self._tab_title("tab_location", self._("tab_location")))

        # ---------- Contact ----------
        contact = self._make_form_tab()
        r = 0
        self.phone = QLineEdit();       self._add_row(contact, r, "phone", self.phone); r += 1
        self.email = QLineEdit();       self._add_row(contact, r, "email", self.email); r += 1
        self.website = QLineEdit();     self._add_row(contact, r, "website", self.website); r += 1
        tabs.addTab(contact["scroll"], self._tab_title("tab_contact", self._("tab_contact")))

        # ---------- Settings ----------
        settings_tab = self._make_form_tab()
        r = 0
        self.cmb_currency = QComboBox(); self._fill_currencies()
        self._add_row(settings_tab, r, "default_currency", self.cmb_currency); r += 1
        self.tax_id = QLineEdit();      self._add_row(settings_tab, r, "tax_id", self.tax_id); r += 1
        self.notes = QTextEdit();       self.notes.setFixedHeight(64)
        self._add_row(settings_tab, r, "notes", self.notes); r += 1
        tabs.addTab(settings_tab["scroll"], self._tab_title("tab_settings", self._("tab_settings")))

        root.addWidget(tabs)

        # Prefill on edit
        if self.client:
            g = self._get
            self.name_ar.setText(g("name_ar", ""))
            self.name_en.setText(g("name_en", ""))
            self.name_tr.setText(g("name_tr", ""))
            self.city.setText(g("city", ""))
            self.address_ar.setText(g("address_ar", "") or g("address", ""))
            self.address_en.setText(g("address_en", ""))
            self.address_tr.setText(g("address_tr", ""))
            self.phone.setText(g("phone", ""))
            self.email.setText(g("email", ""))
            self.website.setText(g("website", ""))
            self.tax_id.setText(g("tax_id", ""))
            self.notes.setText(g("notes", ""))

            cid = g("country_id")
            if cid is not None:
                for i in range(self.cmb_country.count()):
                    if self.cmb_country.itemData(i) == cid:
                        self.cmb_country.setCurrentIndex(i); break

            curid = g("default_currency_id")
            if curid is not None:
                for i in range(self.cmb_currency.count()):
                    if self.cmb_currency.itemData(i) == curid:
                        self.cmb_currency.setCurrentIndex(i); break

        # Footer buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

    # ---- helpers ----
    def _tab_title(self, key: str, fallback: str) -> str:
        t = self._(key)
        return t if t and t != key else fallback

    def _make_form_tab(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        form = QWidget()
        grid = QGridLayout(form)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.setContentsMargins(8, 8, 8, 8)
        scroll.setWidget(form)
        return {"scroll": scroll, "form": form, "grid": grid}

    def _add_row(self, tab_dict, row_index: int, label_key: str, widget):
        lbl = QLabel(self._(label_key))
        tab_dict["grid"].addWidget(lbl, row_index, 0)
        tab_dict["grid"].addWidget(widget, row_index, 1)

    def _get(self, key, default=None):
        if isinstance(self.client, dict):
            return self.client.get(key, default)
        return getattr(self.client, key, default)

    def _fill_countries(self):
        self.cmb_country.clear()
        self.cmb_country.addItem(self._("not_set"), None)
        for c in self.countries:
            label = _name_by_lang(c, self._lang)
            cid = getattr(c, "id", None) if not isinstance(c, dict) else c.get("id")
            self.cmb_country.addItem(label or f"#{cid}", cid)

    def _fill_currencies(self):
        self.cmb_currency.clear()
        self.cmb_currency.addItem(self._("not_set"), None)
        for c in self.currencies:
            code = getattr(c, "code", None) if not isinstance(c, dict) else c.get("code")
            symbol = getattr(c, "symbol", None) if not isinstance(c, dict) else c.get("symbol")
            label = (code or "") + (f" ({symbol})" if symbol else "")
            cid = getattr(c, "id", None) if not isinstance(c, dict) else c.get("id")
            self.cmb_currency.addItem(label or f"#{cid}", cid)

    # ---- data & validation ----
    def get_data(self):
        d = {
            "name_ar": (self.name_ar.text() or "").strip(),
            "name_en": (self.name_en.text() or "").strip(),
            "name_tr": (self.name_tr.text() or "").strip(),
            "country_id": self.cmb_country.currentData(),
            "city": (self.city.text() or "").strip(),
            "address_ar": (self.address_ar.toPlainText() or "").strip(),
            "address_en": (self.address_en.toPlainText() or "").strip(),
            "address_tr": (self.address_tr.toPlainText() or "").strip(),
            "default_currency_id": self.cmb_currency.currentData(),
            "phone": (self.phone.text() or "").strip(),
            "email": (self.email.text() or "").strip(),
            "website": (self.website.text() or "").strip(),
            "tax_id": (self.tax_id.text() or "").strip(),
            "notes": (self.notes.toPlainText() or "").strip(),
        }
        # Uppercase everything except notes
        for k, v in list(d.items()):
            if isinstance(v, str):
                if k not in ("notes", "email"):
                    d[k] = v.upper()

        # email must be lowercase
        if d.get("email"):
            d["email"] = d["email"].lower()

        return d

    def accept(self):
        d = self.get_data()
        errors = []
        if not (d["name_ar"] or d["name_en"] or d["name_tr"]):
            # أبسط تحقق: لازم واحد من الأسماء يكون معبّى
            errors.append(self._("arabic_name_required"))  # نستخدم المفتاح الموجود للتبسيط
        email = d.get("email")
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            errors.append(self._("invalid_email"))
        if errors:
            QMessageBox.warning(self, self._("invalid_data"), "\n".join(errors))
            return
        super().accept()