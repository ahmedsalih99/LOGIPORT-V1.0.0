# -*- coding: utf-8 -*-
"""
pick_entries_dialog.py

Dialog بسيط لاختيار الإدخالات وإضافتها للمعاملة
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from core.base_dialog import BaseDialog
from ui.utils.wheel_blocker import block_wheel_in
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QLineEdit,
    QAbstractItemView, QCheckBox, QWidget
)

try:
    from core.translator import TranslationManager
except:
    class _DummyT:
        @staticmethod
        def get_instance():
            return _DummyT()

        def translate(self, x):
            return x


    TranslationManager = _DummyT

try:
    from database.crud.entries_crud import EntriesCRUD
except:
    EntriesCRUD = None


class PickEntriesDialog(BaseDialog):
    """Dialog لاختيار الإدخالات"""

    def __init__(self, parent=None):
        super().__init__(parent)
        tm = TranslationManager.get_instance()
        self._ = tm.translate

        self.selected_entries = []

        self.setWindowTitle(self._("select_entries"))
        self.resize(900, 600)
        self.setObjectName("pick-entries-dialog")

        self._build_ui()
        block_wheel_in(self)
        self._load_entries()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = QLabel(self._("select_entries_to_add"))
        header.setObjectName("dialog-header")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        # Search
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText(self._("search_by_number_or_ref"))
        self.txt_search.setMinimumHeight(40)
        self.txt_search.textChanged.connect(self._filter_entries)
        search_layout.addWidget(QLabel(self._("search") + ":"))
        search_layout.addWidget(self.txt_search)
        layout.addLayout(search_layout)

        # Table
        self.tbl = QTableWidget(0, 6)
        self.tbl.setObjectName("entries-table")
        self.tbl.setHorizontalHeaderLabels([
            self._("select"),
            self._("transport_ref"),
            self._("entry_date"),
            self._("items_count"),
            self._("total_weight"),
            self._("status")
        ])
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self._apply_tbl_style()
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(self._apply_tbl_style)
        except Exception:
            pass
        layout.addWidget(self.tbl)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_select_all = QPushButton(self._("select_all"))
        self.btn_select_all.setObjectName("secondary-btn")
        self.btn_select_all.setMinimumHeight(40)
        self.btn_select_all.setMinimumWidth(120)
        self.btn_select_all.clicked.connect(self._select_all)

        self.btn_clear = QPushButton(self._("clear_selection"))
        self.btn_clear.setObjectName("secondary-btn")
        self.btn_clear.setMinimumHeight(40)
        self.btn_clear.setMinimumWidth(120)
        self.btn_clear.clicked.connect(self._clear_selection)

        self.btn_add = QPushButton(self._("add_selected"))
        self.btn_add.setObjectName("primary-btn")
        self.btn_add.setMinimumHeight(40)
        self.btn_add.setMinimumWidth(120)
        self.btn_add.clicked.connect(self.accept)

        self.btn_cancel = QPushButton(self._("cancel"))
        self.btn_cancel.setObjectName("secondary-btn")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setMinimumWidth(120)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def _apply_tbl_style(self, *_):
        try:
            from core.theme_manager import ThemeManager
            tm  = ThemeManager.get_instance()
            fs  = tm.get_current_font_size()
            fam = tm.get_current_font_family()
        except Exception:
            fs, fam = 12, "Tajawal"
        row_h = max(32, fs * 3 + 6)
        hdr_h = max(40, fs * 3 + 8)
        hdr_f = QFont(fam, fs); hdr_f.setBold(True)
        self.tbl.verticalHeader().setDefaultSectionSize(row_h)
        self.tbl.verticalHeader().setMinimumSectionSize(32)
        self.tbl.horizontalHeader().setMinimumHeight(hdr_h)
        self.tbl.horizontalHeader().setFont(hdr_f)

    def _make_cell(self, text: str) -> QTableWidgetItem:
        try:
            from core.theme_manager import ThemeManager
            tm = ThemeManager.get_instance()
            f  = QFont(tm.get_current_font_family(), tm.get_current_font_size())
        except Exception:
            f = QFont("Tajawal", 12)
        f.setBold(True)
        item = QTableWidgetItem(str(text))
        item.setFont(f)
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        return item

    def _load_entries(self):
        """تحميل الإدخالات من قاعدة البيانات"""
        if not EntriesCRUD:
            QMessageBox.warning(self, self._("error"),
                                "EntriesCRUD not available")
            return

        try:
            crud = EntriesCRUD()
            # احصل على جميع الإدخالات
            entries = crud.get_all() or []

            self.tbl.setRowCount(0)
            for entry in entries:
                row = self.tbl.rowCount()
                self.tbl.insertRow(row)

                # Checkbox للتحديد
                from PySide6.QtCore import Qt as QtCore

                cb = QCheckBox()
                cb.setProperty("entry_id", getattr(entry, "id", None))
                cb_widget = QWidget()
                cb_layout = QHBoxLayout(cb_widget)
                cb_layout.addWidget(cb)
                cb_layout.setAlignment(QtCore.AlignCenter)
                cb_layout.setContentsMargins(0, 0, 0, 0)
                self.tbl.setCellWidget(row, 0, cb_widget)

                # مرجع وسيلة النقل
                transport_ref = str(getattr(entry, "transport_ref", "") or "")
                self.tbl.setItem(row, 1, self._make_cell(transport_ref))

                # التاريخ
                entry_date = getattr(entry, "entry_date", None)
                date_str = str(entry_date) if entry_date else ""
                self.tbl.setItem(row, 2, self._make_cell(date_str))

                # عدد المواد
                try:
                    items = getattr(entry, "items", []) or []
                    items_count = len(list(items))
                except:
                    items_count = 0
                self.tbl.setItem(row, 3, self._make_cell(str(items_count)))

                # الوزن الإجمالي
                try:
                    total_weight = sum(
                        float(getattr(item, "net_weight_kg", 0) or 0)
                        for item in items
                    )
                except:
                    total_weight = 0
                self.tbl.setItem(row, 4, self._make_cell(f"{total_weight:.2f}"))

                # الحالة
                status = str(getattr(entry, "status", "") or "active")
                self.tbl.setItem(row, 5, self._make_cell(self._(status)))

            # ضبط عرض الأعمدة حسب المحتوى
            from PySide6.QtCore import QTimer
            hdr = self.tbl.horizontalHeader()
            hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
            QTimer.singleShot(0, lambda: hdr.setSectionResizeMode(QHeaderView.Interactive)
                              if not self.tbl.isHidden() else None)
            self.tbl.horizontalHeader().setStretchLastSection(True)

        except Exception as e:
            QMessageBox.critical(self, self._("error"),
                                 f"Failed to load entries: {e}")

    def _filter_entries(self, text):
        """تصفية الإدخالات حسب النص"""
        text = text.lower()
        for row in range(self.tbl.rowCount()):
            show = False
            if not text:
                show = True
            else:
                # ابحث في رقم الإدخال ورقم النقل
                for col in [1]:
                    item = self.tbl.item(row, col)
                    if item and text in item.text().lower():
                        show = True
                        break

            self.tbl.setRowHidden(row, not show)

    def _select_all(self):
        """تحديد جميع الصفوف المرئية"""
        for row in range(self.tbl.rowCount()):
            if not self.tbl.isRowHidden(row):
                cb_widget = self.tbl.cellWidget(row, 0)
                if cb_widget:
                    cb = cb_widget.findChild(QCheckBox)
                    if cb:
                        cb.setChecked(True)

    def _clear_selection(self):
        """إلغاء جميع التحديدات"""
        for row in range(self.tbl.rowCount()):
            cb_widget = self.tbl.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(False)

    def get_selected_entries(self):
        """احصل على الإدخالات المحددة"""
        if not EntriesCRUD:
            return []

        selected_ids = []
        for row in range(self.tbl.rowCount()):
            cb_widget = self.tbl.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    entry_id = cb.property("entry_id")
                    if entry_id:
                        selected_ids.append(entry_id)

        # احصل على الإدخالات الكاملة
        entries = []
        try:
            crud = EntriesCRUD()
            for entry_id in selected_ids:
                entry = crud.get_with_items(entry_id)
                if entry:
                    entries.append(entry)
        except Exception as e:
            QMessageBox.critical(self, self._("error"),
                                 f"Failed to load selected entries: {e}")

        return entries