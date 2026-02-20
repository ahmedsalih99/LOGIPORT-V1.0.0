# -*- coding: utf-8 -*-
"""view_client_dialog.py — محسَّن"""
from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout
from ._view_helpers import _get, _name_by_lang, _add_audit_section
from ui.dialogs.client_contacts_dialog import ClientContactsDialog


class ViewClientDialog(BaseDialog):
    def __init__(self, client, current_user=None, parent=None):
        super().__init__(parent, user=current_user)
        self.client = client
        self.current_user = current_user
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()
        self.setWindowTitle(self._("client_details"))
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        view = BaseDetailsView(self)
        lang = self._lang

        # ── الاسم المترجم ──
        name = (_get(self.client, f"name_{lang}") or
                _get(self.client, "name_en") or
                _get(self.client, "name_ar") or
                _get(self.client, "name_tr") or "")

        # ── العنوان المترجم ──
        address = (_get(self.client, f"address_{lang}") or
                   _get(self.client, "address") or "")

        # ── الدولة ──
        country_label = _name_by_lang(_get(self.client, "country"), lang)

        # ── العملة ──
        cur = _get(self.client, "default_currency")
        cur_code = getattr(cur, "code", None) if cur else str(_get(self.client, "default_currency_id", "") or "")

        # ══ القسم 1: معلومات أساسية ══
        view.begin_section("general_info", icon="👤")
        view.add_row("name",    name,         icon="📛")
        view.add_row("code",    _get(self.client, "code"),  icon="🏷️")
        view.add_row("country", country_label, icon="🌍")
        view.add_row("city",    _get(self.client, "city"),  icon="🏙️")
        view.add_row("address", address,       icon="📍")

        # ══ القسم 2: تواصل ══
        view.begin_section("contact_info", icon="📞")
        view.add_row("phone",   _get(self.client, "phone"),   icon="📱")
        view.add_row("email",   _get(self.client, "email"),   icon="📧")
        view.add_row("website", _get(self.client, "website"), icon="🌐")

        # ══ القسم 3: مالي ══
        view.begin_section("financial_info", icon="💰")
        view.add_row("default_currency", cur_code,                     icon="💵", is_financial=True)
        view.add_row("tax_id",           _get(self.client, "tax_id"),  icon="🧾", is_financial=True)

        # ── ملاحظات ──
        notes = _get(self.client, "notes")
        if notes:
            view.begin_section("notes", icon="📝")
            view.add_row("notes", notes, icon="📝", copyable=False)

        # ── audit للأدمن ──
        if is_admin(self.current_user):
            _add_audit_section(view, self.client, self._)

        layout.addWidget(view)

        btns = QHBoxLayout()
        # Contacts button
        btn_contacts = QPushButton(f"👥 {self._("contacts")}")
        btn_contacts.setObjectName("secondary-btn")
        btn_contacts.clicked.connect(self._open_contacts)
        btns.addWidget(btn_contacts)
        btns.addStretch()
        btn = QPushButton(self._("close"))
        btn.setObjectName("secondary-btn")
        btn.clicked.connect(self.accept)
        btns.addWidget(btn)
        layout.addLayout(btns)

    def _open_contacts(self):
        dlg = ClientContactsDialog(self.client, parent=self)
        dlg.exec()