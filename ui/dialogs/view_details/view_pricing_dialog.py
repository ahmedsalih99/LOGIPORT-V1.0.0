# -*- coding: utf-8 -*-
"""view_pricing_dialog.py — محسَّن"""
from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout
from ._view_helpers import _get, _name_by_lang, _add_audit_section


class ViewPricingDialog(BaseDialog):
    def __init__(self, pricing, current_user=None, parent=None):
        super().__init__(parent, user=current_user)
        self.pricing = pricing
        self.current_user = current_user
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()
        self.setWindowTitle(self._("pricing_details"))
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        view = BaseDetailsView(self)
        lang = self._lang

        seller   = _name_by_lang(_get(self.pricing, "seller_company"),  lang)
        buyer    = _name_by_lang(_get(self.pricing, "buyer_company"),   lang)
        material = _name_by_lang(_get(self.pricing, "material"),        lang)
        ptype    = _get(self.pricing, "pricing_type")
        ptype_label = (_name_by_lang(ptype, lang) or
                       getattr(ptype, "code", "")) if ptype else ""
        cur = _get(self.pricing, "currency")
        cur_code = getattr(cur, "code", "") if cur else ""
        dm = _get(self.pricing, "delivery_method")
        dm_label = _name_by_lang(dm, lang) if dm else str(_get(self.pricing, "delivery_method_id", "") or "")

        # ══ القسم 1: الأطراف والمادة ══
        view.begin_section("parties", icon="👥")
        view.add_row("seller_company", seller,   icon="🏭")
        view.add_row("buyer_company",  buyer,    icon="🏢")
        view.add_row("material",       material, icon="🧪")

        # ══ القسم 2: التسعير — is_financial ══
        view.begin_section("financial_info", icon="💰")
        price = _get(self.pricing, "price")
        price_fmt = f"{float(price):,.4f} {cur_code}".strip() if price not in (None, "") else None
        view.add_row("pricing_type",     ptype_label, icon="📊", is_financial=True)
        view.add_row("price",            price_fmt,   icon="💵", is_financial=True)
        view.add_row("currency",         cur_code,    icon="💲", is_financial=True)
        view.add_row("delivery_method",  dm_label,    icon="🚚")

        # status badge
        is_active = _get(self.pricing, "is_active", True)
        view.add_row("status",
                     self._("active") if is_active else self._("inactive"),
                     icon="🟢" if is_active else "🔴",
                     is_badge=True)

        notes = _get(self.pricing, "notes")
        if notes:
            view.begin_section("notes", icon="📝")
            view.add_row("notes", notes, icon="📝", copyable=False)

        # ── audit للأدمن ──
        if is_admin(self.current_user):
            _add_audit_section(view, self.pricing, self._)

        layout.addWidget(view)

        btns = QHBoxLayout()
        btns.addStretch()
        btn = QPushButton(self._("close"))
        btn.setObjectName("secondary-btn")
        btn.clicked.connect(self.accept)
        btns.addWidget(btn)
        layout.addLayout(btns)
