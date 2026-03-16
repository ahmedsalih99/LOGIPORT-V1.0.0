from PySide6.QtWidgets import QWidget, QFrame, QFormLayout, QHBoxLayout, QVBoxLayout, QLineEdit, QDateEdit, QComboBox, QTextEdit, QLabel
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import QSizePolicy
from ui.utils.wheel_blocker import block_wheel_in

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
        """
        يبني الـ general info card ويرجعه كـ QWidget.
        يُضاف مباشرةً في top_layout بالـ window.

        يتوقع وجود self.cmb_trx_type (ينشئها تلقائياً إذا لم تكن موجودة).
        """
        from PySide6.QtWidgets import QComboBox as _CB
        # أنشئ cmb_trx_type إذا لم تكن موجودة بعد
        if not hasattr(self, "cmb_trx_type") or self.cmb_trx_type is None:
            self.cmb_trx_type = _CB()

        card = QFrame()
        card.setObjectName("general-info-card")

        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(20, 12, 20, 12)
        card_lay.setSpacing(8)

        # ── سطر 1: رقم المعاملة + التاريخ ──────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(24)

        col_no = QVBoxLayout()
        col_no.setSpacing(4)
        lbl_no = QLabel(self._("transaction_no"))
        lbl_no.setObjectName("field-label")
        self.txt_trx_no = QLineEdit()
        self.txt_trx_no.setObjectName("transaction-number-input")
        self.txt_trx_no.setMinimumHeight(34)
        try:
            self.txt_trx_no.setPlaceholderText(self._generate_placeholder_number())
        except Exception:
            pass
        col_no.addWidget(lbl_no)
        col_no.addWidget(self.txt_trx_no)

        col_date = QVBoxLayout()
        col_date.setSpacing(4)
        lbl_date = QLabel(self._("transaction_date"))
        lbl_date.setObjectName("field-label")
        self.dt_trx_date = QDateEdit()
        self.dt_trx_date.setObjectName("transaction-date-input")
        self.dt_trx_date.setMinimumHeight(34)
        self.dt_trx_date.setDisplayFormat("yyyy-MM-dd")
        self.dt_trx_date.setCalendarPopup(True)
        self.dt_trx_date.setDate(QDate.currentDate())
        col_date.addWidget(lbl_date)
        col_date.addWidget(self.dt_trx_date)

        row1.addLayout(col_no, 1)
        row1.addLayout(col_date, 1)
        card_lay.addLayout(row1)

        # ── سطر 2: نوع المعاملة + الملاحظات ────────────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(24)

        col_type = QVBoxLayout()
        col_type.setSpacing(4)
        lbl_type = QLabel(self._("transaction_type"))
        lbl_type.setObjectName("field-label")
        self.cmb_trx_type.setObjectName("transaction-type-combo")
        self.cmb_trx_type.setMinimumHeight(34)
        self.cmb_trx_type.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.cmb_trx_type.setMaximumWidth(240)
        self._fill_trx_types()
        col_type.addWidget(lbl_type)
        col_type.addWidget(self.cmb_trx_type)

        col_notes = QVBoxLayout()
        col_notes.setSpacing(4)
        lbl_notes = QLabel(self._("notes"))
        lbl_notes.setObjectName("field-label")
        self.txt_notes = QTextEdit()
        self.txt_notes.setObjectName("transaction-notes-input")
        self.txt_notes.setMinimumHeight(50)
        self.txt_notes.setMaximumHeight(100)
        try:
            self.txt_notes.setPlaceholderText(self._("enter_notes_optional"))
        except Exception:
            pass
        col_notes.addWidget(lbl_notes)
        col_notes.addWidget(self.txt_notes)

        row2.addLayout(col_type, 1)
        row2.addLayout(col_notes, 1)
        card_lay.addLayout(row2)

        return card

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