# -*- coding: utf-8 -*-
"""
ui/dialogs/client_contacts_dialog.py
======================================
Dialog for managing client contacts (add / edit / delete / set primary).
"""
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QFrame, QScrollArea, QWidget,
    QMessageBox, QSizePolicy,
)
from core.translator import TranslationManager
from database.crud.clients_crud import ClientContactsCRUD


# ── small single-contact form card ───────────────────────────────────────────

class _ContactCard(QFrame):
    """Inline expandable card showing one contact."""

    def __init__(self, contact, crud: ClientContactsCRUD,
                 on_refresh, lang: str, parent=None):
        super().__init__(parent)
        self._contact = contact
        self._crud    = crud
        self._refresh = on_refresh
        self._lang    = lang
        self._ = TranslationManager.get_instance().translate
        self._build()

    def _build(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("contact-card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(4)

        # ── header row ──
        hdr = QHBoxLayout()
        primary_star = "⭐ " if self._contact.is_primary else ""
        name  = self._contact.name or ""
        role  = f"  [{self._contact.role_title}]" if self._contact.role_title else ""
        lbl   = QLabel(f"{primary_star}{name}{role}")
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

        # ── quick info ──
        info_parts = []
        if self._contact.phone: info_parts.append(f"📱 {self._contact.phone}")
        if self._contact.email: info_parts.append(f"📧 {self._contact.email}")
        if info_parts:
            info = QLabel("   ".join(info_parts))
            info.setStyleSheet("color: #64748B; font-size: 11px;")
            outer.addWidget(info)

        # ── edit form (hidden by default) ──
        self._form = QWidget()
        fl = QVBoxLayout(self._form)
        fl.setContentsMargins(0, 6, 0, 0)
        fl.setSpacing(4)

        def _row(label_key, widget):
            row = QHBoxLayout()
            lbl2 = QLabel(self._(label_key) + ":")
            lbl2.setFixedWidth(100)
            row.addWidget(lbl2)
            row.addWidget(widget)
            fl.addLayout(row)

        self._e_name  = QLineEdit(self._contact.name or "")
        self._e_role  = QLineEdit(self._contact.role_title or "")
        self._e_phone = QLineEdit(self._contact.phone or "")
        self._e_email = QLineEdit(self._contact.email or "")
        self._e_notes = QLineEdit(self._contact.notes or "")
        self._chk_primary = QCheckBox(self._("primary_contact"))
        self._chk_primary.setChecked(bool(self._contact.is_primary))

        _row("name",       self._e_name)
        _row("role_title", self._e_role)
        _row("phone",      self._e_phone)
        _row("email",      self._e_email)
        _row("notes",      self._e_notes)
        fl.addWidget(self._chk_primary)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = QPushButton(self._("save"))
        btn_save.setObjectName("primary-btn")
        btn_save.setFixedWidth(80)
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton(self._("cancel"))
        btn_cancel.setObjectName("secondary-btn")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(self._toggle_edit)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        fl.addLayout(btn_row)

        self._form.setVisible(False)
        outer.addWidget(self._form)

    def _toggle_edit(self):
        visible = not self._form.isVisible()
        self._form.setVisible(visible)
        self._btn_edit.setText(self._("cancel") if visible else self._("edit"))

    def _save(self):
        name = self._e_name.text().strip()
        if not name:
            QMessageBox.warning(self, self._("error"), self._("name_required"))
            return
        self._crud.update_contact(
            self._contact.id,
            name=name,
            role_title=self._e_role.text().strip() or None,
            phone=self._e_phone.text().strip() or None,
            email=self._e_email.text().strip() or None,
            notes=self._e_notes.text().strip() or None,
            is_primary=self._chk_primary.isChecked(),
        )
        self._refresh()

    def _delete(self):
        if QMessageBox.question(
            self, self._("confirm_delete"),
            self._("confirm_delete_contact"),
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            self._crud.delete_contact(self._contact.id)
            self._refresh()


# ── add contact form ──────────────────────────────────────────────────────────

class _AddContactForm(QFrame):
    def __init__(self, client_id: int, crud: ClientContactsCRUD, on_refresh, parent=None):
        super().__init__(parent)
        self._client_id = client_id
        self._crud      = crud
        self._refresh   = on_refresh
        self._ = TranslationManager.get_instance().translate
        self._build()

    def _build(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("add-contact-form")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title = QLabel(f"➕ {self._('add_contact')}")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        def _row(label_key, widget):
            row = QHBoxLayout()
            lbl = QLabel(self._(label_key) + ":")
            lbl.setFixedWidth(100)
            row.addWidget(lbl)
            row.addWidget(widget)
            layout.addLayout(row)

        self._name  = QLineEdit(); self._name.setPlaceholderText(self._("required"))
        self._role  = QLineEdit()
        self._phone = QLineEdit()
        self._email = QLineEdit()
        self._notes = QLineEdit()
        self._primary = QCheckBox(self._("primary_contact"))

        _row("name",       self._name)
        _row("role_title", self._role)
        _row("phone",      self._phone)
        _row("email",      self._email)
        _row("notes",      self._notes)
        layout.addWidget(self._primary)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn = QPushButton(self._("add_contact"))
        btn.setObjectName("primary-btn")
        btn.setFixedWidth(120)
        btn.clicked.connect(self._add)
        btn_row.addWidget(btn)
        layout.addLayout(btn_row)

    def _add(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, self._("error"), self._("name_required"))
            return
        self._crud.add_contact(
            client_id=self._client_id,
            name=name,
            role_title=self._role.text().strip() or None,
            phone=self._phone.text().strip() or None,
            email=self._email.text().strip() or None,
            notes=self._notes.text().strip() or None,
            is_primary=self._primary.isChecked(),
        )
        self._name.clear()
        self._role.clear()
        self._phone.clear()
        self._email.clear()
        self._notes.clear()
        self._primary.setChecked(False)
        self._refresh()


# ── main dialog ───────────────────────────────────────────────────────────────

class ClientContactsDialog(QDialog):
    """Full-featured dialog for managing contacts of one client."""

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self._client = client
        self._crud   = ClientContactsCRUD()
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()

        client_name = (
            getattr(client, f"name_{self._lang}", None)
            or getattr(client, "name_en", None)
            or getattr(client, "name_ar", None)
            or str(getattr(client, "id", ""))
        )
        self.setWindowTitle(f"{self._('contacts')} — {client_name}")
        self.resize(520, 560)
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # scroll area for contact cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setSpacing(6)
        self._cards_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self._cards_widget)
        layout.addWidget(scroll, stretch=1)

        # add-contact form
        self._add_form = _AddContactForm(
            self._client.id if hasattr(self._client, "id") else self._client.get("id"),
            self._crud, self._load
        )
        layout.addWidget(self._add_form)

        # close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(self._("close"))
        btn_close.setObjectName("secondary-btn")
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _load(self):
        """Reload contacts from DB and rebuild cards."""
        client_id = (
            self._client.id if hasattr(self._client, "id")
            else self._client.get("id")
        )
        contacts = self._crud.list_contacts(client_id)

        # Clear old cards
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not contacts:
            lbl = QLabel(self._("no_contacts_yet"))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #94A3B8; padding: 20px;")
            self._cards_layout.addWidget(lbl)
        else:
            for contact in contacts:
                card = _ContactCard(contact, self._crud, self._load, self._lang)
                self._cards_layout.addWidget(card)