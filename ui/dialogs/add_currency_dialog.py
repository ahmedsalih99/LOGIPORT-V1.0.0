from core.base_dialog import BaseDialog
from PySide6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QPushButton, QHBoxLayout

class AddCurrencyDialog(BaseDialog):
    def __init__(self, parent=None, currency=None):
        super().__init__(parent)
        self.currency = currency
        self.setWindowTitle(self._("add_currency") if currency is None else self._("edit_currency"))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.name_ar = QLineEdit()
        self.name_en = QLineEdit()
        self.name_tr = QLineEdit()
        self.symbol = QLineEdit()
        self.code = QLineEdit()
        layout.addWidget(QLabel(self._("arabic_name")))
        layout.addWidget(self.name_ar)
        layout.addWidget(QLabel(self._("english_name")))
        layout.addWidget(self.name_en)
        layout.addWidget(QLabel(self._("turkish_name")))
        layout.addWidget(self.name_tr)
        layout.addWidget(QLabel(self._("currency_symbol")))
        layout.addWidget(self.symbol)
        layout.addWidget(QLabel(self._("currency_code")))
        layout.addWidget(self.code)

        if self.currency:
            self.name_ar.setText(self.currency.get("name_ar", ""))
            self.name_en.setText(self.currency.get("name_en", ""))
            self.name_tr.setText(self.currency.get("name_tr", ""))
            self.symbol.setText(self.currency.get("symbol", ""))
            self.code.setText(self.currency.get("code", ""))

        btns = QHBoxLayout()
        self.btn_save = QPushButton(self._("save"))
        self.btn_cancel = QPushButton(self._("cancel"))
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def get_data(self):
        return {
            "name_ar": self.name_ar.text().strip(),
            "name_en": self.name_en.text().strip(),
            "name_tr": self.name_tr.text().strip(),
            "symbol": self.symbol.text().strip(),
            "code": self.code.text().strip(),
        }
