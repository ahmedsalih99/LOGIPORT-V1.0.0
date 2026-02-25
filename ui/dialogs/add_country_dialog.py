from core.form_dialog import FormDialog
from PySide6.QtWidgets import QLineEdit, QMessageBox


class AddCountryDialog(FormDialog):
    def __init__(self, parent=None, country=None):
        self.country = country
        title_key = "add_country" if country is None else "edit_country"
        super().__init__(parent, title_key=title_key, min_width=420)
        self._build_form()
        if country:
            self._populate(country)

    def _build_form(self):
        self.name_ar = QLineEdit()
        self.name_en = QLineEdit()
        self.name_tr = QLineEdit()
        self.code    = QLineEdit()
        self.add_row(self._("arabic_name"),  self.name_ar)
        self.add_row(self._("english_name"), self.name_en)
        self.add_row(self._("turkish_name"), self.name_tr)
        self.add_row(self._("country_code"), self.code)

    def _populate(self, data: dict):
        self.name_ar.setText(data.get("name_ar", ""))
        self.name_en.setText(data.get("name_en", ""))
        self.name_tr.setText(data.get("name_tr", ""))
        self.code.setText(data.get("code", ""))

    def get_data(self):
        return {
            "name_ar": self.name_ar.text().strip().upper(),
            "name_en": self.name_en.text().strip().upper(),
            "name_tr": self.name_tr.text().strip().upper(),
            "code":    self.code.text().strip().upper(),
        }

    def accept(self):
        data = self.get_data()
        errors = []
        if not data["name_ar"]: errors.append(self._("arabic_name_required"))
        if not data["name_en"]: errors.append(self._("english_name_required"))
        if not data["name_tr"]: errors.append(self._("turkish_name_required"))
        if data["code"] and len(data["code"]) > 8:
            errors.append(self._("country_code_too_long"))
        if errors:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, self._("invalid_data"), "\n".join(errors))
            return
        self.name_ar.setText(data["name_ar"])
        self.name_en.setText(data["name_en"])
        self.name_tr.setText(data["name_tr"])
        self.code.setText(data["code"])
        super().accept()
