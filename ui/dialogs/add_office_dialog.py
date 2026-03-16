"""
ui/dialogs/add_office_dialog.py
================================
نافذة إضافة / تعديل مكتب
"""
from core.form_dialog import FormDialog
from PySide6.QtWidgets import QLineEdit, QComboBox, QTextEdit, QSpinBox
from ui.utils.wheel_blocker import block_wheel_in


_COUNTRIES = [
    ("", "—"),
    ("SY", "سوريا / Syria"),
    ("TR", "تركيا / Turkey"),
    ("LB", "لبنان / Lebanon"),
    ("JO", "الأردن / Jordan"),
    ("IQ", "العراق / Iraq"),
    ("DE", "ألمانيا / Germany"),
    ("NL", "هولندا / Netherlands"),
    ("GB", "بريطانيا / UK"),
    ("OTHER", "أخرى / Other"),
]


class AddOfficeDialog(FormDialog):
    def __init__(self, parent=None, office: dict = None):
        self._office = office
        title_key = "add_office" if office is None else "edit_office"
        super().__init__(parent, title_key=title_key, min_width=460, icon="🏢", icon_bg="#EFF6FF")
        self._build_form()
        if office:
            self._populate(office)
        block_wheel_in(self)

    def _build_form(self):
        # الكود — مثل TR-01 / SY-01
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("TR-01")
        self.code_edit.setMaxLength(20)
        self.add_row(self._("office_code"), self.code_edit)

        # الاسم بالعربي
        self.name_ar_edit = QLineEdit()
        self.name_ar_edit.setPlaceholderText(self._("office_name_ar_hint"))
        self.add_row(self._("arabic_name"), self.name_ar_edit)

        # الاسم بالإنجليزي
        self.name_en_edit = QLineEdit()
        self.name_en_edit.setPlaceholderText("Turkey Office")
        self.add_row(self._("english_name"), self.name_en_edit)

        # الاسم بالتركي
        self.name_tr_edit = QLineEdit()
        self.name_tr_edit.setPlaceholderText("Türkiye Ofisi")
        self.add_row(self._("turkish_name"), self.name_tr_edit)

        # البلد
        self.country_combo = QComboBox()
        for code, label in _COUNTRIES:
            self.country_combo.addItem(label, code)
        self.add_row(self._("country"), self.country_combo)

        # المدينة
        self.city_edit = QLineEdit()
        self.city_edit.setPlaceholderText(self._("office_city_hint"))
        self.add_row(self._("city"), self.city_edit)

        # الترتيب
        self.sort_spin = QSpinBox()
        self.sort_spin.setRange(0, 999)
        self.sort_spin.setValue(0)
        self.add_row(self._("sort_order"), self.sort_spin)

        # ملاحظات
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(70)
        self.notes_edit.setPlaceholderText(self._("notes"))
        self.add_row(self._("notes"), self.notes_edit)

    def _populate(self, data: dict):
        self.code_edit.setText(data.get("code", ""))
        self.name_ar_edit.setText(data.get("name_ar", ""))
        self.name_en_edit.setText(data.get("name_en", "") or "")
        self.name_tr_edit.setText(data.get("name_tr", "") or "")
        self.city_edit.setText(data.get("city", "") or "")
        self.sort_spin.setValue(data.get("sort_order", 0) or 0)
        self.notes_edit.setPlainText(data.get("notes", "") or "")
        # البلد
        country = data.get("country", "") or ""
        for i in range(self.country_combo.count()):
            if self.country_combo.itemData(i) == country:
                self.country_combo.setCurrentIndex(i)
                break

    def get_data(self) -> dict:
        return {
            "code":       self.code_edit.text().strip().upper(),
            "name_ar":    self.name_ar_edit.text().strip(),
            "name_en":    self.name_en_edit.text().strip() or None,
            "name_tr":    self.name_tr_edit.text().strip() or None,
            "country":    self.country_combo.currentData() or None,
            "city":       self.city_edit.text().strip() or None,
            "sort_order": self.sort_spin.value(),
            "notes":      self.notes_edit.toPlainText().strip() or None,
        }

    def accept(self):
        data = self.get_data()
        errors = []
        if not data["code"]:
            errors.append(self._("office_code_required"))
        if not data["name_ar"]:
            errors.append(self._("arabic_name_required"))
        if errors:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, self._("invalid_data"), "\n".join(errors))
            return
        super().accept()