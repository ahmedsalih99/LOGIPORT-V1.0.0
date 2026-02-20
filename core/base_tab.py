from PySide6.QtWidgets import (
    QWidget, QTableWidget, QAbstractItemView, QMenu, QVBoxLayout, QHBoxLayout, QPushButton,
    QSpacerItem, QSizePolicy, QLabel, QComboBox, QLineEdit, QFileDialog, QMessageBox, QTableWidgetItem, QHeaderView,
    QCheckBox
)
from PySide6.QtCore import Qt, QModelIndex, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from core.settings_manager import SettingsManager
from core.translator import TranslationManager
from database.crud.permissions_crud import has_permission
from PySide6.QtWidgets import QApplication
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtGui import QTextDocument
import logging
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from database.crud.permissions_crud import has_permission as _has_perm

logger = logging.getLogger(__name__)


def _is_admin(user) -> bool:
    """يتحقق إن كان المستخدم Admin.
    يدعم: ORM أو dict، ويدعم role_id كعدد/نص، ويدعم role كقاموس/كائن/سلسلة.
    """
    if not user:
        return False
    try:
        # استخرِج role_id و role بأي صيغة
        if isinstance(user, dict):
            rid = user.get("role_id")
            role = user.get("role") or user.get("role_name")
        else:
            rid = getattr(user, "role_id", None)
            role = getattr(user, "role", None)

        # 1) فحص role_id مباشرة (عدد أو نص)
        try:
            if rid is not None and int(rid) == 1:
                return True
        except Exception:
            pass

        # 2) لو role قاموس: افحص id ثم name
        if isinstance(role, dict):
            try:
                if role.get("id") is not None and int(role.get("id")) == 1:
                    return True
            except Exception:
                pass
            rname = str(role.get("name") or "").strip().lower()
            if rname == "admin":
                return True

        else:
            # 3) لو role كائن ORM: افحص id ثم name
            try:
                r_id_obj = getattr(role, "id", None)
                if r_id_obj is not None and int(r_id_obj) == 1:
                    return True
            except Exception:
                pass
            rname = role if isinstance(role, str) else (getattr(role, "name", "") or "")
            if str(rname).strip().lower() == "admin":
                return True

        return False
    except Exception:
        return False


class BaseTab(QWidget):
    """
    Base table tab with:
      - Unified toolbar (search/filters/buttons)
      - Pagination
      - Export/Import/Print (ENHANCED)
      - Admin-only columns support (toggle for admins)
      - Improved action buttons (Edit/Delete) without extra containers
    Columns format: {"label": "i18n_key_or_text", "key": "data_key", "align": Qt.AlignCenter}
    """

    row_double_clicked = Signal(int)
    request_edit = Signal(int)
    request_delete = Signal(list)
    request_view = Signal(int)

    required_permissions = {
        "add": None,
        "import": None,
        "export": None,
        "refresh": None,
        "print": None,
        "edit": None,
        "delete": None,
        "view": None,
    }

    def __init__(self, title=None, parent=None, user=None):
        super().__init__(parent)
        self.title = title
        self.settings = SettingsManager.get_instance()
        self._ = TranslationManager.get_instance().translate
        self.user = user or self.settings.get("user", {})
        self.current_user = self.user  # <<< أضِف هذا
        self.is_admin = _is_admin(self.user)

        self.rows_per_page = 20
        self.current_page = 1
        self.total_rows = 0
        self.total_pages = 1
        self.data = []  # List[Dict]

        self.filters = []
        self.filter_widgets = []

        # columns handling
        self.columns = []  # effective columns (base + admin if enabled)
        self._base_columns = []  # visible to all users
        self._admin_columns = []  # extra columns visible to admins only

        self.setup_ui()
        self.setup_filters()
        self.setup_table()
        self.setup_pagination_controls()
        self.setup_shortcuts()
        self.setup_signals()
        self.check_permissions()

        TranslationManager.get_instance().language_changed.connect(self.retranslate_ui)

        if QApplication.instance():
            self.apply_settings()

    # -----------------------------
    # Filters API
    # -----------------------------
    def add_filter(self, widget, label=None):
        self.filters.append((widget, label))
        self.filter_widgets.append(widget)
        if label:
            self.top_bar.insertWidget(0, QLabel(self._(label)))
        self.top_bar.insertWidget(0, widget)

    def setup_filters(self):
        pass

    # -----------------------------
    # Columns API
    # -----------------------------
    def set_columns(self, columns):
        """Set effective columns directly (use set_columns_for_role normally)."""
        self.columns = columns or []
        self.table.setColumnCount(len(self.columns))
        headers = []
        for col in self.columns:
            label = col.get("label", "")
            # allow both raw text and i18n key
            headers.append(self._(label) if label else "")
        self.table.setHorizontalHeaderLabels(headers)
        for i in range(len(self.columns)):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)

    def set_columns_for_role(self, base_columns, admin_columns=None):
        self._base_columns = base_columns or []
        self._admin_columns = admin_columns or []
        self._apply_columns_for_current_role()

    def _apply_columns_for_current_role(self):
        cols = list(self._base_columns)
        if self.is_admin and self.chk_admin_cols.isChecked():
            cols += self._admin_columns
        self.set_columns(cols)

    # -----------------------------
    # UI Setup
    # -----------------------------
    def setup_ui(self):
        self.layout = QVBoxLayout(self)

        self.top_bar = QHBoxLayout()
        self.top_bar.setSpacing(5)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(self._("Search..."))
        self.search_bar.setObjectName("search-field")
        self.search_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.filter_box = QComboBox()
        self.filter_box.addItem(self._("Order by creation date"))

        self.btn_add = QPushButton(self._("add"))
        self.btn_import = QPushButton(self._("import from excel"))
        self.btn_export = QPushButton(self._("export to excel"))
        self.btn_refresh = QPushButton(self._("refresh"))
        self.btn_print = QPushButton(self._("print"))

        # NEW: admin columns toggle (visible only for admins)
        self.chk_admin_cols = QCheckBox(self._("show_admin_columns"))
        self.chk_admin_cols.setVisible(self.is_admin)
        self.chk_admin_cols.setChecked(False)
        self.chk_admin_cols.stateChanged.connect(self._apply_columns_for_current_role)

        for btn in [self.btn_add, self.btn_import, self.btn_export, self.btn_refresh, self.btn_print]:
            btn.setObjectName("action-btn")
            btn.setMinimumWidth(64)
            btn.setMaximumWidth(120)

        self.top_bar.addWidget(self.search_bar)
        self.top_bar.addWidget(self.filter_box)
        self.top_bar.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Expanding))
        self.top_bar.addWidget(self.chk_admin_cols)
        self.top_bar.addWidget(self.btn_add)
        self.top_bar.addWidget(self.btn_import)
        self.top_bar.addWidget(self.btn_export)
        self.top_bar.addWidget(self.btn_refresh)
        self.top_bar.addWidget(self.btn_print)
        self.layout.addLayout(self.top_bar)

        self.table = QTableWidget(0, 0, self)
        self.layout.addWidget(self.table)

        self.pagination_bar = QHBoxLayout()
        self.btn_prev = QPushButton("<")
        self.btn_prev.setObjectName("pagination-btn")
        self.btn_next = QPushButton(">")
        self.btn_next.setObjectName("pagination-btn")

        self.lbl_pagination = QLabel("")
        self.lbl_pagination.setAlignment(Qt.AlignCenter)

        self.cmb_rows_per_page = QComboBox()
        self.cmb_rows_per_page.addItems(["10", "20", "50", "100"])
        self.cmb_rows_per_page.setCurrentText(str(self.rows_per_page))

        self.pagination_bar.addStretch(1)
        self.pagination_bar.addWidget(self.btn_prev)
        self.pagination_bar.addWidget(self.lbl_pagination)
        self.pagination_bar.addWidget(self.btn_next)
        self.pagination_bar.addStretch(1)
        self.pagination_bar.addWidget(QLabel(self._("rows_per_page")))
        self.pagination_bar.addWidget(self.cmb_rows_per_page)
        self.layout.addLayout(self.pagination_bar)

    def setup_table(self):
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.doubleClicked.connect(self.on_row_double_clicked)

        # ✅ ضبط ارتفاع الصفوف - CRITICAL للأزرار
        self.table.verticalHeader().setDefaultSectionSize(34)  # ارتفاع موحد
        self.table.verticalHeader().setMinimumSectionSize(30)  # أقل ارتفاع

        # ✅ ضبط ارتفاع الهيدر
        self.table.horizontalHeader().setMinimumHeight(38)

        def stretch_all_columns():
            col_count = self.table.columnCount()
            if col_count:
                for i in range(col_count):
                    self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)

        self.stretch_all_columns = stretch_all_columns

    def setup_pagination_controls(self):
        self.cmb_rows_per_page.currentTextChanged.connect(self.on_rows_per_page_changed)
        self.btn_prev.clicked.connect(self.go_to_prev_page)
        self.btn_next.clicked.connect(self.go_to_next_page)
        self.update_pagination_label()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+N"), self, self.add_new_item)
        QShortcut(QKeySequence("Ctrl+E"), self, self.edit_selected_item)
        QShortcut(QKeySequence("Delete"), self, self.delete_selected_items)
        QShortcut(QKeySequence("Enter"), self, self.view_selected_item)
        QShortcut(QKeySequence("Return"), self, self.view_selected_item)
        QShortcut(QKeySequence("Ctrl+A"), self, self.select_all_items)
        QShortcut(QKeySequence("Ctrl+D"), self, self.clear_selection)
        QShortcut(QKeySequence("Escape"), self, self.clear_selection)
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)
        QShortcut(QKeySequence("PageUp"), self, self.go_to_prev_page)
        QShortcut(QKeySequence("PageDown"), self, self.go_to_next_page)
        QShortcut(QKeySequence("Ctrl+P"), self, self.print_table)
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_selected)
        QShortcut(QKeySequence("Ctrl+X"), self, self.cut_selected)
        QShortcut(QKeySequence("Ctrl+V"), self, self.paste_data)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_changes)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)
        QShortcut(QKeySequence("Ctrl+I"), self, self.import_from_excel)
        QShortcut(QKeySequence("Ctrl+Shift+E"), self, self.export_table_to_excel)
        QShortcut(QKeySequence("Ctrl+R"), self, self.refresh_data)

    def setup_signals(self):
        self.btn_add.clicked.connect(self.add_new_item)
        self.btn_import.clicked.connect(self.import_from_excel)
        self.btn_export.clicked.connect(self.export_table_to_excel)
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.btn_print.clicked.connect(self.print_table)

    # -----------------------------
    # Pagination helpers
    # -----------------------------
    def update_pagination_label(self):
        self.lbl_pagination.setText(
            f"{self._('page')} {self.current_page} / {self.total_pages} ({self._('total_rows')}: {self.total_rows})"
        )

    def on_rows_per_page_changed(self, value):
        self.rows_per_page = int(value)
        self.current_page = 1
        self.reload_data()

    def go_to_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.reload_data()

    def go_to_next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.reload_data()

    def reload_data(self):
        self.display_data()

    # -----------------------------
    # Data display
    # -----------------------------
    def display_data(self):
        self.update_pagination_label()
        if not self.columns or not self.data:
            self.table.setRowCount(0)
            return
        self.table.setRowCount(len(self.data))
        for i, row in enumerate(self.data):
            for j, col in enumerate(self.columns):
                value = row.get(col.get("key"), "")
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(col.get("align", Qt.AlignCenter))
                self.table.setItem(i, j, item)
        self.stretch_all_columns()

    def on_row_double_clicked(self, index: QModelIndex):
        row = index.row()
        self.row_double_clicked.emit(row)
        self.request_view.emit(row)

    # -----------------------------
    # Context menu
    # -----------------------------
    def show_context_menu(self, pos):
        menu = QMenu(self)
        edit_action = menu.addAction(self._("edit"))
        delete_action = menu.addAction(self._("delete"))
        view_action = menu.addAction(self._("view"))
        extra_actions = self.get_extra_context_actions(menu)
        action = menu.exec(self.table.mapToGlobal(pos))
        selected_rows = self.get_selected_rows()
        if action == edit_action and selected_rows:
            self.request_edit.emit(selected_rows[0])
        elif action == delete_action and selected_rows:
            self.request_delete.emit(selected_rows)
        elif action == view_action and selected_rows:
            self.request_view.emit(selected_rows[0])
        elif extra_actions:
            for act, callback in extra_actions:
                if action == act:
                    callback(selected_rows)
                    break

    def get_extra_context_actions(self, menu):
        return []

    def get_selected_rows(self):
        indexes = self.table.selectionModel().selectedRows()
        return [idx.row() for idx in indexes]

    # -----------------------------
    # Default overridables for children tabs
    # -----------------------------
    def add_new_item(self):
        pass

    def edit_selected_item(self):
        pass

    def delete_selected_items(self):
        selected = self.get_selected_rows()
        if selected:
            self.request_delete.emit(selected)

    def view_selected_item(self):
        selected = self.get_selected_rows()
        if selected:
            self.request_view.emit(selected[0])

    def select_all_items(self):
        self.table.selectAll()

    def clear_selection(self):
        self.table.clearSelection()

    def focus_search(self):
        self.search_bar.setFocus()

    def copy_selected(self):
        pass

    def cut_selected(self):
        pass

    def paste_data(self):
        pass

    def save_changes(self):
        pass

    def undo(self):
        pass

    def redo(self):
        pass

    # -----------------------------
    # ✅ ENHANCED Import/Export/Print
    # -----------------------------
    def import_from_excel(self):
        """
        Enhanced Excel import with validation and tab-specific support.

        Override '_import_excel_custom(path)' in child tabs to handle
        tab-specific data import to database.

        Default behavior: Preview only (doesn't save to database)
        """
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._("Import Excel"),
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        if not path:
            return

        try:
            # Check if child tab has custom import logic
            if hasattr(self, '_import_excel_custom'):
                success = self._import_excel_custom(path)
                if success:
                    QMessageBox.information(
                        self,
                        self._("import from excel"),
                        self._("Data imported successfully!")
                    )
                    self.reload_data()
                return

            # Default behavior: Preview only (visual import, not to database)
            wb = openpyxl.load_workbook(path)
            ws = wb.active

            # Read headers
            headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]

            # Validate headers match current columns (excluding actions)
            expected_headers = [
                self._(col.get("label", ""))
                for col in self.columns
                if col.get("key") != "actions"
            ]

            if len(headers) != len(expected_headers):
                QMessageBox.warning(
                    self,
                    self._("import from excel"),
                    self._("Excel file structure doesn't match table structure.\n\n") +
                    self._("Expected columns: ") + ", ".join(expected_headers) + "\n" +
                    self._("Found columns: ") + ", ".join([str(h) for h in headers]) + "\n\n" +
                    self._("Please export a template first using 'Export to Excel'.")
                )
                return

            # Show preview warning
            result = QMessageBox.question(
                self,
                self._("import from excel"),
                self._("This will preview the Excel data in the table (NOT saved to database).\n\n") +
                self._("To import data to database, this feature needs to be implemented for this specific tab.\n\n") +
                self._("Continue with preview?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if result != QMessageBox.Yes:
                return

            # Preview data in table
            self.table.setRowCount(0)
            for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):
                self.table.insertRow(i)
                for j, value in enumerate(row):
                    if j >= len(expected_headers):  # Skip extra columns
                        continue
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, j, item)

            QMessageBox.information(
                self,
                self._("import from excel"),
                self._("Data previewed successfully! (Not saved to database)")
            )

        except Exception as e:
            logger.exception(f"Import failed: {e}")
            QMessageBox.critical(
                self,
                self._("import from excel"),
                self._("Failed to import: ") + str(e)
            )

    def export_table_to_excel(self):
        """
        Enhanced Excel export with professional formatting.
        Works for all tabs by exporting visible table data.
        """
        # Generate filename based on tab title
        default_filename = f"{self.title or 'data'}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._("Export Excel"),
            default_filename,
            "Excel Files (*.xlsx)"
        )
        if not path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = (self.title or "Data")[:31]  # Excel limit: 31 chars

            # Collect headers and column indices (exclude actions column)
            headers = []
            col_indices = []
            for i in range(self.table.columnCount()):
                # Skip actions column
                if i < len(self.columns) and self.columns[i].get("key") == "actions":
                    continue

                header_item = self.table.horizontalHeaderItem(i)
                if header_item:
                    headers.append(header_item.text())
                    col_indices.append(i)

            # Write headers
            ws.append(headers)

            # ✨ Professional header styling
            header_font = Font(bold=True, color="FFFFFF", size=12)
            header_fill = PatternFill(start_color="4A7EC8", end_color="4A7EC8", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            header_border = Border(
                left=Side(style='thin', color='FFFFFF'),
                right=Side(style='thin', color='FFFFFF'),
                top=Side(style='thin', color='FFFFFF'),
                bottom=Side(style='thin', color='FFFFFF')
            )

            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_num)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = header_border

            # Write data rows
            for row in range(self.table.rowCount()):
                values = []
                for col_idx in col_indices:
                    item = self.table.item(row, col_idx)
                    if item:
                        values.append(item.text())
                    else:
                        # Cell widget (like action buttons) - skip
                        values.append("")

                ws.append(values)

            # ✨ Data rows styling (alternating colors)
            data_alignment = Alignment(horizontal="center", vertical="center")
            light_fill = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")

            for row_num in range(2, ws.max_row + 1):
                for col_num in range(1, len(headers) + 1):
                    cell = ws.cell(row=row_num, column=col_num)
                    cell.alignment = data_alignment
                    # Alternating row colors
                    if row_num % 2 == 0:
                        cell.fill = light_fill

            # ✨ Auto-adjust column widths
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if cell.value and len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                # Set width with min/max limits
                adjusted_width = min(max(max_length + 3, 12), 50)
                ws.column_dimensions[column_letter].width = adjusted_width

            # ✨ Freeze header row
            ws.freeze_panes = "A2"

            # Save file
            wb.save(path)

            QMessageBox.information(
                self,
                self._("export to excel"),
                self._("Data exported successfully!") + f"\n\n{path}"
            )

        except Exception as e:
            logger.exception(f"Export failed: {e}")
            QMessageBox.critical(
                self,
                self._("export to excel"),
                self._("Failed to export: ") + str(e)
            )

    def print_table(self):
        """Print current table data"""
        try:
            html = self._table_to_html()
            doc = QTextDocument()
            doc.setHtml(html)
            printer = QPrinter(QPrinter.HighResolution)
            dialog = QPrintDialog(printer, self)
            if dialog.exec() == QPrintDialog.Accepted:
                doc.print(printer)
                QMessageBox.information(self, self._("print"), self._("Printed successfully!"))
        except Exception as e:
            logger.exception(f"Print failed: {e}")
            QMessageBox.critical(self, self._("print"), self._("Failed to print: ") + str(e))

    def _table_to_html(self):
        """Convert table to HTML for printing"""
        html = "<table border='1' cellspacing='0' cellpadding='5' style='border-collapse:collapse; width:100%;'>"
        html += "<thead><tr style='background-color:#4A7EC8; color:white; font-weight:bold;'>"

        # Headers (exclude actions column)
        for col in range(self.table.columnCount()):
            if col < len(self.columns) and self.columns[col].get("key") == "actions":
                continue
            header = self.table.horizontalHeaderItem(col)
            if header:
                html += f"<th style='padding:8px;'>{header.text()}</th>"
        html += "</tr></thead><tbody>"

        # Data rows
        for row in range(self.table.rowCount()):
            html += "<tr>"
            for col in range(self.table.columnCount()):
                if col < len(self.columns) and self.columns[col].get("key") == "actions":
                    continue
                item = self.table.item(row, col)
                html += f"<td style='padding:5px;'>{item.text() if item else ''}</td>"
            html += "</tr>"

        html += "</tbody></table>"
        return html

    # -----------------------------
    # Permissions + i18n
    # -----------------------------
    def refresh_data(self):
        self.reload_data()
        QMessageBox.information(self, self._("refresh"), self._("Data refreshed!"))

    def apply_settings(self):
        """
        يُطبَّق الثيم مرة واحدة فقط — عند أول تهيئة أو عند تغييره من الإعدادات.
        التبويبات لا تعيد تطبيق الثيم عند كل تحميل.
        """
        try:
            from core.theme_manager import ThemeManager
            tm = ThemeManager.get_instance()
            if not getattr(tm, "_theme_applied", False):
                # أول مرة فقط
                self.settings.apply_all_settings(force=True)
        except Exception as e:
            logging.error(f"Failed to apply settings in BaseTab: {e}")

    def retranslate_ui(self):
        try:
            self.btn_add.setText(self._("add"))
            self.btn_import.setText(self._("import from excel"))
            self.btn_export.setText(self._("export to excel"))
            self.btn_refresh.setText(self._("refresh"))
            self.btn_print.setText(self._("print"))
            self.chk_admin_cols.setText(self._("show_admin_columns"))
            self.search_bar.setPlaceholderText(self._("Search..."))
            if self.filter_box.count() > 0:
                self.filter_box.setItemText(0, self._("Order by creation date"))
            # label on pagination bar
            for i in range(self.pagination_bar.count()):
                w = self.pagination_bar.itemAt(i).widget()
                if isinstance(w, QLabel) and w.text() and w.text() != "":
                    w.setText(self._("rows_per_page"))
                    break
            self.update_pagination_label()
            # header labels
            if self.columns and self.table.columnCount() == len(self.columns):
                for i, col in enumerate(self.columns):
                    header_key = col.get("label", "")
                    translated = self._(header_key) if header_key else ""
                    if self.table.horizontalHeaderItem(i):
                        self.table.horizontalHeaderItem(i).setText(translated)
        except Exception as e:
            logging.warning(f"BaseTab retranslate_ui failed: {e}")

    def check_permissions(self):
        btns = [
            (self.btn_add, "add"),
            (self.btn_import, "import"),
            (self.btn_export, "export"),
            (self.btn_refresh, "refresh"),
            (self.btn_print, "print"),
        ]
        for btn, perm_key in btns:
            required_perm = self.required_permissions.get(perm_key)
            if required_perm and not _has_any_perm(self.user, required_perm):
                btn.setVisible(False)
            else:
                btn.setVisible(True)

    def set_current_user(self, user):
        self.current_user = user
        self.user = user
        try:
            self.is_admin = _is_admin(user)
            self.chk_admin_cols.setVisible(self.is_admin)
        except Exception:
            pass
        try:
            self._apply_columns_for_current_role()
        except Exception:
            pass
        try:
            self.check_permissions()
        except Exception:
            pass
        try:
            self.reload_data()
        except Exception:
            pass


def _has_any_perm(user, required):
    if not required:
        return True
    if isinstance(required, (list, tuple, set)):
        from database.crud.permissions_crud import has_permission
        return any(has_permission(user, r) for r in required)
    from database.crud.permissions_crud import has_permission
    return has_permission(user, required)