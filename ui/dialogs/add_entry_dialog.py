from typing import TYPE_CHECKING, cast
from datetime import date as _date

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QLabel,
    QLineEdit, QComboBox, QTextEdit, QDateEdit, QPushButton,
    QSpinBox, QDoubleSpinBox, QFrame,
    QAbstractItemView, QHeaderView, QSizePolicy, QTableWidget,
    QTableWidgetItem, QMessageBox
)

from core.base_dialog import BaseDialog
from core.translator import TranslationManager
from ui.utils.wheel_blocker import block_wheel_in, block_wheel
from ui.widgets.searchable_combo import SearchableComboBox

if TYPE_CHECKING:
    from database.models.client import Client
    from database.models.material import Material
    from database.models.packaging_type import PackagingType
    from database.models.country import Country


# ── Compact cell styles ──────────────────────────────────────────────────────
_CELL_H = 28   # ارتفاع موحّد لكل widgets داخل الجدول

_COMBO_STYLE = (
    "QComboBox { padding: 1px 6px; font-size: 11px; font-weight: 400;"
    " border: 1px solid #E0E0E0; border-radius: 4px; background: white;"
    " min-height: 0; max-height: 28px; }"
    "QComboBox:focus { border: 1px solid #2563EB; }"
    "QComboBox::drop-down { width:0; border:none; }"
    "QComboBox::down-arrow { width:0; height:0; border:none; image:none; }"
)
_DATE_STYLE = (
    "QDateEdit { padding: 1px 6px; font-size: 11px; font-weight: 400;"
    " border: 1px solid #E0E0E0; border-radius: 4px; background: white;"
    " min-height: 0; max-height: 28px; }"
    "QDateEdit:focus { border: 1px solid #2563EB; }"
    "QDateEdit::drop-down { width:0; border:none; }"
    "QDateEdit::down-arrow { width:0; height:0; border:none; image:none; }"
)
_SPIN_STYLE = (
    "QSpinBox, QDoubleSpinBox { padding: 1px 4px; font-size: 11px; font-weight: 400;"
    " border: 1px solid #E0E0E0; border-radius: 4px; background: white;"
    " min-height: 0; max-height: 28px; }"
    "QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #2563EB; }"
    "QSpinBox::up-button, QSpinBox::down-button,"
    "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button"
    " { width: 0; border: none; }"
)
_LINE_STYLE = (
    "QLineEdit { padding: 1px 6px; font-size: 11px; font-weight: 400;"
    " border: 1px solid #E0E0E0; border-radius: 4px; background: white;"
    " min-height: 0; max-height: 28px; }"
    "QLineEdit:focus { border: 1px solid #2563EB; }"
)


def _qdate_to_py(qd):
    try:
        return qd.toPython()
    except Exception:
        return _date(qd.year(), qd.month(), qd.day())


class _NoHoverTable(QTableWidget):
    """يمنع تحديد السطر بمجرد مرور الماوس فوق cellWidget."""
    def mouseMoveEvent(self, e):
        e.ignore()

    def viewportEvent(self, e):
        from PySide6.QtCore import QEvent
        if e.type() == QEvent.Type.HoverMove:
            return False
        return super().viewportEvent(e)


class AddEntryDialog(BaseDialog):
    # ── أعمدة الجدول ────────────────────────────────────────────────────────
    C_MAT    = 0   # مادة
    C_QTY    = 1   # عدد
    C_NET    = 2   # صافي
    C_GROSS  = 3   # إجمالي
    C_PACK   = 4   # تغليف
    C_CTRY   = 5   # بلد المنشأ
    C_BATCH  = 6   # رقم الدفعة
    C_MFG    = 7   # تاريخ الإنتاج
    C_EXP    = 8   # تاريخ الانتهاء
    C_NOTES  = 9   # ملاحظات
    N_COLS   = 10

    def __init__(self, parent=None, entry=None, *,
                 clients=None, materials=None,
                 packaging_types=None, countries=None, user=None):
        super().__init__(parent=parent, user=user)
        self.setObjectName("AddEntryDialog")
        self.entry = entry
        self._ = TranslationManager.get_instance().translate
        self.set_translated_title("add_entry" if entry is None else "edit_entry")

        self.clients        = clients        or []
        self.materials      = materials      or []
        self.packaging_types = packaging_types or []
        self.countries      = countries      or []
        self._lang = TranslationManager.get_instance().get_current_language()

        self._unsaved = False   # تتبع التغييرات للتحذير عند الإغلاق

        self._init_ui()
        if self.entry is not None:
            self._prefill()
        else:
            self._add_row()   # صف فارغ افتراضي

    # ════════════════════════════════════════════════════════════════════════
    # UI BUILD
    # ════════════════════════════════════════════════════════════════════════

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header card ──────────────────────────────────────────────────────
        header_card = QFrame()
        header_card.setObjectName("general-info-card")
        h_lay = QVBoxLayout(header_card)
        h_lay.setContentsMargins(20, 14, 20, 14)
        h_lay.setSpacing(10)

        # Grid layout — 4 أعمدة: label | field | label | field
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)   # العمود الثاني يتمدد
        grid.setColumnStretch(3, 1)   # العمود الرابع يتمدد

        # الصف 0: تاريخ الإدخال | نوع وسيلة النقل
        self.de_entry_date = QDateEdit()
        self.de_entry_date.setCalendarPopup(True)
        self.de_entry_date.setDate(QDate.currentDate())
        self.de_entry_date.setDisplayFormat("yyyy-MM-dd")
        self.de_entry_date.setMinimumWidth(130)

        self.cmb_transport_type = QComboBox()
        self.cmb_transport_type.addItem(self._("not_set"),   "")
        self.cmb_transport_type.addItem(self._("truck"),     "truck")
        self.cmb_transport_type.addItem(self._("container"), "container")
        self.cmb_transport_type.addItem(self._("other"),     "other")

        grid.addWidget(self._lbl("entry_date"),        0, 0, Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.de_entry_date,             0, 1)
        grid.addWidget(self._lbl("transport_unit_type"), 0, 2, Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.cmb_transport_type,        0, 3)

        # الصف 1: مرجع الشحن | ختم | العميل المالك
        self.le_transport_ref = QLineEdit()
        self.le_transport_ref.setPlaceholderText(self._("container_or_plate_no"))

        self.le_seal_no = QLineEdit()
        self.le_seal_no.setPlaceholderText("—")

        self.cmb_owner = SearchableComboBox(parent=self)
        self.cmb_owner.set_loader(
            loader=self._search_clients,
            display=self._client_display,
            value=lambda c: c.id,
        )

        grid.addWidget(self._lbl("transport_ref"), 1, 0, Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.le_transport_ref,      1, 1)
        grid.addWidget(self._lbl("seal_no"),       1, 2, Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.le_seal_no,            1, 3)

        # الصف 2: العميل المالك يمتد على عمودين
        grid.addWidget(self._lbl("owner_client"), 2, 0, Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(self.cmb_owner,            2, 1, 1, 3)  # يمتد 3 أعمدة

        h_lay.addLayout(grid)

        # الملاحظات — تحت الـ grid بشكل منفصل
        notes_row = QHBoxLayout(); notes_row.setSpacing(12)
        lbl_notes = self._lbl("notes")
        lbl_notes.setAlignment(Qt.AlignTop | Qt.AlignRight)
        lbl_notes.setFixedWidth(100)
        notes_row.addWidget(lbl_notes)
        self.te_notes = QTextEdit()
        self.te_notes.setObjectName("form-notes")
        self.te_notes.setPlaceholderText(self._("optional"))
        self.te_notes.setFixedHeight(48)
        notes_row.addWidget(self.te_notes, 1)
        h_lay.addLayout(notes_row)

        root.addWidget(header_card)

        # ── فاصل ─────────────────────────────────────────────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("form-dialog-sep"); sep.setFixedHeight(1)
        root.addWidget(sep)

        # ── Items section ────────────────────────────────────────────────────
        items_widget = QWidget()
        items_lay = QVBoxLayout(items_widget)
        items_lay.setContentsMargins(16, 10, 16, 8)
        items_lay.setSpacing(8)

        # شريط العنوان + عداد + أزرار
        toolbar = QHBoxLayout(); toolbar.setSpacing(8)
        lbl_items = QLabel(self._("entry_items"))
        lbl_items.setObjectName("section-label")
        toolbar.addWidget(lbl_items)

        self.lbl_row_count = QLabel("0 " + self._("rows"))
        self.lbl_row_count.setObjectName("text-muted")
        toolbar.addWidget(self.lbl_row_count)
        toolbar.addStretch()

        self.btn_add_row = QPushButton("＋  " + self._("add_row"))
        self.btn_add_row.setObjectName("primary-btn")
        self.btn_del_row = QPushButton("✕  " + self._("delete_selected"))
        self.btn_del_row.setObjectName("danger-btn")
        self.btn_add_row.clicked.connect(self._add_row)
        self.btn_del_row.clicked.connect(self._delete_selected_rows)
        toolbar.addWidget(self.btn_add_row)
        toolbar.addWidget(self.btn_del_row)
        items_lay.addLayout(toolbar)

        # ── الجدول ───────────────────────────────────────────────────────────
        self.table = _NoHoverTable(0, self.N_COLS, self)
        self.table.setObjectName("items-table")

        # Headers بالترتيب الجديد (الأهم أولاً)
        self.table.setHorizontalHeaderLabels([
            self._("material"),         # 0
            self._("count"),            # 1
            self._("net_weight_kg"),    # 2
            self._("gross_weight_kg"),  # 3
            self._("packaging_type"),   # 4
            self._("origin_country"),   # 5
            self._("batch_no"),         # 6
            self._("mfg_date"),         # 7
            self._("exp_date"),         # 8
            self._("notes"),            # 9
        ])

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(
            QAbstractItemView.SelectedClicked |
            QAbstractItemView.EditKeyPressed
        )
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ارتفاع الصفوف مضغوط
        vh = self.table.verticalHeader()
        vh.setVisible(False)       # نخفي أرقام الصفوف — توفير مساحة
        vh.setDefaultSectionSize(32)
        vh.setMinimumSectionSize(28)
        vh.setSectionResizeMode(QHeaderView.Fixed)

        # Header الأفقي
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(True)
        hh.setSectionsMovable(False)   # لا نسمح بتحريك الأعمدة
        hh.setMinimumSectionSize(55)

        # عروض ابتدائية
        for col, w in {
            self.C_MAT:   200,
            self.C_QTY:    65,
            self.C_NET:    90,
            self.C_GROSS:  90,
            self.C_PACK:  130,
            self.C_CTRY:  130,
            self.C_BATCH: 110,
            self.C_MFG:   120,
            self.C_EXP:   120,
        }.items():
            self.table.setColumnWidth(col, w)

        items_lay.addWidget(self.table, 1)
        root.addWidget(items_widget, 1)

        # ── Footer ───────────────────────────────────────────────────────────
        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("form-dialog-sep"); sep2.setFixedHeight(1)
        root.addWidget(sep2)

        footer = QWidget(); footer.setObjectName("form-dialog-footer")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(16, 8, 16, 8)
        f_lay.setSpacing(8)
        f_lay.addStretch()
        self.btn_cancel = QPushButton(self._("cancel"))
        self.btn_cancel.setObjectName("secondary-btn")
        self.btn_cancel.setMinimumWidth(90)
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_save = QPushButton(self._("save"))
        self.btn_save.setObjectName("primary-btn")
        self.btn_save.setMinimumWidth(90)
        self.btn_save.clicked.connect(self._accept)
        f_lay.addWidget(self.btn_cancel)
        f_lay.addWidget(self.btn_save)
        root.addWidget(footer)

        # Tab order على الهيدر
        # Tab order: date → transport type → ref → seal → owner → notes
        for a, b in [
            (self.de_entry_date,     self.cmb_transport_type),
            (self.cmb_transport_type, self.le_transport_ref),
            (self.le_transport_ref,   self.le_seal_no),
            (self.le_seal_no,         self.cmb_owner),
            (self.cmb_owner,          self.te_notes),
        ]:
            self.setTabOrder(a, b)

        block_wheel_in(self)

    # ════════════════════════════════════════════════════════════════════════
    # ROW MANAGEMENT
    # ════════════════════════════════════════════════════════════════════════

    def _add_row(self, preset: dict | None = None):
        self.table.setUpdatesEnabled(False)
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setRowHeight(r, 32)

        # ── المادة — searchable ──────────────────────────────────────────
        cmb_mat = SearchableComboBox(parent=self.table)
        cmb_mat.set_loader(
            loader=lambda q="": [
                m for m in self.materials
                if not q or q.lower() in self._label(m).lower()
            ],
            display=lambda m, _l: self._label(m),
            value=lambda m: getattr(m, "id", None),
        )
        cmb_mat.setFixedHeight(_CELL_H)
        # SearchableComboBox is editable — override QLineEdit inside too
        cmb_mat.setStyleSheet(
            _COMBO_STYLE +
            "QComboBox QLineEdit { padding: 0 4px; font-size: 11px;"
            " border: none; background: transparent; min-height: 0; }"
        )
        self.table.setCellWidget(r, self.C_MAT, cmb_mat)

        # ── العدد ────────────────────────────────────────────────────────
        sp_qty = QSpinBox()
        sp_qty.setFocusPolicy(Qt.ClickFocus)
        sp_qty.setRange(0, 10**9)
        sp_qty.setFixedHeight(_CELL_H)
        sp_qty.setStyleSheet(_SPIN_STYLE)
        self.table.setCellWidget(r, self.C_QTY, sp_qty)

        # ── الأوزان ──────────────────────────────────────────────────────
        def _dspin():
            ds = QDoubleSpinBox()
            ds.setFocusPolicy(Qt.ClickFocus)
            ds.setDecimals(3)
            ds.setRange(0, 10**9)
            ds.setFixedHeight(_CELL_H)
            ds.setStyleSheet(_SPIN_STYLE)
            return ds
        ds_net   = _dspin()
        ds_gross = _dspin()
        self.table.setCellWidget(r, self.C_NET,   ds_net)
        self.table.setCellWidget(r, self.C_GROSS, ds_gross)

        # ── التغليف ──────────────────────────────────────────────────────
        cmb_pack = QComboBox()
        cmb_pack.setFocusPolicy(Qt.ClickFocus)
        cmb_pack.addItem(self._("not_set"), None)
        for p in self.packaging_types:
            cmb_pack.addItem(self._label(p), getattr(p, "id", None))
        cmb_pack.setFixedHeight(_CELL_H)
        cmb_pack.setStyleSheet(_COMBO_STYLE)
        self.table.setCellWidget(r, self.C_PACK, cmb_pack)

        # ── بلد المنشأ ───────────────────────────────────────────────────
        cmb_ctry = QComboBox()
        cmb_ctry.setFocusPolicy(Qt.ClickFocus)
        cmb_ctry.addItem(self._("not_set"), None)
        for co in self.countries:
            cmb_ctry.addItem(self._label(co), getattr(co, "id", None))
        cmb_ctry.setFixedHeight(_CELL_H)
        cmb_ctry.setStyleSheet(_COMBO_STYLE)
        self.table.setCellWidget(r, self.C_CTRY, cmb_ctry)

        # ── رقم الدفعة ───────────────────────────────────────────────────
        le_batch = QLineEdit()
        le_batch.setFocusPolicy(Qt.ClickFocus)
        le_batch.setFixedHeight(_CELL_H)
        le_batch.setStyleSheet(_LINE_STYLE)
        self.table.setCellWidget(r, self.C_BATCH, le_batch)

        # ── التواريخ ─────────────────────────────────────────────────────
        def _date_edit():
            de = QDateEdit()
            de.setFocusPolicy(Qt.ClickFocus)
            de.setCalendarPopup(True)
            de.setDisplayFormat("yyyy-MM-dd")
            de.setSpecialValueText("—")
            de.setMinimumDate(QDate(2000, 1, 1))
            de.setDate(de.minimumDate())
            de.setFixedHeight(_CELL_H)
            de.setStyleSheet(_DATE_STYLE)
            return de
        de_mfg = _date_edit()
        de_exp = _date_edit()
        self.table.setCellWidget(r, self.C_MFG, de_mfg)
        self.table.setCellWidget(r, self.C_EXP, de_exp)

        # ── ملاحظات الصف ─────────────────────────────────────────────────
        le_notes = QLineEdit()
        le_notes.setFocusPolicy(Qt.ClickFocus)
        le_notes.setFixedHeight(_CELL_H)
        le_notes.setStyleSheet(_LINE_STYLE)
        self.table.setCellWidget(r, self.C_NOTES, le_notes)

        # ── Preset (تعبئة عند التعديل) ───────────────────────────────────
        if preset:
            self._apply_preset(r, preset, cmb_mat, cmb_pack, cmb_ctry,
                               sp_qty, ds_net, ds_gross,
                               de_mfg, de_exp, le_batch, le_notes)

        block_wheel(cmb_pack, sp_qty, ds_net, ds_gross,
                    cmb_ctry, de_mfg, de_exp)

        self.table.setUpdatesEnabled(True)
        self._update_row_count()
        self._unsaved = True

    def _apply_preset(self, r, preset,
                      cmb_mat, cmb_pack, cmb_ctry,
                      sp_qty, ds_net, ds_gross,
                      de_mfg, de_exp, le_batch, le_notes):
        # مادة
        if hasattr(cmb_mat, "set_value"):
            mat_id = preset.get("material_id")
            if mat_id:
                mat_obj = next((m for m in self.materials
                                if getattr(m, "id", None) == mat_id), None)
                if mat_obj:
                    cmb_mat.set_value(mat_id, display_text=self._label(mat_obj))
        else:
            idx = cmb_mat.findData(preset.get("material_id"))
            if idx != -1:
                cmb_mat.setCurrentIndex(idx)

        # باقي الحقول
        idx = cmb_pack.findData(preset.get("packaging_type_id"))
        if idx != -1:
            cmb_pack.setCurrentIndex(idx)
        sp_qty.setValue(int(preset.get("count") or 0))
        ds_net.setValue(float(preset.get("net_weight_kg") or 0))
        ds_gross.setValue(float(preset.get("gross_weight_kg") or 0))

        def _set_date(de, val):
            if not val:
                return
            try:
                parts = str(val).split("-")
                if len(parts) == 3:
                    de.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
            except Exception:
                pass
        _set_date(de_mfg, preset.get("mfg_date"))
        _set_date(de_exp, preset.get("exp_date"))

        idx = cmb_ctry.findData(preset.get("origin_country_id"))
        if idx != -1:
            cmb_ctry.setCurrentIndex(idx)
        le_batch.setText(preset.get("batch_no") or "")
        le_notes.setText(preset.get("notes") or "")

    def _delete_selected_rows(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        self._update_row_count()
        self._unsaved = True

    def _update_row_count(self):
        n = self.table.rowCount()
        self.lbl_row_count.setText(f"{n}  " + self._("rows"))

    # ════════════════════════════════════════════════════════════════════════
    # PREFILL (edit mode)
    # ════════════════════════════════════════════════════════════════════════

    def _prefill(self):
        # Header
        if getattr(self.entry, "entry_date", None):
            y, m, d = str(self.entry.entry_date).split("-")
            self.de_entry_date.setDate(QDate(int(y), int(m), int(d)))

        tt = getattr(self.entry, "transport_unit_type", "") or ""
        idx = self.cmb_transport_type.findData(tt)
        if idx != -1:
            self.cmb_transport_type.setCurrentIndex(idx)

        self.le_transport_ref.setText(getattr(self.entry, "transport_ref", "") or "")
        self.le_seal_no.setText(getattr(self.entry, "seal_no", "") or "")

        owner_id = getattr(self.entry, "owner_client_id", None)
        if owner_id:
            owner_obj = next((c for c in self.clients
                              if getattr(c, "id", None) == owner_id), None)
            if owner_obj:
                self.cmb_owner.set_value(owner_id,
                                         display_text=self._label(owner_obj))

        self.te_notes.setPlainText(getattr(self.entry, "notes", "") or "")

        # Items
        self.table.setRowCount(0)
        for it in getattr(self.entry, "items", []) or []:
            self._add_row(preset={
                "material_id":       getattr(it, "material_id", None),
                "packaging_type_id": getattr(it, "packaging_type_id", None),
                "count":             getattr(it, "count", 0),
                "net_weight_kg":     getattr(it, "net_weight_kg", 0),
                "gross_weight_kg":   getattr(it, "gross_weight_kg", 0),
                "mfg_date":          getattr(it, "mfg_date", None),
                "exp_date":          getattr(it, "exp_date", None),
                "origin_country_id": getattr(it, "origin_country_id", None),
                "batch_no":          getattr(it, "batch_no", ""),
                "notes":             getattr(it, "notes", ""),
            })
        self._unsaved = False

    # ════════════════════════════════════════════════════════════════════════
    # VALIDATION & SAVE
    # ════════════════════════════════════════════════════════════════════════

    def _accept(self):
        # التحقق من صاحب البضاعة
        if self.cmb_owner.current_value() is None:
            self._warn(self._("please_choose_owner_client"))
            return

        # التحقق من وجود صفوف
        if self.table.rowCount() == 0:
            self._warn(self._("please_add_at_least_one_item"))
            return

        for r in range(self.table.rowCount()):
            # مادة مطلوبة
            mat_w = self.table.cellWidget(r, self.C_MAT)
            mat_id = (mat_w.current_value()
                      if hasattr(mat_w, "current_value")
                      else mat_w.currentData() if mat_w else None)
            if mat_id is None:
                self._warn(self._("material_required_row").format(row=r + 1))
                self.table.selectRow(r)
                return

            # الوزن الإجمالي ≥ الصافي
            ds_net   = self.table.cellWidget(r, self.C_NET)
            ds_gross = self.table.cellWidget(r, self.C_GROSS)
            if ds_net and ds_gross and ds_gross.value() < ds_net.value():
                self._warn(self._("gross_less_than_net_row").format(row=r + 1))
                self.table.selectRow(r)
                return

        self._unsaved = False
        self.accept()

    def _on_cancel(self):
        """تحذير إذا وجدت تغييرات غير محفوظة."""
        if self._unsaved and self.table.rowCount() > 0:
            reply = QMessageBox.question(
                self,
                self._("confirm"),
                self._("unsaved_changes_confirm"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.reject()

    def closeEvent(self, event):
        if self._unsaved and self.table.rowCount() > 0:
            reply = QMessageBox.question(
                self,
                self._("confirm"),
                self._("unsaved_changes_confirm"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        super().closeEvent(event)

    # ════════════════════════════════════════════════════════════════════════
    # OUTPUT
    # ════════════════════════════════════════════════════════════════════════

    def get_data(self):
        entry_qd = self.de_entry_date.date()
        header = {
            "entry_no":           None,
            "entry_date":         _qdate_to_py(entry_qd),
            "transport_unit_type": self.cmb_transport_type.currentData() or None,
            "transport_ref":      self.le_transport_ref.text().strip() or None,
            "seal_no":            self.le_seal_no.text().strip() or None,
            "owner_client_id":    self.cmb_owner.current_value(),
            "notes":              self.te_notes.toPlainText().strip() or None,
        }

        items = []
        for r in range(self.table.rowCount()):
            mat_w  = self.table.cellWidget(r, self.C_MAT)
            mat_id = (mat_w.current_value()
                      if hasattr(mat_w, "current_value")
                      else mat_w.currentData() if mat_w else None)

            de_mfg   = self.table.cellWidget(r, self.C_MFG)
            de_exp   = self.table.cellWidget(r, self.C_EXP)
            sp_qty   = self.table.cellWidget(r, self.C_QTY)
            ds_net   = self.table.cellWidget(r, self.C_NET)
            ds_gross = self.table.cellWidget(r, self.C_GROSS)
            cmb_pack = self.table.cellWidget(r, self.C_PACK)
            cmb_ctry = self.table.cellWidget(r, self.C_CTRY)
            le_batch = self.table.cellWidget(r, self.C_BATCH)
            le_notes = self.table.cellWidget(r, self.C_NOTES)

            def _clean_date(de):
                if de and de.date().isValid() and de.date() != de.minimumDate():
                    return _qdate_to_py(de.date())
                return None

            items.append({
                "material_id":       mat_id,
                "packaging_type_id": cmb_pack.currentData() if cmb_pack else None,
                "count":             sp_qty.value() if sp_qty else 0,
                "net_weight_kg":     float(ds_net.value()) if ds_net else 0,
                "gross_weight_kg":   float(ds_gross.value()) if ds_gross else 0,
                "mfg_date":          _clean_date(de_mfg),
                "exp_date":          _clean_date(de_exp),
                "origin_country_id": cmb_ctry.currentData() if cmb_ctry else None,
                "batch_no":          le_batch.text().strip() or None if le_batch else None,
                "notes":             le_notes.text().strip() or None if le_notes else None,
            })
        return header, items

    # ════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _lbl(self, key: str) -> QLabel:
        lbl = QLabel(self._(key))
        lbl.setObjectName("form-dialog-label")
        lbl.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        return lbl

    def _label(self, obj) -> str:
        if not obj:
            return ""
        if self._lang == "ar" and getattr(obj, "name_ar", None):
            return obj.name_ar
        if self._lang == "tr" and getattr(obj, "name_tr", None):
            return obj.name_tr
        return (getattr(obj, "name_en", None)
                or getattr(obj, "name_ar", None)
                or getattr(obj, "name_tr", None) or "")

    def _search_clients(self, q: str = "") -> list:
        if not q:
            return self.clients[:60]
        q = q.casefold()
        return [
            c for c in self.clients
            if q in (getattr(c, "name_ar", "") or "").casefold()
            or q in (getattr(c, "name_en", "") or "").casefold()
            or q in (getattr(c, "name_tr", "") or "").casefold()
            or q in (getattr(c, "client_code", "") or "").casefold()
        ][:60]

    def _client_display(self, c, lang: str) -> str:
        return self._label(c)

    def _warn(self, msg: str):
        self.show_warning("warning", msg)