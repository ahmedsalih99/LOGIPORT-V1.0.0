from PySide6.QtWidgets import QWidget, QFrame, QFormLayout, QLineEdit, QDateEdit, QComboBox, QTextEdit, QVBoxLayout
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import QSizePolicy

class GeneralTabMixin:
    """
    General tab for Add/Edit Transaction (status removed).
    Fields:
      - transaction_no (editable, placeholder only; empty -> CRUD auto-generates)
      - transaction_date (QDateEdit)
      - transaction_type (import/export/transit)
      - notes (multiline)
    """

    def _build_tab_general(self) -> QWidget:
        tab = QWidget(self)

        v = QVBoxLayout(tab)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(12)

        card = QFrame(tab)
        card.setObjectName("general-info-card")

        form = QFormLayout(card)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        # Transaction number
        self.txt_trx_no = QLineEdit()
        self.txt_trx_no.setObjectName("transaction-number-input")
        self.txt_trx_no.setMinimumHeight(36)
        try:
            self.txt_trx_no.setPlaceholderText(self._generate_placeholder_number())
        except Exception:
            pass

        # Date
        self.dt_trx_date = QDateEdit()
        self.dt_trx_date.setObjectName("transaction-date-input")
        self.dt_trx_date.setMinimumHeight(36)
        self.dt_trx_date.setDisplayFormat("yyyy-MM-dd")
        self.dt_trx_date.setCalendarPopup(True)
        self.dt_trx_date.setDate(QDate.currentDate())

        # Type
        self.cmb_trx_type.setObjectName("transaction-type-combo")
        self.cmb_trx_type.setMinimumHeight(36)
        self.cmb_trx_type.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.cmb_trx_type.setMaximumWidth(240)
        self._fill_trx_types()

        # Notes
        self.txt_notes = QTextEdit()
        self.txt_notes.setObjectName("transaction-notes-input")
        self.txt_notes.setMinimumHeight(80)
        self.txt_notes.setMaximumHeight(120)

        form.addRow(self._("transaction_no"), self.txt_trx_no)
        form.addRow(self._("transaction_date"), self.dt_trx_date)
        form.addRow(self._("transaction_type"), self.cmb_trx_type)
        form.addRow(self._("notes"), self.txt_notes)

        v.addWidget(card)
        v.addStretch()

        return tab

    # ------------------------ helpers ------------------------
    def _fill_trx_types(self):
        self.cmb_trx_type.clear()
        for label, code in ((self._("import"), "import"),
                            (self._("export"), "export"),
                            (self._("transit"), "transit")):
            self.cmb_trx_type.addItem(label, code)

    # ------------------- Prefill / getters -------------------
    def prefill_general(self, trx):
        """Prefill General tab from ORM object or dict.
        Status was removed; do not read or write it.
        """
        if not trx:
            # Set placeholder number for new transaction
            try:
                self.txt_trx_no.setText(self._generate_placeholder_number())
            except Exception:
                pass
            return

        get = (lambda o, k, d=None: o.get(k, d) if isinstance(o, dict) else getattr(o, k, d))

        no = get(trx, "transaction_no", "") or ""
        if no:
            self.txt_trx_no.setText(str(no))

        try:
            dt = get(trx, "transaction_date", None)
            if dt:
                # accept datetime/date or string 'YYYY-MM-DD'
                if hasattr(dt, "year"):
                    self.dt_trx_date.setDate(QDate(dt.year, dt.month, dt.day))
                else:
                    parts = str(dt).split("-")
                    self.dt_trx_date.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
        except Exception:
            pass

        tcode = get(trx, "transaction_type", "import") or "import"
        # find matching index by data role
        for i in range(self.cmb_trx_type.count()):
            if self.cmb_trx_type.itemData(i) == tcode:
                self.cmb_trx_type.setCurrentIndex(i)
                break

        notes = get(trx, "notes", "") or ""
        self.txt_notes.setPlainText(str(notes))

    def get_general_data(self) -> dict:
        # Python date
        qd = self.dt_trx_date.date()
        from datetime import date as _pydate
        trx_date = _pydate(qd.year(), qd.month(), qd.day())

        return {
            "transaction_no": (self.txt_trx_no.text() or "").strip(),
            "transaction_date": trx_date,
            "transaction_type": self.cmb_trx_type.currentData(),
            # 'status' intentionally removed
            "notes": (self.txt_notes.toPlainText() or "").strip(),
        }
