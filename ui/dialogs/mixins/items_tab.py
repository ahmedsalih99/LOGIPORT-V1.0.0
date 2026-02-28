from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING, cast

from PySide6.QtCore import Qt, QDate, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSplitter,
    QTableWidget, QTableWidgetItem, QComboBox, QDateEdit, QMessageBox, QDialog,
    QAbstractItemView, QMenu, QHeaderView
)
from PySide6.QtGui import QAction, QIcon

# ---------- Real DB models (SQLAlchemy) ----------
from database.models import (
    get_session_local,
    Material,
    PackagingType,
)

# Optional: Currency, PricingType may not be exported; handle gracefully
try:
    from database.models import Currency, PricingType
except Exception:
    Currency = None  # type: ignore[assignment]
    PricingType = None  # type: ignore[assignment]

# CRUD for entries (to fetch entry_no/items by entry id)
try:
    from database.crud.entries_crud import EntriesCRUD
except Exception:
    EntriesCRUD = None  # type: ignore[assignment]

if TYPE_CHECKING:
    # نصرّح بما نتوقّعه من الـ parent ليرضى الفاحص
    from PySide6.QtWidgets import QTabWidget


class _NoHoverTable(QTableWidget):
    """
    QTableWidget لا يغير الـ current row عند hover —
    يمنع تلوين السطر بمجرد مرور الماوس فوق cellWidget (combo/date).
    """
    def mouseMoveEvent(self, event):
        # نتجاهل mouseMoveEvent تماماً → لا تغيير للـ current item عند الـ hover
        # المستخدم يحدد السطر فقط بالنقر
        event.ignore()

    def viewportEvent(self, event):
        from PySide6.QtCore import QEvent
        # نمنع HoverMove من الوصول للـ viewport
        if event.type() == QEvent.Type.HoverMove:
            return False
        return super().viewportEvent(event)


class ItemsTabMixin:
    """
    جدول المواد للمعاملة — مع تحسينات UX و Context Menu
    """

    # نتوقّع وجود تابس ومترجم في الأب:
    tabs: "QTabWidget"  # يملك addTab(...)
    _lang: str = "ar"

    # 0 source | 1 truck | 2 material | 3 packaging | 4 qty | 5 gross | 6 net | 7 prod | 8 exp
    # 9 currency | 10 pricing_type | 11 unit_price | 12 total
    COL_SOURCE = 0;
    COL_TRUCK = 1;
    COL_MATERIAL = 2;
    COL_PACK = 3;
    COL_QTY = 4;
    COL_GROSS = 5;
    COL_NET = 6;
    COL_PROD = 7;
    COL_EXP = 8;
    COL_CURR = 9;
    COL_PTYPE = 10;
    COL_UNIT_PRICE = 11;
    COL_TOTAL = 12

    # نُعرّف خصائص الـ instance هنا لتفادي تحذير "defined outside __init__"
    _updating: bool = False
    _materials: List[tuple] = []
    _packs: List[tuple] = []
    _currencies: List[tuple] = []
    _pricing_types: List[tuple] = []

    # Fallback مترجم حتى لو ما كان عندك self._ في الأب
    def _(self, key: str) -> str:  # noqa: D401
        try:
            t = getattr(self, "translate", None)
            if callable(t):
                return t(key)  # type: ignore[misc]
            tr = getattr(self, "translator", None)
            if tr and callable(getattr(tr, "translate", None)):
                return tr.translate(key)  # type: ignore[attr-defined]
        except Exception:
            pass
        return key

    # ----------------------------- build UI -----------------------------
    def _build_items_tab(self) -> None:
        self._updating = False

        self.tab_items = QWidget()
        self.tab_items.setObjectName("items-tab")

        outer = QVBoxLayout(self.tab_items)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(12)

        # ================= Toolbar =================
        tools = QHBoxLayout()
        tools.setSpacing(8)

        self.btn_pick = QPushButton(self._("add_from_entries"))
        self.btn_pick.setObjectName("primary-btn")
        self.btn_pick.setToolTip(self._("add_from_entries") + " (Ctrl+E)")
        try:
            self.btn_pick.setIcon(QIcon.fromTheme("list-add"))
        except Exception:
            pass

        self.btn_add = QPushButton(self._("add_manual_item"))
        self.btn_add.setObjectName("primary-btn")
        self.btn_add.setToolTip(self._("add_manual_item") + " (Ctrl+N)")
        try:
            self.btn_add.setIcon(QIcon.fromTheme("document-new"))
        except Exception:
            pass

        self.btn_del = QPushButton(self._("delete_selected"))
        self.btn_del.setObjectName("danger-btn")
        self.btn_del.setToolTip(self._("delete_selected") + " (Del)")
        try:
            self.btn_del.setIcon(QIcon.fromTheme("edit-delete"))
        except Exception:
            pass

        self.btn_auto = QPushButton(self._("auto_price_all"))
        self.btn_auto.setObjectName("secondary-btn")
        self.btn_auto.setToolTip(self._("auto_price_all"))
        try:
            self.btn_auto.setIcon(QIcon.fromTheme("view-refresh"))
        except Exception:
            pass

        tools.addWidget(self.btn_pick)
        tools.addWidget(self.btn_add)
        tools.addWidget(self.btn_del)
        tools.addStretch()
        tools.addWidget(self.btn_auto)

        # ================= Splitter =================
        splitter = QSplitter(Qt.Vertical, self.tab_items)
        splitter.setObjectName("items-splitter")

        # -------- Top (Table) --------
        top = QWidget(self.tab_items)
        top.setObjectName("items-table-container")
        tl = QVBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(8)

        # -------- Bottom (Totals) --------
        bottom = QWidget(self.tab_items)
        bottom.setObjectName("items-totals-container")
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(12, 8, 12, 8)
        bl.setSpacing(16)

        # ================= Table =================
        self.tbl = _NoHoverTable(0, 13, self.tab_items)
        self.tbl.setObjectName("items-table")
        self.tbl.setHorizontalHeaderLabels([
            self._("source"), self._("truck_or_container_no"), self._("material"), self._("packaging_type"),
            self._("count"), self._("gross_weight_kg"), self._("net_weight_kg"),
            self._("production_date"), self._("expiry_date"),
            self._("currency"), self._("pricing_type"),
            self._("unit_price"), self._("total_price")
        ])

        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        # DoubleClicked | SelectedClicked | EditKeyPressed فقط — بدون CurrentChanged
        # AllEditTriggers كانت تُحدِّد السطر بمجرد مرور الماوس
        self.tbl.setEditTriggers(
            QAbstractItemView.DoubleClicked |
            QAbstractItemView.SelectedClicked |
            QAbstractItemView.EditKeyPressed
        )
        self.tbl.setAlternatingRowColors(True)

        # Header + row height (ثيم)
        hdr = self.tbl.horizontalHeader()
        hdr.setStretchLastSection(True)
        hdr.setDefaultAlignment(Qt.AlignCenter)
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        self.tbl.verticalHeader().setDefaultSectionSize(46)

        # Context menu
        self.tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl.customContextMenuRequested.connect(self._show_table_context_menu)

        self.tbl.itemChanged.connect(self._on_cell_changed)

        # ================= Totals =================
        self.lbl_q = QLabel(self._("count") + ": 0")
        self.lbl_q.setObjectName("total-label")

        self.lbl_g = QLabel(self._("gross_weight_kg") + ": 0")
        self.lbl_g.setObjectName("total-label")

        self.lbl_n = QLabel(self._("net_weight_kg") + ": 0")
        self.lbl_n.setObjectName("total-label")

        self.lbl_v = QLabel(self._("total_price") + ": 0")
        self.lbl_v.setObjectName("total-value-label")

        # ================= Layout assemble =================
        tl.addLayout(tools)
        tl.addWidget(self.tbl)

        bl.addStretch()
        bl.addWidget(self.lbl_q)
        bl.addWidget(self.lbl_g)
        bl.addWidget(self.lbl_n)
        bl.addWidget(self.lbl_v)

        splitter.addWidget(top)
        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        outer.addWidget(splitter)

        # ================= Add tab =================
        tabs = cast("QTabWidget", getattr(self, "tabs"))
        tabs.addTab(self.tab_items, self._("items"))

        # ================= Load caches =================
        self._materials = self._load_table(Material)
        self._packs = self._load_table(PackagingType)
        self._currencies = self._load_table(Currency) if Currency else []
        self._pricing_types = self._load_table(PricingType) if PricingType else []

        # ================= Signals =================
        self.btn_add.clicked.connect(self._add_manual_row)
        self.btn_del.clicked.connect(self._delete_selected)
        self.btn_pick.clicked.connect(self._pick_entries)
        self.btn_auto.clicked.connect(self._auto_price_all)

    # ----------------------------- Context Menu -----------------------------
    def _show_table_context_menu(self, pos: QPoint):
        """عرض قائمة سياقية عند النقر بالزر الأيمن على الجدول"""
        if not hasattr(self, 'tbl'):
            return

        # تحديد الصف المحدد
        item = self.tbl.itemAt(pos)
        if not item:
            return

        row = item.row()

        # إنشاء القائمة
        menu = QMenu(self.tbl)
        menu.setObjectName("context-menu")

        # خيار: إضافة صف جديد
        add_action = QAction(self._("add_manual_item"), menu)
        try:
            add_action.setIcon(QIcon.fromTheme("list-add"))
        except:
            pass
        add_action.triggered.connect(self._add_manual_row)
        menu.addAction(add_action)

        # خيار: حذف الصف الحالي
        delete_action = QAction(self._("delete_selected"), menu)
        try:
            delete_action.setIcon(QIcon.fromTheme("edit-delete"))
        except:
            pass
        delete_action.triggered.connect(self._delete_selected)
        menu.addAction(delete_action)

        menu.addSeparator()

        # خيار: تكرار الصف
        duplicate_action = QAction(self._("duplicate_row"), menu)
        try:
            duplicate_action.setIcon(QIcon.fromTheme("edit-copy"))
        except:
            pass
        duplicate_action.triggered.connect(lambda: self._duplicate_row(row))
        menu.addAction(duplicate_action)

        menu.addSeparator()

        # خيار: مسح القيم في الصف
        clear_action = QAction(self._("clear_row_values"), menu)
        try:
            clear_action.setIcon(QIcon.fromTheme("edit-clear"))
        except:
            pass
        clear_action.triggered.connect(lambda: self._clear_row(row))
        menu.addAction(clear_action)

        # عرض القائمة
        menu.exec(self.tbl.viewport().mapToGlobal(pos))

    def _duplicate_row(self, row: int):
        """تكرار صف موجود"""
        if not hasattr(self, 'tbl') or row < 0 or row >= self.tbl.rowCount():
            return

        # إضافة صف جديد
        new_row = self.tbl.rowCount()
        self.tbl.insertRow(new_row)

        # نسخ القيم من الصف الأصلي
        for col in range(self.tbl.columnCount()):
            orig_item = self.tbl.item(row, col)
            if orig_item:
                new_item = QTableWidgetItem(orig_item.text())
                new_item.setData(Qt.ItemDataRole.UserRole, orig_item.data(Qt.ItemDataRole.UserRole))
                self.tbl.setItem(new_row, col, new_item)
            else:
                # نسخ الـ widget إذا كان الـ cell يحتوي widget (combo/date)
                orig_widget = self.tbl.cellWidget(row, col)
                if isinstance(orig_widget, QComboBox):
                    new_combo = QComboBox()
                    new_combo.setFocusPolicy(Qt.ClickFocus)
                    for i in range(orig_widget.count()):
                        new_combo.addItem(orig_widget.itemText(i), orig_widget.itemData(i))
                    new_combo.setCurrentIndex(orig_widget.currentIndex())
                    self.tbl.setCellWidget(new_row, col, new_combo)
                elif isinstance(orig_widget, QDateEdit):
                    new_date = QDateEdit()
                    new_date.setFocusPolicy(Qt.ClickFocus)
                    new_date.setDate(orig_widget.date())
                    self.tbl.setCellWidget(new_row, col, new_date)

        self._recalc_totals()

    def _clear_row(self, row: int):
        """مسح القيم في صف معين"""
        if not hasattr(self, 'tbl') or row < 0 or row >= self.tbl.rowCount():
            return

        # مسح النصوص
        for col in [self.COL_SOURCE, self.COL_TRUCK, self.COL_QTY,
                    self.COL_GROSS, self.COL_NET, self.COL_UNIT_PRICE, self.COL_TOTAL]:
            item = self.tbl.item(row, col)
            if item:
                item.setText("")

        # إعادة تعيين ComboBoxes للخيار الأول
        for col in [self.COL_MATERIAL, self.COL_PACK, self.COL_CURR, self.COL_PTYPE]:
            widget = self.tbl.cellWidget(row, col)
            if isinstance(widget, QComboBox) and widget.count() > 0:
                widget.setCurrentIndex(0)

        # إعادة تعيين التواريخ للتاريخ الحالي
        for col in [self.COL_PROD, self.COL_EXP]:
            widget = self.tbl.cellWidget(row, col)
            if isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())

        self._recalc_totals()

    # --------------------------- DB helpers ---------------------------
    def _load_table(self, model_cls) -> List[tuple]:
        """
        يحمّل الجدول ويحفظ بيانات كل صف كـ dict بدل ORM object
        لتجنب DetachedInstanceError بعد إغلاق الـ session.
        """
        try:
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                rows = s.query(model_cls).all()
                # نحوّل كل row لـ dict داخل الـ session (قبل إغلاقها)
                snapshots = []
                for r in rows:
                    d = {c.name: getattr(r, c.name, None)
                         for c in r.__table__.columns}
                    snapshots.append(d)
            lang = getattr(self, "_lang", "ar") or "ar"
            lang_fields = [f"name_{lang}", "name_en", "name_ar", "name_tr", "code", "name"]
            result: List[tuple] = []
            for d in snapshots:
                rid = d.get("id")
                label = None
                for f in lang_fields:
                    label = d.get(f)
                    if label:
                        break
                if not label:
                    label = str(rid)
                result.append((str(label), rid, d))
            return result
        except Exception:
            return []

    def _items_from_cache(self, cache, *, role="generic") -> List[tuple]:
        if not cache:
            return [(self._("select"), None)]
        lang = getattr(self, "_lang", "ar") or "ar"
        out: List[tuple] = []
        for _label, rid, row in cache or []:
            # row is now a dict (after _load_table fix)
            _g = (row.get if isinstance(row, dict) else lambda k, d=None: getattr(row, k, d))
            name = None
            for f in (f"name_{lang}", "name_en", "name_ar", "name_tr", "name"):
                name = _g(f)
                if name:
                    break
            code = _g("code")
            if role in ("currency", "ptype"):
                label = str(code) if code else (name or rid)
                if name and code and str(name).strip().lower() not in (str(code).strip().lower(),):
                    label = f"{code} — {name}"
            else:
                label = name or code or str(rid)
            out.append((str(label), rid))
        return out

    # ... باقي الكود كما هو (نفس المنطق من الملف الأصلي) ...
    # هنا سأضع الدوال الأساسية فقط لتوفير المساحة

    def _add_manual_row(self) -> None:
        """إضافة صف يدوي فارغ"""
        r = self.tbl.rowCount()
        self.tbl.insertRow(r)

        self._set_text(r, self.COL_SOURCE, "manual")
        self._set_text(r, self.COL_TRUCK, "")
        self._set_combo(r, self.COL_MATERIAL, self._items_from_cache(self._materials), None)
        self._set_combo(r, self.COL_PACK, self._items_from_cache(self._packs), None)
        self._set_text(r, self.COL_QTY, "")
        self._set_text(r, self.COL_GROSS, "")
        self._set_text(r, self.COL_NET, "")
        self._set_date(r, self.COL_PROD, QDate.currentDate())
        self._set_date(r, self.COL_EXP, QDate.currentDate())
        self._set_combo(r, self.COL_CURR, self._items_from_cache(self._currencies, role="currency"), None)
        self._set_combo(r, self.COL_PTYPE, self._items_from_cache(self._pricing_types, role="ptype"), None)
        self._set_text(r, self.COL_UNIT_PRICE, "")
        self._set_text(r, self.COL_TOTAL, "0.00")

    def _delete_selected(self) -> None:
        """حذف الصف المحدد"""
        sel = self.tbl.selectedIndexes()
        if not sel:
            return
        rows = sorted(set(idx.row() for idx in sel), reverse=True)
        for r in rows:
            self.tbl.removeRow(r)
        self._recalc_totals()

    def _pick_entries(self) -> None:
        """فتح dialog لاختيار الإدخالات وإضافة موادها للجدول"""

        # محاولة استيراد أي من الـ dialogs المتاحة
        dialog_class = None

        # حاول الـ dialog الجديد أولاً
        try:
            from ui.dialogs.pick_entries_dialog import PickEntriesDialog
            dialog_class = PickEntriesDialog
        except ImportError:
            pass

        # إذا ما اشتغل، حاول القديم
        if not dialog_class:
            try:
                from ui.dialogs.pick_entries_dialog import EntriesPickerDialog
                dialog_class = EntriesPickerDialog
            except ImportError:
                pass

        # إذا ما في أي dialog
        if not dialog_class:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.tab_items if hasattr(self, 'tab_items') else None,
                self._("error"),
                "Cannot find pick_entries_dialog. Please check installation."
            )
            return

        # فتح الـ dialog
        try:
            dlg = dialog_class(parent=self.tab_items if hasattr(self, 'tab_items') else None)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.tab_items if hasattr(self, 'tab_items') else None,
                self._("error"),
                f"Failed to open dialog: {e}"
            )
            return

        # التعامل مع EntriesPickerDialog (القديم) الذي يستخدم Signal
        if dialog_class.__name__ == 'EntriesPickerDialog':
            selected_entries_data = []

            def on_picked(entries_list):
                nonlocal selected_entries_data
                selected_entries_data = entries_list

            dlg.picked.connect(on_picked)

            if dlg.exec() != QDialog.Accepted:
                return

            if not selected_entries_data:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self.tab_items if hasattr(self, 'tab_items') else None,
                    self._("info"),
                    self._("no_entries_selected")
                )
                return

            # معالجة البيانات من EntriesPickerDialog
            self._process_entries_picker_data(selected_entries_data)

        # التعامل مع PickEntriesDialog (الجديد)
        else:
            if dlg.exec() != QDialog.Accepted:
                return

            selected_entries = dlg.get_selected_entries()

            if not selected_entries:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self.tab_items if hasattr(self, 'tab_items') else None,
                    self._("info"),
                    self._("no_entries_selected")
                )
                return

            # معالجة البيانات من PickEntriesDialog
            self._process_pick_entries_data(selected_entries)

        # رسالة نجاح
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            self.tab_items if hasattr(self, 'tab_items') else None,
            self._("success"),
            self._("entries_items_added_successfully")
        )

    def _process_entries_picker_data(self, selected_entries_data):
        """
        معالجة البيانات من EntriesPickerDialog
        Format: [{"entry_id": 123, "entry_no": "ABC", "items": [...]}]
        """
        from PySide6.QtCore import QDate, Qt

        for entry_data in selected_entries_data:
            entry_id = entry_data.get("entry_id")
            entry_no = entry_data.get("entry_no") or entry_data.get("truck_or_container_no", "")
            items = entry_data.get("items", [])

            for item in items:
                r = self.tbl.rowCount()
                self.tbl.insertRow(r)

                self._set_text(r, self.COL_SOURCE, "entry")
                self._set_text(r, self.COL_TRUCK, str(entry_no))

                truck_item = self.tbl.item(r, self.COL_TRUCK)
                if truck_item and entry_id:
                    meta = {"entry_id": entry_id}
                    item_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
                    if item_id:
                        meta["entry_item_id"] = item_id
                    truck_item.setData(Qt.ItemDataRole.UserRole, meta)

                def get_val(key, default=None):
                    if isinstance(item, dict):
                        return item.get(key, default)
                    return getattr(item, key, default)

                material_id = get_val("material_id")
                self._set_combo(r, self.COL_MATERIAL,
                                self._items_from_cache(self._materials), material_id)

                pack_id = get_val("packaging_type_id")
                self._set_combo(r, self.COL_PACK,
                                self._items_from_cache(self._packs), pack_id)

                # ✅ entry_items يستخدم "count" — هذا صحيح
                qty = get_val("count", 0) or 0
                gross = get_val("gross_weight_kg", 0) or 0
                net = get_val("net_weight_kg", 0) or 0
                self._set_text(r, self.COL_QTY, str(qty) if qty else "")
                self._set_text(r, self.COL_GROSS, str(gross) if gross else "")
                self._set_text(r, self.COL_NET, str(net) if net else "")

                prod_date = get_val("production_date") or get_val("mfg_date")
                exp_date = get_val("expiry_date") or get_val("exp_date")

                if prod_date and hasattr(prod_date, "year"):
                    self._set_date(r, self.COL_PROD,
                                   QDate(prod_date.year, prod_date.month, prod_date.day))
                else:
                    self._set_date(r, self.COL_PROD, QDate.currentDate())

                if exp_date and hasattr(exp_date, "year"):
                    self._set_date(r, self.COL_EXP,
                                   QDate(exp_date.year, exp_date.month, exp_date.day))
                else:
                    self._set_date(r, self.COL_EXP, QDate.currentDate())

                curr_id = get_val("currency_id")
                ptype_id = get_val("pricing_type_id")
                self._set_combo(r, self.COL_CURR,
                                self._items_from_cache(self._currencies, role="currency"), curr_id)
                self._set_combo(r, self.COL_PTYPE,
                                self._items_from_cache(self._pricing_types, role="ptype"), ptype_id)

                unit_price = get_val("unit_price", 0) or 0
                self._set_text(r, self.COL_UNIT_PRICE,
                               str(unit_price) if unit_price else "")

                self._recalc_row(r)

        self._recalc_totals()

    def _process_pick_entries_data(self, selected_entries):
        """
        معالجة البيانات من PickEntriesDialog
        Format: [(entry_obj, [items...])] or [entry_obj_with_items_attr]
        """
        from PySide6.QtCore import QDate, Qt

        for entry in selected_entries:
            # entry قد يكون tuple (entry_dict, items) أو ORM object
            if isinstance(entry, tuple):
                entry_obj, items = entry
            else:
                entry_obj = entry
                items = getattr(entry, "items", []) or []

            # entry_obj قد يكون dict أو ORM object
            _eg = (entry_obj.get if isinstance(entry_obj, dict)
                   else lambda k, d=None: getattr(entry_obj, k, d))

            entry_id = _eg("id")
            entry_no = str(_eg("entry_no", "") or "")
            transport_ref = str(_eg("transport_ref", "") or "")
            display_ref = transport_ref or entry_no

            for item in items:
                r = self.tbl.rowCount()
                self.tbl.insertRow(r)

                # item قد يكون dict أو ORM object
                _g = (item.get if isinstance(item, dict) else lambda k, d=None: getattr(item, k, d))

                self._set_text(r, self.COL_SOURCE, "entry")
                self._set_text(r, self.COL_TRUCK, display_ref)

                truck_item = self.tbl.item(r, self.COL_TRUCK)
                if truck_item and entry_id:
                    meta = {"entry_id": entry_id}
                    item_id = _g("id")
                    if item_id:
                        meta["entry_item_id"] = item_id
                    truck_item.setData(Qt.ItemDataRole.UserRole, meta)

                material_id = _g("material_id")
                self._set_combo(r, self.COL_MATERIAL,
                                self._items_from_cache(self._materials), material_id)

                pack_id = _g("packaging_type_id")
                self._set_combo(r, self.COL_PACK,
                                self._items_from_cache(self._packs), pack_id)

                qty = _g("count", 0) or 0
                gross = _g("gross_weight_kg", 0) or 0
                net = _g("net_weight_kg", 0) or 0
                self._set_text(r, self.COL_QTY, str(qty) if qty else "")
                self._set_text(r, self.COL_GROSS, str(gross) if gross else "")
                self._set_text(r, self.COL_NET, str(net) if net else "")

                prod_date = _g("production_date") or _g("mfg_date")
                exp_date = _g("expiry_date") or _g("exp_date")

                if prod_date and hasattr(prod_date, "year"):
                    self._set_date(r, self.COL_PROD,
                                   QDate(prod_date.year, prod_date.month, prod_date.day))
                else:
                    self._set_date(r, self.COL_PROD, QDate.currentDate())

                if exp_date and hasattr(exp_date, "year"):
                    self._set_date(r, self.COL_EXP,
                                   QDate(exp_date.year, exp_date.month, exp_date.day))
                else:
                    self._set_date(r, self.COL_EXP, QDate.currentDate())

                curr_id = _g("currency_id")
                ptype_id = _g("pricing_type_id")
                self._set_combo(r, self.COL_CURR,
                                self._items_from_cache(self._currencies, role="currency"), curr_id)
                self._set_combo(r, self.COL_PTYPE,
                                self._items_from_cache(self._pricing_types, role="ptype"), ptype_id)

                unit_price = _g("unit_price", 0) or 0
                self._set_text(r, self.COL_UNIT_PRICE,
                               str(unit_price) if unit_price else "")

                self._recalc_row(r)

        self._recalc_totals()

    def _on_cell_changed(self, item: QTableWidgetItem) -> None:
        """معالجة تغيير الخلية"""
        if self._updating:
            return
        r = item.row()
        c = item.column()
        # ✅ أُضيف: COL_GROSS و COL_NET لأن الصيغة تعتمد على الأوزان
        if c in (self.COL_QTY, self.COL_GROSS, self.COL_NET, self.COL_UNIT_PRICE):
            self._recalc_row(r)

    def _recalc_totals(self) -> None:
        """تحديث ملصقات الإجماليات في أسفل جدول الأقلام."""
        total_qty = total_gross = total_net = total_val = 0.0
        try:
            for r in range(self.tbl.rowCount()):
                total_qty += self._num(r, self.COL_QTY)
                total_gross += self._num(r, self.COL_GROSS)
                total_net += self._num(r, self.COL_NET)
                total_val += self._num(r, self.COL_TOTAL)
        except Exception:
            pass
        try:
            _ = getattr(self, "_", lambda k: k)
            if hasattr(self, "lbl_q"):
                self.lbl_q.setText(f'{_("count")}: {total_qty:,.3f}')
            if hasattr(self, "lbl_g"):
                self.lbl_g.setText(f'{_("gross_weight_kg")}: {total_gross:,.3f}')
            if hasattr(self, "lbl_n"):
                self.lbl_n.setText(f'{_("net_weight_kg")}: {total_net:,.3f}')
            if hasattr(self, "lbl_v"):
                self.lbl_v.setText(f'{_("total_price")}: {total_val:,.2f}')
        except Exception:
            pass

    def _recalc_row(self, row: int) -> None:
        """إعادة حساب الإجمالي للصف حسب نوع التسعير الفعلي"""
        try:
            qty = self._num(row, self.COL_QTY)
            gross = self._num(row, self.COL_GROSS)
            net = self._num(row, self.COL_NET)
            price = self._num(row, self.COL_UNIT_PRICE)

            ptype_combo = self.tbl.cellWidget(row, self.COL_PTYPE)
            pid = ptype_combo.currentData() if ptype_combo else None

            total = self._compute_line_total(pid, qty, gross, net, price)
            self._set_text(row, self.COL_TOTAL, f"{total:.2f}")
            self._recalc_totals()
        except Exception:
            pass

    def _compute_line_total(
            self,
            pricing_type_id,
            qty: float,
            gross: float,
            net: float,
            price: float,
    ) -> float:
        """
        حساب إجمالي السطر حسب نوع التسعير.
        الأولوية: compute_by من DB → fallback بالكود → qty×price
        """
        if price == 0:
            return 0.0

        pt_id = pricing_type_id
        if pt_id:
            for _label, rid, row_obj in (self._pricing_types or []):
                if rid != pt_id:
                    continue
                # row_obj هو dict (من _load_table)
                if isinstance(row_obj, dict):
                    _g = row_obj.get
                else:
                    _g = lambda k, df="": getattr(row_obj, k, df)

                cb = str(_g("compute_by", "") or "").upper()
                dv = float(_g("divisor", 1.0) or 1.0) or 1.0

                # حساب حسب compute_by
                if cb == "QTY":
                    return (qty / dv) * price
                if cb == "NET":
                    return (net / dv) * price
                if cb == "GROSS":
                    return (gross / dv) * price

                # compute_by فارغ → fallback بالكود
                code = str(_g("code", "") or "").upper()
                if code in ("UNIT", "PCS", "PIECE"):
                    return qty * price
                if code in ("KG", "KILO", "KG_NET"):
                    return net * price
                if code in ("KG_GROSS", "GROSS_KG", "BRUT"):
                    return gross * price
                if code in ("TON", "T", "MT", "TON_NET"):
                    return (net / 1000.0) * price
                if code in ("TON_GROSS",):
                    return (gross / 1000.0) * price
                break  # نوع موجود لكن غير معروف

        # لا نوع تسعير → كمية × سعر
        return qty * price

    # Helper methods
    def _num(self, row: int, col: int) -> float:
        """قراءة رقم من خلية"""
        item = self.tbl.item(row, col)
        if not item:
            return 0.0
        try:
            return float(item.text().replace(",", ""))
        except:
            return 0.0

    def _set_text(self, row: int, col: int, value: Any) -> None:
        """كتابة نص في خلية"""
        self._updating = True
        item = self.tbl.item(row, col)
        if not item:
            item = QTableWidgetItem()
            self.tbl.setItem(row, col, item)
        item.setText(str(value) if value not in (None, "") else "")
        self._updating = False

    def _set_combo(self, row: int, col: int, items: List[tuple], selected_id: Any) -> None:
        combo = QComboBox()
        combo.setObjectName("table-combo")
        combo.setMinimumHeight(38)
        combo.setFocusPolicy(Qt.ClickFocus)  # لا يأخذ focus بالـ hover → يمنع تحديد السطر

        for label, rid in items:
            combo.addItem(str(label), rid)

        if selected_id is not None:
            for i in range(combo.count()):
                if combo.itemData(i) == selected_id:
                    combo.setCurrentIndex(i)
                    break

        # ✅ ربط signal: تغيير نوع التسعير أو العملة يُعيد حساب الإجمالي فوراً
        if col in (self.COL_PTYPE, self.COL_CURR):
            combo.currentIndexChanged.connect(
                lambda _idx, r=row: self._recalc_row(r)
            )

        self.tbl.setCellWidget(row, col, combo)

    def _set_date(self, row: int, col: int, date: QDate) -> None:
        de = QDateEdit()
        de.setObjectName("table-date")
        de.setMinimumHeight(38)
        de.setFocusPolicy(Qt.ClickFocus)  # نفس السبب — لا يأخذ focus بالـ hover
        de.setDisplayFormat("yyyy-MM-dd")
        de.setCalendarPopup(True)
        de.setDate(date)
        self.tbl.setCellWidget(row, col, de)

    def get_items_data(self) -> List[Dict[str, Any]]:
        """جمع بيانات الجدول للحفظ — جميع المفاتيح متوافقة مع CRUD"""
        data = []
        for r in range(self.tbl.rowCount()):
            source = self.tbl.item(r, self.COL_SOURCE)
            source_text = source.text() if source else "manual"

            truck = self.tbl.item(r, self.COL_TRUCK)
            truck_text = truck.text() if truck else ""

            mat_combo = self.tbl.cellWidget(r, self.COL_MATERIAL)
            pack_combo = self.tbl.cellWidget(r, self.COL_PACK)
            curr_combo = self.tbl.cellWidget(r, self.COL_CURR)
            ptype_combo = self.tbl.cellWidget(r, self.COL_PTYPE)
            prod_widget = self.tbl.cellWidget(r, self.COL_PROD)
            exp_widget = self.tbl.cellWidget(r, self.COL_EXP)

            rec = {
                "source_type": source_text,
                "transport_ref": truck_text,
                "material_id": mat_combo.currentData() if mat_combo else None,
                "packaging_type_id": pack_combo.currentData() if pack_combo else None,
                # ✅ تم التصحيح: "count" → "quantity" ليتوافق مع CRUD و TransactionItem
                "quantity": self._num(r, self.COL_QTY),
                "gross_weight_kg": self._num(r, self.COL_GROSS),
                "net_weight_kg": self._num(r, self.COL_NET),
                "production_date": prod_widget.date().toPython() if prod_widget else None,
                "expiry_date": exp_widget.date().toPython() if exp_widget else None,
                "currency_id": curr_combo.currentData() if curr_combo else None,
                "pricing_type_id": ptype_combo.currentData() if ptype_combo else None,
                "unit_price": self._num(r, self.COL_UNIT_PRICE),
                # نبقي total_price أيضاً لأن CRUD يقبل كلاهما (line_total, total_price)
                "total_price": self._num(r, self.COL_TOTAL),
                "is_manual": (source_text == "manual"),
            }

            # إضافة entry_id / entry_item_id من الـ UserRole metadata
            meta = truck.data(Qt.ItemDataRole.UserRole) if truck else None
            if isinstance(meta, dict):
                if "entry_id" in meta:
                    rec["entry_id"] = meta["entry_id"]
                if "entry_item_id" in meta:
                    rec["entry_item_id"] = meta["entry_item_id"]

            # تجاهل الصفوف الفارغة (لا مادة ولا كمية)
            if rec["material_id"] is None and rec["quantity"] == 0.0:
                continue

            data.append(rec)

        return data

    def prefill_items(self, trx) -> None:
        """تعبئة الجدول من معاملة موجودة (ORM object أو dict)"""
        self.tbl.setRowCount(0)
        if not trx:
            self._recalc_totals()
            return

        # استخرج قائمة البنود (items) من الكائن أو القاموس
        get = lambda o, k, d=None: o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)

        items = get(trx, "items", None)
        if items is None:
            # محاولة احتياطية: اجلب من قاعدة البيانات مباشرة
            try:
                from database.crud.transactions_crud import TransactionsCRUD
                trx_id = get(trx, "id", None)
                if trx_id:
                    crud = TransactionsCRUD()
                    result = crud.get_with_items(int(trx_id))
                    if result:
                        _, items = result
            except Exception:
                items = []

        if not items:
            self._recalc_totals()
            return

        self.tbl.blockSignals(True)
        try:
            for it in items:
                r = self.tbl.rowCount()
                self.tbl.insertRow(r)

                # نوع المصدر
                src = get(it, "source_type", None) or ("manual" if get(it, "is_manual", False) else "entry")
                self._set_text(r, self.COL_SOURCE, src)

                # رقم الشاحنة/الكونتينر
                transport = get(it, "transport_ref", "") or ""
                self._set_text(r, self.COL_TRUCK, transport)

                # خزّن meta (entry_id, entry_item_id) في UserRole
                entry_id = get(it, "entry_id", None)
                entry_item_id = get(it, "entry_item_id", None)
                if entry_id or entry_item_id:
                    truck_cell = self.tbl.item(r, self.COL_TRUCK)
                    if truck_cell:
                        meta = {}
                        if entry_id:      meta["entry_id"] = entry_id
                        if entry_item_id: meta["entry_item_id"] = entry_item_id
                        truck_cell.setData(Qt.ItemDataRole.UserRole, meta)

                # المادة
                self._set_combo(r, self.COL_MATERIAL,
                                self._items_from_cache(self._materials),
                                get(it, "material_id", None))

                # نوع التعبئة
                self._set_combo(r, self.COL_PACK,
                                self._items_from_cache(self._packs),
                                get(it, "packaging_type_id", None))

                # الكمية والأوزان
                qty = get(it, "quantity", None) or get(it, "count", 0)
                gross = get(it, "gross_weight_kg", 0)
                net = get(it, "net_weight_kg", 0)
                self._set_text(r, self.COL_QTY, str(float(qty or 0)))
                self._set_text(r, self.COL_GROSS, str(float(gross or 0)))
                self._set_text(r, self.COL_NET, str(float(net or 0)))

                # تاريخ الإنتاج
                prod_date = get(it, "production_date", None)
                if prod_date and hasattr(prod_date, "year"):
                    self._set_date(r, self.COL_PROD, QDate(prod_date.year, prod_date.month, prod_date.day))
                else:
                    self._set_date(r, self.COL_PROD, QDate.currentDate())

                # تاريخ الانتهاء
                exp_date = get(it, "expiry_date", None)
                if exp_date and hasattr(exp_date, "year"):
                    self._set_date(r, self.COL_EXP, QDate(exp_date.year, exp_date.month, exp_date.day))
                else:
                    self._set_date(r, self.COL_EXP, QDate.currentDate())

                # العملة
                self._set_combo(r, self.COL_CURR,
                                self._items_from_cache(self._currencies, role="currency"),
                                get(it, "currency_id", None))

                # نوع التسعير
                self._set_combo(r, self.COL_PTYPE,
                                self._items_from_cache(self._pricing_types, role="ptype"),
                                get(it, "pricing_type_id", None))

                # السعر الوحدوي
                unit_price = get(it, "unit_price", 0) or 0
                self._set_text(r, self.COL_UNIT_PRICE, str(float(unit_price)))

                # الإجمالي
                line_total = get(it, "line_total", None) or get(it, "total_price", None)
                if line_total is not None:
                    self._set_text(r, self.COL_TOTAL, f"{float(line_total):.2f}")
                else:
                    self._recalc_row(r)

        finally:
            self.tbl.blockSignals(False)

        self._recalc_totals()

    def _auto_price_all(self) -> None:
        """جلب الأسعار من جدول pricing ثم إعادة حساب الإجماليات"""
        # 1. اجلب seller/buyer من نافذة المعاملة
        seller_id = None
        buyer_id  = None
        try:
            # cmb_exporter / cmb_importer موجودة في PartiesGeoTabMixin
            if hasattr(self, "cmb_exporter"):
                seller_id = self.cmb_exporter.currentData()
            if hasattr(self, "cmb_importer"):
                buyer_id = self.cmb_importer.currentData()
        except Exception:
            pass

        # 2. جلب طريقة التسليم من نافذة المعاملة
        delivery_method_id = None
        try:
            if hasattr(self, "cmb_delivery"):
                delivery_method_id = self.cmb_delivery.currentData()
        except Exception:
            pass

        # 3. لو ما في seller/buyer → فقط أعد حساب الإجمالي بالسعر المدخل
        if not seller_id and not buyer_id:
            for r in range(self.tbl.rowCount()):
                self._recalc_row(r)
            return

        # 4. جلب الأسعار من DB
        fetched = 0
        try:
            from services.pricing_service import PricingService
            svc = PricingService()

            for row in range(self.tbl.rowCount()):
                mat_combo   = self.tbl.cellWidget(row, self.COL_MATERIAL)
                ptype_combo = self.tbl.cellWidget(row, self.COL_PTYPE)
                curr_combo  = self.tbl.cellWidget(row, self.COL_CURR)

                material_id     = mat_combo.currentData()   if mat_combo   else None
                pricing_type_id = ptype_combo.currentData() if ptype_combo else None
                currency_id     = curr_combo.currentData()  if curr_combo  else None

                if not material_id or not pricing_type_id or not currency_id:
                    self._recalc_row(row)
                    continue

                p = svc.find_best_price(
                    seller_company_id = seller_id or 0,
                    buyer_company_id  = buyer_id  or 0,
                    material_id       = material_id,
                    pricing_type_id   = pricing_type_id,
                    currency_id       = currency_id,
                    delivery_method_id= delivery_method_id,
                )
                if p is not None:
                    price_val = float(getattr(p, "price", 0) or 0)
                    self._set_text(row, self.COL_UNIT_PRICE, f"{price_val:.4f}".rstrip("0").rstrip("."))
                    fetched += 1

                self._recalc_row(row)

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("auto_price error: %s", e)
            # fallback: recalc فقط
            for r in range(self.tbl.rowCount()):
                self._recalc_row(r)

        # 5. إشعار المستخدم
        try:
            from PySide6.QtWidgets import QMessageBox
            parent = self.tab_items if hasattr(self, "tab_items") else None
            _ = getattr(self, "_", lambda k: k)
            if fetched > 0:
                QMessageBox.information(parent, _("success"),
                    _("auto_price_applied").format(count=fetched) if "{count}" in _("auto_price_applied")
                    else f"{_('auto_price_applied')} ({fetched})")
            else:
                QMessageBox.warning(parent, _("no_price_found"),
                    _("no_price_found_for_items"))
        except Exception:
            pass

    def refresh_language_items(self) -> None:
        """تحديث اللغة"""
        self._materials = self._load_table(Material)
        self._packs = self._load_table(PackagingType)
        self._currencies = self._load_table(Currency) if Currency else []
        self._pricing_types = self._load_table(PricingType) if PricingType else []