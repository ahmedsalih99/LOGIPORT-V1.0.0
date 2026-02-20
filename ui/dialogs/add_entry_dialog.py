from typing import TYPE_CHECKING, cast
from datetime import date as _date

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QLineEdit, QComboBox, QTextEdit, QDateEdit, QPushButton, QTableWidget,
    QSpinBox, QDoubleSpinBox, QSplitter, QGridLayout, QFrame,
    QAbstractItemView, QDialogButtonBox, QHeaderView, QSizePolicy
)

from core.base_dialog import BaseDialog
from core.translator import TranslationManager

if TYPE_CHECKING:
    from database.models.client import Client
    from database.models.material import Material
    from database.models.packaging_type import PackagingType
    from database.models.country import Country


def _qdate_to_py(qd):
    try:
        return qd.toPython()
    except Exception:
        return _date(qd.year(), qd.month(), qd.day())


class AddEntryDialog(BaseDialog):
    def __init__(self, parent=None, entry=None, *, clients=None, materials=None, packaging_types=None, countries=None, user=None):
        super().__init__(parent=parent, user=user)
        self.setObjectName("AddEntryDialog")
        self.entry = entry
        self._ = TranslationManager.get_instance().translate
        self.set_translated_title("add_entry" if entry is None else "edit_entry")

        self.clients = clients or []
        self.materials = materials or []
        self.packaging_types = packaging_types or []
        self.countries = countries or []
        self._lang = TranslationManager.get_instance().get_current_language()

        self._init_ui()
        if self.entry is not None:
            self._prefill()

    # ---------- UI ----------
    def _init_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 15, 20, 15)
        main.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Vertical, self)
        splitter.setChildrenCollapsible(False)
        main.addWidget(splitter)

        # ================= HEADER =================
        header_widget = QWidget(self)
        header_widget.setObjectName("general-info-card")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(10)

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)

        self.de_entry_date = QDateEdit()
        self.de_entry_date.setCalendarPopup(True)
        self.de_entry_date.setDate(QDate.currentDate())

        self.cmb_transport_type = QComboBox()
        self.cmb_transport_type.addItem(self._("not_set"), "")
        self.cmb_transport_type.addItem(self._("truck"), "truck")
        self.cmb_transport_type.addItem(self._("container"), "container")
        self.cmb_transport_type.addItem(self._("other"), "other")

        self.le_transport_ref = QLineEdit()
        self.le_transport_ref.setPlaceholderText(self._("container_or_plate_no"))

        self.le_seal_no = QLineEdit()

        self.cmb_owner = QComboBox()
        self._fill_clients()

        r = 0
        grid.addWidget(QLabel(self._("entry_date")), r, 0)
        grid.addWidget(self.de_entry_date, r, 1)
        grid.addWidget(QLabel(self._("entry_no")), r, 2)
        grid.addWidget(self.le_transport_ref, r, 3)
        r += 1

        grid.addWidget(QLabel(self._("transport_unit_type")), r, 0)
        grid.addWidget(self.cmb_transport_type, r, 1)
        r += 1

        grid.addWidget(QLabel(self._("seal_no")), r, 0)
        grid.addWidget(self.le_seal_no, r, 1)
        grid.addWidget(QLabel(self._("owner_client")), r, 2)
        grid.addWidget(self.cmb_owner, r, 3)
        r += 1

        self.te_notes = QTextEdit()
        self.te_notes.setMinimumHeight(80)
        self.te_notes.setObjectName("form-notes")

        grid.addWidget(QLabel(self._("notes")), r, 0)
        grid.addWidget(self.te_notes, r, 1, 1, 3)

        header_layout.addLayout(grid)
        splitter.addWidget(header_widget)

        # ================= TABLE =================
        items_widget = QWidget(self)
        items_layout = QVBoxLayout(items_widget)
        items_layout.setSpacing(8)

        lbl_items = QLabel(self._("entry_items"))
        lbl_items.setObjectName("section-label")
        items_layout.addWidget(lbl_items)

        self.table = QTableWidget(0, 10, self)
        self.table.setObjectName("entryTable")

        headers = [
            self._("material"),
            self._("packaging_type"),
            self._("count"),
            self._("net_weight_kg"),
            self._("gross_weight_kg"),
            self._("mfg_date"),
            self._("exp_date"),
            self._("origin_country"),
            self._("batch_no"),
            self._("notes"),
        ]

        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(True)

        # 🔥 صفوف قابلة للتعديل + ارتفاع مريح
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.verticalHeader().setMinimumSectionSize(40)

        # 🔥 إعداد أعمدة احترافي
        hh = self.table.horizontalHeader()

        # المستخدم يقدر يغير عرض أي عمود
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(True)  # آخر عمود يملأ المساحة دائماً
        hh.setSectionsMovable(True)

        # عرض ابتدائي منطقي
        initial_widths = {
            0: 180,  # material
            1: 130,  # packaging
            2: 70,  # count (أصغر)
            3: 100,  # net (أصغر)
            4: 100,  # gross (أصغر)
            5: 140,  # mfg_date (أعرض)
            6: 140,  # exp_date (أعرض)
            7: 160,  # origin_country (أعرض)
            8: 130,  # batch
            9: 220,  # notes (يتمدد)
        }

        for col, w in initial_widths.items():
            self.table.setColumnWidth(col, w)

        # حد أدنى حتى ما يختفي العمود
        for col in range(10):
            self.table.horizontalHeader().setMinimumSectionSize(60)

        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        items_layout.addWidget(self.table, 1)

        # ===== Buttons =====
        btns = QHBoxLayout()
        btn_add = QPushButton(self._("add_row"))
        btn_del = QPushButton(self._("delete_selected"))
        btn_add.setObjectName("primary-btn")
        btn_del.setObjectName("danger-btn")

        btn_add.clicked.connect(self._add_row)
        btn_del.clicked.connect(self._delete_selected_rows)

        btns.addWidget(btn_add)
        btns.addWidget(btn_del)
        btns.addStretch()

        items_layout.addLayout(btns)

        splitter.addWidget(items_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)


        # ================= OK / CANCEL =================
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self
        )

        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)

        main.addWidget(self.buttons)

        if self.entry is None:
            self._add_row()

        self._tag_entry_fields()

    # ---------- helpers ----------
    def _label(self, obj):
        if not obj:
            return ""
        if self._lang == "ar" and getattr(obj, "name_ar", None):
            return obj.name_ar
        if self._lang == "tr" and getattr(obj, "name_tr", None):
            return obj.name_tr
        return getattr(obj, "name_en", None) or getattr(obj, "name_ar", None) or getattr(obj, "name_tr", None) or ""

    def _fill_clients(self):
        self.cmb_owner.clear()
        self.cmb_owner.addItem(self._("choose"), None)
        for c in self.clients:
            self.cmb_owner.addItem(self._label(c), getattr(c, "id", None))

    def _add_row(self, preset: dict | None = None):
        self.table.setUpdatesEnabled(False)

        r = self.table.rowCount()
        self.table.insertRow(r)

        # material
        cmb_mat = QComboBox()
        cmb_mat.addItem(self._("choose"), None)
        for m in self.materials:
            cmb_mat.addItem(self._label(m), getattr(m, "id", None))
        self.table.setCellWidget(r, 0, cmb_mat)

        # packaging_type
        cmb_pack = QComboBox()
        cmb_pack.addItem(self._("not_set"), None)
        for p in self.packaging_types:
            cmb_pack.addItem(self._label(p), getattr(p, "id", None))
        self.table.setCellWidget(r, 1, cmb_pack)

        # count
        sp_count = QSpinBox()
        sp_count.setMinimum(0)
        sp_count.setMaximum(10**9)
        self.table.setCellWidget(r, 2, sp_count)

        # net, gross
        ds_net = QDoubleSpinBox()
        ds_net.setDecimals(3)
        ds_net.setMinimum(0)
        ds_net.setMaximum(10**9)
        ds_gross = QDoubleSpinBox()
        ds_gross.setDecimals(3)
        ds_gross.setMinimum(0)
        ds_gross.setMaximum(10**9)
        self.table.setCellWidget(r, 3, ds_net)
        self.table.setCellWidget(r, 4, ds_gross)

        # mfg, exp
        de_mfg = QDateEdit()
        de_mfg.setCalendarPopup(True)
        de_mfg.setDisplayFormat("yyyy-MM-dd")
        de_exp = QDateEdit()
        de_exp.setCalendarPopup(True)
        de_exp.setDisplayFormat("yyyy-MM-dd")
        self.table.setCellWidget(r, 5, de_mfg)
        self.table.setCellWidget(r, 6, de_exp)

        # origin
        cmb_country = QComboBox()
        cmb_country.addItem(self._("not_set"), None)
        for co in self.countries:
            cmb_country.addItem(self._label(co), getattr(co, "id", None))
        self.table.setCellWidget(r, 7, cmb_country)

        # batch, notes
        le_batch = QLineEdit()
        self.table.setCellWidget(r, 8, le_batch)
        le_notes = QLineEdit()
        self.table.setCellWidget(r, 9, le_notes)

        # preset (for edit)
        if preset:
            idx = cmb_mat.findData(preset.get("material_id"))
            if idx != -1:
                cmb_mat.setCurrentIndex(idx)
            idx = cmb_pack.findData(preset.get("packaging_type_id"))
            if idx != -1:
                cmb_pack.setCurrentIndex(idx)
            sp_count.setValue(int(preset.get("count") or 0))
            ds_net.setValue(float(preset.get("net_weight_kg") or 0))
            ds_gross.setValue(float(preset.get("gross_weight_kg") or 0))
            if preset.get("mfg_date"):
                y, m, d = str(preset["mfg_date"]).split("-")
                de_mfg.setDate(QDate(int(y), int(m), int(d)))
            if preset.get("exp_date"):
                y, m, d = str(preset["exp_date"]).split("-")
                de_exp.setDate(QDate(int(y), int(m), int(d)))
            idx = cmb_country.findData(preset.get("origin_country_id"))
            if idx != -1:
                cmb_country.setCurrentIndex(idx)
            le_batch.setText(preset.get("batch_no") or "")
            le_notes.setText(preset.get("notes") or "")

        # بعد إضافة صف جديد، زامن مقاسات محرراته فورًا
        self.table.setUpdatesEnabled(True)

    def _delete_selected_rows(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    # ---------- prefill ----------
    def _prefill(self):
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
        idx = self.cmb_owner.findData(owner_id)
        if idx != -1:
            self.cmb_owner.setCurrentIndex(idx)

        self.te_notes.setPlainText(getattr(self.entry, "notes", "") or "")

        self.table.setRowCount(0)
        for it in getattr(self.entry, "items", []) or []:
            preset = {
                "material_id": getattr(it, "material_id", None),
                "packaging_type_id": getattr(it, "packaging_type_id", None),
                "count": getattr(it, "count", 0),
                "net_weight_kg": getattr(it, "net_weight_kg", 0),
                "gross_weight_kg": getattr(it, "gross_weight_kg", 0),
                "mfg_date": getattr(it, "mfg_date", None),
                "exp_date": getattr(it, "exp_date", None),
                "origin_country_id": getattr(it, "origin_country_id", None),
                "batch_no": getattr(it, "batch_no", ""),
                "notes": getattr(it, "notes", ""),
            }
            self._add_row(preset=preset)

        self._tag_entry_fields()

    # ---------- validation ----------
    def _accept(self):
        if self.cmb_owner.currentData() is None:
            self._warn(self._("please_choose_owner_client"))
            return

        if self.table.rowCount() == 0:
            self._warn(self._("please_add_at_least_one_item"))
            return

        for r in range(self.table.rowCount()):
            if self._cmb(r, 0).currentData() is None:
                self._warn(self._("material_required_row").format(row=r + 1))
                return

            if self._dspin(r, 4).value() < self._dspin(r, 3).value():
                self._warn(self._("gross_less_than_net_row").format(row=r + 1))
                return

        self.accept()

    # ---- Typed getters ----
    def _cmb(self, row: int, col: int) -> QComboBox:
        return cast(QComboBox, self.table.cellWidget(row, col))

    def _spin(self, row: int, col: int) -> QSpinBox:
        return cast(QSpinBox, self.table.cellWidget(row, col))

    def _dspin(self, row: int, col: int) -> QDoubleSpinBox:
        return cast(QDoubleSpinBox, self.table.cellWidget(row, col))

    def _dateedit(self, row: int, col: int) -> QDateEdit:
        return cast(QDateEdit, self.table.cellWidget(row, col))

    def _line(self, row: int, col: int) -> QLineEdit:
        return cast(QLineEdit, self.table.cellWidget(row, col))

    # ---------- output ----------
    def get_data(self):
        entry_qd = self.de_entry_date.date()
        header = {
            "entry_no": None,
            "entry_date": _qdate_to_py(entry_qd),
            "transport_unit_type": self.cmb_transport_type.currentData() or None,
            "transport_ref": (self.le_transport_ref.text().strip() or None),
            "seal_no": (self.le_seal_no.text().strip() or None),
            "owner_client_id": self.cmb_owner.currentData(),
            "notes": (self.te_notes.toPlainText().strip() or None),
        }

        items = []
        for r in range(self.table.rowCount()):
            de_mfg = self._dateedit(r, 5)
            de_exp = self._dateedit(r, 6)
            mfg = _qdate_to_py(de_mfg.date()) if de_mfg.date().isValid() else None
            exp = _qdate_to_py(de_exp.date()) if de_exp.date().isValid() else None
            items.append({
                "material_id":       self._cmb(r, 0).currentData(),
                "packaging_type_id": self._cmb(r, 1).currentData(),
                "count":             self._spin(r, 2).value(),
                "net_weight_kg":     float(self._dspin(r, 3).value()),
                "gross_weight_kg":   float(self._dspin(r, 4).value()),
                "mfg_date":          mfg,
                "exp_date":          exp,
                "origin_country_id": self._cmb(r, 7).currentData(),
                "batch_no":          self._twotext(self._line(r, 8)),
                "notes":             self._twotext(self._line(r, 9)),
            })
        return header, items

    @staticmethod
    def _twotext(w):
        try:
            return w.text().strip() or None
        except Exception:
            return None

    # ---------- minor tags ----------
    def _tag_entry_fields(self):
        for w in [
            self.le_transport_ref, self.le_seal_no, self.te_notes,
            self.de_entry_date, self.cmb_transport_type, self.cmb_owner
        ]:
            w.setProperty("variant", "entry")
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                ed = self.table.cellWidget(r, c)
                if ed:
                    ed.setProperty("variant", "entry")

    def _warn(self, msg):
        self.show_warning("warning", msg)
