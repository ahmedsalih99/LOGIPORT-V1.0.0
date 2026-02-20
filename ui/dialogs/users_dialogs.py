# -*- coding: utf-8 -*-
"""
ui/dialogs/users_dialogs.py
============================
Enhanced Add/Edit User dialog with:
  - Password confirmation field
  - Password strength indicator
  - Active/inactive toggle
  - Consistent styling with base dialog
"""
from core.base_dialog import BaseDialog
from ui.widgets.custom_button import CustomButton
from PySide6.QtWidgets import (
    QVBoxLayout, QLineEdit, QLabel, QComboBox,
    QHBoxLayout, QCheckBox, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from core.translator import TranslationManager
from database.crud.permissions_crud import RolesCRUD


from utils.password_utils import password_strength as _password_strength


class UserDialog(BaseDialog):
    def __init__(self, user=None, parent=None):
        super().__init__(parent=parent)
        self.user = user or {}
        self.roles = []
        self.init_ui()
        self.retranslate_ui()
        self.load_roles()
        self.load_user_data()
        TranslationManager.get_instance().language_changed.connect(self.on_language_change)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        def _field_row(label_widget, input_widget):
            layout.addWidget(label_widget)
            layout.addWidget(input_widget)

        # Username
        self.lbl_username = QLabel()
        self.edit_username = QLineEdit()
        self.edit_username.setObjectName("form-input")
        _field_row(self.lbl_username, self.edit_username)

        # Full name
        self.lbl_fullname = QLabel()
        self.edit_fullname = QLineEdit()
        self.edit_fullname.setObjectName("form-input")
        _field_row(self.lbl_fullname, self.edit_fullname)

        # Password
        self.lbl_password = QLabel()
        self.edit_password = QLineEdit()
        self.edit_password.setEchoMode(QLineEdit.Password)
        self.edit_password.setObjectName("form-input")
        self.edit_password.textChanged.connect(self._on_password_changed)
        _field_row(self.lbl_password, self.edit_password)

        # Password strength indicator
        self.lbl_strength = QLabel()
        self.lbl_strength.setStyleSheet("font-size: 11px; padding: 0 2px;")
        layout.addWidget(self.lbl_strength)

        # Password confirm (only for new users)
        self.lbl_confirm = QLabel()
        self.edit_confirm = QLineEdit()
        self.edit_confirm.setEchoMode(QLineEdit.Password)
        self.edit_confirm.setObjectName("form-input")
        self.edit_confirm.textChanged.connect(self._on_confirm_changed)
        _field_row(self.lbl_confirm, self.edit_confirm)

        # Match indicator
        self.lbl_match = QLabel()
        self.lbl_match.setStyleSheet("font-size: 11px; padding: 0 2px;")
        layout.addWidget(self.lbl_match)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        layout.addWidget(sep)

        # Role
        self.lbl_role = QLabel()
        self.combo_role = QComboBox()
        self.combo_role.setObjectName("form-input")
        _field_row(self.lbl_role, self.combo_role)

        # Active checkbox
        self.chk_active = QCheckBox()
        self.chk_active.setChecked(True)
        layout.addWidget(self.chk_active)

        # Buttons
        row_btn = QHBoxLayout()
        row_btn.addStretch()
        self.btn_cancel = CustomButton(self._("cancel"))
        self.btn_cancel.setObjectName("secondary-btn")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = CustomButton(self._("save"))
        self.btn_save.clicked.connect(self.accept)
        row_btn.addWidget(self.btn_cancel)
        row_btn.addWidget(self.btn_save)
        layout.addLayout(row_btn)

        self.setLayout(layout)
        self.setMinimumWidth(360)

    def _on_password_changed(self, text: str):
        if not text:
            self.lbl_strength.setText("")
            return
        key, color = _password_strength(text)
        self.lbl_strength.setText(f"  {self._(key)}")
        self.lbl_strength.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
        self._on_confirm_changed(self.edit_confirm.text())

    def _on_confirm_changed(self, text: str):
        pw = self.edit_password.text()
        if not pw or not text:
            self.lbl_match.setText("")
            return
        if pw == text:
            self.lbl_match.setText("  ✓ " + self._("passwords_match"))
            self.lbl_match.setStyleSheet("color: #10B981; font-size: 11px; font-weight: bold;")
        else:
            self.lbl_match.setText("  ✗ " + self._("passwords_no_match"))
            self.lbl_match.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: bold;")

    def load_roles(self):
        lang = TranslationManager.get_instance().get_current_language()
        self.roles = RolesCRUD().get_all(language=lang)
        self.combo_role.clear()
        for role in self.roles:
            self.combo_role.addItem(role["label"], role["id"])

    def load_user_data(self):
        is_edit = bool(self.user.get("username"))
        if is_edit:
            self.edit_username.setText(self.user.get("username", ""))
            self.edit_fullname.setText(self.user.get("full_name", ""))
            self.edit_username.setReadOnly(True)
            self.edit_password.setPlaceholderText(self._("leave_blank_to_keep"))
            # In edit mode, confirm field can be hidden since password is optional
            self.edit_confirm.setPlaceholderText(self._("leave_blank_to_keep"))
            self.chk_active.setChecked(bool(self.user.get("is_active", True)))
            # Set role
            role_id = self.user.get("role_id") or self.user.get("role")
            if role_id:
                idx = self.combo_role.findData(role_id)
                if idx >= 0:
                    self.combo_role.setCurrentIndex(idx)
        else:
            self.edit_username.setReadOnly(False)
            for w in (self.edit_username, self.edit_fullname,
                      self.edit_password, self.edit_confirm):
                w.clear()
            self.combo_role.setCurrentIndex(0)
            self.chk_active.setChecked(True)

    def retranslate_ui(self):
        self.set_translated_title("add_edit_user")
        self.lbl_username.setText(self._("username") + " *")
        self.lbl_fullname.setText(self._("full_name"))
        self.lbl_password.setText(
            self._("password") + (" *" if not self.user.get("username") else "")
        )
        self.lbl_confirm.setText(self._("confirm_password"))
        self.lbl_role.setText(self._("role"))
        self.chk_active.setText(self._("active"))
        self.btn_save.setText(self._("save"))
        self.btn_cancel.setText(self._("cancel"))

    def on_language_change(self):
        self.retranslate_ui()
        self.load_roles()
        self.load_user_data()

    def get_data(self):
        return {
            "username":  self.edit_username.text().strip(),
            "full_name": self.edit_fullname.text().strip(),
            "password":  self.edit_password.text(),
            "role":      self.combo_role.currentData(),
            "is_active": self.chk_active.isChecked(),
        }

    def accept(self):
        data = self.get_data()
        is_new = not self.user.get("username")

        # Validate username
        if not data["username"]:
            self.show_error("error", "must_fill_username_password")
            return

        # Validate password for new users
        if is_new:
            if not data["password"]:
                self.show_error("error", "must_fill_username_password")
                return
            # Validate confirm matches
            if data["password"] != self.edit_confirm.text():
                self.show_error("error", "passwords_no_match")
                return

        # If editing with new password, confirm must also match
        if not is_new and data["password"]:
            if data["password"] != self.edit_confirm.text():
                self.show_error("error", "passwords_no_match")
                return

        super().accept()