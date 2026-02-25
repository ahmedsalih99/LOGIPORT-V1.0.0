from core.form_dialog import FormDialog
from PySide6.QtWidgets import QLineEdit


class AddCurrencyDialog(FormDialog):
    def __init__(self, parent=None, currency=None):
        self.currency = currency
        title_key = "add_currency" if currency is None else "edit_currency"
        super().__init__(parent, title_key=title_key, min_width=420)
        self._build_form()
        if currency:
            self._populate(currency)

    def _build_form(self):
        self.name_ar = QLineEdit()
        self.name_en = QLineEdit()
        self.name_tr = QLineEdit()
        self.symbol  = QLineEdit()
        self.code    = QLineEdit()
        self.add_row(self._("arabic_name"),    self.name_ar)
        self.add_row(self._("english_name"),   self.name_en)
        self.add_row(self._("turkish_name"),   self.name_tr)
        self.add_row(self._("currency_symbol"), self.symbol)
        self.add_row(self._("currency_code"),  self.code)

    def _populate(self, data: dict):
        self.name_ar.setText(data.get("name_ar", ""))
        self.name_en.setText(data.get("name_en", ""))
        self.name_tr.setText(data.get("name_tr", ""))
        self.symbol.setText(data.get("symbol", ""))
        self.code.setText(data.get("code", ""))

    def get_data(self):
        return {
            "name_ar": self.name_ar.text().strip(),
            "name_en": self.name_en.text().strip(),
            "name_tr": self.name_tr.text().strip(),
            "symbol":  self.symbol.text().strip(),
            "code":    self.code.text().strip(),
        }
