from PySide6.QtWidgets import (
    QWidget, QTableWidget, QAbstractItemView, QMenu, QVBoxLayout, QHBoxLayout, QPushButton,
    QSpacerItem, QSizePolicy, QLabel, QComboBox, QLineEdit, QFileDialog, QMessageBox, QTableWidgetItem, QHeaderView,
    QCheckBox, QAbstractSpinBox
)
from PySide6.QtCore import Qt, QModelIndex, Signal, QTimer, QEvent, QObject
from PySide6.QtGui import QKeySequence, QShortcut, QGuiApplication, QFont
from core.settings_manager import SettingsManager
from core.translator import TranslationManager
from core.permissions import is_admin as _is_admin, has_perm as _has_perm, has_any_perm
from PySide6.QtWidgets import QApplication
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtGui import QTextDocument
import logging

# ── فونت bold مشترك لكل خلايا الجداول ─────────────────────────────────────
_BOLD_ITEM_FONT = QFont()
_BOLD_ITEM_FONT.setBold(True)
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

logger = logging.getLogger(__name__)


class _NoWheelOnInputs(QObject):
    """
    EventFilter يمنع QComboBox و QSpinBox من تغيير قيمتها بعجلة الفارة
    ما لم يكن الـ widget مضغوطاً عليه بشكل صريح (hasFocus).

    يُنصَّب مرة واحدة على مستوى QApplication فيغطّي كل الـ widgets.
    """
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Wheel:
            if isinstance(obj, (QComboBox, QAbstractSpinBox)):
                event.ignore()
                return True   # ابتلع الحدث كلياً — لا تغيير بالعجلة مطلقاً
        return super().eventFilter(obj, event)


# نصنع instance واحد فقط لكل عمر التطبيق
_wheel_filter = _NoWheelOnInputs()


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
        # عرض الأعمدة يُضبط لاحقاً في stretch_all_columns بعد تحميل البيانات

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
        self.table.setObjectName("data-table")
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
        self.table.horizontalHeader().setSectionsMovable(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.doubleClicked.connect(self.on_row_double_clicked)

        # ✅ ضبط ارتفاع الصفوف
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.verticalHeader().setMinimumSectionSize(42)

        # ضبط ارتفاع الهيدر + bold font
        self.table.horizontalHeader().setMinimumHeight(44)
        _hdr_font = self.table.horizontalHeader().font()
        _hdr_font.setBold(True)
        _hdr_font.setPointSize(_hdr_font.pointSize() + 0)  # نفس الحجم — bold فقط
        self.table.horizontalHeader().setFont(_hdr_font)

        # منع QComboBox/QSpinBox من تغيير قيمتها بالعجلة بدون focus
        # (الـ filter يُنصَّب مرة واحدة في main.py على QApplication — يغطي كل الـ widgets)

        def stretch_all_columns():
            col_count = self.table.columnCount()
            if not col_count:
                return
            hdr = self.table.horizontalHeader()
            hdr.setSectionResizeMode(QHeaderView.Interactive)

        self.stretch_all_columns = stretch_all_columns

    def _apply_table_direction(self):
        """الجدول يبقى LTR دائماً — Qt يتولى عكس المحتوى تلقائياً عبر QApplication."""
        pass

    def setup_pagination_controls(self):
        self.cmb_rows_per_page.currentTextChanged.connect(self.on_rows_per_page_changed)
        self.btn_prev.clicked.connect(self.go_to_prev_page)
        self.btn_next.clicked.connect(self.go_to_next_page)
        self.update_pagination_label()

    def _table_has_focus(self) -> bool:
        """True إذا كان الـ focus على الجدول وليس على search_bar أو أي input آخر."""
        focused = QApplication.focusWidget()
        if focused is None:
            return False
        # إذا كان الـ focus على أي QLineEdit أو QComboBox → لا تنفّذ اختصارات الجدول
        if isinstance(focused, (QLineEdit, QComboBox)):
            return False
        return True

    def setup_shortcuts(self):
        # ── اختصارات آمنة دائماً ──────────────────────────────────────────
        QShortcut(QKeySequence("Ctrl+N"), self, self.add_new_item)
        QShortcut(QKeySequence("Ctrl+E"), self, self.edit_selected_item)
        QShortcut(QKeySequence("Ctrl+A"), self, self.select_all_items)
        QShortcut(QKeySequence("Ctrl+D"), self, self.clear_selection)
        QShortcut(QKeySequence("PageUp"),  self, self.go_to_prev_page)
        QShortcut(QKeySequence("PageDown"), self, self.go_to_next_page)
        QShortcut(QKeySequence("Ctrl+P"), self, self.print_table)
        QShortcut(QKeySequence("Ctrl+I"), self, self.import_from_excel)
        QShortcut(QKeySequence("Ctrl+Shift+E"), self, self.export_table_to_excel)
        QShortcut(QKeySequence("Ctrl+R"), self, self.refresh_data)
        # Ctrl+F → focus على search_bar المحلي فقط (لا يتعارض مع Global Search)
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)
        # Ctrl+C → نسخ خلايا الجدول المحددة
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_selected)

        # ── اختصارات context-aware (تعمل فقط عندما الجدول هو المركّز) ─────
        QShortcut(QKeySequence("Delete"), self,
                  lambda: self.delete_selected_items() if self._table_has_focus() else None)
        QShortcut(QKeySequence("Enter"), self,
                  lambda: self.view_selected_item() if self._table_has_focus() else None)
        QShortcut(QKeySequence("Return"), self,
                  lambda: self.view_selected_item() if self._table_has_focus() else None)
        QShortcut(QKeySequence("Escape"), self,
                  lambda: self.clear_selection() if self._table_has_focus() else None)

    def setup_signals(self):
        self.btn_add.clicked.connect(self.add_new_item)
        self.btn_import.clicked.connect(self.import_from_excel)
        self.btn_export.clicked.connect(self.export_table_to_excel)
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.btn_print.clicked.connect(self.print_table)

        # debounce للـ search_bar — ينتظر 350ms بعد آخر حرف قبل الاستعلام
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(350)
        self._search_timer.timeout.connect(self._on_search_changed)
        self.search_bar.textChanged.connect(lambda _: self._search_timer.start())

        # filter_box — يعيد التحميل عند تغيير الترتيب
        self.filter_box.currentIndexChanged.connect(self._on_filter_box_changed)

    def _on_search_changed(self):
        """يُستدعى بعد انتهاء الـ debounce — يعيد تحميل البيانات."""
        self.current_page = 1
        self.reload_data()

    def _on_filter_box_changed(self, _index: int):
        """يُستدعى عند تغيير ترتيب العرض — يعيد تحميل البيانات."""
        self.current_page = 1
        self.reload_data()

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

    def select_record_by_id(self, record_id: int):
        """
        يبحث عن السجل بالـ ID في self.data ويحدده في الجدول.
        يُستدعى من البحث العام عند الانتقال لنتيجة.
        """
        # تأكد أن البيانات محملة
        if not self.data:
            self.reload_data()

        # ابحث عن الصف
        for row_idx, row in enumerate(self.data):
            row_id = row.get("id")
            if row_id is not None and int(row_id) == int(record_id):
                self.table.setCurrentCell(row_idx, 0)
                self.table.scrollTo(
                    self.table.model().index(row_idx, 0),
                    self.table.PositionAtCenter
                )
                self.table.selectRow(row_idx)
                return

        # إذا ما لقيناه — ممكن مفلتر، نرجع للكل ونعيد البحث
        try:
            self._reset_filters()
            self.reload_data()
            for row_idx, row in enumerate(self.data):
                if row.get("id") is not None and int(row.get("id")) == int(record_id):
                    self.table.setCurrentCell(row_idx, 0)
                    self.table.scrollTo(
                        self.table.model().index(row_idx, 0),
                        self.table.PositionAtCenter
                    )
                    self.table.selectRow(row_idx)
                    return
        except Exception:
            pass

    def _reset_filters(self):
        """يصفّر الفلاتر — يُعاد تعريفه في التابات التي لديها فلاتر."""
        if hasattr(self, "search_bar"):
            self.search_bar.clear()

    def reload_data(self):
        self.display_data()

    # ─────────────────────────────────────────────────────────────────────
    # Search / Sort / Status helpers
    # ─────────────────────────────────────────────────────────────────────
    def _get_search_keys(self) -> list:
        skip = {"id", "actions", "created_at", "updated_at", "created_by_name", "updated_by_name"}
        return [c.get("key", "") for c in self.columns if c.get("key") and c.get("key") not in skip]

    def _apply_base_search(self, rows: list) -> list:
        q = (self.search_bar.text() or "").strip().casefold()
        if not q:
            return rows
        keys = self._get_search_keys()
        result = []
        for row in rows:
            for k in keys:
                if q in str(row.get(k, "") or "").casefold():
                    result.append(row)
                    break
        return result

    def _apply_base_sort(self, rows: list) -> list:
        order = self.filter_box.currentData() or "date_desc"
        try:
            if order == "name_asc":
                for k in ("name_local", "name_ar", "name_en", "name", "full_name"):
                    if any(k in r for r in rows):
                        return sorted(rows, key=lambda r: str(r.get(k, "") or "").casefold())
            elif order == "name_desc":
                for k in ("name_local", "name_ar", "name_en", "name", "full_name"):
                    if any(k in r for r in rows):
                        return sorted(rows, key=lambda r: str(r.get(k, "") or "").casefold(), reverse=True)
            elif order == "date_asc":
                for k in ("transaction_date", "entry_date", "created_at", "date"):
                    if any(k in r for r in rows):
                        return sorted(rows, key=lambda r: str(r.get(k, "") or ""))
        except Exception:
            pass
        return rows

    def _update_status_bar(self, displayed: int, total: int):
        if not hasattr(self, "_lbl_count"):
            return
        q = (self.search_bar.text() or "").strip()
        if q and displayed < total:
            self._lbl_count.setText(f"🔍 {displayed} {self._('of')} {total} {self._('total_rows')}")
        else:
            self._lbl_count.setText(f"{displayed} {self._('total_rows')}")
        order_label = self.filter_box.currentText() if self.filter_box.count() else ""
        self._lbl_sort.setText(f"↕ {order_label}" if order_label else "")

    def _show_empty_state(self, empty: bool, searched: bool = False):
        if not hasattr(self, "_empty_widget"):
            return
        if empty:
            self._lbl_empty_icon.setText("🔍" if searched else "📋")
            self._lbl_empty_text.setText(
                self._("no_search_results") if searched else self._("no_data_available")
            )
            self._empty_widget.setGeometry(0, 40, self.table.width(), max(self.table.height() - 40, 100))
            self._empty_widget.show()
            self._empty_widget.raise_()
        else:
            self._empty_widget.hide()

    # -----------------------------
    # Data display
    # -----------------------------
    def display_data(self):
        rows = list(self.data) if self.data else []
        total_before = len(rows)
        searched = bool((self.search_bar.text() or "").strip())

        if not getattr(self, "_skip_base_search", False):
            rows = self._apply_base_search(rows)
        if not getattr(self, "_skip_base_sort", False):
            rows = self._apply_base_sort(rows)

        self.total_rows  = len(rows)
        self.total_pages = max(1, (self.total_rows + self.rows_per_page - 1) // self.rows_per_page)
        self.current_page = max(1, min(self.current_page, self.total_pages))
        start = (self.current_page - 1) * self.rows_per_page
        page_rows = rows[start: start + self.rows_per_page]

        self.update_pagination_label()
        self._update_status_bar(len(rows), total_before)
        self._show_empty_state(len(rows) == 0, searched=searched)

        if not self.columns:
            self.table.setRowCount(0)
            return

        # ── تجميد الـ UI أثناء التحميل لمنع إعادة الرسم مع كل صف ────────
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(page_rows))
            for i, row in enumerate(page_rows):
                for j, col in enumerate(self.columns):
                    key   = col.get("key", "")
                    value = row.get(key, "")
                    item  = QTableWidgetItem(str(value) if value is not None else "")
                    item.setTextAlignment(col.get("align", Qt.AlignCenter))
                    item.setFont(_BOLD_ITEM_FONT)
                    self.table.setItem(i, j, item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.setSortingEnabled(True)
        self.stretch_all_columns()

    # ─────────────────────────────────────────────────────────────────────
    # Shared display_data with actions  (تستخدمها التابات بدل display_data)
    # ─────────────────────────────────────────────────────────────────────
    def _display_with_actions(self, edit_perm: str, delete_perm: str):
        """
        عرض self.data مع:
          - بحث + ترتيب + pagination (من display_data في البيس)
          - أزرار Edit/Delete موحدة في عمود actions
          - إخفاء عمود actions إذا لا صلاحية
          - إخفاء أعمدة الأدمن للمستخدمين العاديين

        الشرط: التاب يجب أن يعرّف:
          self._open_edit_dialog(obj)
          self._delete_single(obj)
        """
        can_edit   = _has_perm(self.current_user, edit_perm)   if edit_perm   else False
        can_delete = _has_perm(self.current_user, delete_perm) if delete_perm else False
        show_actions = can_edit or can_delete

        # ── تطبيق البحث / الترتيب / pagination من البيس ─────────────────
        rows = list(self.data) if self.data else []
        total_before = len(rows)
        searched = bool((self.search_bar.text() or "").strip())

        if not getattr(self, "_skip_base_search", False):
            rows = self._apply_base_search(rows)
        if not getattr(self, "_skip_base_sort", False):
            rows = self._apply_base_sort(rows)

        self.total_rows  = len(rows)
        self.total_pages = max(1, (self.total_rows + self.rows_per_page - 1) // self.rows_per_page)
        self.current_page = max(1, min(self.current_page, self.total_pages))
        start = (self.current_page - 1) * self.rows_per_page
        page_rows = rows[start: start + self.rows_per_page]

        self.update_pagination_label()
        self._update_status_bar(len(rows), total_before)
        self._show_empty_state(len(rows) == 0, searched=searched)

        # ── رسم الجدول ───────────────────────────────────────────────────
        # تجميد الرسم أثناء التحميل — يمنع إعادة الرسم مع كل صف (أسرع بـ 5-10x)
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(page_rows))
            for row_idx, row in enumerate(page_rows):
                for col_idx, col in enumerate(self.columns):
                    key = col.get("key", "")
                    if key == "actions":
                        if not show_actions:
                            continue
                        obj = row.get("actions")
                        if can_edit and can_delete:
                            w = QWidget()
                            lay = QHBoxLayout(w)
                            lay.setContentsMargins(2, 2, 2, 2)
                            lay.setSpacing(3)
                            btn_e = QPushButton(self._("edit"))
                            btn_e.setObjectName("primary-btn")
                            btn_e.clicked.connect(lambda _=False, o=obj: self._open_edit_dialog(o))
                            btn_d = QPushButton(self._("delete"))
                            btn_d.setObjectName("danger-btn")
                            btn_d.clicked.connect(lambda _=False, o=obj: self._delete_single(o))
                            lay.addWidget(btn_e)
                            lay.addWidget(btn_d)
                            self.table.setCellWidget(row_idx, col_idx, w)
                        elif can_edit:
                            btn = QPushButton(self._("edit"))
                            btn.setObjectName("primary-btn")
                            btn.clicked.connect(lambda _=False, o=obj: self._open_edit_dialog(o))
                            self.table.setCellWidget(row_idx, col_idx, btn)
                        elif can_delete:
                            btn = QPushButton(self._("delete"))
                            btn.setObjectName("danger-btn")
                            btn.clicked.connect(lambda _=False, o=obj: self._delete_single(o))
                            self.table.setCellWidget(row_idx, col_idx, btn)
                    else:
                        val = row.get(key, "")
                        item = QTableWidgetItem(str(val) if val is not None else "")
                        item.setTextAlignment(col.get("align", Qt.AlignCenter))
                        item.setFont(_BOLD_ITEM_FONT)
                        self.table.setItem(row_idx, col_idx, item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.setSortingEnabled(True)

        # ── إخفاء عمود actions إذا لا صلاحية ───────────────────────────
        try:
            ai = next((i for i, c in enumerate(self.columns) if c.get("key") == "actions"), None)
            if ai is not None:
                self.table.setColumnHidden(ai, not show_actions)
        except Exception:
            pass

        self._apply_admin_columns()
        self.stretch_all_columns()

    def _apply_admin_columns(self):
        """يخفي أعمدة الأدمن (id, created_by, ...) للمستخدمين العاديين."""
        admin_keys = {"id", "created_by_name", "updated_by_name", "created_at", "updated_at"}
        for idx, col in enumerate(self.columns):
            if col.get("key") in admin_keys:
                try:
                    self.table.setColumnHidden(idx, not self.is_admin)
                except Exception:
                    pass

    def on_row_double_clicked(self, index: QModelIndex):
        row = index.row()
        self.row_double_clicked.emit(row)
        self.request_view.emit(row)

    # -----------------------------
    # Context menu
    # -----------------------------
    def show_context_menu(self, pos):
        selected_rows = self.get_selected_rows()
        count = len(selected_rows)

        menu = QMenu(self)

        # ── عنوان يُظهر عدد الصفوف المحددة ──────────────────────────────
        if count > 1:
            title = menu.addAction(f"✓  {count}  {self._('selected_rows_count') if hasattr(self, '_') else 'rows selected'}")
            title.setEnabled(False)
            menu.addSeparator()

        # ── إجراءات الصف الواحد ──────────────────────────────────────────
        view_action   = menu.addAction(self._("view"))
        edit_action   = menu.addAction(self._("edit"))

        # edit و view: متاحان فقط بصف واحد
        view_action.setEnabled(count == 1)
        edit_action.setEnabled(count == 1)

        menu.addSeparator()

        # ── نسخ ─────────────────────────────────────────────────────────
        copy_action = menu.addAction(self._("copy") if "copy" in (self._.__doc__ or "") or True else "Copy")
        copy_action.setEnabled(count >= 1)

        menu.addSeparator()

        # ── حذف (يعمل مع تعدد) ──────────────────────────────────────────
        if count > 1:
            delete_action = menu.addAction(f"🗑  {self._('delete')}  ({count})")
        else:
            delete_action = menu.addAction(self._("delete"))
        delete_action.setEnabled(count >= 1)

        # ── إجراءات إضافية من التاب الفرعي ─────────────────────────────
        extra_actions = self.get_extra_context_actions(menu)

        # ── تنفيذ ────────────────────────────────────────────────────────
        action = menu.exec(self.table.mapToGlobal(pos))
        if action is None:
            return

        if action == view_action and selected_rows:
            self.request_view.emit(selected_rows[0])
        elif action == edit_action and selected_rows:
            self.request_edit.emit(selected_rows[0])
        elif action == copy_action and selected_rows:
            self.copy_selected()
        elif action == delete_action and selected_rows:
            self.request_delete.emit(selected_rows)
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
        """Ctrl+C — ينسخ محتوى الخلايا المحددة إلى الـ clipboard بصيغة TSV (متوافقة مع Excel)."""
        selected = self.table.selectedItems()
        if not selected:
            return
        # نرتب الخلايا حسب row ثم column
        rows_data: dict = {}
        for item in selected:
            r, c = item.row(), item.column()
            rows_data.setdefault(r, {})[c] = item.text()
        lines = []
        for r in sorted(rows_data):
            cols = rows_data[r]
            lines.append("\t".join(cols[c] for c in sorted(cols)))
        QGuiApplication.clipboard().setText("\n".join(lines))

    def cut_selected(self):
        """Ctrl+X — نسخ فقط (الجدول read-only، لا حذف)."""
        self.copy_selected()

    def paste_data(self):
        """Ctrl+V — غير مدعوم (الجدول read-only)."""
        pass

    def save_changes(self):
        """Ctrl+S — يُطبَّق فقط في تابات تدعمه (override في الـ child)."""
        pass

    def undo(self):
        """Ctrl+Z — غير مدعوم على مستوى التاب."""
        pass

    def redo(self):
        """Ctrl+Y — غير مدعوم على مستوى التاب."""
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
                    item.setFont(_BOLD_ITEM_FONT)
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
        # عرض رسالة خفيفة في status bar عوضاً عن popup مزعج
        try:
            from PySide6.QtWidgets import QApplication
            main_win = QApplication.activeWindow()
            if main_win and hasattr(main_win, "statusBar"):
                main_win.statusBar().showMessage(self._("Data refreshed!"), 2000)
        except Exception:
            pass

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
            _sort_keys = ["sort_by_date_desc", "sort_by_date_asc", "sort_by_name_asc", "sort_by_name_desc"]
            for i, key in enumerate(_sort_keys):
                if i < self.filter_box.count():
                    self.filter_box.setItemText(i, self._(key))
            if hasattr(self, "_lbl_empty_text"):
                self._lbl_empty_text.setText(self._("no_results_found"))
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
            # ── اتجاه الجدول والهيدر ──────────────────────────────────
            self._apply_table_direction()

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
            if required_perm:
                # قد يكون required_perm قائمة أو نص واحد
                if isinstance(required_perm, (list, tuple, set)):
                    visible = has_any_perm(self.user, list(required_perm))
                else:
                    visible = _has_perm(self.user, required_perm)
                btn.setVisible(visible)
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