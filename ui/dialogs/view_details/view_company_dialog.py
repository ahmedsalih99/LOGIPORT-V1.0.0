# -*- coding: utf-8 -*-
"""view_company_dialog.py — محسَّن"""
from typing import List, Tuple, Optional

from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout
from ._view_helpers import _get, _name_by_lang, _add_audit_section
from ui.dialogs.company_banks_dialog import CompanyBanksDialog
from ui.dialogs.company_partners_dialog import CompanyPartnersDialog

try:
    from database.models import get_session_local
    from database.models.company import CompanyRoleLink, CompanyRole
except Exception:
    get_session_local = None
    CompanyRoleLink = CompanyRole = None


def _roles_for_company(company_id: Optional[int], lang: str) -> List[str]:
    """يجلب أدوار الشركة من DB حتى لو كانت الجلسة مغلقة."""
    out: List[str] = []
    if not company_id or not get_session_local or not CompanyRoleLink or not CompanyRole:
        return out
    try:
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            rows: List[Tuple] = (
                s.query(CompanyRole.name_ar, CompanyRole.name_en, CompanyRole.name_tr)
                 .join(CompanyRoleLink, CompanyRole.id == CompanyRoleLink.role_id)
                 .filter(CompanyRoleLink.company_id == company_id)
                 .order_by(CompanyRole.sort_order.asc(), CompanyRole.id.asc())
                 .all()
            )
        for nar, nen, ntr in rows:
            label = (nar if (lang == "ar" and nar) else
                     (ntr if (lang == "tr" and ntr) else (nen or nar or ntr)))
            if label:
                out.append(label)
    except Exception:
        pass
    return out


class ViewCompanyDialog(BaseDialog):
    def __init__(self, company, current_user=None, parent=None):
        super().__init__(parent, user=current_user)
        self.company = company
        self.current_user = current_user
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()
        self.setWindowTitle(self._("company_details"))
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        view = BaseDetailsView(self)
        lang = self._lang

        # ══ القسم 1: الأسماء ══
        view.begin_section("company_info", icon="🏢")
        view.add_row("arabic_name",  _get(self.company, "name_ar"), icon="🔤")
        view.add_row("english_name", _get(self.company, "name_en"), icon="🔤")
        view.add_row("turkish_name", _get(self.company, "name_tr"), icon="🔤")

        # ══ القسم 2: الموقع ══
        view.begin_section("location_info", icon="📍")
        country_label = _name_by_lang(_get(self.company, "country"), lang)
        # العنوان حسب اللغة مع fallback
        address = (_get(self.company, f"address_{lang}") or
                   _get(self.company, "address_en") or
                   _get(self.company, "address_ar") or "")
        view.add_row("country", country_label,                      icon="🌍")
        view.add_row("city",    _get(self.company, "city", ""),     icon="🏙️")
        view.add_row("address", address,                            icon="📌")

        # ══ القسم 3: تواصل ══
        view.begin_section("contact_info", icon="📞")
        view.add_row("phone",   _get(self.company, "phone",   ""), icon="📱")
        view.add_row("email",   _get(self.company, "email",   ""), icon="📧")
        view.add_row("website", _get(self.company, "website", ""), icon="🌐")

        # ══ القسم 4: أدوار + حالة ══
        view.begin_section("roles_status", icon="🎭")
        roles = _roles_for_company(_get(self.company, "id"), lang)
        view.add_row("roles", ", ".join(roles) if roles else None, icon="🏷️", copyable=False)

        is_active = _get(self.company, "is_active", True)
        view.add_row("status",
                     self._("active") if is_active else self._("inactive"),
                     icon="🟢" if is_active else "🔴",
                     is_badge=True)

        # ── audit للأدمن ──
        if is_admin(self.current_user):
            _add_audit_section(view, self.company, self._)

        layout.addWidget(view)

        btns = QHBoxLayout()
        btn_banks = QPushButton(f"🏦 {self._('bank_accounts')}")
        btn_banks.setObjectName("secondary-btn")
        btn_banks.clicked.connect(self._open_banks)
        btns.addWidget(btn_banks)

        btn_partners = QPushButton(f"🤝 {self._('partners')}")
        btn_partners.setObjectName("secondary-btn")
        btn_partners.clicked.connect(self._open_partners)
        btns.addWidget(btn_partners)

        btns.addStretch()
        btn = QPushButton(self._("close"))
        btn.setObjectName("secondary-btn")
        btn.clicked.connect(self.accept)
        btns.addWidget(btn)
        layout.addLayout(btns)

    def _open_banks(self):
        CompanyBanksDialog(self.company, parent=self).exec()

    def _open_partners(self):
        CompanyPartnersDialog(self.company, parent=self).exec()