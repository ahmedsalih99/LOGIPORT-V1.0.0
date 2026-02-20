from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QTextEdit,
    QDialogButtonBox, QLabel
)

from core.translator import TranslationManager

# -------- Guarded CRUD imports --------------------------------------------
try:
    from database.crud.materials_crud import MaterialsCRUD
except Exception:  # pragma: no cover
    MaterialsCRUD = None  # type: ignore
try:
    from database.crud.packaging_types_crud import PackagingTypesCRUD
except Exception:  # pragma: no cover
    PackagingTypesCRUD = None  # type: ignore
try:
    from database.crud.pricing_types_crud import PricingTypesCRUD
except Exception:  # pragma: no cover
    PricingTypesCRUD = None  # type: ignore
try:
    from database.crud.currencies_crud import CurrenciesCRUD
except Exception:  # pragma: no cover
    CurrenciesCRUD = None  # type: ignore
try:
    from database.crud.countries_crud import CountriesCRUD
except Exception:  # pragma: no cover
    CountriesCRUD = None  # type: ignore


class ManualItemDialog(QDialog):
    """Dialog for adding a manual item (not sourced from entries)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()

        self.setWindowTitle(self._("add_manual_item"))
        self.setModal(True)
        self.resize(520, 540)

        self._build_ui()
        self._fill_lookups()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        # Widgets
        self.cmb_material = QComboBox(); self.cmb_material.setObjectName("cmb_material")
        self.cmb_packaging = QComboBox(); self.cmb_packaging.setObjectName("cmb_packaging")
        self.edt_qty = QLineEdit(); self.edt_qty.setObjectName("edt_qty")
        self.edt_gross = QLineEdit(); self.edt_gross.setObjectName("edt_gross")
        self.edt_net = QLineEdit(); self.edt_net.setObjectName("edt_net")
        self.cmb_pricing_type = QComboBox(); self.cmb_pricing_type.setObjectName("cmb_pricing_type")
        self.edt_unit_price = QLineEdit(); self.edt_unit_price.setObjectName("edt_unit_price")
        self.cmb_currency = QComboBox(); self.cmb_currency.setObjectName("cmb_currency")
        self.cmb_origin = QComboBox(); self.cmb_origin.setObjectName("cmb_origin")
        self.txt_notes = QTextEdit(); self.txt_notes.setObjectName("txt_notes"); self.txt_notes.setFixedHeight(64)

        # Validators for numeric inputs
        for le in (self.edt_qty, self.edt_gross, self.edt_net, self.edt_unit_price):
            le.setValidator(QDoubleValidator(0.0, 1e12, 3, self))
            le.setPlaceholderText("0")

        # Labels
        t = self._
        form.addRow(t("material"), self.cmb_material)
        form.addRow(t("packaging_type"), self.cmb_packaging)
        form.addRow(t("quantity"), self.edt_qty)
        form.addRow(t("gross_weight"), self.edt_gross)
        form.addRow(t("net_weight"), self.edt_net)
        form.addRow(t("pricing_type"), self.cmb_pricing_type)
        form.addRow(t("unit_price"), self.edt_unit_price)
        form.addRow(t("currency"), self.cmb_currency)
        form.addRow(t("origin_country"), self.cmb_origin)
        form.addRow(t("notes"), self.txt_notes)

        v.addLayout(form)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        v.addWidget(btns)

    # ------------------------------------------------------------------ Lookups
    def _fill_lookups(self):
        self._fill_materials()
        self._fill_packaging()
        self._fill_pricing_types()
        self._fill_currencies()
        self._fill_countries()

    def _fill_materials(self):
        self.cmb_material.clear(); self.cmb_material.addItem(self._("select"), None)
        items = []
        try:
            if MaterialsCRUD:
                items = (MaterialsCRUD()).get_all() or []
        except Exception:
            items = []
        for it in items:
            self.cmb_material.addItem(self._name_by_lang(it), self._id(it))

    def _fill_packaging(self):
        self.cmb_packaging.clear(); self.cmb_packaging.addItem(self._("not_set"), None)
        items = []
        try:
            if PackagingTypesCRUD:
                items = (PackagingTypesCRUD()).get_all() or []
        except Exception:
            items = []
        for it in items:
            self.cmb_packaging.addItem(self._name_by_lang(it), self._id(it))

    def _fill_pricing_types(self):
        self.cmb_pricing_type.clear(); self.cmb_pricing_type.addItem(self._("select"), None)
        items = []
        try:
            if PricingTypesCRUD:
                items = (PricingTypesCRUD()).get_all() or []
        except Exception:
            items = []
        for it in items:
            self.cmb_pricing_type.addItem(self._name_by_lang(it), self._id(it))

    def _fill_currencies(self):
        self.cmb_currency.clear(); self.cmb_currency.addItem(self._("select"), None)
        items = []
        try:
            if CurrenciesCRUD:
                items = (CurrenciesCRUD()).get_all() or []
        except Exception:
            items = []
        for it in items:
            code = self._attr(it, 'code'); symbol = self._attr(it, 'symbol')
            label = (code or "") + (f" ({symbol})" if symbol else "")
            self.cmb_currency.addItem(label or f"#{self._id(it)}", self._id(it))

    def _fill_countries(self):
        self.cmb_origin.clear(); self.cmb_origin.addItem(self._("select"), None)
        items = []
        try:
            if CountriesCRUD:
                items = (CountriesCRUD()).get_all() or []
        except Exception:
            items = []
        for it in items:
            self.cmb_origin.addItem(self._name_by_lang(it), self._id(it))

    # ------------------------------------------------------------------ Actions
    def _on_accept(self):
        from PySide6.QtWidgets import QMessageBox

        missing = []

        if not self.cmb_material.currentData():
            missing.append(self._("material"))

        if not self.cmb_pricing_type.currentData():
            missing.append(self._("pricing_type"))

        if not self.cmb_currency.currentData():
            missing.append(self._("currency"))

        # unit_price يجب أن يكون > 0
        try:
            price_val = float((self.edt_unit_price.text() or "0").replace(',', '.'))
        except Exception:
            price_val = 0.0
        if price_val <= 0:
            missing.append(self._("unit_price") + " (> 0)")

        if missing:
            QMessageBox.warning(
                self,
                self._("invalid_data"),
                self._("please_fill_required_fields") + ":\n• " + "\n• ".join(missing)
            )
            return

        self.accept()

    # ------------------------------------------------------------------ Public API
    def get_data(self) -> dict:
        def _num(le: QLineEdit) -> float:
            try:
                return float((le.text() or "0").replace(',', '.'))
            except Exception:
                return 0.0
        return {
            "material_id": self.cmb_material.currentData(),
            "material_label": self.cmb_material.currentText(),
            "packaging_type_id": self.cmb_packaging.currentData(),
            "packaging_label": self.cmb_packaging.currentText(),
            "quantity": _num(self.edt_qty),
            "gross_weight_kg": _num(self.edt_gross),
            "net_weight_kg": _num(self.edt_net),
            "pricing_type_id": self.cmb_pricing_type.currentData(),
            "pricing_type_label": self.cmb_pricing_type.currentText(),
            "unit_price": _num(self.edt_unit_price),
            "currency_id": self.cmb_currency.currentData(),
            "currency_label": self.cmb_currency.currentText(),
            "origin_country_id": self.cmb_origin.currentData(),
            "origin_label": self.cmb_origin.currentText(),
            "notes": self.txt_notes.toPlainText() or "",
            "is_manual": True,
            "source": "manual",
        }

    # ------------------------------------------------------------------ Helpers
    def _name_by_lang(self, obj) -> str:
        if not obj:
            return ""
        data = obj if isinstance(obj, dict) else getattr(obj, "__dict__", {})
        for key in (f"name_{self._lang}", "name_en", "name_ar", "name_tr", "title", "name"):
            val = data.get(key)
            if val:
                return str(val)
        # Currency special-case
        code = data.get("code"); symbol = data.get("symbol")
        if code or symbol:
            return (code or "") + (f" ({symbol})" if symbol else "")
        return str(data.get("id", ""))

    def _id(self, obj):
        return obj.get('id') if isinstance(obj, dict) else getattr(obj, 'id', None)

    def _attr(self, obj, key, default=None):
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)
