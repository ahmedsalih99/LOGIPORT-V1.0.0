from __future__ import annotations

"""
Enhanced DocumentsTab - Fixed to prevent BaseTab UI overlap
Key changes:
1. Override BaseTab methods to prevent duplicate UI
2. Clean initialization
3. Single unified UI
"""

from typing import Any, Dict, List, Optional, Tuple
import os
import platform
import subprocess

from PySide6.QtCore import Qt, QTimer, QUrl, QPoint
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QMenu, QMessageBox, QHeaderView, QSplitter
)

# ---- App core (guarded) -------------------------------------------------
try:
    from core.base_tab import BaseTab
except Exception:
    class BaseTab(QWidget):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)

try:
    from core.translator import TranslationManager
except Exception:
    class _DummyT:
        @staticmethod
        def get_instance():
            return _DummyT()

        def translate(self, x):
            return x

        def get_current_language(self):
            return "ar"


    TranslationManager = _DummyT

# Database access
try:
    from sqlalchemy import text
    from database.models import get_session_local
except Exception:
    text = None
    get_session_local = None

# Dialog
try:
    from ui.dialogs.generate_document_dialog import GenerateDocumentDialog
except Exception:
    GenerateDocumentDialog = None


# -------------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------------

def _tr(key: str) -> str:
    return TranslationManager.get_instance().translate(key)


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return _tr("dash")
    return str(value)


def _open_session():
    if get_session_local is None:
        return None
    obj = get_session_local
    try:
        s = obj()
    except TypeError:
        s = obj
    if callable(s) and not hasattr(s, "execute"):
        s = s()
    return s

def _table_has_column(table: str, column: str) -> bool:
    if get_session_local is None or text is None:
        return True  # assume exists in design-time
    s = _open_session()
    try:
        rows = s.execute(text(f"PRAGMA table_info({table})")).fetchall()
        for r in rows:
            try:
                name = r[1]
            except Exception:
                name = r._mapping.get("name")  # type: ignore
            if str(name).lower() == column.lower():
                return True
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


# -------------------------------------------------------------------------
# Enhanced DocumentsTab - NO BaseTab UI Overlap
# -------------------------------------------------------------------------
class DocumentsTab(BaseTab):
    """
    Clean documents tab WITHOUT BaseTab UI interference
    """

    COL_DOCNO = 0
    COL_TRANSACTION = 1
    COL_TYPE = 2
    COL_LANG = 3
    COL_PATH = 4
    COL_ACTIONS = 5

    def __init__(self, parent: Optional[QWidget] = None, *, current_user: Any = None,
                 transaction_id: Optional[int] = None):
        # ⭐ CRITICAL: Initialize BaseTab WITHOUT calling its setupUI
        # This prevents BaseTab from creating duplicate UI elements
        QWidget.__init__(self, parent)  # Skip BaseTab.__init__ UI setup

        # Manually init translation shortcut (BaseTab.__init__ was skipped)
        self._ = TranslationManager.get_instance().translate

        self.current_user = current_user
        self._selected_transaction_id: Optional[int] = transaction_id

        # Paging
        self._page = 1
        self._page_size = 25
        self._total = 0

        # Build our own UI completely
        self._build_ui()
        self._wire()

        # Initial load
        self._refresh_transactions_seed()
        self._reload_docs(reset_page=True)

    # ⭐ Override BaseTab methods to prevent duplicate UI
    def setupUI(self):
        """Override BaseTab.setupUI to prevent duplicate UI"""
        pass  # Do nothing - we build our own UI in _build_ui()

    def refresh_data(self):
        """Override BaseTab refresh to use our own refresh"""
        self._refresh_all(reset_page=True)

    def retranslate_ui(self):
        """Override to handle translation updates"""
        # Update UI texts when language changes
        try:
            if hasattr(self, 'txt_search'):
                self.txt_search.setPlaceholderText(_tr("search_documents"))
            if hasattr(self, 'btn_generate'):
                self.btn_generate.setText(_tr("generate_documents"))
            if hasattr(self, 'btn_refresh'):
                self.btn_refresh.setText(_tr("refresh"))
            if hasattr(self, 'btn_clear_transaction'):
                self.btn_clear_transaction.setText(_tr("show_all"))

            # Update table headers
            if hasattr(self, 'tbl'):
                self.tbl.setHorizontalHeaderLabels([
                    _tr("doc_no"),
                    _tr("transaction_no"),
                    _tr("doc_type"),
                    _tr("language"),
                    _tr("file_name"),
                    _tr("actions")
                ])

            # Reload to refresh button texts
            self._reload_docs(reset_page=False)
        except Exception:
            pass  # Ignore translation errors

    # ---------------- UI -----------------
    def _build_ui(self):
        """Build complete UI from scratch"""
        # Clear any existing layout
        if self.layout() is not None:
            QWidget().setLayout(self.layout())  # Reparent to clear

        # Create fresh layout
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setLayout(root)

        # === Top Bar: Minimal & Clean ===
        top_bar_widget = QWidget()
        top_bar_widget.setObjectName("top-bar")
        top_bar = QHBoxLayout(top_bar_widget)
        top_bar.setContentsMargins(12, 12, 12, 12)
        top_bar.setSpacing(8)

        # Search field
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText(_tr("search_documents"))
        self.txt_search.setObjectName("search-field")
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.setMaximumWidth(300)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(500)

        # Generate button
        self.btn_generate = QPushButton(_tr("generate_documents"))
        self.btn_generate.setObjectName("primary-btn")

        # Refresh button
        self.btn_refresh = QPushButton(_tr("refresh"))
        self.btn_refresh.setObjectName("secondary-btn")

        # Build top bar
        top_bar.addWidget(QLabel(_tr("documents")))
        top_bar.addStretch()
        top_bar.addWidget(self.txt_search)
        top_bar.addWidget(self.btn_generate)
        top_bar.addWidget(self.btn_refresh)

        root.addWidget(top_bar_widget)

        # === Main Content with Splitter ===
        splitter = QSplitter(Qt.Horizontal)

        # Left: Transaction Picker
        left_panel = self._build_transaction_picker()
        splitter.addWidget(left_panel)

        # Right: Documents table + filters

        right_panel = self._build_documents_panel()
        splitter.addWidget(right_panel)

        # Splitter proportions (20% left, 80% right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        root.addWidget(splitter, 1)

    def _build_transaction_picker(self) -> QWidget:
        """Build transaction picker sidebar"""
        panel = QWidget()
        panel.setObjectName("sidebar-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Title
        lbl_title = QLabel(_tr("select_transaction"))
        lbl_title.setObjectName("sidebar-title")
        layout.addWidget(lbl_title)

        # Transaction combo
        self.cmb_transaction = QComboBox()
        self.cmb_transaction.setObjectName("transaction-picker")
        self.cmb_transaction.setEditable(True)
        self.cmb_transaction.setInsertPolicy(QComboBox.NoInsert)
        layout.addWidget(self.cmb_transaction)

        # Clear button
        self.btn_clear_transaction = QPushButton(_tr("show_all"))
        self.btn_clear_transaction.setObjectName("secondary-btn-small")
        layout.addWidget(self.btn_clear_transaction)

        layout.addStretch()

        return panel

    def _build_documents_panel(self) -> QWidget:
        """Build documents table panel with filters"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # === Filters Bar ===
        from PySide6.QtWidgets import QDateEdit, QFrame as _QFrame2
        from PySide6.QtCore import QDate
        from PySide6.QtGui import QFont as _QFont2

        filters_bar = QHBoxLayout()
        filters_bar.setSpacing(8)

        # ── Date From / To ──
        lbl_df = QLabel("\U0001f4c5 " + _tr("date_from") + ":")
        lbl_df.setFont(_QFont2("Tajawal", 9))
        filters_bar.addWidget(lbl_df)

        self.doc_date_from = QDateEdit()
        self.doc_date_from.setObjectName("form-input")
        self.doc_date_from.setCalendarPopup(True)
        self.doc_date_from.setDisplayFormat("yyyy-MM-dd")
        self.doc_date_from.setDate(QDate.currentDate().addMonths(-3))
        self.doc_date_from.setMinimumWidth(108)
        filters_bar.addWidget(self.doc_date_from)

        lbl_dt = QLabel("→ " + _tr("date_to") + ":")
        lbl_dt.setFont(_QFont2("Tajawal", 9))
        filters_bar.addWidget(lbl_dt)

        self.doc_date_to = QDateEdit()
        self.doc_date_to.setObjectName("form-input")
        self.doc_date_to.setCalendarPopup(True)
        self.doc_date_to.setDisplayFormat("yyyy-MM-dd")
        self.doc_date_to.setDate(QDate.currentDate())
        self.doc_date_to.setMinimumWidth(108)
        filters_bar.addWidget(self.doc_date_to)

        for _lbl2, _slot2 in (
            ("\U0001f4c5 " + _tr("today"),      "_doc_preset_today"),
            ("\U0001f4c5 " + _tr("this_month"), "_doc_preset_month"),
        ):
            _btn2 = QPushButton(_lbl2)
            _btn2.setObjectName("topbar-btn")
            _btn2.setMinimumHeight(28)
            _btn2.setFont(_QFont2("Tajawal", 9))
            _btn2.setCursor(Qt.PointingHandCursor)
            _btn2.clicked.connect(lambda _=False, s=_slot2: getattr(self, s)())
            filters_bar.addWidget(_btn2)

        _clr2 = QPushButton("\u2716")
        _clr2.setObjectName("topbar-btn")
        _clr2.setMinimumHeight(28)
        _clr2.setToolTip(_tr("clear"))
        _clr2.setCursor(Qt.PointingHandCursor)
        _clr2.clicked.connect(self._doc_preset_clear)
        filters_bar.addWidget(_clr2)

        _sep2 = _QFrame2()
        _sep2.setFrameShape(_QFrame2.VLine)
        _sep2.setFixedWidth(1); _sep2.setFixedHeight(22)
        filters_bar.addWidget(_sep2)

        # Type filter
        lbl_type = QLabel(_tr("document_type") + ":")
        lbl_type.setFont(_QFont2("Tajawal", 9))
        self.cmb_type = QComboBox()
        self.cmb_type.setObjectName("filter-combo")
        self.cmb_type.addItem(_tr("all_types"), None)
        self.cmb_type.addItem(_tr("document_invoice"), "invoice")
        self.cmb_type.addItem(_tr("document_packing_list"), "packing")
        self.cmb_type.addItem("CMR", "cmr")
        self.cmb_type.addItem(_tr("form_a_certificate"), "form_a")

        # Language filter
        lbl_lang = QLabel(_tr("language") + ":")
        lbl_lang.setFont(_QFont2("Tajawal", 9))
        self.cmb_lang = QComboBox()
        self.cmb_lang.setObjectName("filter-combo")
        self.cmb_lang.addItem(_tr("all_languages"), None)
        self.cmb_lang.addItem(self._("arabic"), "ar")
        self.cmb_lang.addItem(self._("english"), "en")
        self.cmb_lang.addItem(self._("turkish"), "tr")

        filters_bar.addWidget(lbl_type)
        filters_bar.addWidget(self.cmb_type)
        filters_bar.addSpacing(12)
        filters_bar.addWidget(lbl_lang)
        filters_bar.addWidget(self.cmb_lang)
        filters_bar.addStretch()

        layout.addLayout(filters_bar)

        # === Table ===
        self.tbl = QTableWidget(0, 6)
        self.tbl.setObjectName("documents-table")
        self.tbl.setHorizontalHeaderLabels([
            _tr("doc_no"),
            _tr("transaction_no"),
            _tr("doc_type"),
            _tr("language"),
            _tr("file_name"),
            _tr("actions")
        ])

        # Table settings
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(44)  # row height
        self.tbl.verticalHeader().setMinimumSectionSize(44)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setWordWrap(False)
        self.tbl.setContextMenuPolicy(Qt.CustomContextMenu)

        # Column sizing
        header = self.tbl.horizontalHeader()
        header.setSectionResizeMode(self.COL_DOCNO, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_TRANSACTION, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_TYPE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_LANG, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_PATH, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_ACTIONS, QHeaderView.Fixed)
        header.setDefaultAlignment(Qt.AlignCenter)

        # Fixed width for actions column
        self.tbl.setColumnWidth(self.COL_ACTIONS, 220)

        layout.addWidget(self.tbl, 1)

        # === Pagination Bar ===
        pagination_bar = QHBoxLayout()
        pagination_bar.setSpacing(8)

        self.btn_prev = QPushButton("◀ " + _tr("previous"))
        self.btn_prev.setObjectName("secondary-btn-small")

        self.lbl_page = QLabel()
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.lbl_page.setObjectName("page-label")

        self.btn_next = QPushButton(_tr("next") + " ▶")
        self.btn_next.setObjectName("secondary-btn-small")

        self.cmb_page_size = QComboBox()
        self.cmb_page_size.setObjectName("page-size-combo")
        self.cmb_page_size.addItem("10", 10)
        self.cmb_page_size.addItem("25", 25)
        self.cmb_page_size.addItem("50", 50)
        self.cmb_page_size.addItem("100", 100)
        self.cmb_page_size.setCurrentIndex(1)  # Default 25

        pagination_bar.addWidget(self.btn_prev)
        pagination_bar.addWidget(self.lbl_page, 1)
        pagination_bar.addWidget(self.btn_next)
        pagination_bar.addWidget(QLabel(_tr("items_per_page") + ":"))
        pagination_bar.addWidget(self.cmb_page_size)

        layout.addLayout(pagination_bar)

        return panel

    # ---------------- Wiring -----------------
    def _wire(self):
        """Connect all signals"""
        # Search
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        self._search_timer.timeout.connect(self._do_search)

        # Filters
        self.cmb_type.currentIndexChanged.connect(lambda: self._reload_docs(reset_page=True))
        self.cmb_lang.currentIndexChanged.connect(lambda: self._reload_docs(reset_page=True))
        self.doc_date_from.dateChanged.connect(lambda: self._reload_docs(reset_page=True))
        self.doc_date_to.dateChanged.connect(lambda: self._reload_docs(reset_page=True))

        # Transaction picker
        self.cmb_transaction.currentIndexChanged.connect(self._on_transaction_changed)
        self.btn_clear_transaction.clicked.connect(self._on_clear_transaction)

        # Table
        self.tbl.customContextMenuRequested.connect(self._table_context_menu)
        self.tbl.doubleClicked.connect(self._on_table_double_click)

        # Pagination
        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_next.clicked.connect(self._next_page)
        self.cmb_page_size.currentIndexChanged.connect(self._on_page_size_changed)

        # Actions
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_refresh.clicked.connect(self._refresh_all)

    def _on_search_text_changed(self, text: str):
        """Debounced search"""
        self._search_timer.stop()
        self._search_timer.start()

    def _do_search(self):
        """Perform search"""
        self._reload_docs(reset_page=True)

    def _on_transaction_changed(self, idx: int):
        """Transaction selected"""
        if idx < 0:
            return
        tid = self.cmb_transaction.itemData(idx)
        if tid != self._selected_transaction_id:
            self._selected_transaction_id = tid
            self._reload_docs(reset_page=True)

    def _on_clear_transaction(self):
        """Clear transaction filter"""
        self._selected_transaction_id = None
        self.cmb_transaction.setCurrentIndex(-1)
        self._reload_docs(reset_page=True)

    # ── Date presets for documents tab ──────────────────────────────────────
    def _doc_preset_today(self):
        from PySide6.QtCore import QDate
        today = QDate.currentDate()
        self.doc_date_from.setDate(today)
        self.doc_date_to.setDate(today)

    def _doc_preset_month(self):
        from PySide6.QtCore import QDate
        today = QDate.currentDate()
        self.doc_date_from.setDate(QDate(today.year(), today.month(), 1))
        self.doc_date_to.setDate(today)

    def _doc_preset_clear(self):
        from PySide6.QtCore import QDate
        self.doc_date_from.setDate(QDate.currentDate().addMonths(-3))
        self.doc_date_to.setDate(QDate.currentDate())

    def _refresh_transactions_seed(self):
        """Load recent transactions"""
        txs = self._db_find_transactions(limit=50)
        self.cmb_transaction.clear()
        for tid, label in txs:
            self.cmb_transaction.addItem(label, tid)

        # Set current if provided
        if self._selected_transaction_id:
            for i in range(self.cmb_transaction.count()):
                if self.cmb_transaction.itemData(i) == self._selected_transaction_id:
                    self.cmb_transaction.setCurrentIndex(i)
                    break

    def _refresh_all(self, reset_page: bool = True):
        """Refresh both transactions and documents"""
        self._refresh_transactions_seed()
        self._reload_docs(reset_page=reset_page)

    # ---------------- Pagination -----------------
    def _on_page_size_changed(self, *_):
        """Page size changed"""
        try:
            v = int(self.cmb_page_size.currentData())
        except:
            v = 25
        self._page_size = v
        self._reload_docs(reset_page=True)

    def _prev_page(self):
        """Previous page"""
        if self._page > 1:
            self._page -= 1
            self._reload_docs(reset_page=False)

    def _next_page(self):
        """Next page"""
        max_pages = max(1, (self._total + self._page_size - 1) // self._page_size)
        if self._page < max_pages:
            self._page += 1
            self._reload_docs(reset_page=False)

    def _update_page_label(self):
        """Update pagination label"""
        max_pages = max(1, (self._total + self._page_size - 1) // self._page_size)
        text = f"{_tr('page')} {self._page} {_tr('of')} {max_pages}  •  {_tr('total')}: {self._total}"
        self.lbl_page.setText(text)

    # ---------------- Table Rendering -----------------
    def _reload_docs(self, *, reset_page: bool):
        """Reload documents with current filters"""
        if reset_page:
            self._page = 1

        q = self.txt_search.text().strip()
        f_type = self.cmb_type.currentData()
        f_lang = self.cmb_lang.currentData()
        d_from = self.doc_date_from.date().toString("yyyy-MM-dd") if hasattr(self, "doc_date_from") else None
        d_to   = self.doc_date_to.date().toString("yyyy-MM-dd")   if hasattr(self, "doc_date_to")   else None

        rows, total = self._db_list_documents(
            query=q,
            doc_type=f_type,
            lang=f_lang,
            transaction_id=self._selected_transaction_id,
            date_from=d_from,
            date_to=d_to,
            page=self._page,
            page_size=self._page_size,
        )

        self._total = total
        self._render_table(rows)
        self._update_page_label()

    def _render_table(self, rows: List[Dict[str, Any]]):
        """Render documents table with action buttons"""
        from pathlib import Path
        self.tbl.setRowCount(0)

        for r, rec in enumerate(rows):
            self.tbl.insertRow(r)
            file_missing = rec.get("_file_missing", False)

            # Doc number
            item_doc = QTableWidgetItem(_fmt(rec.get("doc_no")))
            item_doc.setData(Qt.UserRole, rec)
            item_doc.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(r, self.COL_DOCNO, item_doc)

            # Transaction number
            item_tx = QTableWidgetItem(_fmt(rec.get("transaction_no")))
            item_tx.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(r, self.COL_TRANSACTION, item_tx)

            # Type
            item_type = QTableWidgetItem(_fmt(rec.get("doc_type_label")))
            item_type.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(r, self.COL_TYPE, item_type)

            # Language
            item_lang = QTableWidgetItem(_fmt(rec.get("lang")))
            item_lang.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(r, self.COL_LANG, item_lang)

            # File name — يظهر "مفقود" إذا الملف غير موجود
            full_path = _fmt(rec.get("path"))
            if file_missing:
                file_name = "⚠ " + _tr("file_missing")
                item_path = QTableWidgetItem(file_name)
                item_path.setForeground(__import__("PySide6.QtGui", fromlist=["QColor"]).QColor("#EF4444"))
            else:
                file_name = Path(full_path).name if full_path != "-" else "-"
                item_path = QTableWidgetItem(file_name)
            item_path.setToolTip(full_path)
            item_path.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(r, self.COL_PATH, item_path)

            # Actions
            actions_widget = self._create_action_buttons(rec, file_missing=file_missing)
            self.tbl.setCellWidget(r, self.COL_ACTIONS, actions_widget)

    def _create_action_buttons(self, rec: Dict[str, Any], file_missing: bool = False) -> QWidget:
        """Create action buttons — open/folder disabled if file missing"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        r = rec  # avoid lambda capture issues

        btn_open = QPushButton(self._("open_file"))
        btn_open.setObjectName("primary-btn")
        btn_open.setFixedHeight(30)
        btn_open.setCursor(Qt.PointingHandCursor if not file_missing else Qt.ForbiddenCursor)
        btn_open.setEnabled(not file_missing)
        btn_open.setToolTip(_tr("open_file") if not file_missing else _tr("file_missing"))
        btn_open.clicked.connect(lambda checked=False, _r=r: self._open_file(_r))

        btn_folder = QPushButton(self._("open_folder"))
        btn_folder.setObjectName("secondary-btn")
        btn_folder.setFixedHeight(30)
        btn_folder.setCursor(Qt.PointingHandCursor)
        btn_folder.setToolTip(_tr("open_folder"))
        btn_folder.clicked.connect(lambda checked=False, _r=r: self._open_folder(_r))

        btn_delete = QPushButton(self._("delete"))
        btn_delete.setObjectName("danger-btn")
        btn_delete.setFixedHeight(30)
        btn_delete.setCursor(Qt.PointingHandCursor)
        btn_delete.setToolTip(_tr("delete"))
        btn_delete.clicked.connect(lambda checked=False, _r=r: self._delete_document(_r))

        layout.addWidget(btn_open)
        layout.addWidget(btn_folder)
        layout.addWidget(btn_delete)

        return container

    # ---------------- Context Menu -----------------
    def _on_table_double_click(self, index):
        """Handle double click on table row - open file"""
        row = index.row()
        if row < 0:
            return

        item = self.tbl.item(row, self.COL_DOCNO)
        if not item:
            return

        rec = item.data(Qt.UserRole)
        if rec:
            self._open_file(rec)

    def _table_context_menu(self, pos: QPoint):
        """Right-click context menu"""
        row = self.tbl.currentRow()
        if row < 0:
            return

        item = self.tbl.item(row, self.COL_DOCNO)
        if not item:
            return

        rec = item.data(Qt.UserRole)
        if not rec:
            return

        menu = QMenu(self)

        act_open = menu.addAction(_tr("open_file"))
        act_folder = menu.addAction(_tr("open_folder"))
        menu.addSeparator()
        act_delete = menu.addAction(_tr("delete"))

        action = menu.exec(self.tbl.viewport().mapToGlobal(pos))

        if action == act_open:
            self._open_file(rec)
        elif action == act_folder:
            self._open_folder(rec)
        elif action == act_delete:
            self._delete_document(rec)

    # ---------------- Actions -----------------
    def _open_file(self, rec: Dict[str, Any]):
        """Open document file"""
        path = rec.get("path", "")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, _tr("error"), _tr("file_not_found"))
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _open_folder(self, rec: Dict[str, Any]):
        """Open folder containing document"""
        path = rec.get("path", "")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, _tr("error"), _tr("file_not_found"))
            return

        folder = os.path.dirname(path)

        # Platform-specific folder opening
        if platform.system() == "Windows":
            subprocess.Popen(f'explorer /select,"{path}"')
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", folder])

    def _delete_document(self, rec: Dict[str, Any]):
        """Delete document — file + DB record"""
        doc_no = rec.get("doc_no", "")

        reply = QMessageBox.question(
            self,
            _tr("confirm_delete"),
            _tr("confirm_delete_doc").format(doc_no=doc_no),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        errors = []

        # 1. حذف الملف من القرص
        path = rec.get("path", "")
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                errors.append(f"File: {e}")

        # 2. حذف السجل من قاعدة البيانات
        doc_id = rec.get("id")
        if doc_id:
            try:
                from database.crud.documents_crud import DocumentsCRUD
                DocumentsCRUD().delete_document(int(doc_id))
            except Exception as e:
                errors.append(f"DB: {e}")
        else:
            # fallback: حذف عبر file_path مباشرة
            if path:
                try:
                    from sqlalchemy import text as _sql
                    from database.models import get_session_local as _gs
                    s = _gs()()
                    s.execute(_sql("DELETE FROM documents WHERE file_path = :p"), {"p": path})
                    s.commit()
                    s.close()
                except Exception as e:
                    errors.append(f"DB path: {e}")

        if errors:
            import logging
            logging.getLogger(__name__).warning("Delete errors: %s", errors)

        # 3. تحديث الجدول فوراً
        self._reload_docs(reset_page=False)

    def _on_generate(self):
        """Open generate document dialog"""
        if not self._selected_transaction_id:
            QMessageBox.warning(
                self,
                _tr("warning"),
                _tr("please_select_transaction")
            )
            return

        if GenerateDocumentDialog is None:
            QMessageBox.warning(
                self,
                _tr("error"),
                _tr("generate_dialog_not_available")
            )
            return

        # Get transaction number
        tx_no = self._get_transaction_no(self._selected_transaction_id)

        dialog = GenerateDocumentDialog(
            self._selected_transaction_id,
            tx_no,
            self
        )

        if dialog.exec():
            # Refresh after generation
            self._refresh_all(reset_page=True)

    def _get_transaction_no(self, transaction_id: int) -> str:
        """Get transaction number from ID"""
        if get_session_local is None or text is None:
            return f"T{transaction_id:04d}"

        s = _open_session()
        try:
            row = s.execute(
                text("SELECT COALESCE(transaction_no, CAST(id AS TEXT)) FROM transactions WHERE id=:i"),
                {"i": int(transaction_id)}
            ).fetchone()
            return str(row[0]) if row else f"T{transaction_id:04d}"
        finally:
            try:
                s.close()
            except:
                pass

    # ---------------- DB Layer -----------------
    @staticmethod
    def _db_find_transactions(limit: int = 50) -> List[Tuple[int, str]]:
        """Find recent transactions"""
        if get_session_local is None or text is None:
            return [(i, f"T{i:04d} • Client X • 2026-01-{i:02d}") for i in range(1, min(limit, 20))]

        sql = text("""
            SELECT t.id,
                   COALESCE(t.transaction_no, CAST(t.id AS TEXT)) || ' • ' ||
                   COALESCE(c.name_ar, c.name_en, c.name_tr, '') || ' • ' ||
                   COALESCE(substr(t.created_at, 1, 10), '') AS label
            FROM transactions t
            LEFT JOIN clients c ON c.id = t.client_id
            ORDER BY t.created_at DESC
            LIMIT :lim
        """)

        s = _open_session()
        try:
            rows = s.execute(sql, {"lim": limit}).fetchall()
            return [(int(r[0]), str(r[1])) for r in rows]
        finally:
            try:
                s.close()
            except:
                pass

    def _db_list_documents(self,
                           *,
                           query: str,
                           doc_type: Optional[str],
                           lang: Optional[str],
                           transaction_id: Optional[int],
                           date_from: Optional[str] = None,
                           date_to: Optional[str] = None,
                           page: int,
                           page_size: int,
                           ) -> Tuple[List[Dict[str, Any]], int]:
        # design-time fake data
        if get_session_local is None or text is None:
            total = 24
            start = (page - 1) * page_size
            rows = []
            for i in range(start, min(start + page_size, total)):
                rows.append({
                    "id": i + 1,
                    "doc_no": f"D-2025-09-{(i // 3) + 1:04d}",
                    "doc_type_label": _tr("document_invoice") if i % 2 == 0 else _tr("document_packing_list"),
                    "lang": ["ar", "en", "tr"][i % 3],
                    "path": f"C:/tmp/docs/D-{i + 1}.pdf",
                    "doc_code": "invoice",
                })
            # قبول كل الأنواع في وضع التصميم
            return rows, len(rows)

        # detect group column name dynamically
        group_col = "group_id" if _table_has_column("documents", "group_id") else (
            "doc_group_id" if _table_has_column("documents", "doc_group_id") else None)
        join_groups = f" LEFT JOIN doc_groups g ON g.id = d.{group_col} " if group_col else " LEFT JOIN doc_groups g ON 1=0 "

        # join to transactions via documents.transaction_id if exists, else via groups.transaction_id
        if _table_has_column("documents", "transaction_id"):
            tran_join = " LEFT JOIN transactions t ON t.id = d.transaction_id "
            tid_field = "d.transaction_id"
        elif group_col:
            tran_join = " LEFT JOIN transactions t ON t.id = g.transaction_id "
            tid_field = "g.transaction_id"
        else:
            tran_join = " LEFT JOIN transactions t ON 1=0 "
            tid_field = None

        # WHERE building (no status filter — removed) + force invoices in SQL
        where = ["1=1"]
        params: Dict[str, Any] = {}

        # لا نحصر بنوع معين — نعرض الفواتير وقوائم التعبئة وكل الأنواع

        if query:
            where.append("(g.doc_no LIKE :q OR t.transaction_no LIKE :q)")
            params["q"] = f"%{query}%"
        if doc_type:
            # تعيين فلتر نوع المستند بشكل مرن
            doc_type_lower = str(doc_type).lower()
            if doc_type_lower in ("invoice", "inv"):
                # كل الفواتير: تبدأ بـ inv
                where.append("LOWER(COALESCE(dt.code,'')) LIKE 'inv%'")
            elif doc_type_lower in ("packing", "packing_list", "pl"):
                # كل قوائم التعبئة: تبدأ بـ pl_ أو تساوي packing
                where.append("(LOWER(COALESCE(dt.code,'')) LIKE 'pl%' OR LOWER(COALESCE(dt.code,'')) IN ('packing','packing_list'))")
            elif doc_type_lower in ("coo", "certificate_of_origin"):
                where.append("LOWER(COALESCE(dt.code,'')) IN ('coo','certificate_of_origin')")
            elif doc_type_lower in ("form_a", "form.a"):
                where.append("LOWER(COALESCE(dt.code,'')) IN ('form_a','form.a')")
            elif doc_type_lower == "cmr":
                where.append("LOWER(COALESCE(dt.code,'')) = 'cmr'")
            else:
                where.append("LOWER(COALESCE(dt.code,'')) = :dtype")
                params["dtype"] = doc_type_lower
        if lang:
            where.append("d.language = :lang")
            params["lang"] = lang
        if transaction_id is not None:
            if tid_field:
                where.append(f"{tid_field} = :tid")
                params["tid"] = transaction_id
            else:
                where.append("1=0")  # schema lacks transaction link
        if date_from:
            where.append("COALESCE(d.created_at, '') >= :d_from")
            params["d_from"] = str(date_from)
        if date_to:
            where.append("COALESCE(d.created_at, '') <= :d_to_end")
            params["d_to_end"] = str(date_to) + " 23:59:59"
        where_sql = " AND ".join(where)

        sql_data = text(f"""
                SELECT d.id,
                       COALESCE(g.doc_no, '') AS doc_no,
                       COALESCE(dt.code, '') AS doc_code,
                       d.language AS lang,
                       d.file_path AS path,

                       -- ⭐ إضافة رقم المعاملة
                       COALESCE(t.transaction_no, CAST({tid_field} AS TEXT)) AS transaction_no,

                       CASE LOWER(COALESCE(dt.code,''))
                            WHEN 'inv_ext'               THEN :lbl_inv_com
                            WHEN 'invoice.commercial'    THEN :lbl_inv_com
                            WHEN 'invoice.foreign.commercial' THEN :lbl_inv_com
                            WHEN 'inv_pro'               THEN :lbl_inv_pro
                            WHEN 'inv_proforma'          THEN :lbl_inv_pro
                            WHEN 'invoice.proforma'      THEN :lbl_inv_pro
                            WHEN 'inv_normal'            THEN :lbl_inv_nor
                            WHEN 'invoice.normal'        THEN :lbl_inv_nor
                            WHEN 'invoice'               THEN :lbl_inv_nor
                            WHEN 'invoice.syrian.entry'  THEN :lbl_inv_se
                            WHEN 'inv_sy'                THEN :lbl_inv_st
                            WHEN 'inv_syr_trans'         THEN :lbl_inv_st
                            WHEN 'invoice.syrian.transit' THEN :lbl_inv_st
                            WHEN 'inv_indirect'          THEN :lbl_inv_si
                            WHEN 'inv_syr_interm'        THEN :lbl_inv_si
                            WHEN 'invoice.syrian.intermediary' THEN :lbl_inv_si
                            WHEN 'packing'               THEN :lbl_pck
                            WHEN 'packing_list'          THEN :lbl_pck
                            WHEN 'pl_export_simple'      THEN :lbl_pck
                            WHEN 'packing_list.export.simple' THEN :lbl_pck
                            WHEN 'pl_export_with_dates'  THEN :lbl_pck_dates
                            WHEN 'packing_list.export.with_dates' THEN :lbl_pck_dates
                            WHEN 'pl_export_with_line_id' THEN :lbl_pck_line
                            WHEN 'packing_list.export.with_line_id' THEN :lbl_pck_line
                            WHEN 'coo'                   THEN :lbl_coo
                            WHEN 'certificate_of_origin' THEN :lbl_coo
                            WHEN 'form_a'                THEN :lbl_fa
                            ELSE COALESCE(dt.name_ar, dt.code, '')
                       END AS doc_type_label
                FROM documents d
                {join_groups}
                LEFT JOIN document_types dt ON dt.id = d.document_type_id
                {tran_join}
                WHERE {where_sql}
                ORDER BY d.id DESC
                LIMIT :lim OFFSET :off
            """)

        sql_cnt = text(
            f"SELECT COUNT(1) FROM documents d {join_groups} LEFT JOIN document_types dt ON dt.id=d.document_type_id {tran_join} WHERE {where_sql}"
        )
        params_data = dict(params)
        # جلب أوسع قليلاً لتعويض الفلترة المحلية بسبب وجود الملف
        params_data = dict(params)
        params_data.update({
            "lbl_inv_com": _tr("document_invoice_commercial"),
            "lbl_inv_pro": _tr("document_invoice_proforma"),
            "lbl_inv_nor": _tr("document_invoice_normal"),
            "lbl_inv_se": _tr("document_invoice_syrian_entry"),
            "lbl_inv_st": _tr("document_invoice_syrian_transit"),
            "lbl_inv_si": _tr("document_invoice_syrian_intermediary"),
            "lbl_pck": _tr("document_packing_list_simple"),
            "lbl_pck_dates": _tr("document_packing_list_dates"),
            "lbl_pck_line": _tr("document_packing_list_line_id"),
            "lbl_coo": _tr("document_certificate_of_origin"),
            "lbl_fa": _tr("document_form_a"),
        })

        s = _open_session()
        try:
            total_sql = int(s.execute(sql_cnt, params).scalar() or 0)

            # -----------------------------
            # Smart pagination without double slicing
            # -----------------------------
            collected: List[Dict[str, Any]] = []
            offset = (page - 1) * page_size
            batch_size = page_size
            current_offset = offset

            # جلب مباشر بدون فلترة filesystem — يمنع التجميد
            batch_params = dict(params_data)
            batch_params.update({"lim": page_size, "off": offset})
            rows_raw = [
                dict(r._mapping)
                for r in s.execute(sql_data, batch_params).fetchall()
            ]
            # أضف حالة الملف كمعلومة عرض فقط (لا تفلتر)
            for rec in rows_raw:
                p = str(rec.get("path") or "")
                rec["_file_missing"] = p and not self._file_exists_any(p)
                collected.append(rec)

            return collected, total_sql

        finally:
            try:
                s.close()
            except Exception:
                pass

    @staticmethod
    def _db_regenerate_document(doc_id: Optional[int]) -> Tuple[bool, str]:
        if not doc_id:
            return False, _tr("invalid_document")
        try:
            # from documents.generator import regenerate_by_document_id
            # regenerate_by_document_id(int(doc_id))
            return True, ""
        except Exception as e:
            return False, str(e)

    def _file_exists_any(self, p: str) -> bool:
        if not p:
            return False
        if os.path.exists(p):
            return True
        root, ext = os.path.splitext(p)
        for c in (
                root + ".pdf",
                root + ".html",
                root + ".htm",
                os.path.join(os.path.dirname(p), "document.html"),
                os.path.join(os.path.dirname(p), "index.html"),
        ):
            if os.path.exists(c):
                return True
        return False