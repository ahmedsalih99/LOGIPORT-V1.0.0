from core.base_dialog import BaseDialog
from PySide6.QtWidgets import QVBoxLayout, QLineEdit, QLabel, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt

class AddCountryDialog(BaseDialog):
    def __init__(self, parent=None, country=None):
        super().__init__(parent)
        self.country = country
        self.setWindowTitle(self._("add_country") if country is None else self._("edit_country"))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.name_ar = QLineEdit()
        self.name_en = QLineEdit()
        self.name_tr = QLineEdit()
        self.code = QLineEdit()
        layout.addWidget(QLabel(self._("arabic_name")))
        layout.addWidget(self.name_ar)
        layout.addWidget(QLabel(self._("english_name")))
        layout.addWidget(self.name_en)
        layout.addWidget(QLabel(self._("turkish_name")))
        layout.addWidget(self.name_tr)
        layout.addWidget(QLabel(self._("country_code")))
        layout.addWidget(self.code)

        if self.country:
            self.name_ar.setText(self.country.get("name_ar", ""))
            self.name_en.setText(self.country.get("name_en", ""))
            self.name_tr.setText(self.country.get("name_tr", ""))
            self.code.setText(self.country.get("code", ""))

        btns = QHBoxLayout()
        self.btn_save = QPushButton(self._("save"))
        self.btn_cancel = QPushButton(self._("cancel"))
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def get_data(self):
        # كل شيء UPPER قبل الإرجاع
        name_ar = (self.name_ar.text() or "").strip().upper()
        name_en = (self.name_en.text() or "").strip().upper()
        name_tr = (self.name_tr.text() or "").strip().upper()
        code = (self.code.text() or "").strip().upper()
        return {
            "name_ar": name_ar,
            "name_en": name_en,
            "name_tr": name_tr,
            "code": code,
        }

    def accept(self):
        # نقرأ ونطبّق الفاليديشن على القيم بعد تحويلها لأحرف كبيرة
        data = self.get_data()
        name_ar = data["name_ar"]
        name_en = data["name_en"]
        name_tr = data["name_tr"]
        code = data["code"]

        errors = []
        if not name_ar: errors.append(self._("arabic_name_required"))
        if not name_en: errors.append(self._("english_name_required"))
        if not name_tr: errors.append(self._("turkish_name_required"))
        if code and len(code) > 8:
            errors.append(self._("country_code_too_long"))

        if errors:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, self._("invalid_data"), "\n".join(errors))
            return

        # حدّث الحقول في الواجهة لتظهر Upper فعلياً
        self.name_ar.setText(name_ar)
        self.name_en.setText(name_en)
        self.name_tr.setText(name_tr)
        self.code.setText(code)

        super().accept()
