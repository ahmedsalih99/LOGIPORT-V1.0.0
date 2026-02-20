# -*- coding: utf-8 -*-
"""view_material_dialog.py — محسَّن"""
from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout
from ._view_helpers import _get, _name_by_lang, _add_audit_section


class ViewMaterialDialog(BaseDialog):
    def __init__(self, material, current_user=None, parent=None):
        super().__init__(parent, user=current_user)
        self.material = material
        self.current_user = current_user
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()
        self.setWindowTitle(self._("material_details"))
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        view = BaseDetailsView(self)
        lang = self._lang

        # ── بيانات ──
        mt_label  = _name_by_lang(_get(self.material, "material_type"), lang)
        cur       = _get(self.material, "currency")
        cur_code  = getattr(cur, "code", None) if cur else str(_get(self.material, "currency_id", "") or "")
        ep        = _get(self.material, "estimated_price")

        # ══ القسم 1: الأسماء ══
        view.begin_section("material_info", icon="🧪")
        view.add_row("code",          _get(self.material, "code"),    icon="🏷️")
        view.add_row("arabic_name",   _get(self.material, "name_ar"), icon="🔤")
        view.add_row("english_name",  _get(self.material, "name_en"), icon="🔤")
        view.add_row("turkish_name",  _get(self.material, "name_tr"), icon="🔤")
        view.add_row("material_type", mt_label,                        icon="🗂️")

        # ══ القسم 2: السعر ══
        view.begin_section("financial_info", icon="💰")
        ep_txt = f"{float(ep):,.3f}" if ep not in (None, "") else None
        view.add_row("estimated_price", ep_txt,   icon="💵", is_financial=True)
        view.add_row("currency",        cur_code, icon="💲", is_financial=True)

        # ── audit للأدمن ──
        if is_admin(self.current_user):
            _add_audit_section(view, self.material, self._)

        layout.addWidget(view)

        btns = QHBoxLayout()
        btns.addStretch()
        btn = QPushButton(self._("close"))
        btn.setObjectName("secondary-btn")
        btn.clicked.connect(self.accept)
        btns.addWidget(btn)
        layout.addLayout(btns)
