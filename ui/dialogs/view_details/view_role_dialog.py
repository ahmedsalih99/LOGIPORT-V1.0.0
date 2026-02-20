# -*- coding: utf-8 -*-
"""view_role_dialog.py — محسَّن"""
from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from ._view_helpers import _get

try:
    from database.crud.permissions_crud import get_role_permissions
except Exception:
    def get_role_permissions(role_id, language="ar"):
        return []


class ViewRoleDialog(BaseDialog):
    def __init__(self, role, current_user=None, parent=None):
        super().__init__(parent, user=current_user)
        self.role = role
        self.current_user = current_user
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()
        self.setWindowTitle(self._("role_details"))
        self.resize(480, 560)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        view = BaseDetailsView(self)

        role_id = _get(self.role, "id")
        perms   = get_role_permissions(role_id, language=self._lang) if role_id else []

        # ══ القسم 1: معلومات الدور ══
        view.begin_section("role_info", icon="🎭")
        view.add_row("role",
                     _get(self.role, "label_ar") or _get(self.role, "label_en") or _get(self.role, "name", ""),
                     icon="🏷️")
        view.add_row("internal_name", _get(self.role, "name", ""), icon="🔤")
        desc = _get(self.role, "description", "")
        if desc:
            view.add_row("description", desc, icon="📝", copyable=False)
        view.add_row("permissions_count", str(len(perms)), icon="🔐")

        # ══ القسم 2: الصلاحيات — مطوي افتراضياً ══
        if perms:
            sec = view.begin_section("permissions", icon="🔐", collapsed=False)
            if sec:
                for p in perms:
                    label = p.get("label") or p.get("code", "")
                    code  = p.get("code", "")
                    # كل صلاحية كصف: label | code
                    view.add_row(code, label, icon="•", copyable=False)

        layout.addWidget(view)

        btns = QHBoxLayout()
        btns.addStretch()
        btn = QPushButton(self._("close"))
        btn.setObjectName("secondary-btn")
        btn.clicked.connect(self.accept)
        btns.addWidget(btn)
        layout.addLayout(btns)
