# -*- coding: utf-8 -*-
"""view_packaging_type_dialog.py — محسَّن"""
from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout
from ._view_helpers import _add_audit_section


class ViewPackagingTypeDialog(BaseDialog):
    def __init__(self, packaging_type, current_user=None, parent=None):
        super().__init__(parent, user=current_user)
        self.packaging_type = packaging_type
        self.current_user = current_user
        self._ = TranslationManager.get_instance().translate
        self.setWindowTitle(self._("packaging_type_details"))
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        view = BaseDetailsView(self)

        view.begin_section("packaging_type_info", icon="📦")
        view.add_row("arabic_name",  getattr(self.packaging_type, "name_ar", None), icon="🔤")
        view.add_row("english_name", getattr(self.packaging_type, "name_en", None), icon="🔤")
        view.add_row("turkish_name", getattr(self.packaging_type, "name_tr", None), icon="🔤")

        if is_admin(self.current_user):
            _add_audit_section(view, self.packaging_type, self._)

        layout.addWidget(view)
        btns = QHBoxLayout()
        btns.addStretch()
        btn = QPushButton(self._("close"))
        btn.setObjectName("secondary-btn")
        btn.clicked.connect(self.accept)
        btns.addWidget(btn)
        layout.addLayout(btns)
