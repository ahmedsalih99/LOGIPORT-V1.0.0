# -*- coding: utf-8 -*-
"""
ui/dialogs/company_partners_dialog.py
=======================================
Dialog for managing company partners / shareholders.
"""
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDoubleSpinBox, QCheckBox, QComboBox,
    QFrame, QScrollArea, QWidget, QMessageBox,
)
from core.translator import TranslationManager
from database.crud.companies_crud import CompanyPartnersCRUD
from database.crud.clients_crud import ClientsCRUD


class _PartnerCard(QFrame):
    def __init__(self, link, crud, on_refresh, lang, parent=None):
        super().__init__(parent)
        self._link    = link
        self._crud    = crud
        self._refresh = on_refresh
        self._lang    = lang
        self._        = TranslationManager.get_instance().translate
        self._build()

    def _client_name(self):
        client = getattr(self._link, "partner_client", None)
        if client:
            return (getattr(client, f"name_{self._lang}", None) or
                    getattr(client, "name_en", None) or
                    getattr(client, "name_ar", None) or "")
        return str(self._link.client_id)

    def _build(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("contact-card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(4)

        hdr = QHBoxLayout()
        share = f" ({self._link.share_percent:.1f}%)" if self._link.share_percent else ""
        role  = f"  [{self._link.partner_role}]" if self._link.partner_role else ""
        status = "" if self._link.is_active else "  ⛔"
        lbl = QLabel(f"🤝 {self._client_name()}{role}{share}{status}")
        lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        hdr.addWidget(lbl)
        hdr.addStretch()

        self._btn_edit = QPushButton(self._("edit"))
        self._btn_edit.setObjectName("secondary-btn")
        self._btn_edit.setFixedWidth(72)
        self._btn_edit.clicked.connect(self._toggle_edit)
        hdr.addWidget(self._btn_edit)

        btn_del = QPushButton(self._("delete"))
        btn_del.setObjectName("danger-btn")
        btn_del.setFixedWidth(72)
        btn_del.clicked.connect(self._delete)
        hdr.addWidget(btn_del)
        outer.addLayout(hdr)

        # Edit form
        self._form = QWidget()
        fl = QVBoxLayout(self._form)
        fl.setContentsMargins(0, 6, 0, 0)
        fl.setSpacing(4)

        def _row(key, widget):
            row = QHBoxLayout()
            lbl2 = QLabel(self._(key) + ":")
            lbl2.setFixedWidth(120)
            row.addWidget(lbl2)
            row.addWidget(widget)
            fl.addLayout(row)

        self._e_role = QLineEdit(self._link.partner_role or "")
        self._e_share = QDoubleSpinBox()
        self._e_share.setRange(0, 100); self._e_share.setSuffix("%")
        self._e_share.setValue(self._link.share_percent or 0.0)
        self._e_notes = QLineEdit(self._link.notes or "")
        self._chk_active = QCheckBox(self._("active"))
        self._chk_active.setChecked(bool(self._link.is_active))

        _row("partner_role",  self._e_role)
        _row("share_percent", self._e_share)
        _row("notes",         self._e_notes)
        fl.addWidget(self._chk_active)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(self._("cancel"))
        btn_cancel.setObjectName("secondary-btn")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(self._toggle_edit)
        btn_save = QPushButton(self._("save"))
        btn_save.setObjectName("primary-btn")
        btn_save.setFixedWidth(80)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        fl.addLayout(btn_row)

        self._form.setVisible(False)
        outer.addWidget(self._form)

    def _toggle_edit(self):
        vis = not self._form.isVisible()
        self._form.setVisible(vis)
        self._btn_edit.setText(self._("cancel") if vis else self._("edit"))

    def _save(self):
        self._crud.update_partner(self._link.id, {
            "partner_role":  self._e_role.text().strip() or None,
            "share_percent": self._e_share.value() or None,
            "notes":         self._e_notes.text().strip() or None,
            "is_active":     self._chk_active.isChecked(),
        })
        self._refresh()

    def _delete(self):
        if QMessageBox.question(
            self, self._("confirm_delete"),
            self._("confirm_delete_partner"),
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            self._crud.delete_partner(self._link.id)
            self._refresh()


class _AddPartnerForm(QFrame):
    def __init__(self, company_id, crud, on_refresh, lang, parent=None):
        super().__init__(parent)
        self._company_id = company_id
        self._crud       = crud
        self._refresh    = on_refresh
        self._lang       = lang
        self._clients    = []
        self._           = TranslationManager.get_instance().translate
        self._build()
        self._load_clients()

    def _build(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("add-contact-form")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title = QLabel(f"➕ {self._('add_partner')}")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        def _row(key, widget):
            row = QHBoxLayout()
            lbl = QLabel(self._(key) + ":")
            lbl.setFixedWidth(120)
            row.addWidget(lbl)
            row.addWidget(widget)
            layout.addLayout(row)

        self._cmb_client = QComboBox()
        self._cmb_client.setEditable(True)
        self._e_role  = QLineEdit()
        self._e_share = QDoubleSpinBox()
        self._e_share.setRange(0, 100); self._e_share.setSuffix("%")

        _row("client",        self._cmb_client)
        _row("partner_role",  self._e_role)
        _row("share_percent", self._e_share)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn = QPushButton(self._("add_partner"))
        btn.setObjectName("primary-btn")
        btn.setFixedWidth(120)
        btn.clicked.connect(self._add)
        btn_row.addWidget(btn)
        layout.addLayout(btn_row)

    def _load_clients(self):
        self._clients = ClientsCRUD().list_clients()
        self._cmb_client.clear()
        for c in self._clients:
            name = (getattr(c, f"name_{self._lang}", None) or
                    getattr(c, "name_en", None) or
                    getattr(c, "name_ar", None) or "")
            self._cmb_client.addItem(f"{name} ({getattr(c,'code','')})", c.id)

    def _add(self):
        client_id = self._cmb_client.currentData()
        if not client_id:
            QMessageBox.warning(self, self._("error"), self._("client_required"))
            return
        self._crud.add_partner(
            self._company_id,
            client_id,
            partner_role=self._e_role.text().strip() or None,
            share_percent=self._e_share.value() or None,
        )
        self._e_role.clear()
        self._e_share.setValue(0)
        self._refresh()


class CompanyPartnersDialog(QDialog):
    """Dialog for managing company shareholders/partners."""

    def __init__(self, company, parent=None):
        super().__init__(parent)
        self._company = company
        self._crud    = CompanyPartnersCRUD()
        self._        = TranslationManager.get_instance().translate
        self._lang    = TranslationManager.get_instance().get_current_language()

        name = (getattr(company, f"name_{self._lang}", None) or
                getattr(company, "name_en", None) or
                getattr(company, "name_ar", None) or
                str(getattr(company, "id", "")))
        self.setWindowTitle(f"🤝 {self._('partners')} — {name}")
        self.resize(540, 520)
        self._build()
        self._load()

    def _get_id(self):
        return getattr(self._company, "id", None) or (
            self._company.get("id") if isinstance(self._company, dict) else None
        )

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setSpacing(6)
        self._cards_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self._cards_widget)
        layout.addWidget(scroll, stretch=1)

        self._add_form = _AddPartnerForm(self._get_id(), self._crud, self._load, self._lang)
        layout.addWidget(self._add_form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(self._("close"))
        btn_close.setObjectName("secondary-btn")
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _load(self):
        partners = self._crud.list_partners(self._get_id())

        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if not partners:
            lbl = QLabel(self._("no_partners"))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #94A3B8; padding: 20px;")
            self._cards_layout.addWidget(lbl)
        else:
            for p in partners:
                self._cards_layout.addWidget(_PartnerCard(p, self._crud, self._load, self._lang))
