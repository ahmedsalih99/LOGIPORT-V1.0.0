# -*- coding: utf-8 -*-
"""
view_office_dialog.py
=====================
نافذة عرض تفاصيل مكتب — قراءة فقط.
"""
from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout
from ._view_helpers import _get, _add_audit_section


class ViewOfficeDialog(BaseDialog):
    def __init__(self, office, current_user=None, parent=None):
        super().__init__(parent, user=current_user)
        self.office = office
        self.current_user = current_user
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()
        self.setWindowTitle(self._("office_details"))
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        view = BaseDetailsView(self)

        is_active = _get(self.office, "is_active", True)

        # القسم 1: معلومات أساسية
        view.begin_section("general_info", icon="🏢")
        view.add_row("office_code",  _get(self.office, "code"),    icon="🏷️")
        view.add_row("arabic_name",  _get(self.office, "name_ar"), icon="📛")
        view.add_row("english_name", _get(self.office, "name_en"), icon="📛")
        view.add_row("turkish_name", _get(self.office, "name_tr"), icon="📛")

        # القسم 2: موقع
        view.begin_section("location", icon="📍")
        view.add_row("country", _get(self.office, "country"), icon="🌍")
        view.add_row("city",    _get(self.office, "city"),    icon="🏙️")

        # القسم 3: حالة
        view.begin_section("status", icon="🟢")
        view.add_row(
            "status",
            self._("active") if is_active else self._("inactive"),
            icon="✅" if is_active else "⛔",
            is_badge=True,
        )
        view.add_row("sort_order", str(_get(self.office, "sort_order", 0)), icon="🔢")

        # ملاحظات
        notes = _get(self.office, "notes")
        if notes:
            view.begin_section("notes", icon="📝")
            view.add_row("notes", notes, icon="📝", copyable=False)

        # Audit للأدمن
        if is_admin(self.current_user):
            _add_audit_section(view, self.office, self._)

        layout.addWidget(view)

        # أزرار
        btns = QHBoxLayout()
        btns.addStretch()
        btn_close = QPushButton(self._("close"))
        btn_close.setObjectName("secondary-btn")
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)
        layout.addLayout(btns)