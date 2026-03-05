# -*- coding: utf-8 -*-
"""
pick_entries_dialog.py

Dialog بسيط لاختيار الإدخالات وإضافتها للمعاملة
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QMessageBox, QLineEdit,
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


class PickEntriesDialog(QDialog):
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
        self.tbl = QTableWidget(0, 7)
        self.tbl.setObjectName("entries-table")
        self.tbl.setHorizontalHeaderLabels([
            self._("select"),
            self._("entry_number"),
            self._("transport_ref"),
            self._("entry_date"),
            self._("items_count"),
            self._("total_weight"),
            self._("status")
        ])
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setVisible(False)
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

                # رقم الإدخال
                entry_no = str(getattr(entry, "entry_no", "") or "")
                self.tbl.setItem(row, 1, QTableWidgetItem(entry_no))

                # رقم النقل
                transport_ref = str(getattr(entry, "transport_ref", "") or "")
                self.tbl.setItem(row, 2, QTableWidgetItem(transport_ref))

                # التاريخ
                entry_date = getattr(entry, "entry_date", None)
                date_str = str(entry_date) if entry_date else ""
                self.tbl.setItem(row, 3, QTableWidgetItem(date_str))

                # عدد المواد
                try:
                    items = getattr(entry, "items", []) or []
                    items_count = len(list(items))
                except:
                    items_count = 0
                self.tbl.setItem(row, 4, QTableWidgetItem(str(items_count)))

                # الوزن الإجمالي
                try:
                    total_weight = sum(
                        float(getattr(item, "net_weight_kg", 0) or 0)
                        for item in items
                    )
                except:
                    total_weight = 0
                self.tbl.setItem(row, 5, QTableWidgetItem(f"{total_weight:.2f}"))

                # الحالة
                status = str(getattr(entry, "status", "") or "active")
                self.tbl.setItem(row, 6, QTableWidgetItem(self._(status)))

            # ضبط عرض الأعمدة
            self.tbl.resizeColumnsToContents()

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
                for col in [1, 2]:
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