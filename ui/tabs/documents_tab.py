from __future__ import annotations

"""
ui/tabs/documents_tab.py
========================
تاب المستندات — يرث من BaseTab بشكل صحيح.

التغييرات عن النسخة القديمة:
  - يرث من BaseTab الآن بدلاً من QWidget.__init__() المباشر
  - self.table   (من BaseTab) يحل محل self.tbl القديم
  - self.search_bar (من BaseTab) يحل محل self.txt_search القديم
  - pagination موحّد مع بقية التابات (btn_prev/btn_next/lbl_pagination)
  - btn_generate يحل محل btn_add في شريط الأدوات
  - الـ Splitter + Transaction Picker يُبنيان مباشرة في _setup_ui()
  - Export Excel مجاني من BaseTab
  - Keyboard shortcuts مجانية (Ctrl+F, Ctrl+R ...)
  - retranslate_ui() موحّد ومكتمل
"""

from typing import Any, Dict, List, Optional, Tuple
import os
import platform
import subprocess

from PySide6.QtCore import Qt, QUrl, QPoint
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidgetItem, QAbstractItemView,
    QMenu, QMessageBox, QHeaderView, QSplitter,
)

from core.base_tab import BaseTab, DateRangeBar
from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from core.permissions import has_perm, is_admin

try:
    from sqlalchemy import text
    from database.models import get_session_local
except Exception:
    text = None
    get_session_local = None

try:
    from ui.dialogs.generate_document_dialog import GenerateDocumentDialog
except Exception:
    GenerateDocumentDialog = None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

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
        return True
    s = _open_session()
    try:
        rows = s.execute(text(f"PRAGMA table_info({table})")).fetchall()
        for r in rows:
            try:
                name = r[1]
            except Exception:
                name = r._mapping.get("name")
            if str(name).lower() == column.lower():
                return True
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


_schema_cache: Dict[str, bool] = {}


def _table_has_column_cached(table: str, column: str) -> bool:
    key = table + "." + column
    if key not in _schema_cache:
        _schema_cache[key] = _table_has_column(table, column)
    return _schema_cache[key]


# ---------------------------------------------------------------------------
# DocumentsTab
# ---------------------------------------------------------------------------

class DocumentsTab(BaseTab):
    """
    تاب المستندات يرث من BaseTab بشكل كامل.

    Layout:
      top_bar:  search_bar | btn_generate | btn_export | btn_refresh
      body:     Splitter [ Transaction Picker | DateRangeBar + filters + table ]
      footer:   pagination bar
    """

    COL_DOCNO       = 0
    COL_TRANSACTION = 1
    COL_TYPE        = 2
    COL_LANG        = 3
    COL_PATH        = 4
    COL_ACTIONS     = 5

    required_permissions: dict = {
        "view":    ["view_documents"],
        "add":     ["view_documents"],
        "export":  ["view_documents"],
        "refresh": ["view_documents"],
    }

    # ------------------------------------------------------------------
    def __init__(self, parent: Optional[QWidget] = None, *,
                 current_user: Any = None,
                 transaction_id: Optional[int] = None):

        u = current_user or SettingsManager.get_instance().get("user")
        super().__init__(title=_tr("documents"), parent=parent, user=u)

        self._selected_transaction_id: Optional[int] = transaction_id

        # pagination (BaseTab fields)
        self.rows_per_page = 25
        self.current_page  = 1
        self.total_rows    = 0
        self.total_pages   = 1

        # إعدادات الجدول
        self.table.setAlternatingRowColors(True)
        # SingleSelection محذوف — نترك ExtendedSelection الافتراضي من BaseTab
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.verticalHeader().setMinimumSectionSize(36)
        self.table.setWordWrap(False)

        # زر أعمدة الأدمن غير ذي معنى في هذا التاب — نخفيه
        self.chk_admin_cols.setVisible(False)

        # أعمدة
        self.set_columns([
            {"label": "doc_no",         "key": "doc_no"},
            {"label": "transaction_no", "key": "transaction_no"},
            {"label": "doc_type",       "key": "doc_type_label"},
            {"label": "language",       "key": "lang"},
            {"label": "file_name",      "key": "_file_name_display"},
            {"label": "actions",        "key": "actions"},
        ])

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(self.COL_DOCNO,       QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(self.COL_TRANSACTION, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(self.COL_TYPE,        QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(self.COL_LANG,        QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(self.COL_PATH,        QHeaderView.Stretch)
        hdr.setSectionResizeMode(self.COL_ACTIONS,     QHeaderView.Fixed)
        self.table.setColumnWidth(self.COL_ACTIONS, 175)

        self._build_filter_widgets()
        self._replace_add_btn_with_generate()

        # تعيين النصوص للـ widgets التي بُنيت في _setup_ui
        self._lbl_pick_tx.setText(_tr("select_transaction"))
        self.btn_clear_transaction.setText(_tr("show_all"))

        self._wire_docs()

        TranslationManager.get_instance().language_changed.connect(
            self._on_language_changed
        )

        self._refresh_transactions_seed()
        self.reload_data()

    # ------------------------------------------------------------------
    # Override _setup_ui to inject Splitter
    # ------------------------------------------------------------------

    def _setup_ui(self):
        super()._setup_ui()

        # اجلب الجدول من layout البيس وأزله مؤقتاً
        self._layout.removeWidget(self.table)

        # Left panel — يُبنى هنا مباشرة بدون placeholder
        self._left_panel = QWidget()
        self._left_panel.setObjectName("sidebar-panel")
        _left_lay = QVBoxLayout(self._left_panel)
        _left_lay.setContentsMargins(12, 12, 12, 12)
        _left_lay.setSpacing(8)

        self._lbl_pick_tx = QLabel()
        self._lbl_pick_tx.setObjectName("sidebar-title")
        _left_lay.addWidget(self._lbl_pick_tx)

        self.cmb_transaction = QComboBox()
        self.cmb_transaction.setObjectName("transaction-picker")
        self.cmb_transaction.setEditable(True)
        self.cmb_transaction.setInsertPolicy(QComboBox.NoInsert)
        _left_lay.addWidget(self.cmb_transaction)

        self.btn_clear_transaction = QPushButton()
        self.btn_clear_transaction.setObjectName("secondary-btn-small")
        _left_lay.addWidget(self.btn_clear_transaction)

        _left_lay.addStretch()

        # Right panel: سيُضاف DateRangeBar فوق الجدول في _build_filter_widgets
        self._right_panel = QWidget()
        self._right_layout = QVBoxLayout(self._right_panel)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(4)
        self._right_layout.addWidget(self.table)

        # Splitter
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setObjectName("docs-splitter")
        self._splitter.addWidget(self._left_panel)
        self._splitter.addWidget(self._right_panel)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 4)

        # أدرج Splitter بعد top_bar (index=1)
        self._layout.insertWidget(1, self._splitter, 1)

    # ------------------------------------------------------------------
    # Filter widgets: DateRangeBar + type + language
    # ------------------------------------------------------------------

    def _build_filter_widgets(self):
        self._date_bar = DateRangeBar(self, default_months=3)
        self._date_bar.changed.connect(lambda: self.reload_data())

        self.doc_date_from = self._date_bar._date_from
        self.doc_date_to   = self._date_bar._date_to

        self.cmb_type = QComboBox()
        self.cmb_type.setObjectName("filter-combo")
        self.cmb_type.addItem(_tr("all_types"),             None)
        self.cmb_type.addItem(_tr("document_invoice"),      "invoice")
        self.cmb_type.addItem(_tr("document_packing_list"), "packing")
        self.cmb_type.addItem("CMR",                        "cmr")
        self.cmb_type.addItem(_tr("form_a_certificate"),    "form_a")
        self._date_bar.add_widget(self.cmb_type)

        self.cmb_lang = QComboBox()
        self.cmb_lang.setObjectName("filter-combo")
        self.cmb_lang.addItem(_tr("all_languages"), None)
        self.cmb_lang.addItem(_tr("arabic"),        "ar")
        self.cmb_lang.addItem(_tr("english"),       "en")
        self.cmb_lang.addItem(_tr("turkish"),       "tr")
        self._date_bar.add_widget(self.cmb_lang)

        self._right_layout.insertWidget(0, self._date_bar)

    # ------------------------------------------------------------------
    # Replace btn_add with btn_generate
    # ------------------------------------------------------------------

    def _replace_add_btn_with_generate(self):
        self.btn_add.setVisible(False)

        self.btn_generate = QPushButton(_tr("generate_documents"))
        self.btn_generate.setObjectName("action-btn")
        self.btn_generate.setMinimumWidth(120)

        idx = self.top_bar.indexOf(self.btn_export)
        self.top_bar.insertWidget(idx, self.btn_generate)

    # ------------------------------------------------------------------
    # Wire
    # ------------------------------------------------------------------

    def _wire_docs(self):
        self.cmb_type.currentIndexChanged.connect(lambda: self.reload_data())
        self.cmb_lang.currentIndexChanged.connect(lambda: self.reload_data())
        self.cmb_transaction.currentIndexChanged.connect(self._on_transaction_changed)
        self.btn_clear_transaction.clicked.connect(self._on_clear_transaction)
        self.table.customContextMenuRequested.connect(self._table_context_menu)
        self.table.doubleClicked.connect(self._on_table_double_click)
        self.btn_generate.clicked.connect(self._on_generate)

    # ------------------------------------------------------------------
    # BaseTab overrides
    # ------------------------------------------------------------------

    def reload_data(self):
        self.current_page = max(1, self.current_page)

        q      = (self.search_bar.text() or "").strip()
        f_type = self.cmb_type.currentData()  if hasattr(self, "cmb_type")       else None
        f_lang = self.cmb_lang.currentData()  if hasattr(self, "cmb_lang")       else None
        d_from = self.doc_date_from.date().toString("yyyy-MM-dd") if hasattr(self, "doc_date_from") else None
        d_to   = self.doc_date_to.date().toString("yyyy-MM-dd")   if hasattr(self, "doc_date_to")   else None

        rows, total = self._db_list_documents(
            query=q,
            doc_type=f_type,
            lang=f_lang,
            transaction_id=self._selected_transaction_id,
            date_from=d_from,
            date_to=d_to,
            page=self.current_page,
            page_size=self.rows_per_page,
        )

        self.total_rows  = total
        self.total_pages = max(1, (total + self.rows_per_page - 1) // self.rows_per_page)
        self.current_page = max(1, min(self.current_page, self.total_pages))

        self._render_table(rows)
        self._update_pagination_label()
        self._update_status_bar(len(rows), total)
        self._show_empty_state(len(rows) == 0, searched=bool(q or f_type or f_lang))

        if hasattr(self, "_date_bar"):
            self._date_bar.set_count(total)

    def refresh_data(self):
        self._refresh_transactions_seed()
        self.reload_data()

    def add_new_item(self):
        self._on_generate()

    # ------------------------------------------------------------------
    # Transaction Picker
    # ------------------------------------------------------------------

    def _on_transaction_changed(self, idx: int):
        if idx < 0:
            return
        tid = self.cmb_transaction.itemData(idx)
        if tid != self._selected_transaction_id:
            self._selected_transaction_id = tid
            self.current_page = 1
            self.reload_data()

    def _on_clear_transaction(self):
        self._selected_transaction_id = None
        self.cmb_transaction.setCurrentIndex(-1)
        self.current_page = 1
        self.reload_data()

    def _refresh_transactions_seed(self):
        """
        Fills the combo with the last 50 transactions.
        - If _selected_transaction_id is set: selects it (fetches it separately if outside top-50).
        - If _selected_transaction_id is None: sets index to -1 so no transaction is
          visually pre-selected and the table shows all documents correctly.
        """
        txs = self._db_find_transactions(limit=50)
        self.cmb_transaction.blockSignals(True)
        self.cmb_transaction.clear()
        for tid, label in txs:
            self.cmb_transaction.addItem(label, tid)

        if self._selected_transaction_id:
            found_idx = -1
            for i in range(self.cmb_transaction.count()):
                if self.cmb_transaction.itemData(i) == self._selected_transaction_id:
                    found_idx = i
                    break

            if found_idx == -1:
                # Transaction not in top-50 — fetch it separately
                try:
                    extra = self._db_find_transactions(
                        transaction_id=self._selected_transaction_id, limit=1
                    )
                    if extra:
                        tid, label = extra[0]
                        self.cmb_transaction.insertItem(0, label, tid)
                        found_idx = 0
                except Exception:
                    pass

            self.cmb_transaction.setCurrentIndex(found_idx)
        else:
            # No transaction selected — force combo to show placeholder (-1)
            self.cmb_transaction.setCurrentIndex(-1)

        self.cmb_transaction.blockSignals(False)

    # ------------------------------------------------------------------
    # Table rendering
    # ------------------------------------------------------------------

    def _render_table(self, rows: List[Dict[str, Any]]):
        from pathlib import Path

        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(rows))
            for r, rec in enumerate(rows):
                file_missing = rec.get("_file_missing", False)

                item_doc = QTableWidgetItem(_fmt(rec.get("doc_no")))
                item_doc.setData(Qt.UserRole, rec)
                item_doc.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, self.COL_DOCNO, item_doc)

                item_tx = QTableWidgetItem(_fmt(rec.get("transaction_no")))
                item_tx.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, self.COL_TRANSACTION, item_tx)

                item_type = QTableWidgetItem(_fmt(rec.get("doc_type_label")))
                item_type.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, self.COL_TYPE, item_type)

                item_lang = QTableWidgetItem(_fmt(rec.get("lang")))
                item_lang.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, self.COL_LANG, item_lang)

                full_path = _fmt(rec.get("path"))
                if file_missing:
                    from PySide6.QtGui import QColor
                    item_path = QTableWidgetItem("⚠ " + _tr("file_missing"))
                    item_path.setForeground(QColor("#EF4444"))
                else:
                    fname = Path(full_path).name if full_path != "-" else "-"
                    item_path = QTableWidgetItem(fname)
                item_path.setToolTip(full_path)
                item_path.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, self.COL_PATH, item_path)

                self.table.setCellWidget(
                    r, self.COL_ACTIONS,
                    self._create_action_buttons(rec, file_missing=file_missing)
                )
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.setSortingEnabled(True)

    def _create_action_buttons(self, rec: Dict[str, Any], file_missing: bool = False) -> QWidget:
        """ثلاثة أزرار مضغوطة مباشرة على خلفية الجدول."""
        cell = QWidget()
        cell.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(cell)
        lay.setContentsMargins(6, 3, 6, 3)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignCenter)

        # ── فتح ─────────────────────────────────────────
        btn_open = QPushButton("📄 " + _tr("open_file"))
        btn_open.setObjectName("table-edit")
        btn_open.setFixedHeight(26)
        btn_open.setEnabled(not file_missing)
        btn_open.setCursor(Qt.PointingHandCursor if not file_missing else Qt.ForbiddenCursor)
        btn_open.setToolTip(_tr("open_file") if not file_missing else _tr("file_missing"))
        btn_open.clicked.connect(lambda _=False, r=rec: self._open_file(r))

        # ── مجلد ────────────────────────────────────────
        btn_folder = QPushButton("📁")
        btn_folder.setObjectName("secondary-btn-small")
        btn_folder.setFixedSize(28, 26)
        btn_folder.setCursor(Qt.PointingHandCursor)
        btn_folder.setToolTip(_tr("open_folder"))
        btn_folder.clicked.connect(lambda _=False, r=rec: self._open_folder(r))

        # ── حذف ─────────────────────────────────────────
        _user = SettingsManager.get_instance().get("user")
        _can_delete = is_admin(_user) or has_perm(_user, "delete_transaction")
        if _can_delete:
            btn_delete = QPushButton("🗑")
            btn_delete.setObjectName("table-delete")
            btn_delete.setFixedSize(28, 26)
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.setToolTip(_tr("delete"))
            btn_delete.clicked.connect(lambda _=False, r=rec: self._delete_document(r))
            lay.addWidget(btn_delete)

        lay.addWidget(btn_open)
        lay.addWidget(btn_folder)
        return cell

    # ------------------------------------------------------------------
    # Context menu & double-click
    # ------------------------------------------------------------------

    def _on_table_double_click(self, index):
        row = index.row()
        if row < 0:
            return
        item = self.table.item(row, self.COL_DOCNO)
        if item:
            rec = item.data(Qt.UserRole)
            if rec:
                self._open_file(rec)

    def _table_context_menu(self, pos: QPoint):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, self.COL_DOCNO)
        if not item:
            return
        rec = item.data(Qt.UserRole)
        if not rec:
            return

        menu = QMenu(self)
        act_open   = menu.addAction(_tr("open_file"))
        act_folder = menu.addAction(_tr("open_folder"))
        menu.addSeparator()
        act_delete = menu.addAction(_tr("delete"))

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_open:
            self._open_file(rec)
        elif action == act_folder:
            self._open_folder(rec)
        elif action == act_delete:
            self._delete_document(rec)

    # ------------------------------------------------------------------
    # File actions
    # ------------------------------------------------------------------

    def _open_file(self, rec: Dict[str, Any]):
        path = rec.get("path", "")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, _tr("error"), _tr("file_not_found"))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _open_folder(self, rec: Dict[str, Any]):
        path = rec.get("path", "")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, _tr("error"), _tr("file_not_found"))
            return
        folder = os.path.dirname(path)
        if platform.system() == "Windows":
            subprocess.Popen(f'explorer /select,"{path}"')
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", folder])

    def _delete_document(self, rec: Dict[str, Any]):
        doc_no = rec.get("doc_no", "")
        reply = QMessageBox.question(
            self,
            _tr("confirm_delete"),
            _tr("confirm_delete_doc").format(doc_no=doc_no),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        errors = []
        path = rec.get("path", "")
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                errors.append(f"File: {e}")

        doc_id = rec.get("id")
        if doc_id:
            try:
                from database.crud.documents_crud import DocumentsCRUD
                DocumentsCRUD().delete_document(int(doc_id))
            except Exception as e:
                errors.append(f"DB: {e}")
        elif path:
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

        self.reload_data()

    # ------------------------------------------------------------------
    # Generate dialog
    # ------------------------------------------------------------------

    def _on_generate(self):
        if not self._selected_transaction_id:
            QMessageBox.warning(self, _tr("warning"), _tr("please_select_transaction"))
            return
        if GenerateDocumentDialog is None:
            QMessageBox.warning(self, _tr("error"), _tr("generate_dialog_not_available"))
            return

        tx_no  = self._get_transaction_no(self._selected_transaction_id)
        dialog = GenerateDocumentDialog(self._selected_transaction_id, tx_no, self)
        if dialog.exec():
            self.refresh_data()

    def _get_transaction_no(self, transaction_id: int) -> str:
        if get_session_local is None or text is None:
            return f"T{transaction_id:04d}"
        s = _open_session()
        try:
            row = s.execute(
                text("SELECT COALESCE(transaction_no, CAST(id AS TEXT)) FROM transactions WHERE id=:i"),
                {"i": int(transaction_id)},
            ).fetchone()
            return str(row[0]) if row else f"T{transaction_id:04d}"
        finally:
            try:
                s.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def _on_language_changed(self):
        self._ = TranslationManager.get_instance().translate
        self._refresh_transactions_seed()
        self.retranslate_ui()
        self.reload_data()

    def retranslate_ui(self):
        try:
            super().retranslate_ui()
        except Exception:
            pass

        try:
            if hasattr(self, "btn_generate"):
                self.btn_generate.setText(_tr("generate_documents"))
            if hasattr(self, "_lbl_pick_tx"):
                self._lbl_pick_tx.setText(_tr("select_transaction"))
            if hasattr(self, "btn_clear_transaction"):
                self.btn_clear_transaction.setText(_tr("show_all"))
            if hasattr(self, "cmb_type"):
                self.cmb_type.setItemText(0, _tr("all_types"))
                self.cmb_type.setItemText(1, _tr("document_invoice"))
                self.cmb_type.setItemText(2, _tr("document_packing_list"))
                # index 3 = CMR ثابت
                self.cmb_type.setItemText(4, _tr("form_a_certificate"))
            if hasattr(self, "cmb_lang"):
                self.cmb_lang.setItemText(0, _tr("all_languages"))
                self.cmb_lang.setItemText(1, _tr("arabic"))
                self.cmb_lang.setItemText(2, _tr("english"))
                self.cmb_lang.setItemText(3, _tr("turkish"))
            if hasattr(self, "_date_bar"):
                self._date_bar.retranslate()
            if hasattr(self, "table") and self.table.columnCount() == 6:
                self.table.setHorizontalHeaderLabels([
                    _tr("doc_no"),
                    _tr("transaction_no"),
                    _tr("doc_type"),
                    _tr("language"),
                    _tr("file_name"),
                    _tr("actions"),
                ])
        except Exception:
            pass

    # ------------------------------------------------------------------
    # DB Layer
    # ------------------------------------------------------------------

    @staticmethod
    def _db_find_transactions(limit: int = 50, transaction_id: Optional[int] = None) -> List[Tuple[int, str]]:
        if get_session_local is None or text is None:
            return [(i, f"T{i:04d} - Client X - 2026-01-{i:02d}") for i in range(1, min(limit, 20))]

        lang = TranslationManager.get_instance().get_current_language()
        if lang == "en":
            name_expr = "COALESCE(c.name_en, c.name_ar, c.name_tr, '')"
        elif lang == "tr":
            name_expr = "COALESCE(c.name_tr, c.name_ar, c.name_en, '')"
        else:
            name_expr = "COALESCE(c.name_ar, c.name_en, c.name_tr, '')"

        where  = "WHERE t.id = :tid" if transaction_id else ""
        params: dict = {"lim": limit}
        if transaction_id:
            params["tid"] = transaction_id

        sql = text(f"""
            SELECT t.id,
                   COALESCE(t.transaction_no, CAST(t.id AS TEXT)) || ' - ' ||
                   {name_expr} || ' - ' ||
                   COALESCE(substr(t.created_at, 1, 10), '') AS label
            FROM transactions t
            LEFT JOIN clients c ON c.id = t.client_id
            {where}
            ORDER BY t.created_at DESC
            LIMIT :lim
        """)

        s = _open_session()
        try:
            rows = s.execute(sql, params).fetchall()
            return [(int(r[0]), str(r[1])) for r in rows]
        finally:
            try:
                s.close()
            except Exception:
                pass

    def _db_list_documents(
        self,
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
            return rows, len(rows)

        group_col = "group_id" if _table_has_column_cached("documents", "group_id") else (
            "doc_group_id" if _table_has_column_cached("documents", "doc_group_id") else None
        )
        join_groups = (
            f" LEFT JOIN doc_groups g ON g.id = d.{group_col} "
            if group_col else " LEFT JOIN doc_groups g ON 1=0 "
        )

        if _table_has_column_cached("documents", "transaction_id"):
            tran_join = " LEFT JOIN transactions t ON t.id = d.transaction_id "
            tid_field = "d.transaction_id"
        elif group_col:
            tran_join = " LEFT JOIN transactions t ON t.id = g.transaction_id "
            tid_field = "g.transaction_id"
        else:
            tran_join = " LEFT JOIN transactions t ON 1=0 "
            tid_field = None

        where: List[str] = ["1=1"]
        params: Dict[str, Any] = {}

        if query:
            where.append("(g.doc_no LIKE :q OR t.transaction_no LIKE :q)")
            params["q"] = f"%{query}%"

        if doc_type:
            dl = str(doc_type).lower()
            if dl in ("invoice", "inv"):
                where.append("LOWER(COALESCE(dt.code,'')) LIKE 'inv%'")
            elif dl in ("packing", "packing_list", "pl"):
                where.append(
                    "(LOWER(COALESCE(dt.code,'')) LIKE 'pl%' "
                    "OR LOWER(COALESCE(dt.code,'')) IN ('packing','packing_list'))"
                )
            elif dl in ("coo", "certificate_of_origin"):
                where.append("LOWER(COALESCE(dt.code,'')) IN ('coo','certificate_of_origin')")
            elif dl in ("form_a", "form.a"):
                where.append("LOWER(COALESCE(dt.code,'')) IN ('form_a','form.a')")
            elif dl == "cmr":
                where.append("LOWER(COALESCE(dt.code,'')) = 'cmr'")
            else:
                where.append("LOWER(COALESCE(dt.code,'')) = :dtype")
                params["dtype"] = dl

        if lang:
            where.append("d.language = :lang")
            params["lang"] = lang

        if transaction_id is not None:
            if tid_field:
                where.append(f"{tid_field} = :tid")
                params["tid"] = transaction_id
            else:
                where.append("1=0")

        if date_from:
            where.append("COALESCE(d.created_at, '') >= :d_from")
            params["d_from"] = str(date_from)

        if date_to:
            where.append("COALESCE(d.created_at, '') <= :d_to_end")
            params["d_to_end"] = str(date_to) + " 23:59:59"

        where_sql = " AND ".join(where)
        app_lang  = TranslationManager.get_instance().get_current_language()
        lang_col  = {"en": "en", "tr": "tr"}.get(app_lang, "ar")

        sql_data = text(f"""
            SELECT d.id,
                   COALESCE(g.doc_no, '') AS doc_no,
                   COALESCE(dt.code, '') AS doc_code,
                   d.language AS lang,
                   d.file_path AS path,
                   COALESCE(t.transaction_no, CAST({tid_field} AS TEXT)) AS transaction_no,
                   CASE LOWER(COALESCE(dt.code,''))
                        WHEN 'inv_ext'                          THEN :lbl_inv_com
                        WHEN 'invoice.commercial'               THEN :lbl_inv_com
                        WHEN 'invoice.foreign.commercial'       THEN :lbl_inv_com
                        WHEN 'inv_pro'                          THEN :lbl_inv_pro
                        WHEN 'inv_proforma'                     THEN :lbl_inv_pro
                        WHEN 'invoice.proforma'                 THEN :lbl_inv_pro
                        WHEN 'inv_normal'                       THEN :lbl_inv_nor
                        WHEN 'invoice.normal'                   THEN :lbl_inv_nor
                        WHEN 'invoice'                          THEN :lbl_inv_nor
                        WHEN 'invoice.syrian.entry'             THEN :lbl_inv_se
                        WHEN 'inv_sy'                           THEN :lbl_inv_st
                        WHEN 'inv_syr_trans'                    THEN :lbl_inv_st
                        WHEN 'invoice.syrian.transit'           THEN :lbl_inv_st
                        WHEN 'inv_indirect'                     THEN :lbl_inv_si
                        WHEN 'inv_syr_interm'                   THEN :lbl_inv_si
                        WHEN 'invoice.syrian.intermediary'      THEN :lbl_inv_si
                        WHEN 'packing'                          THEN :lbl_pck
                        WHEN 'packing_list'                     THEN :lbl_pck
                        WHEN 'pl_export_simple'                 THEN :lbl_pck
                        WHEN 'packing_list.export.simple'       THEN :lbl_pck
                        WHEN 'pl_export_with_dates'             THEN :lbl_pck_dates
                        WHEN 'packing_list.export.with_dates'   THEN :lbl_pck_dates
                        WHEN 'pl_export_with_line_id'           THEN :lbl_pck_line
                        WHEN 'packing_list.export.with_line_id' THEN :lbl_pck_line
                        WHEN 'coo'                              THEN :lbl_coo
                        WHEN 'certificate_of_origin'            THEN :lbl_coo
                        WHEN 'form_a'                           THEN :lbl_fa
                        ELSE COALESCE(dt.name_{lang_col}, dt.name_ar, dt.code, '')
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
            f"SELECT COUNT(1) FROM documents d"
            f" {join_groups}"
            f" LEFT JOIN document_types dt ON dt.id = d.document_type_id"
            f" {tran_join}"
            f" WHERE {where_sql}"
        )

        params_data = dict(params)
        params_data.update({
            "lbl_inv_com":   _tr("document_invoice_commercial"),
            "lbl_inv_pro":   _tr("document_invoice_proforma"),
            "lbl_inv_nor":   _tr("document_invoice_normal"),
            "lbl_inv_se":    _tr("document_invoice_syrian_entry"),
            "lbl_inv_st":    _tr("document_invoice_syrian_transit"),
            "lbl_inv_si":    _tr("document_invoice_syrian_intermediary"),
            "lbl_pck":       _tr("document_packing_list_simple"),
            "lbl_pck_dates": _tr("document_packing_list_dates"),
            "lbl_pck_line":  _tr("document_packing_list_line_id"),
            "lbl_coo":       _tr("document_certificate_of_origin"),
            "lbl_fa":        _tr("document_form_a"),
        })

        s = _open_session()
        try:
            total_sql = int(s.execute(sql_cnt, params).scalar() or 0)
            offset = (page - 1) * page_size
            batch  = dict(params_data)
            batch.update({"lim": page_size, "off": offset})
            rows_raw = [
                dict(r._mapping)
                for r in s.execute(sql_data, batch).fetchall()
            ]
            for rec in rows_raw:
                p = str(rec.get("path") or "")
                rec["_file_missing"] = bool(p and not self._file_exists_any(p))
            return rows_raw, total_sql
        finally:
            try:
                s.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    def _file_exists_any(self, p: str) -> bool:
        if not p:
            return False
        if os.path.exists(p):
            return True
        root, _ = os.path.splitext(p)
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