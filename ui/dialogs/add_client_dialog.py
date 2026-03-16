"""
ui/dialogs/add_client_dialog.py
================================
Add/Edit Client — ترث BaseDialog مباشرةً (لأنها تحتوي على QTabWidget).
هيكل: Header (primary) → QTabWidget (stretch) → Footer (حفظ/إلغاء)
Tabs: General / Location / Contact / Settings
"""
from core.base_dialog import BaseDialog
from core.translator import TranslationManager

from PySide6.QtWidgets import (
    QLineEdit, QTextEdit, QComboBox,
    QTabWidget, QScrollArea, QWidget,
    QFormLayout, QLabel, QFrame,
    QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.utils.wheel_blocker import block_wheel_in


def _name_by_lang(obj, lang: str) -> str:
    if not obj:
        return ""
    if isinstance(obj, dict):
        return (obj.get(f"name_{lang}") or obj.get("name_ar")
                or obj.get("name_en") or obj.get("name_tr") or "")
    return (getattr(obj, f"name_{lang}", None) or getattr(obj, "name_ar", None)
            or getattr(obj, "name_en", None) or getattr(obj, "name_tr", None) or "")


class AddClientDialog(BaseDialog):
    """Add/Edit Client dialog — أربعة tabs."""

    def __init__(self, parent=None, client=None, *, countries=None, currencies=None):
        super().__init__(parent)
        self._client = client
        self._countries = countries or []
        self._currencies = currencies or []
        self._lang = TranslationManager.get_instance().get_current_language()

        title_key = "add_client" if client is None else "edit_client"
        self.set_translated_title(title_key)
        self.setMinimumWidth(520)
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
            title=self._("add_client" if not self._client else "edit_client")
        )
        root.addWidget(header)
        root.addWidget(sep)

        # ── Tabs ──────────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        # Tab 1: General
        tab1, f1 = self._make_tab()
        self.name_ar = QLineEdit()
        self._row(f1, "arabic_name",  self.name_ar,  required=True)
        self.name_en = QLineEdit()
        self._row(f1, "english_name", self.name_en)
        self.name_tr = QLineEdit()
        self._row(f1, "turkish_name", self.name_tr)
        self._tabs.addTab(tab1, self._("tab_general"))

        # Tab 2: Location
        tab2, f2 = self._make_tab()
        self.cmb_country = QComboBox()
        self._fill_countries()
        self._row(f2, "country", self.cmb_country)
        self.city = QLineEdit()
        self._row(f2, "city", self.city)
        self.address_ar = _AutoTextEdit()
        self._row(f2, "address_ar", self.address_ar)
        self.address_en = _AutoTextEdit()
        self._row(f2, "address_en", self.address_en)
        self.address_tr = _AutoTextEdit()
        self._row(f2, "address_tr", self.address_tr)
        self._tabs.addTab(tab2, self._("tab_location"))

        # Tab 3: Contact
        tab3, f3 = self._make_tab()
        self.phone = QLineEdit()
        self._row(f3, "phone", self.phone)
        self.email = QLineEdit()
        self._row(f3, "email", self.email)
        self.website = QLineEdit()
        self._row(f3, "website", self.website)
        self._tabs.addTab(tab3, self._("tab_contact"))

        # Tab 4: Settings
        tab4, f4 = self._make_tab()
        self.cmb_currency = QComboBox()
        self._fill_currencies()
        self._row(f4, "default_currency", self.cmb_currency)
        self.tax_id = QLineEdit()
        self._row(f4, "tax_id", self.tax_id)
        self.notes = _AutoTextEdit()
        self._row(f4, "notes", self.notes)
        self._tabs.addTab(tab4, self._("tab_settings"))

        root.addWidget(self._tabs, 1)   # stretch=1

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
        self.cmb_country.addItem(self._("not_set"), None)
        for c in self._countries:
            label = _name_by_lang(c, self._lang)
            cid   = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
            self.cmb_country.addItem(label or f"#{cid}", cid)

    def _fill_currencies(self):
        self.cmb_currency.clear()
        self.cmb_currency.addItem(self._("not_set"), None)
        for c in self._currencies:
            code   = c.get("code") if isinstance(c, dict) else getattr(c, "code", None)
            symbol = c.get("symbol") if isinstance(c, dict) else getattr(c, "symbol", None)
            label  = (code or "") + (f" ({symbol})" if symbol else "")
            cid    = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
            self.cmb_currency.addItem(label or f"#{cid}", cid)

    # ─────────────────────────────────────────────────────────────────────────
    # Populate (edit mode)
    # ─────────────────────────────────────────────────────────────────────────

    def _populate(self):
        if not self._client:
            return
        g = self._get

        self.name_ar.setText(g("name_ar", ""))
        self.name_en.setText(g("name_en", ""))
        self.name_tr.setText(g("name_tr", ""))

        cid = g("country_id")
        if cid is not None:
            for i in range(self.cmb_country.count()):
                if self.cmb_country.itemData(i) == cid:
                    self.cmb_country.setCurrentIndex(i)
                    break

        self.city.setText(g("city", ""))
        self.address_ar.setPlainText(g("address_ar", "") or g("address", ""))
        self.address_en.setPlainText(g("address_en", ""))
        self.address_tr.setPlainText(g("address_tr", ""))

        self.phone.setText(g("phone", ""))
        self.email.setText(g("email", ""))
        self.website.setText(g("website", ""))
        self.tax_id.setText(g("tax_id", ""))
        self.notes.setPlainText(g("notes", ""))

        curid = g("default_currency_id")
        if curid is not None:
            for i in range(self.cmb_currency.count()):
                if self.cmb_currency.itemData(i) == curid:
                    self.cmb_currency.setCurrentIndex(i)
                    break

    def _get(self, key, default=None):
        if isinstance(self._client, dict):
            return self._client.get(key, default)
        return getattr(self._client, key, default)

    # ─────────────────────────────────────────────────────────────────────────
    # Data & Validation
    # ─────────────────────────────────────────────────────────────────────────

    def get_data(self) -> dict:
        return {
            "name_ar":             (self.name_ar.text() or "").strip().upper(),
            "name_en":             (self.name_en.text() or "").strip().upper(),
            "name_tr":             (self.name_tr.text() or "").strip().upper(),
            "country_id":          self.cmb_country.currentData(),
            "city":                (self.city.text() or "").strip(),
            "address_ar":          (self.address_ar.toPlainText() or "").strip(),
            "address_en":          (self.address_en.toPlainText() or "").strip(),
            "address_tr":          (self.address_tr.toPlainText() or "").strip(),
            "phone":               (self.phone.text() or "").strip(),
            "email":               (self.email.text() or "").strip().lower(),
            "website":             (self.website.text() or "").strip(),
            "default_currency_id": self.cmb_currency.currentData(),
            "tax_id":              (self.tax_id.text() or "").strip(),
            "notes":               (self.notes.toPlainText() or "").strip(),
        }

    def accept(self):
        d = self.get_data()
        errors = []

        if not (d["name_ar"] or d["name_en"] or d["name_tr"]):
            errors.append(self._("arabic_name_required"))
            self._tabs.setCurrentIndex(0)

        email = d["email"]
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            errors.append(self._("invalid_email"))
            if not errors or len(errors) == 1:
                self._tabs.setCurrentIndex(2)

        if errors:
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
    - حد أدنى: 72px
    - حد أقصى: 35% من ارتفاع الشاشة
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
        doc_h = int(self.document().size().height()) + 8
        new_h = max(self._MIN_H, min(doc_h, self._max_h()))
        if self.height() != new_h:
            self.setFixedHeight(new_h)

    def sizeHint(self):
        from PySide6.QtCore import QSize
        doc_h = int(self.document().size().height()) + 8
        h = max(self._MIN_H, min(doc_h, self._max_h()))
        return QSize(super().sizeHint().width(), h)