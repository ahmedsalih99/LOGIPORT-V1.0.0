from PySide6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout,
    QLineEdit, QDateEdit, QComboBox, QTextEdit, QLabel,
    QPushButton, QDialog, QSizePolicy, QScrollArea,
)
from PySide6.QtCore import Qt, QDate
from ui.utils.wheel_blocker import block_wheel_in
from ui.utils.font_utils import app_font, SM, BODY, MD

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
        شريط أفقي مدمج بارتفاع ~66px:
        [رقم المعاملة] [التاريخ] [Pill: نوع المعاملة] [زر الملاحظات]
        """
        from PySide6.QtWidgets import QComboBox as _CB
        if not hasattr(self, "cmb_trx_type") or self.cmb_trx_type is None:
            self.cmb_trx_type = _CB()

        strip = QFrame()
        strip.setObjectName("general-info-strip")

        lay = QHBoxLayout(strip)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(20)

        # ── رقم المعاملة ─────────────────────────────────────────────────────
        col_no = QVBoxLayout()
        col_no.setSpacing(3)
        lbl_no = QLabel(self._("transaction_no"))
        lbl_no.setObjectName("field-label")
        lbl_no.setFont(app_font(SM))
        self.txt_trx_no = QLineEdit()
        self.txt_trx_no.setObjectName("transaction-number-input")
        self.txt_trx_no.setFixedHeight(34)
        self.txt_trx_no.setMinimumWidth(140)
        self.txt_trx_no.setMaximumWidth(200)
        try:
            self.txt_trx_no.setPlaceholderText(self._generate_placeholder_number())
        except Exception:
            pass
        col_no.addWidget(lbl_no)
        col_no.addWidget(self.txt_trx_no)

        # ── التاريخ ───────────────────────────────────────────────────────────
        col_date = QVBoxLayout()
        col_date.setSpacing(3)
        lbl_date = QLabel(self._("transaction_date"))
        lbl_date.setObjectName("field-label")
        lbl_date.setFont(app_font(SM))
        self.dt_trx_date = QDateEdit()
        self.dt_trx_date.setObjectName("transaction-date-input")
        self.dt_trx_date.setFixedHeight(34)
        self.dt_trx_date.setMinimumWidth(130)
        self.dt_trx_date.setMaximumWidth(170)
        self.dt_trx_date.setDisplayFormat("yyyy-MM-dd")
        self.dt_trx_date.setCalendarPopup(True)
        self.dt_trx_date.setDate(QDate.currentDate())
        col_date.addWidget(lbl_date)
        col_date.addWidget(self.dt_trx_date)

        # ── نوع المعاملة — Pill buttons ────────────────────────────────────────
        col_type = QVBoxLayout()
        col_type.setSpacing(3)
        lbl_type = QLabel(self._("transaction_type"))
        lbl_type.setObjectName("field-label")
        lbl_type.setFont(app_font(SM))

        self._pill_btns: dict = {}
        pill_row = QHBoxLayout()
        pill_row.setSpacing(4)

        _PILL_DEFS = [
            ("import",  "📥", "trx-pill-import"),
            ("export",  "📤", "trx-pill-export"),
            ("transit", "🔄", "trx-pill-transit"),
        ]
        for code, icon, obj_name in _PILL_DEFS:
            btn = QPushButton(f"{icon}  {self._(code)}")
            btn.setObjectName(obj_name)
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setMinimumWidth(90)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(app_font(SM, bold=True))
            self._pill_btns[code] = btn
            pill_row.addWidget(btn)

        # رابط الـ Pill بالـ combo الداخلي
        def _on_pill(checked, c=None):
            if not checked:
                return
            for k, b in self._pill_btns.items():
                b.setChecked(k == c)
            # مزامنة مع cmb_trx_type
            for i in range(self.cmb_trx_type.count()):
                if self.cmb_trx_type.itemData(i) == c:
                    self.cmb_trx_type.setCurrentIndex(i)
                    break
            # تحديث badge في الـ header
            try:
                self._update_header_badge(c)
            except Exception:
                pass

        for code, btn in self._pill_btns.items():
            btn.clicked.connect(lambda chk, c=code: _on_pill(chk, c))

        # مزامنة عكسية: cmb_trx_type → pills
        def _sync_pills(idx):
            code = self.cmb_trx_type.itemData(idx)
            for k, b in self._pill_btns.items():
                b.setChecked(k == code)
        self.cmb_trx_type.currentIndexChanged.connect(_sync_pills)

        # إخفاء الـ combo القديم (محتاجه للحفظ)
        self.cmb_trx_type.setVisible(False)
        self._fill_trx_types()
        # اختر الأول تلقائياً
        if self.cmb_trx_type.count() > 0:
            self.cmb_trx_type.setCurrentIndex(0)
            first_code = self.cmb_trx_type.itemData(0)
            if first_code in self._pill_btns:
                self._pill_btns[first_code].setChecked(True)

        col_type.addWidget(lbl_type)
        col_type.addLayout(pill_row)

        # ── زر الملاحظات — Popover ────────────────────────────────────────────
        col_notes = QVBoxLayout()
        col_notes.setSpacing(3)
        lbl_notes_spacer = QLabel("")  # spacer لمحاذاة الزر مع بقية الحقول
        self.btn_notes = QPushButton("📝  " + self._("notes"))
        self.btn_notes.setObjectName("secondary-btn")
        self.btn_notes.setFixedHeight(34)
        self.btn_notes.setMinimumWidth(100)
        self.btn_notes.setCheckable(True)
        self.btn_notes.setFont(app_font(SM))
        self.btn_notes.setCursor(Qt.PointingHandCursor)

        # QTextEdit مخفي — يُستخدم للحفظ فقط
        self.txt_notes = QTextEdit()
        self.txt_notes.setVisible(False)
        self.txt_notes.setObjectName("transaction-notes-input")

        self.btn_notes.clicked.connect(self._toggle_notes_popover)
        col_notes.addWidget(lbl_notes_spacer)
        col_notes.addWidget(self.btn_notes)

        # تجميع الـ strip
        lay.addLayout(col_no)
        lay.addLayout(col_date)
        lay.addLayout(col_type)
        lay.addStretch()
        lay.addLayout(col_notes)
        lay.addWidget(self.cmb_trx_type)  # مخفي — للحفظ

        return strip

    def _toggle_notes_popover(self, checked: bool):
        """يفتح/يغلق Popover صغير للملاحظات."""
        if not checked:
            if hasattr(self, "_notes_popover") and self._notes_popover:
                self._notes_popover.hide()
            return
        if not hasattr(self, "_notes_popover") or not self._notes_popover:
            self._notes_popover = self._create_notes_popover()
        # تحديث النص
        self._popover_edit.setPlainText(self.txt_notes.toPlainText())
        # تحديد موضع الـ popover أسفل الزر
        btn = self.btn_notes
        gpos = btn.mapToGlobal(btn.rect().bottomLeft())
        from PySide6.QtWidgets import QApplication as _App
        screen = _App.primaryScreen().availableGeometry()
        w, h = 380, 140
        x = min(gpos.x(), screen.right() - w - 10)
        y = min(gpos.y() + 4, screen.bottom() - h - 10)
        self._notes_popover.setGeometry(x, y, w, h)
        self._notes_popover.show()
        self._notes_popover.raise_()
        self._popover_edit.setFocus()

    def _create_notes_popover(self) -> QFrame:
        """ينشئ popover الملاحظات — frame عائم."""
        pop = QFrame(None)  # بدون parent → نافذة tool
        pop.setObjectName("notes-popover")
        pop.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        pop.setAttribute(Qt.WA_ShowWithoutActivating, False)

        lay = QVBoxLayout(pop)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        self._popover_edit = QTextEdit()
        self._popover_edit.setObjectName("transaction-notes-input")
        self._popover_edit.setPlaceholderText(self._("enter_notes_optional") if hasattr(self, "_") else "")
        self._popover_edit.setMinimumHeight(80)
        self._popover_edit.textChanged.connect(self._sync_notes_from_popover)

        lay.addWidget(self._popover_edit)
        return pop

    def _sync_notes_from_popover(self):
        """يُزامن نص الـ popover مع txt_notes الخفي."""
        if hasattr(self, "_popover_edit") and hasattr(self, "txt_notes"):
            text = self._popover_edit.toPlainText()
            self.txt_notes.setPlainText(text)
            # تحديث لون الزر إذا فيه نص
            has_text = bool(text.strip())
            self.btn_notes.setChecked(True)
            self.btn_notes.setText(("📝  " + self._("notes") + f" ({len(text.splitlines())} ✓)") if has_text
                                   else "📝  " + self._("notes"))


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