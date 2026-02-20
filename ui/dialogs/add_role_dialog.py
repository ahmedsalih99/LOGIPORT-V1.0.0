from core.base_dialog import BaseDialog
from ui.widgets.custom_button import CustomButton
from PySide6.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QTextEdit, QHBoxLayout
from core.translator import TranslationManager
from database.crud.permissions_crud import RolesCRUD

class AddRoleDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._ = TranslationManager.get_instance().translate
        self.init_ui()
        self.retranslate_ui()
        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

    def init_ui(self):
        layout = QVBoxLayout()
        self.lbl_name = QLabel()
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText(self._("role_code_hint"))
        self.lbl_label_ar = QLabel()
        self.edit_label_ar = QLineEdit()
        self.lbl_label_en = QLabel()
        self.edit_label_en = QLineEdit()
        self.lbl_label_tr = QLabel()
        self.edit_label_tr = QLineEdit()
        self.lbl_desc = QLabel()
        self.edit_desc = QTextEdit()

        layout.addWidget(self.lbl_name)
        layout.addWidget(self.edit_name)
        layout.addWidget(self.lbl_label_ar)
        layout.addWidget(self.edit_label_ar)
        layout.addWidget(self.lbl_label_en)
        layout.addWidget(self.edit_label_en)
        layout.addWidget(self.lbl_label_tr)
        layout.addWidget(self.edit_label_tr)
        layout.addWidget(self.lbl_desc)
        layout.addWidget(self.edit_desc)

        self.btn_save = CustomButton(self._("save"))
        self.btn_save.clicked.connect(self.accept)
        row_btn = QHBoxLayout()
        row_btn.addStretch()
        row_btn.addWidget(self.btn_save)
        layout.addLayout(row_btn)
        self.setLayout(layout)

    def retranslate_ui(self):
        self.set_translated_title("add_role")
        self.lbl_name.setText(self._("role_code") + " " + self._("role_code_lang"))
        self.lbl_label_ar.setText(self._("role_label_ar"))
        self.lbl_label_en.setText(self._("role_label_en"))
        self.lbl_label_tr.setText(self._("role_label_tr"))
        self.lbl_desc.setText(self._("description"))
        self.btn_save.setText(self._("save"))

    def get_data(self):
        return {
            "name": self.edit_name.text().strip(),
            "label_ar": self.edit_label_ar.text().strip(),
            "label_en": self.edit_label_en.text().strip(),
            "label_tr": self.edit_label_tr.text().strip(),
            "description": self.edit_desc.toPlainText().strip()
        }

    def accept(self):
        data = self.get_data()
        # تحقق من عدم التكرار وملء جميع الحقول الأساسية
        if not all([data["name"], data["label_ar"], data["label_en"], data["label_tr"]]):
            self.show_error("error", "all_fields_required")
            return
        # تحقق من عدم تكرار الاسم الداخلي للدور
        roles = RolesCRUD().get_all()
        if any(role["name"].lower() == data["name"].lower() for role in roles):
            self.show_error("error", "role_code_already_exists")
            return
        # إضافة الدور
        RolesCRUD().add_role(
            data["name"], data["label_ar"], data["label_en"], data["label_tr"], data["description"]
        )
        super().accept()
