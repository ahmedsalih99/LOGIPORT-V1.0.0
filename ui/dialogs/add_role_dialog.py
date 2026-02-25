from core.form_dialog import FormDialog
from PySide6.QtWidgets import QLineEdit, QTextEdit
from database.crud.permissions_crud import RolesCRUD


class AddRoleDialog(FormDialog):
    def __init__(self, parent=None):
        super().__init__(parent, title_key="add_role", min_width=460)
        self._build_form()

    def _build_form(self):
        self.edit_name     = QLineEdit()
        self.edit_name.setPlaceholderText(self._("role_code_hint"))
        self.edit_label_ar = QLineEdit()
        self.edit_label_en = QLineEdit()
        self.edit_label_tr = QLineEdit()
        self.edit_desc     = QTextEdit()
        self.edit_desc.setFixedHeight(80)

        self.add_row(self._("role_code"),     self.edit_name)
        self.add_section("role_labels")
        self.add_row(self._("role_label_ar"), self.edit_label_ar)
        self.add_row(self._("role_label_en"), self.edit_label_en)
        self.add_row(self._("role_label_tr"), self.edit_label_tr)
        self.add_row(self._("description"),   self.edit_desc)

    def get_data(self):
        return {
            "name":        self.edit_name.text().strip(),
            "label_ar":    self.edit_label_ar.text().strip(),
            "label_en":    self.edit_label_en.text().strip(),
            "label_tr":    self.edit_label_tr.text().strip(),
            "description": self.edit_desc.toPlainText().strip(),
        }

    def accept(self):
        data = self.get_data()
        if not all([data["name"], data["label_ar"], data["label_en"], data["label_tr"]]):
            self.show_error("error", "all_fields_required")
            return
        roles = RolesCRUD().get_all()
        if any(r["name"].lower() == data["name"].lower() for r in roles):
            self.show_error("error", "role_code_already_exists")
            return
        RolesCRUD().add_role(
            data["name"], data["label_ar"], data["label_en"],
            data["label_tr"], data["description"]
        )
        super().accept()
