from typing import TYPE_CHECKING, cast
from datetime import date as _date

from PySide6.QtCore import Qt, QDate
from ui.utils.wheel_blocker import block_wheel_in
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QLineEdit, QComboBox, QTextEdit, QDateEdit, QPushButton, QTableWidget,
    QSpinBox, QDoubleSpinBox, QSplitter, QGridLayout, QFrame,
    QAbstractItemView, QHeaderView, QSizePolicy
)

from core.base_dialog import BaseDialog
from ui.widgets.searchable_combo import SearchableComboBox


class _NoHoverTable(QTableWidget):
    """يمنع تحديد السطر بمجرد مرور الماوس فوق cellWidget."""
    def mouseMoveEvent(self, event):
        event.ignore()

    def viewportEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.HoverMove:
            return False
        return super().viewportEvent(event)
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
        main.setContentsMargins(16, 12, 16, 8)
        main.setSpacing(10)

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

        self.cmb_owner = SearchableComboBox(parent=self)
        self.cmb_owner.set_loader(
            loader=self._search_clients,
            display=self._client_display,
            value=lambda c: c.id,
        )

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

        self.table = _NoHoverTable(0, 10, self)
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


        # ================= Footer =================
        from PySide6.QtWidgets import QFrame as _QFrame
        sep_f = _QFrame(); sep_f.setFrameShape(_QFrame.HLine)
        sep_f.setObjectName("form-dialog-sep"); sep_f.setFixedHeight(1)

        footer_w = QWidget(); footer_w.setObjectName("form-dialog-footer")
        f_lay = QHBoxLayout(footer_w)
        f_lay.setContentsMargins(0, 10, 0, 2); f_lay.setSpacing(10)
        f_lay.addStretch()
        self.btn_cancel = QPushButton(self._("cancel"))
        self.btn_cancel.setObjectName("secondary-btn"); self.btn_cancel.setMinimumWidth(90)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton(self._("save"))
        self.btn_save.setObjectName("primary-btn"); self.btn_save.setMinimumWidth(90)
        self.btn_save.clicked.connect(self._accept)
        f_lay.addWidget(self.btn_cancel); f_lay.addWidget(self.btn_save)

        main.addWidget(sep_f)
        main.addWidget(footer_w)

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

    def _add_row(self, preset: dict | None = None):
        self.table.setUpdatesEnabled(False)

        r = self.table.rowCount()
        self.table.insertRow(r)

        # material — searchable
        cmb_mat = SearchableComboBox(parent=self.table)
        lang = self._lang
        cmb_mat.set_loader(
            loader=lambda q="": [
                m for m in self.materials
                if not q or q.lower() in self._label(m).lower()
            ],
            display=lambda m, _lang: self._label(m),
            value=lambda m: getattr(m, "id", None),
        )
        self.table.setCellWidget(r, 0, cmb_mat)

        # packaging_type
        cmb_pack = QComboBox()
        cmb_pack.setFocusPolicy(Qt.ClickFocus)
        cmb_pack.addItem(self._("not_set"), None)
        for p in self.packaging_types:
            cmb_pack.addItem(self._label(p), getattr(p, "id", None))
        self.table.setCellWidget(r, 1, cmb_pack)

        # count
        sp_count = QSpinBox()
        sp_count.setFocusPolicy(Qt.ClickFocus)
        sp_count.setMinimum(0)
        sp_count.setMaximum(10**9)
        self.table.setCellWidget(r, 2, sp_count)

        # net, gross
        ds_net = QDoubleSpinBox()
        ds_net.setFocusPolicy(Qt.ClickFocus)
        ds_net.setDecimals(3)
        ds_net.setMinimum(0)
        ds_net.setMaximum(10**9)
        ds_gross = QDoubleSpinBox()
        ds_gross.setFocusPolicy(Qt.ClickFocus)
        ds_gross.setDecimals(3)
        ds_gross.setMinimum(0)
        ds_gross.setMaximum(10**9)
        self.table.setCellWidget(r, 3, ds_net)
        self.table.setCellWidget(r, 4, ds_gross)

        # mfg, exp — with empty option
        def _make_date_edit():
            de = QDateEdit()
            de.setFocusPolicy(Qt.ClickFocus)
            de.setCalendarPopup(True)
            de.setDisplayFormat("yyyy-MM-dd")
            de.setSpecialValueText("—")          # نص عند القيمة الدنيا = فارغ
            de.setMinimumDate(QDate(2000, 1, 1)) # تاريخ "صفر" يعني لا تاريخ
            de.setDate(de.minimumDate())          # افتراضي: فارغ
            return de
        de_mfg = _make_date_edit()
        de_exp = _make_date_edit()
        self.table.setCellWidget(r, 5, de_mfg)
        self.table.setCellWidget(r, 6, de_exp)

        # origin
        cmb_country = QComboBox()
        cmb_country.setFocusPolicy(Qt.ClickFocus)
        cmb_country.addItem(self._("not_set"), None)
        for co in self.countries:
            cmb_country.addItem(self._label(co), getattr(co, "id", None))
        self.table.setCellWidget(r, 7, cmb_country)

        # batch, notes
        le_batch = QLineEdit()
        le_batch.setFocusPolicy(Qt.ClickFocus)
        self.table.setCellWidget(r, 8, le_batch)
        le_notes = QLineEdit()
        le_notes.setFocusPolicy(Qt.ClickFocus)
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
            def _set_date(de, val):
                if val:
                    try:
                        parts = str(val).split("-")
                        if len(parts) == 3:
                            de.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
                    except Exception:
                        pass
            _set_date(de_mfg, preset.get("mfg_date"))
            _set_date(de_exp, preset.get("exp_date"))
            idx = cmb_country.findData(preset.get("origin_country_id"))
            if idx != -1:
                cmb_country.setCurrentIndex(idx)
            le_batch.setText(preset.get("batch_no") or "")
            le_notes.setText(preset.get("notes") or "")

        # Wheel blocker على كل widgets الصف
        from ui.utils.wheel_blocker import block_wheel
        block_wheel(cmb_pack, sp_count, ds_net, ds_gross, cmb_country, de_mfg, de_exp)

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
        if owner_id:
            owner_obj = next((c for c in self.clients if getattr(c, "id", None) == owner_id), None)
            if owner_obj:
                self.cmb_owner.set_value(owner_id, display_text=self._label(owner_obj))

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
        if self.cmb_owner.current_value() is None:
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
            "owner_client_id": self.cmb_owner.current_value(),
            "notes": (self.te_notes.toPlainText().strip() or None),
        }

        items = []
        for r in range(self.table.rowCount()):
            de_mfg = self._dateedit(r, 5)
            de_exp = self._dateedit(r, 6)
            # التاريخ فارغ إذا كان عند minimumDate (special value)
            mfg = (_qdate_to_py(de_mfg.date())
                   if de_mfg.date().isValid() and de_mfg.date() != de_mfg.minimumDate()
                   else None)
            exp = (_qdate_to_py(de_exp.date())
                   if de_exp.date().isValid() and de_exp.date() != de_exp.minimumDate()
                   else None)
            # material_id: SearchableComboBox or regular QComboBox
            mat_widget = self.table.cellWidget(r, 0)
            if hasattr(mat_widget, "current_value"):
                mat_id = mat_widget.current_value()
            else:
                mat_id = self._cmb(r, 0).currentData()
            items.append({
                "material_id":       mat_id,
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