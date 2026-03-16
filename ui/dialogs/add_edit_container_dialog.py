"""
add_edit_container_dialog.py — LOGIPORT v2
============================================
ديالوغ إضافة / تعديل بوليصة شحن.

التصنيف:
  Section 1 - معلومات البوليصة: bl_number*, shipping_line, client,
               cargo_type, quantity, origin_country, port_of_discharge
  Section 2 - التتبع والوثائق:  docs_delivered, cargo_tracking,
               docs_received_date, containers_count, bl_status, eta
  Section 3 - الكونتينرات:      جدول قابل للتعديل (container_no, seal_no, recipient)
  Section 4 - الإعدادات:        status, transaction, notes
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QWidget,
    QLineEdit, QTextEdit, QComboBox, QPushButton, QLabel,
    QDateEdit, QCheckBox, QMessageBox, QSizePolicy, QFrame,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSpinBox,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from ui.utils.wheel_blocker import block_wheel_in

from core.base_dialog import BaseDialog
from core.translator import TranslationManager
from ui.widgets.searchable_combo import SearchableComboBox

from database.crud.container_tracking_crud import ContainerTrackingCRUD
from database.models.container_tracking import ContainerTracking

_crud = ContainerTrackingCRUD()

_STATUS_META = {
    "booked":     {"icon": "📋", "color": "#6366F1"},
    "in_transit": {"icon": "🚢", "color": "#2563EB"},
    "arrived":    {"icon": "⚓", "color": "#7C3AED"},
    "customs":    {"icon": "🏛️", "color": "#D97706"},
    "delivered":  {"icon": "✅", "color": "#059669"},
    "hold":       {"icon": "⚠️",  "color": "#DC2626"},
}


class AddEditContainerDialog(BaseDialog):

    def __init__(self, parent=None, *, current_user=None, record: ContainerTracking | None = None):
        super().__init__(parent, user=current_user)
        self._record = record
        self._lang = TranslationManager.get_instance().get_current_language()

        is_edit = record is not None
        self.set_translated_title("edit_container" if is_edit else "add_container")
        self.setMinimumWidth(860)
        self.setMinimumHeight(640)
        self.setSizeGripEnabled(True)

        self._build_ui()
        if is_edit:
            self._populate(record)
        block_wheel_in(self)

    # ─────────────────────────────────────────────────────────────────────
    # UI BUILD
    # ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header, sep = self._build_primary_header(
            title=self._("add_container" if not self._record else "edit_container")
        )
        root.addWidget(header)
        root.addWidget(sep)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        body = QVBoxLayout(inner)
        body.setContentsMargins(16, 16, 16, 8)
        body.setSpacing(12)

        # ── Two-column layout: left + right ─────────────────────────────
        cols = QHBoxLayout()
        cols.setSpacing(14)
        left  = QVBoxLayout(); left.setSpacing(12)
        right = QVBoxLayout(); right.setSpacing(12)
        cols.addLayout(left, 3)
        cols.addLayout(right, 2)
        body.addLayout(cols)

        # ────────────────────────────────────────────────────────────────
        # Section 1: معلومات البوليصة
        # ────────────────────────────────────────────────────────────────
        grp1, g1 = self._group("section_bl_info")
        r = 0

        self._f_bl_number = self._line()
        self._add_row(g1, r, "bl_number_label", self._f_bl_number, required=True); r += 1

        self._f_shipping_line = self._line()
        self._add_row(g1, r, "shipping_line_label", self._f_shipping_line); r += 1

        self._combo_client = SearchableComboBox(parent=inner)
        self._combo_client.set_loader(
            loader=self._load_clients,
            display=self._client_display,
            value=lambda c: c.id,
        )
        self._add_row(g1, r, "client_label", self._combo_client); r += 1

        self._f_cargo_type = self._line()
        self._add_row(g1, r, "cargo_type_label", self._f_cargo_type); r += 1

        self._f_quantity = self._line()
        self._add_row(g1, r, "quantity_label", self._f_quantity); r += 1

        self._f_origin_country = self._line()
        self._add_row(g1, r, "origin_country_label", self._f_origin_country); r += 1

        self._f_pod = self._line()
        self._add_row(g1, r, "port_of_discharge_label", self._f_pod); r += 1

        left.addWidget(grp1)

        # ────────────────────────────────────────────────────────────────
        # Section 2: التتبع والوثائق
        # ────────────────────────────────────────────────────────────────
        grp2, g2 = self._group("section_tracking")
        r = 0

        self._f_docs_delivered = QCheckBox(self._("docs_delivered_label"))
        g2.addWidget(self._f_docs_delivered, r, 0, 1, 2); r += 1

        self._f_docs_received_date = self._date_widget()
        self._add_row(g2, r, "docs_received_date_label", self._f_docs_received_date); r += 1

        self._f_eta = self._date_widget()
        self._add_row(g2, r, "eta_label", self._f_eta); r += 1

        self._f_containers_count = QSpinBox()
        self._f_containers_count.setRange(0, 9999)
        self._f_containers_count.setSpecialValueText("—")
        self._add_row(g2, r, "containers_count_label", self._f_containers_count); r += 1

        self._f_bl_status = QComboBox()
        self._f_bl_status.addItem(self._("not_set"), None)
        for s in ContainerTracking.BL_STATUSES:
            self._f_bl_status.addItem(self._(f"bl_status_{s}"), s)
        self._add_row(g2, r, "bl_status_label", self._f_bl_status); r += 1

        self._f_cargo_tracking = QTextEdit()
        self._f_cargo_tracking.setMinimumHeight(56)
        self._f_cargo_tracking.setPlaceholderText(self._("cargo_tracking_placeholder"))
        self._add_row(g2, r, "cargo_tracking_label", self._f_cargo_tracking); r += 1

        right.addWidget(grp2)

        # ────────────────────────────────────────────────────────────────
        # Section 4: الإعدادات (يمين سفل)
        # ────────────────────────────────────────────────────────────────
        grp4, g4 = self._group("links_section")
        r = 0

        self._f_status = QComboBox()
        for s in ContainerTracking.STATUSES:
            meta = _STATUS_META.get(s, {})
            self._f_status.addItem(
                f"{meta.get('icon','')} {self._(f'container_status_{s}')}", s
            )
        self._add_row(g4, r, "status_label", self._f_status); r += 1

        self._combo_tx = SearchableComboBox(parent=inner)
        self._combo_tx.set_loader(
            loader=self._load_transactions,
            display=self._tx_display,
            value=lambda t: t.id,
        )
        self._add_row(g4, r, "transaction_label", self._combo_tx); r += 1

        self._f_notes = QTextEdit()
        self._f_notes.setMinimumHeight(62)
        self._f_notes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._f_notes.setPlaceholderText(self._("notes_placeholder"))
        self._add_row(g4, r, "notes", self._f_notes); r += 1

        right.addWidget(grp4)
        right.addStretch()
        left.addStretch()

        # ────────────────────────────────────────────────────────────────
        # Section 3: جدول الكونتينرات — full width
        # ────────────────────────────────────────────────────────────────
        grp3 = QGroupBox(self._("section_containers"))
        f = QFont(); f.setBold(True); grp3.setFont(f)
        g3v = QVBoxLayout(grp3)
        g3v.setContentsMargins(10, 14, 10, 10)
        g3v.setSpacing(6)

        # toolbar للجدول
        tbar = QHBoxLayout()
        btn_add_row = QPushButton(f"+ {self._('add_container_row')}")
        btn_add_row.setObjectName("secondary-btn")
        btn_add_row.clicked.connect(self._add_container_row)
        btn_del_row = QPushButton(f"🗑 {self._('delete_selected_row')}")
        btn_del_row.setObjectName("danger-btn")
        btn_del_row.clicked.connect(self._del_container_row)
        tbar.addWidget(btn_add_row)
        tbar.addWidget(btn_del_row)
        tbar.addStretch()
        g3v.addLayout(tbar)

        self._tbl_containers = QTableWidget(0, 3)
        self._tbl_containers.setObjectName("data-table")
        self._tbl_containers.setHorizontalHeaderLabels([
            self._("container_no_label"),
            self._("seal_no_label"),
            self._("recipient_label"),
        ])
        self._tbl_containers.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._tbl_containers.verticalHeader().setVisible(False)
        self._tbl_containers.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tbl_containers.setAlternatingRowColors(True)
        self._tbl_containers.setFixedHeight(160)
        g3v.addWidget(self._tbl_containers)

        body.addWidget(grp3)

        # ── Footer ─────────────────────────────────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("form-dialog-sep")
        sep2.setFixedHeight(1)

        footer = QWidget()
        footer.setObjectName("form-dialog-footer")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(16, 10, 16, 10)
        f_lay.setSpacing(8)

        if self._record:
            btn_del = QPushButton(f"🗑  {self._('delete')}")
            btn_del.setObjectName("danger-btn")
            btn_del.clicked.connect(self._delete)
            f_lay.addWidget(btn_del)

        f_lay.addStretch()

        btn_cancel = QPushButton(self._("cancel"))
        btn_cancel.setObjectName("secondary-btn")
        btn_cancel.clicked.connect(self.reject)

        self._btn_save = QPushButton(self._("save"))
        self._btn_save.setObjectName("primary-btn")
        self._btn_save.clicked.connect(self._save)

        f_lay.addWidget(btn_cancel)
        f_lay.addWidget(self._btn_save)

        root.addWidget(sep2)
        root.addWidget(footer)

    # ─────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────

    def _group(self, title_key: str):
        grp = QGroupBox(self._(title_key))
        f = QFont(); f.setBold(True); grp.setFont(f)
        g = QGridLayout(grp)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)
        g.setContentsMargins(10, 14, 10, 10)
        g.setColumnMinimumWidth(0, 140)
        g.setColumnStretch(1, 1)
        return grp, g

    def _line(self, ph="") -> QLineEdit:
        w = QLineEdit()
        w.setPlaceholderText(ph)
        return w

    def _date_widget(self) -> QWidget:
        """QDateEdit مع checkbox للتفعيل/الإلغاء."""
        row = QWidget()
        hl  = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        chk = QCheckBox()
        chk.setFixedWidth(20)
        chk.setToolTip(self._("enable_date"))
        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setDisplayFormat("yyyy-MM-dd")
        de.setDate(QDate.currentDate())
        de.setEnabled(False)
        chk.toggled.connect(de.setEnabled)
        hl.addWidget(chk)
        hl.addWidget(de, 1)
        row._chk = chk
        row._de  = de
        return row

    def _add_row(self, grid: QGridLayout, row: int, key: str, widget, required=False):
        lbl = QLabel(self._(key) + (" *" if required else ""))
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(lbl, row, 0)
        grid.addWidget(widget, row, 1)

    def _get_date(self, widget: QWidget):
        chk = getattr(widget, "_chk", None)
        de  = getattr(widget, "_de",  None)
        if not chk or not de or not chk.isChecked():
            return None
        d = de.date()
        from datetime import date
        return date(d.year(), d.month(), d.day())

    def _set_date(self, widget: QWidget, d):
        chk = getattr(widget, "_chk", None)
        de  = getattr(widget, "_de",  None)
        if chk and de and d:
            chk.setChecked(True)
            de.setDate(QDate(d.year, d.month, d.day))

    # ─────────────────────────────────────────────────────────────────────
    # Container rows
    # ─────────────────────────────────────────────────────────────────────

    def _add_container_row(self, container_no="", seal_no="", recipient=""):
        r = self._tbl_containers.rowCount()
        self._tbl_containers.insertRow(r)
        self._tbl_containers.setItem(r, 0, QTableWidgetItem(container_no))
        self._tbl_containers.setItem(r, 1, QTableWidgetItem(seal_no))
        self._tbl_containers.setItem(r, 2, QTableWidgetItem(recipient))

    def _del_container_row(self):
        rows = sorted({i.row() for i in self._tbl_containers.selectedItems()}, reverse=True)
        for r in rows:
            self._tbl_containers.removeRow(r)

    def _get_containers(self) -> list:
        result = []
        for r in range(self._tbl_containers.rowCount()):
            def _cell(c): return (self._tbl_containers.item(r, c) or QTableWidgetItem("")).text().strip()
            cn = _cell(0); sn = _cell(1); rec = _cell(2)
            if cn or sn or rec:
                result.append({"container_no": cn or None, "seal_no": sn or None, "recipient": rec or None})
        return result

    # ─────────────────────────────────────────────────────────────────────
    # POPULATE
    # ─────────────────────────────────────────────────────────────────────

    def _populate(self, rec: ContainerTracking):
        self._f_bl_number.setText(rec.bl_number     or "")
        self._f_shipping_line.setText(rec.shipping_line or "")
        self._f_cargo_type.setText(rec.cargo_type   or "")
        self._f_quantity.setText(rec.quantity        or "")
        self._f_origin_country.setText(rec.origin_country or "")
        self._f_pod.setText(rec.port_of_discharge    or "")
        self._f_notes.setPlainText(rec.notes         or "")
        self._f_cargo_tracking.setPlainText(rec.cargo_tracking or "")

        self._f_docs_delivered.setChecked(bool(rec.docs_delivered))

        if rec.containers_count:
            self._f_containers_count.setValue(rec.containers_count)

        idx = self._f_bl_status.findData(rec.bl_status)
        if idx >= 0:
            self._f_bl_status.setCurrentIndex(idx)

        self._set_date(self._f_eta, rec.eta)
        self._set_date(self._f_docs_received_date, rec.docs_received_date)

        idx = self._f_status.findData(rec.status)
        if idx >= 0:
            self._f_status.setCurrentIndex(idx)

        if rec.client_id and rec.client:
            display = getattr(rec.client, "name_ar", None) or getattr(rec.client, "name_en", None) or ""
            self._combo_client.set_value(rec.client_id, display_text=display)
        elif rec.client_id and hasattr(rec, "_client_name_ar"):
            display = rec._client_name_ar or rec._client_name_en or ""
            self._combo_client.set_value(rec.client_id, display_text=display)

        if rec.transaction_id:
            tx_no = getattr(rec, "_transaction_no", None) or str(rec.transaction_id)
            self._combo_tx.set_value(rec.transaction_id, display_text=tx_no)

        # تحميل الكونتينرات
        containers = getattr(rec, "_containers_data", None) or []
        if not containers and hasattr(rec, "containers") and rec.containers:
            containers = [
                {"container_no": c.container_no or "", "seal_no": c.seal_no or "", "recipient": c.recipient or ""}
                for c in rec.containers
            ]
        for c in containers:
            self._add_container_row(
                c.get("container_no", ""),
                c.get("seal_no",      ""),
                c.get("recipient",    ""),
            )

    # ─────────────────────────────────────────────────────────────────────
    # LOADERS
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_clients(q: str = "") -> list:
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
            ][:50]
        except Exception:
            return []

    @staticmethod
    def _client_display(c, lang: str) -> str:
        if lang.startswith("ar"):
            name = getattr(c, "name_ar", None) or getattr(c, "name_en", None)
        else:
            name = getattr(c, "name_en", None) or getattr(c, "name_ar", None)
        return (name or "").strip() or f"#{c.id}"

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
        tx_no = getattr(t, "transaction_no", None) or f"#{t.id}"
        client = getattr(t, "client", None)
        client_name = ""
        if client:
            client_name = getattr(client, "name_ar", None) or getattr(client, "name_en", None) or ""
        date = str(getattr(t, "transaction_date", None) or "")[:10]
        parts = [tx_no]
        if client_name: parts.append(client_name)
        if date:        parts.append(date)
        return "  —  ".join(parts)

    # ─────────────────────────────────────────────────────────────────────
    # SAVE / DELETE
    # ─────────────────────────────────────────────────────────────────────

    def _save(self):
        bl_number = self._f_bl_number.text().strip()
        if not bl_number:
            QMessageBox.warning(self, self._("validation_error"), self._("bl_number_required"))
            return

        containers_count = self._f_containers_count.value() or None

        data = {
            "bl_number":          bl_number,
            "shipping_line":      self._f_shipping_line.text().strip()      or None,
            "cargo_type":         self._f_cargo_type.text().strip()         or None,
            "quantity":           self._f_quantity.text().strip()           or None,
            "origin_country":     self._f_origin_country.text().strip()     or None,
            "port_of_discharge":  self._f_pod.text().strip()                or None,
            "docs_delivered":     self._f_docs_delivered.isChecked(),
            "cargo_tracking":     self._f_cargo_tracking.toPlainText().strip() or None,
            "docs_received_date": self._get_date(self._f_docs_received_date),
            "containers_count":   containers_count,
            "bl_status":          self._f_bl_status.currentData(),
            "eta":                self._get_date(self._f_eta),
            "status":             self._f_status.currentData(),
            "notes":              self._f_notes.toPlainText().strip()       or None,
            "client_id":          self._combo_client.current_value(),
            "transaction_id":     self._combo_tx.current_value(),
            "containers":         self._get_containers(),
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
            self._("confirm_delete_container").format(no=self._record.bl_number or ""),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                _crud.delete(self._record.id, current_user=self.current_user)
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, self._("error"), str(e))