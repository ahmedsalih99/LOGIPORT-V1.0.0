from core.base_dialog import BaseDialog
from PySide6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QPushButton, QHBoxLayout

class AddDeliveryMethodDialog(BaseDialog):
    def __init__(self, parent=None, delivery_method=None):
        super().__init__(parent)
        self.delivery_method = delivery_method
        self.setWindowTitle(self._("add_delivery_method") if delivery_method is None else self._("edit_delivery_method"))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.name_ar = QLineEdit()
        self.name_en = QLineEdit()
        self.name_tr = QLineEdit()
        layout.addWidget(QLabel(self._("arabic_name")))
        layout.addWidget(self.name_ar)
        layout.addWidget(QLabel(self._("english_name")))
        layout.addWidget(self.name_en)
        layout.addWidget(QLabel(self._("turkish_name")))
        layout.addWidget(self.name_tr)

        if self.delivery_method:
            self.name_ar.setText(self.delivery_method.get("name_ar", ""))
            self.name_en.setText(self.delivery_method.get("name_en", ""))
            self.name_tr.setText(self.delivery_method.get("name_tr", ""))

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
        }
