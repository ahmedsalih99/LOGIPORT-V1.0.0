# -*- coding: utf-8 -*-
"""
view_delivery_method_dialog.py — محسَّن
"""
from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout
from ._view_helpers import _add_audit_section


class ViewDeliveryMethodDialog(BaseDialog):
    def __init__(self, delivery_method, current_user=None, parent=None):
        super().__init__(parent, user=current_user)
        self.delivery_method = delivery_method
        self.current_user = current_user
        self._ = TranslationManager.get_instance().translate
        self.setWindowTitle(self._("delivery_method_details"))
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        view = BaseDetailsView(self)

        view.begin_section("delivery_method_info", icon="🚚")
        view.add_row("arabic_name",  getattr(self.delivery_method, "name_ar", None), icon="🔤")
        view.add_row("english_name", getattr(self.delivery_method, "name_en", None), icon="🔤")
        view.add_row("turkish_name", getattr(self.delivery_method, "name_tr", None), icon="🔤")

        if is_admin(self.current_user):
            _add_audit_section(view, self.delivery_method, self._)

        layout.addWidget(view)
        self._add_close_btn(layout)

    def _add_close_btn(self, layout):
        btns = QHBoxLayout()
        btns.addStretch()
        btn = QPushButton(self._("close"))
        btn.setObjectName("secondary-btn")
        btn.clicked.connect(self.accept)
        btns.addWidget(btn)
        layout.addLayout(btns)
