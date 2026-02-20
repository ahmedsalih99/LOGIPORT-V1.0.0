from decimal import Decimal, InvalidOperation

from core.base_dialog import BaseDialog
from core.translator import TranslationManager

from PySide6.QtWidgets import (
    QVBoxLayout, QLineEdit, QLabel, QPushButton, QHBoxLayout, QMessageBox, QComboBox
)

# لعرض أسماء الأنواع حسب اللغة
def _name_by_lang(obj, lang: str) -> str:
    if not obj:
        return ""
    if lang == "ar" and getattr(obj, "name_ar", None):
        return obj.name_ar
    if lang == "tr" and getattr(obj, "name_tr", None):
        return obj.name_tr
    # en افتراضيًا
    return getattr(obj, "name_en", None) or getattr(obj, "name_ar", None) or getattr(obj, "name_tr", None) or ""


class AddMaterialDialog(BaseDialog):
    """
    Dialog للإضافة/التعديل على مادة.
    الحقول: code, name_ar, name_en, name_tr, material_type_id, estimated_price (اختياري), currency_id (مطلوب إذا السعر موجود)
    """
    def __init__(self, parent=None, material=None, *, material_types=None, currencies=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()

        # material: ORM أو dict
        self.material = material
        self.material_types = material_types or []
        self.currencies = currencies or []

        self.setWindowTitle(self._("add_material") if material is None else self._("edit_material"))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Code
        layout.addWidget(QLabel(self._("code")))
        self.code = QLineEdit()
        layout.addWidget(self.code)

        # Arabic/English/Turkish names
        layout.addWidget(QLabel(self._("arabic_name")))
        self.name_ar = QLineEdit()
        layout.addWidget(self.name_ar)

        layout.addWidget(QLabel(self._("english_name")))
        self.name_en = QLineEdit()
        layout.addWidget(self.name_en)

        layout.addWidget(QLabel(self._("turkish_name")))
        self.name_tr = QLineEdit()
        layout.addWidget(self.name_tr)

        # Material Type (combo)
        layout.addWidget(QLabel(self._("material_type")))
        self.cmb_type = QComboBox()
        self._fill_material_types()
        layout.addWidget(self.cmb_type)

        # Estimated price + Currency
        layout.addWidget(QLabel(self._("estimated_price")))
        self.estimated_price = QLineEdit()
        self.estimated_price.setPlaceholderText("e.g. 12.50")
        layout.addWidget(self.estimated_price)

        layout.addWidget(QLabel(self._("currency")))
        self.cmb_currency = QComboBox()
        self._fill_currencies()
        layout.addWidget(self.cmb_currency)

        # Existing material values
        if self.material:
            get = self._get
            self.code.setText(get("code", ""))
            self.name_ar.setText(get("name_ar", ""))
            self.name_en.setText(get("name_en", ""))
            self.name_tr.setText(get("name_tr", ""))

            # type
            mt_id = get("material_type_id")
            if mt_id is not None:
                for i in range(self.cmb_type.count()):
                    if self.cmb_type.itemData(i) == mt_id:
                        self.cmb_type.setCurrentIndex(i)
                        break

            # price
            ep = get("estimated_price")
            self.estimated_price.setText("" if ep in (None, "") else str(ep))

            cur_id = get("currency_id")
            if cur_id is not None:
                for i in range(self.cmb_currency.count()):
                    if self.cmb_currency.itemData(i) == cur_id:
                        self.cmb_currency.setCurrentIndex(i)
                        break

        # Buttons
        btns = QHBoxLayout()
        self.btn_save = QPushButton(self._("save"))
        self.btn_cancel = QPushButton(self._("cancel"))
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def _get(self, key, default=None):
        if isinstance(self.material, dict):
            return self.material.get(key, default)
        return getattr(self.material, key, default)

    def _fill_material_types(self):
        self.cmb_type.clear()
        for mt in self.material_types:
            label = _name_by_lang(mt, self._lang)
            mt_id = getattr(mt, "id", None) if not isinstance(mt, dict) else mt.get("id")
            self.cmb_type.addItem(label or f"#{mt_id}", mt_id)

    def _fill_currencies(self):
        self.cmb_currency.clear()
        # عنصر فارغ اختياري
        self.cmb_currency.addItem(self._("not_set"), None)
        for c in self.currencies:
            # عرض code (+symbol إن وجد)
            code = getattr(c, "code", None) if not isinstance(c, dict) else c.get("code")
            symbol = getattr(c, "symbol", None) if not isinstance(c, dict) else c.get("symbol")
            label = (code or "") + (f" ({symbol})" if symbol else "")
            cid = getattr(c, "id", None) if not isinstance(c, dict) else c.get("id")
            self.cmb_currency.addItem(label or f"#{cid}", cid)

    def get_data(self):
        # تحويل السعر إلى Decimal أو None
        price_txt = (self.estimated_price.text() or "").strip()
        price_val = None
        if price_txt:
            try:
                price_val = Decimal(price_txt)
            except (InvalidOperation, ValueError):
                price_val = None  # سيُلتقط بالتحقق في accept()

        return {
            "code": self.code.text().strip(),
            "name_ar": self.name_ar.text().strip(),
            "name_en": self.name_en.text().strip(),
            "name_tr": self.name_tr.text().strip(),
            "material_type_id": self.cmb_type.currentData(),
            "estimated_price": price_val,
            "currency_id": self.cmb_currency.currentData(),
        }

    def accept(self):
        d = self.get_data()
        errors = []
        if not d["code"]:
            errors.append(self._("code_required"))
        if not d["name_ar"]:
            errors.append(self._("arabic_name_required"))
        if not d["material_type_id"]:
            errors.append(self._("material_type_required"))

        # إذا السعر موجود، لازم عملة
        if d["estimated_price"] is not None and d["currency_id"] is None:
            errors.append(self._("currency_required_when_price_set"))

        if errors:
            QMessageBox.warning(self, self._("invalid_data"), "\n".join(errors))
            return

        super().accept()
