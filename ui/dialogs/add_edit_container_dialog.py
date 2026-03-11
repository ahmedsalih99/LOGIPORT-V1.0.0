"""
add_edit_container_dialog.py — LOGIPORT
=========================================
ديالوغ إضافة / تعديل كونتينر.
- يرث BaseDialog
- client picker محترم (ClientPickerDialog)
- date widgets مع checkbox تفعيل
- entries linking
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QScrollArea, QWidget,
    QFormLayout, QLineEdit, QTextEdit, QComboBox,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QDateEdit, QCheckBox, QMessageBox, QSizePolicy,
    QFrame,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui  import QFont

from core.base_dialog  import BaseDialog
from core.translator   import TranslationManager
from ui.widgets.searchable_combo import SearchableComboBox

from database.crud.container_tracking_crud import ContainerTrackingCRUD
from database.models.container_tracking    import ContainerTracking

_crud = ContainerTrackingCRUD()

_STATUS_META = {
    "booked":     {"icon": "📋", "color": "#6366F1"},
    "loaded":     {"icon": "📦", "color": "#0891B2"},
    "in_transit": {"icon": "🚢", "color": "#2563EB"},
    "arrived":    {"icon": "⚓", "color": "#7C3AED"},
    "customs":    {"icon": "🏛️", "color": "#D97706"},
    "delivered":  {"icon": "✅", "color": "#059669"},
    "hold":       {"icon": "⚠️",  "color": "#DC2626"},
}


class AddEditContainerDialog(BaseDialog):
    """
    الاستخدام:
        # إضافة
        dlg = AddEditContainerDialog(parent=self, current_user=user)

        # تعديل
        dlg = AddEditContainerDialog(parent=self, current_user=user, record=container)

        if dlg.exec() == QDialog.Accepted:
            self._load_data()
    """

    def __init__(self, parent=None, *, current_user=None, record: ContainerTracking | None = None):
        super().__init__(parent, user=current_user)
        self._record = record
        self._date_widgets: dict = {}   # name → (QCheckBox, QDateEdit)

        is_edit = record is not None
        self.set_translated_title("edit_container" if is_edit else "add_container")
        self.setMinimumWidth(560)
        self.setMinimumHeight(600)
        self.setSizeGripEnabled(True)

        self._build_ui()

        if is_edit:
            self._populate(record)

    # ─────────────────────────────────────────────────────────────────────
    # UI BUILD
    # ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 12)
        root.setSpacing(0)

        # ── scrollable form area ────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        form  = QFormLayout(inner)
        form.setContentsMargins(20, 16, 20, 8)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # ── helpers ─────────────────────────────────────────────────────
        def _line(ph=""):
            w = QLineEdit()
            w.setPlaceholderText(ph)
            return w

        def _section_label(key: str):
            lbl = QLabel(self._(key))
            f = QFont(); f.setBold(True)
            lbl.setFont(f)
            lbl.setObjectName("text-muted")
            lbl.setContentsMargins(0, 10, 0, 2)
            return lbl

        def _date_row(name: str) -> QWidget:
            """صف يحتوي checkbox + QDateEdit."""
            row = QWidget()
            hl  = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(8)

            chk = QCheckBox()
            chk.setFixedWidth(22)
            chk.setToolTip(self._("enable_date"))

            de = QDateEdit()
            de.setCalendarPopup(True)
            de.setDisplayFormat("yyyy-MM-dd")
            de.setDate(QDate.currentDate())
            de.setEnabled(False)

            chk.toggled.connect(de.setEnabled)

            hl.addWidget(chk)
            hl.addWidget(de, 1)

            self._date_widgets[name] = (chk, de)
            return row

        # ── الزبون: SearchableComboBox ───────────────────────────────────
        self._combo_client = SearchableComboBox(parent=inner)
        self._combo_client.set_loader(
            loader=self._load_clients,
            display=self._client_display,
            value=lambda c: c.id,
        )

        # ── المعاملة: SearchableComboBox ─────────────────────────────────
        self._combo_tx = SearchableComboBox(parent=inner)
        self._combo_tx.set_loader(
            loader=self._load_transactions,
            display=self._tx_display,
            value=lambda t: t.id,
        )

        # ── SECTION: معلومات الكونتينر ──────────────────────────────────
        form.addRow("", _section_label("container_info"))

        self._f_container_no  = _line("MSCU1234567")
        self._f_bl_number     = _line()
        self._f_booking_no    = _line()
        self._f_shipping_line = _line("Maersk, MSC...")
        self._f_vessel_name   = _line()
        self._f_voyage_no     = _line()

        form.addRow(self._(  "container_no_label") + " *", self._f_container_no)
        form.addRow(self._(  "bl_number_label"),           self._f_bl_number)
        form.addRow(self._(  "booking_no_label"),           self._f_booking_no)
        form.addRow(self._(  "shipping_line_label"),        self._f_shipping_line)
        form.addRow(self._(  "vessel_name_label"),          self._f_vessel_name)
        form.addRow(self._(  "voyage_no_label"),            self._f_voyage_no)

        # ── SECTION: الموانئ ─────────────────────────────────────────────
        form.addRow("", _section_label("ports_section"))

        self._f_pol         = _line()
        self._f_pod         = _line()
        self._f_destination = _line()

        form.addRow(self._("port_of_loading_label"),   self._f_pol)
        form.addRow(self._("port_of_discharge_label"), self._f_pod)
        form.addRow(self._("final_destination_label"), self._f_destination)

        # ── SECTION: التواريخ ────────────────────────────────────────────
        form.addRow("", _section_label("dates_section"))

        form.addRow(self._("etd_label"),          _date_row("etd"))
        form.addRow(self._("eta_label"),           _date_row("eta"))
        form.addRow(self._("atd_label"),           _date_row("atd"))
        form.addRow(self._("ata_label"),           _date_row("ata"))
        form.addRow(self._("customs_date_label"),  _date_row("customs_date"))
        form.addRow(self._("delivery_date_label"), _date_row("delivery_date"))

        # ── SECTION: الحالة والربط ───────────────────────────────────────
        form.addRow("", _section_label("links_section"))

        # الحالة
        self._f_status = QComboBox()
        for s in ContainerTracking.STATUSES:
            meta = _STATUS_META.get(s, {})
            self._f_status.addItem(f"{meta.get('icon','')} {self._(f'container_status_{s}')}", s)
        form.addRow(self._("status_label"), self._f_status)

        form.addRow(self._("client_label"), self._combo_client)

        # المعاملة
        form.addRow(self._("transaction_label"), self._combo_tx)

        # ملاحظات
        self._f_notes = QTextEdit()
        self._f_notes.setFixedHeight(72)
        self._f_notes.setPlaceholderText(self._("notes_placeholder"))
        form.addRow(self._("notes"), self._f_notes)

        # ── entries section (للتعديل فقط) ──────────────────────────────
        if self._record:
            form.addRow("", _section_label("linked_entries"))
            self._entries_list = QListWidget()
            self._entries_list.setFixedHeight(130)
            self._entries_list.setObjectName("data-table")

            entries_btns = QHBoxLayout()
            btn_link   = QPushButton(f"+ {self._('link_entry')}")
            btn_link.setObjectName("secondary-btn")
            btn_link.clicked.connect(self._link_entry)
            btn_unlink = QPushButton(f"✕ {self._('unlink_entry')}")
            btn_unlink.setObjectName("danger-btn")
            btn_unlink.clicked.connect(self._unlink_entry)
            entries_btns.addWidget(btn_link)
            entries_btns.addWidget(btn_unlink)
            entries_btns.addStretch()

            entries_container = QWidget()
            ev = QVBoxLayout(entries_container)
            ev.setContentsMargins(0, 0, 0, 0)
            ev.setSpacing(4)
            ev.addWidget(self._entries_list)
            ev.addLayout(entries_btns)
            form.addRow("", entries_container)
            self._refresh_entries_list()

        # ── bottom action bar ────────────────────────────────────────────
        bar = QHBoxLayout()
        bar.setContentsMargins(20, 8, 20, 0)
        bar.setSpacing(8)

        if self._record:
            btn_del = QPushButton(f"🗑  {self._('delete')}")
            btn_del.setObjectName("danger-btn")
            btn_del.clicked.connect(self._delete)
            bar.addWidget(btn_del)

        bar.addStretch()

        btn_cancel = QPushButton(self._("cancel"))
        btn_cancel.setObjectName("secondary-btn")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton(self._("save"))
        btn_save.setObjectName("primary-btn")
        btn_save.setObjectName("btn_save")        # لـ Ctrl+S في BaseDialog
        btn_save.clicked.connect(self._save)

        bar.addWidget(btn_cancel)
        bar.addWidget(btn_save)
        root.addLayout(bar)

    # ─────────────────────────────────────────────────────────────────────
    # POPULATE (تعديل)
    # ─────────────────────────────────────────────────────────────────────

    def _populate(self, rec: ContainerTracking):
        self._f_container_no.setText(rec.container_no  or "")
        self._f_bl_number.setText(rec.bl_number        or "")
        self._f_booking_no.setText(rec.booking_no      or "")
        self._f_shipping_line.setText(rec.shipping_line or "")
        self._f_vessel_name.setText(rec.vessel_name    or "")
        self._f_voyage_no.setText(rec.voyage_no        or "")
        self._f_pol.setText(rec.port_of_loading        or "")
        self._f_pod.setText(rec.port_of_discharge      or "")
        self._f_destination.setText(rec.final_destination or "")
        self._f_notes.setPlainText(rec.notes           or "")

        def _set_date(name: str, d):
            pair = self._date_widgets.get(name)
            if pair and d:
                chk, de = pair
                chk.setChecked(True)
                de.setDate(QDate(d.year, d.month, d.day))

        _set_date("etd",           rec.etd)
        _set_date("eta",           rec.eta)
        _set_date("atd",           rec.atd)
        _set_date("ata",           rec.ata)
        _set_date("customs_date",  rec.customs_date)
        _set_date("delivery_date", rec.delivery_date)

        idx = self._f_status.findData(rec.status)
        if idx >= 0:
            self._f_status.setCurrentIndex(idx)

        if rec.client_id and rec.client:
            display = (
                getattr(rec.client, "name_ar", None)
                or getattr(rec.client, "name_en", None) or ""
            )
            self._combo_client.set_value(rec.client_id, display_text=display)

        if rec.transaction_id:
            tx_no = (rec.transaction.transaction_no if rec.transaction else None) \
                    or str(rec.transaction_id)
            self._combo_tx.set_value(rec.transaction_id, display_text=tx_no)

    # ─────────────────────────────────────────────────────────────────────
    # CLIENT COMBO HELPERS
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_clients(q: str = "") -> list:
        """loader للـ SearchableComboBox — يقبل نص البحث."""
        try:
            from database.crud.clients_crud import ClientsCRUD
            all_clients = ClientsCRUD().list_clients()
            if not q:
                return all_clients[:50]
            q = q.casefold()
            return [
                c for c in all_clients
                if q in (getattr(c, "name_ar", "") or "").casefold()
                or q in (getattr(c, "name_en", "") or "").casefold()
                or q in (getattr(c, "name_tr", "") or "").casefold()
                or q in (getattr(c, "client_code", "") or "").casefold()
            ][:50]
        except Exception:
            return []

    @staticmethod
    def _client_display(c, lang: str) -> str:
        if lang.startswith("ar"):
            name = getattr(c, "name_ar", None) or getattr(c, "name_en", None) or getattr(c, "name_tr", None)
        elif lang.startswith("tr"):
            name = getattr(c, "name_tr", None) or getattr(c, "name_ar", None) or getattr(c, "name_en", None)
        else:
            name = getattr(c, "name_en", None) or getattr(c, "name_ar", None) or getattr(c, "name_tr", None)
        return (name or "").strip() or f"#{c.id}"

    # ─────────────────────────────────────────────────────────────────────
    # TRANSACTION COMBO HELPERS
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_transactions(q: str = "") -> list:
        try:
            from database.models import get_session_local
            from database.models.transaction import Transaction
            from sqlalchemy import select
            from sqlalchemy.orm import joinedload

            with get_session_local()() as s:
                stmt = (
                    select(Transaction)
                    .options(joinedload(Transaction.client))
                    .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
                )
                if q:
                    stmt = stmt.where(Transaction.transaction_no.ilike(f"%{q}%"))
                stmt = stmt.limit(50)
                results = list(s.execute(stmt).scalars().unique().all())
                s.expunge_all()
                return results
        except Exception:
            return []

    @staticmethod
    def _tx_display(t, lang: str) -> str:
        tx_no  = getattr(t, "transaction_no", None) or f"#{t.id}"
        client = getattr(t, "client", None)
        client_name = ""
        if client:
            if lang.startswith("ar"):
                client_name = getattr(client, "name_ar", None) or getattr(client, "name_en", None) or ""
            else:
                client_name = getattr(client, "name_en", None) or getattr(client, "name_ar", None) or ""
        date = str(getattr(t, "transaction_date", None) or "")[:10]
        parts = [tx_no]
        if client_name: parts.append(client_name)
        if date:        parts.append(date)
        return "  —  ".join(parts)

    # ─────────────────────────────────────────────────────────────────────
    # ENTRIES LINKING
    # ─────────────────────────────────────────────────────────────────────

    def _refresh_entries_list(self):
        if not hasattr(self, "_entries_list") or not self._record:
            return
        self._entries_list.clear()
        try:
            for e in _crud.get_entries(self._record.id):
                label = e.entry_no or f"#{e.id}"
                client = ""
                if hasattr(e, "owner_client") and e.owner_client:
                    client = (
                        getattr(e.owner_client, "name_ar", None)
                        or getattr(e.owner_client, "name_en", None) or ""
                    )
                text = f"{label}  —  {client}" if client else label
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, e.id)
                self._entries_list.addItem(item)
        except Exception:
            pass

    def _link_entry(self):
        from PySide6.QtWidgets import QInputDialog
        entry_no, ok = QInputDialog.getText(
            self, self._("link_entry"), self._("enter_entry_no")
        )
        if not (ok and entry_no.strip()):
            return
        try:
            from database.crud.entries_crud import EntriesCRUD
            q = entry_no.strip().casefold()
            all_entries = EntriesCRUD().get_all(limit=500)
            results = [
                e for e in all_entries
                if q in str(getattr(e, "entry_no", "") or "").casefold()
            ][:5]
            if not results:
                QMessageBox.warning(self, self._("not_found"), self._("entry_not_found"))
                return
            if len(results) == 1:
                chosen_id = results[0].id
            else:
                items = [r.entry_no or f"#{r.id}" for r in results]
                choice, ok2 = QInputDialog.getItem(
                    self, self._("link_entry"), self._("select_from_list"), items, 0, False
                )
                if not ok2:
                    return
                chosen_id = results[items.index(choice)].id
            if _crud.link_entries(self._record.id, [chosen_id], current_user=self.current_user):
                self._refresh_entries_list()
            else:
                QMessageBox.warning(self, self._("error"), self._("link_failed"))
        except Exception as e:
            QMessageBox.critical(self, self._("error"), str(e))

    def _unlink_entry(self):
        if not hasattr(self, "_entries_list"):
            return
        item = self._entries_list.currentItem()
        if not item:
            QMessageBox.information(self, self._("info"), self._("select_entry_first"))
            return
        _crud.unlink_entry(self._record.id, item.data(Qt.UserRole))
        self._refresh_entries_list()

    # ─────────────────────────────────────────────────────────────────────
    # DATE HELPERS
    # ─────────────────────────────────────────────────────────────────────

    def _get_date(self, name: str):
        pair = self._date_widgets.get(name)
        if not pair:
            return None
        chk, de = pair
        if not chk.isChecked():
            return None
        d = de.date()
        from datetime import date
        return date(d.year(), d.month(), d.day())

    # ─────────────────────────────────────────────────────────────────────
    # SAVE / DELETE
    # ─────────────────────────────────────────────────────────────────────

    def _save(self):
        container_no = self._f_container_no.text().strip()
        if not container_no:
            QMessageBox.warning(
                self, self._("validation_error"), self._("container_no_required")
            )
            return

        data = {
            "container_no":      container_no,
            "bl_number":         self._f_bl_number.text().strip()     or None,
            "booking_no":        self._f_booking_no.text().strip()     or None,
            "shipping_line":     self._f_shipping_line.text().strip()  or None,
            "vessel_name":       self._f_vessel_name.text().strip()    or None,
            "voyage_no":         self._f_voyage_no.text().strip()      or None,
            "port_of_loading":   self._f_pol.text().strip()            or None,
            "port_of_discharge": self._f_pod.text().strip()            or None,
            "final_destination": self._f_destination.text().strip()    or None,
            "etd":               self._get_date("etd"),
            "eta":               self._get_date("eta"),
            "atd":               self._get_date("atd"),
            "ata":               self._get_date("ata"),
            "customs_date":      self._get_date("customs_date"),
            "delivery_date":     self._get_date("delivery_date"),
            "status":            self._f_status.currentData(),
            "notes":             self._f_notes.toPlainText().strip()   or None,
            "client_id":         self._combo_client.current_value(),
            "transaction_id":    self._combo_tx.current_value(),
        }

        try:
            if self._record:
                _crud.update(self._record.id, data, current_user=self.current_user)
            else:
                _crud.create(data, current_user=self.current_user)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self._("error"), str(e))

    def _delete(self):
        reply = QMessageBox.question(
            self,
            self._("confirm_delete"),
            self._("confirm_delete_container").format(no=self._record.container_no),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                _crud.delete(self._record.id, current_user=self.current_user)
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, self._("error"), str(e))