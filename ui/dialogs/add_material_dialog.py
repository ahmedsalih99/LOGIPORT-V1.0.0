"""
ui/dialogs/add_material_dialog.py
==================================
Add/Edit Material — ترث FormDialog مباشرةً.
الحقول: code, name_ar, name_en, name_tr, material_type_id,
         estimated_price (اختياري), currency_id (مطلوب إذا السعر موجود)
"""
from decimal import Decimal, InvalidOperation

from core.form_dialog import FormDialog
from core.translator import TranslationManager

from PySide6.QtWidgets import QLineEdit, QComboBox
from ui.utils.wheel_blocker import block_wheel_in


def _name_by_lang(obj, lang: str) -> str:
    if not obj:
        return ""
    if isinstance(obj, dict):
        return (obj.get(f"name_{lang}") or obj.get("name_ar")
                or obj.get("name_en") or obj.get("name_tr") or "")
    return (getattr(obj, f"name_{lang}", None) or getattr(obj, "name_ar", None)
            or getattr(obj, "name_en", None) or getattr(obj, "name_tr", None) or "")


class AddMaterialDialog(FormDialog):
    """Dialog لإضافة / تعديل مادة."""

    def __init__(self, parent=None, material=None, *, material_types=None, currencies=None):
        self._material = material
        self._material_types = material_types or []
        self._currencies = currencies or []
        self._lang = TranslationManager.get_instance().get_current_language()

        title_key = "add_material" if material is None else "edit_material"
        super().__init__(parent, title_key=title_key, min_width=480, icon="🧱", icon_bg="#FFF7ED")

        self._build_form()
        self._populate()
        block_wheel_in(self)

    # ─────────────────────────────────────────────────────────────────────────
    # Build
    # ─────────────────────────────────────────────────────────────────────────

    def _build_form(self):
        # ── الرمز والأسماء ───────────────────────────────────────────────
        self.add_section("section_basic_info")

        self.code = QLineEdit()
        self.add_row("code", self.code, required=True)

        self.name_ar = QLineEdit()
        self.add_row("arabic_name", self.name_ar, required=True)

        self.name_en = QLineEdit()
        self.add_row("english_name", self.name_en)

        self.name_tr = QLineEdit()
        self.add_row("turkish_name", self.name_tr)

        # ── النوع ────────────────────────────────────────────────────────
        self.add_section("section_classification")

        self.cmb_type = QComboBox()
        self._fill_material_types()
        self.add_row("material_type", self.cmb_type, required=True)

        # ── السعر التقديري ───────────────────────────────────────────────
        self.add_section("section_pricing")

        self.estimated_price = QLineEdit()
        self.estimated_price.setPlaceholderText("e.g. 12.50")
        self.add_row("estimated_price", self.estimated_price)

        self.cmb_currency = QComboBox()
        self._fill_currencies()
        self.add_row("currency", self.cmb_currency)

    # ─────────────────────────────────────────────────────────────────────────
    # Combo fillers
    # ─────────────────────────────────────────────────────────────────────────

    def _fill_material_types(self):
        self.cmb_type.clear()
        self.cmb_type.addItem(self._("not_set"), None)
        for mt in self._material_types:
            label = _name_by_lang(mt, self._lang)
            mt_id = mt.get("id") if isinstance(mt, dict) else getattr(mt, "id", None)
            self.cmb_type.addItem(label or f"#{mt_id}", mt_id)

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
        if not self._material:
            return
        g = self._get
        self.code.setText(g("code", ""))
        self.name_ar.setText(g("name_ar", ""))
        self.name_en.setText(g("name_en", ""))
        self.name_tr.setText(g("name_tr", ""))

        mt_id = g("material_type_id")
        if mt_id is not None:
            for i in range(self.cmb_type.count()):
                if self.cmb_type.itemData(i) == mt_id:
                    self.cmb_type.setCurrentIndex(i)
                    break

        ep = g("estimated_price")
        self.estimated_price.setText("" if ep in (None, "") else str(ep))

        cur_id = g("currency_id")
        if cur_id is not None:
            for i in range(self.cmb_currency.count()):
                if self.cmb_currency.itemData(i) == cur_id:
                    self.cmb_currency.setCurrentIndex(i)
                    break

    def _get(self, key, default=None):
        if isinstance(self._material, dict):
            return self._material.get(key, default)
        return getattr(self._material, key, default)

    # ─────────────────────────────────────────────────────────────────────────
    # Data & Validation
    # ─────────────────────────────────────────────────────────────────────────

    def get_data(self) -> dict:
        price_txt = (self.estimated_price.text() or "").strip()
        price_val = None
        if price_txt:
            try:
                price_val = Decimal(price_txt)
            except (InvalidOperation, ValueError):
                price_val = "__invalid__"

        return {
            "code":             (self.code.text() or "").strip(),
            "name_ar":          (self.name_ar.text() or "").strip(),
            "name_en":          (self.name_en.text() or "").strip(),
            "name_tr":          (self.name_tr.text() or "").strip(),
            "material_type_id": self.cmb_type.currentData(),
            "estimated_price":  price_val,
            "currency_id":      self.cmb_currency.currentData(),
        }

    def accept(self):
        self.clear_all_errors()
        d = self.get_data()
        ok = True

        if not d["code"]:
            self.show_field_error(self.code, self._("code_required"))
            ok = False

        if not d["name_ar"]:
            self.show_field_error(self.name_ar, self._("arabic_name_required"))
            ok = False

        if not d["material_type_id"]:
            self.show_field_error(self.cmb_type, self._("material_type_required"))
            ok = False

        price_txt = (self.estimated_price.text() or "").strip()
        if price_txt and d["estimated_price"] == "__invalid__":
            self.show_field_error(self.estimated_price, self._("invalid_price_format"))
            ok = False
        elif d["estimated_price"] not in (None, "__invalid__") and not d["currency_id"]:
            self.show_field_error(self.cmb_currency, self._("currency_required_when_price_set"))
            ok = False

        if not ok:
            return

        super().accept()