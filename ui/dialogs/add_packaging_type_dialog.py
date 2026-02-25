from core.form_dialog import FormDialog
from PySide6.QtWidgets import QLineEdit


class AddPackagingTypeDialog(FormDialog):
    def __init__(self, parent=None, packaging_type=None):
        self.packaging_type = packaging_type
        title_key = "add_packaging_type" if packaging_type is None else "edit_packaging_type"
        super().__init__(parent, title_key=title_key, min_width=420)
        self._build_form()
        if packaging_type:
            self._populate(packaging_type)

    def _build_form(self):
        self.name_ar = QLineEdit()
        self.name_en = QLineEdit()
        self.name_tr = QLineEdit()
        self.add_row(self._("arabic_name"),  self.name_ar)
        self.add_row(self._("english_name"), self.name_en)
        self.add_row(self._("turkish_name"), self.name_tr)

    def _populate(self, data: dict):
        self.name_ar.setText(data.get("name_ar", ""))
        self.name_en.setText(data.get("name_en", ""))
        self.name_tr.setText(data.get("name_tr", ""))

    def get_data(self):
        return {
            "name_ar": self.name_ar.text().strip(),
            "name_en": self.name_en.text().strip(),
            "name_tr": self.name_tr.text().strip(),
        }
