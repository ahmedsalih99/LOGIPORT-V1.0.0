# -*- coding: utf-8 -*-
"""view_user_dialog.py — محسَّن"""
from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout
from ._view_helpers import _get, _add_audit_section


class ViewUserDialog(BaseDialog):
    def __init__(self, user, current_user=None, parent=None):
        super().__init__(parent, user=current_user)
        self.user_obj = user
        self.current_user = current_user
        self._ = TranslationManager.get_instance().translate
        self.setWindowTitle(self._("user_details"))
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        view = BaseDetailsView(self)

        # ── معلومات المستخدم ──
        view.begin_section("user_info", icon="👤")
        view.add_row("username",  _get(self.user_obj, "username"),  icon="👤")
        view.add_row("full_name", _get(self.user_obj, "full_name"), icon="📛")
        view.add_row("role",
                     _get(self.user_obj, "role_label",
                          _get(self.user_obj, "role")),
                     icon="🎭")

        # status كـ badge
        is_active = _get(self.user_obj, "is_active", False)
        status_val = "active" if is_active else "inactive"
        view.add_row("status",
                     self._(status_val),
                     icon="🟢" if is_active else "🔴",
                     is_badge=True)

        # ── audit للأدمن ──
        if is_admin(self.current_user):
            _add_audit_section(view, self.user_obj, self._)

        layout.addWidget(view)

        btns = QHBoxLayout()
        btns.addStretch()
        btn = QPushButton(self._("close"))
        btn.setObjectName("secondary-btn")
        btn.clicked.connect(self.accept)
        btns.addWidget(btn)
        layout.addLayout(btns)
