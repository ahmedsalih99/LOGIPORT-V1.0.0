# -*- coding: utf-8 -*-
"""
ui/dialogs/company_banks_dialog.py
====================================
Dialog for managing company bank accounts — add, edit, delete, set primary.
"""
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QFrame, QScrollArea, QWidget,
    QMessageBox,
)
from core.translator import TranslationManager
from database.crud.companies_crud import CompanyBanksCRUD


class _BankCard(QFrame):
    """Inline expandable card for one bank account."""

    def __init__(self, bank, crud: CompanyBanksCRUD, on_refresh, parent=None):
        super().__init__(parent)
        self._bank    = bank
        self._crud    = crud
        self._refresh = on_refresh
        self._        = TranslationManager.get_instance().translate
        self._build()

    def _build(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("contact-card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(4)

        # Header row
        hdr = QHBoxLayout()
        star  = "⭐ " if self._bank.is_primary else "🏦 "
        title = self._bank.bank_name or self._("unnamed_bank")
        if self._bank.iban:
            title += f"  ·  {self._bank.iban}"
        lbl = QLabel(f"{star}{title}")
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

        # Quick info line
        parts = []
        if self._bank.swift_bic:    parts.append(f"SWIFT: {self._bank.swift_bic}")
        if self._bank.account_number: parts.append(f"ACC: {self._bank.account_number}")
        if self._bank.beneficiary_name: parts.append(f"📋 {self._bank.beneficiary_name}")
        if parts:
            info = QLabel("   ".join(parts))
            info.setStyleSheet("color: #64748B; font-size: 11px;")
            outer.addWidget(info)

        # Edit form (hidden)
        self._form = QWidget()
        fl = QVBoxLayout(self._form)
        fl.setContentsMargins(0, 6, 0, 0)
        fl.setSpacing(4)

        def _row(key, widget):
            row = QHBoxLayout()
            lbl2 = QLabel(self._(key) + ":")
            lbl2.setFixedWidth(130)
            row.addWidget(lbl2)
            row.addWidget(widget)
            fl.addLayout(row)

        self._e_bank    = QLineEdit(self._bank.bank_name or "")
        self._e_branch  = QLineEdit(self._bank.branch or "")
        self._e_benef   = QLineEdit(self._bank.beneficiary_name or "")
        self._e_iban    = QLineEdit(self._bank.iban or "")
        self._e_swift   = QLineEdit(self._bank.swift_bic or "")
        self._e_acc     = QLineEdit(self._bank.account_number or "")
        self._e_notes   = QLineEdit(self._bank.notes or "")
        self._chk_prim  = QCheckBox(self._("primary_account"))
        self._chk_prim.setChecked(bool(self._bank.is_primary))

        _row("bank_name",         self._e_bank)
        _row("branch",            self._e_branch)
        _row("beneficiary_name",  self._e_benef)
        _row("iban",              self._e_iban)
        _row("swift_bic",         self._e_swift)
        _row("account_number",    self._e_acc)
        _row("notes",             self._e_notes)
        fl.addWidget(self._chk_prim)

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
        self._crud.update_bank(self._bank.id, {
            "bank_name":       self._e_bank.text().strip() or None,
            "branch":          self._e_branch.text().strip() or None,
            "beneficiary_name": self._e_benef.text().strip() or None,
            "iban":            self._e_iban.text().strip() or None,
            "swift_bic":       self._e_swift.text().strip() or None,
            "account_number":  self._e_acc.text().strip() or None,
            "notes":           self._e_notes.text().strip() or None,
            "is_primary":      self._chk_prim.isChecked(),
        })
        self._refresh()

    def _delete(self):
        if QMessageBox.question(
            self, self._("confirm_delete"),
            self._("confirm_delete_bank"),
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            self._crud.delete_bank(self._bank.id)
            self._refresh()


class _AddBankForm(QFrame):
    def __init__(self, company_id: int, crud: CompanyBanksCRUD, on_refresh, parent=None):
        super().__init__(parent)
        self._company_id = company_id
        self._crud       = crud
        self._refresh    = on_refresh
        self._           = TranslationManager.get_instance().translate
        self._build()

    def _build(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("add-contact-form")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title = QLabel(f"➕ {self._('add_bank_account')}")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        def _row(key, widget):
            row = QHBoxLayout()
            lbl = QLabel(self._(key) + ":")
            lbl.setFixedWidth(130)
            row.addWidget(lbl)
            row.addWidget(widget)
            layout.addLayout(row)

        self._e_bank   = QLineEdit()
        self._e_benef  = QLineEdit()
        self._e_iban   = QLineEdit()
        self._e_swift  = QLineEdit()
        self._e_acc    = QLineEdit()
        self._chk_prim = QCheckBox(self._("primary_account"))

        _row("bank_name",        self._e_bank)
        _row("beneficiary_name", self._e_benef)
        _row("iban",             self._e_iban)
        _row("swift_bic",        self._e_swift)
        _row("account_number",   self._e_acc)
        layout.addWidget(self._chk_prim)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn = QPushButton(self._("add_bank_account"))
        btn.setObjectName("primary-btn")
        btn.setFixedWidth(140)
        btn.clicked.connect(self._add)
        btn_row.addWidget(btn)
        layout.addLayout(btn_row)

    def _add(self):
        self._crud.add_bank(self._company_id, {
            "bank_name":       self._e_bank.text().strip() or None,
            "beneficiary_name": self._e_benef.text().strip() or None,
            "iban":            self._e_iban.text().strip() or None,
            "swift_bic":       self._e_swift.text().strip() or None,
            "account_number":  self._e_acc.text().strip() or None,
            "is_primary":      self._chk_prim.isChecked(),
        })
        self._e_bank.clear(); self._e_benef.clear()
        self._e_iban.clear(); self._e_swift.clear()
        self._e_acc.clear();  self._chk_prim.setChecked(False)
        self._refresh()


class CompanyBanksDialog(QDialog):
    """Full dialog for managing company bank accounts."""

    def __init__(self, company, parent=None):
        super().__init__(parent)
        self._company = company
        self._crud    = CompanyBanksCRUD()
        self._        = TranslationManager.get_instance().translate

        lang = TranslationManager.get_instance().get_current_language()
        name = (getattr(company, f"name_{lang}", None) or
                getattr(company, "name_en", None) or
                getattr(company, "name_ar", None) or
                str(getattr(company, "id", "")))
        self.setWindowTitle(f"🏦 {self._('bank_accounts')} — {name}")
        self.resize(540, 560)
        self._build()
        self._load()

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

        cid = getattr(self._company, "id", None) or (self._company.get("id") if isinstance(self._company, dict) else None)
        self._add_form = _AddBankForm(cid, self._crud, self._load)
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
        cid = getattr(self._company, "id", None) or (self._company.get("id") if isinstance(self._company, dict) else None)
        banks = self._crud.list_banks(cid)

        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if not banks:
            lbl = QLabel(self._("no_bank_accounts"))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #94A3B8; padding: 20px;")
            self._cards_layout.addWidget(lbl)
        else:
            for bank in banks:
                self._cards_layout.addWidget(_BankCard(bank, self._crud, self._load))
