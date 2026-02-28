"""
TransactionsTab - LOGIPORT v3.2
================================

Added filters:
  - Date range  (from / to)  → uses CRUD date_from / date_to
  - Type combo  (all / export / import / transit)
  - Search bar  (client name / transaction_no — client-side after load)
  - Quick presets: Today / This Week / This Month / Clear
"""

from core.base_tab import BaseTab
from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from core.permissions import has_perm, is_admin
from core.admin_columns import apply_admin_columns_to_table

from database.crud.transactions_crud import TransactionsCRUD
from database.models import get_session_local, User
from sqlalchemy import func

try:
    from database.models import Client, Company, Country, Currency
except Exception:
    Client = Company = Country = Currency = None

from ui.dialogs.add_TransactionWindow.window import AddTransactionWindow

try:
    from services.excel_service import ExcelService as _ExcelSvc
    _HAS_EXCEL_SVC = True
except Exception:
    _HAS_EXCEL_SVC = False

from PySide6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QHBoxLayout, QWidget, QPushButton,
    QDateEdit, QComboBox, QLabel, QFrame, QSizePolicy, QVBoxLayout
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from datetime import date, timedelta


class TransactionsTab(BaseTab):
    required_permissions = {
        "view":    ["view_transactions"],
        "add":     ["add_transaction"],
        "edit":    ["edit_transaction"],
        "delete":  ["delete_transaction"],
        "import":  ["view_transactions"],
        "export":  ["view_transactions"],
        "print":   ["view_transactions"],
        "refresh": ["view_transactions"],
    }

    def __init__(self, parent=None, current_user=None):
        _ = TranslationManager.get_instance().translate
        u = current_user or SettingsManager.get_instance().get("user")
        super().__init__(parent)
        self._ = _
        self.set_current_user(u)
        self.trx_crud = TransactionsCRUD()

        self.table.setAlternatingRowColors(True)
        self.set_columns_for_role(
            base_columns=[
                {"label": "transaction_no",       "key": "transaction_no"},
                {"label": "transaction_type",     "key": "transaction_type_badge"},
                {"label": "transaction_date",     "key": "transaction_date"},
                {"label": "client",               "key": "client_name"},
                {"label": "exporting_company",    "key": "exporter_name"},
                {"label": "importing_company",    "key": "importer_name"},
                {"label": "relationship_type",    "key": "relationship_label"},
                {"label": "linked_entries_count", "key": "entries_count"},
                {"label": "total_value",          "key": "totals_value_label"},
                {"label": "actions",              "key": "actions"},
            ],
            admin_columns=[
                {"label": "ID",          "key": "id"},
                {"label": "created_by",  "key": "created_by_name"},
                {"label": "updated_by",  "key": "updated_by_name"},
                {"label": "created_at",  "key": "created_at"},
                {"label": "updated_at",  "key": "updated_at"},
            ],
        )
        self.check_permissions()
        try:
            self.can_edit   = has_perm(self.current_user, self.required_permissions.get("edit",   []))
            self.can_delete = has_perm(self.current_user, self.required_permissions.get("delete", []))
        except Exception:
            self.can_edit = self.can_delete = False

        # ── build date/type filter bar ──────────────────────────────
        self._build_filter_bar()
        self._build_footer()
        # filter_box من البيس مكرر مع _type_combo الخاص بنا — نخفيه
        if hasattr(self, "filter_box"):
            self.filter_box.setVisible(False)

        for sig_name, handler in (
            ("request_add",        self.add_new_item),
            ("request_edit",       self.edit_selected_item),
            ("request_delete",     self.delete_selected_items),
            ("row_double_clicked", self.on_row_double_clicked),
            ("request_refresh",    self.reload_data),
        ):
            sig = getattr(self, sig_name, None)
            if sig:
                try: sig.connect(handler)
                except Exception: pass

        self.reload_data()

    # ── Filter bar ────────────────────────────────────────────────────────

    def _build_filter_bar(self):
        """شريط فلترة احترافي مع تجميع منطقي للعناصر."""
        from PySide6.QtWidgets import QGroupBox

        filter_bar = QWidget()
        filter_bar.setObjectName("filter-bar")
        outer = QHBoxLayout(filter_bar)
        outer.setContentsMargins(0, 4, 0, 4)
        outer.setSpacing(10)

        # ── مجموعة 1: نطاق التاريخ ──────────────────────────────────────
        date_group = QWidget()
        date_group.setObjectName("filter-group")
        date_lay = QHBoxLayout(date_group)
        date_lay.setContentsMargins(10, 4, 10, 4)
        date_lay.setSpacing(6)

        lbl_from = QLabel("📅")
        lbl_from.setFixedWidth(18)
        date_lay.addWidget(lbl_from)

        self._date_from = QDateEdit()
        self._date_from.setObjectName("form-input")
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        self._date_from.setDate(QDate.currentDate().addMonths(-3))
        self._date_from.setFixedWidth(106)
        self._date_from.dateChanged.connect(self._on_filter_changed)
        date_lay.addWidget(self._date_from)

        arr = QLabel("→")
        arr.setStyleSheet("color: #6b7280; font-weight: 600;")
        date_lay.addWidget(arr)

        self._date_to = QDateEdit()
        self._date_to.setObjectName("form-input")
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setFixedWidth(106)
        self._date_to.dateChanged.connect(self._on_filter_changed)
        date_lay.addWidget(self._date_to)

        outer.addWidget(date_group)

        # ── أزرار Preset مدمجة ──────────────────────────────────────────
        preset_group = QWidget()
        preset_lay = QHBoxLayout(preset_group)
        preset_lay.setContentsMargins(0, 0, 0, 0)
        preset_lay.setSpacing(4)

        presets = [
            (self._("today"),      self._preset_today,  "📅"),
            (self._("this_week"),  self._preset_week,   "📆"),
            (self._("this_month"), self._preset_month,  "🗓"),
        ]
        for label, slot, icon in presets:
            btn = QPushButton(f"{icon} {label}")
            btn.setObjectName("filter-preset-btn")
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton#filter-preset-btn {
                    background: transparent;
                    border: 1.5px solid #D1D5DB;
                    border-radius: 8px;
                    padding: 0 10px;
                    font-size: 11px;
                    color: #374151;
                }
                QPushButton#filter-preset-btn:hover {
                    background: #EFF6FF;
                    border-color: #3B82F6;
                    color: #1D4ED8;
                }
            """)
            btn.clicked.connect(slot)
            preset_lay.addWidget(btn)

        clr = QPushButton("✖")
        clr.setObjectName("filter-preset-btn")
        clr.setFixedSize(32, 32)
        clr.setCursor(Qt.PointingHandCursor)
        clr.setToolTip(self._("clear"))
        clr.setStyleSheet("""
            QPushButton#filter-preset-btn {
                background: transparent;
                border: 1.5px solid #FCA5A5;
                border-radius: 8px;
                font-size: 12px; color: #DC2626;
            }
            QPushButton#filter-preset-btn:hover {
                background: #FEF2F2; border-color: #DC2626;
            }
        """)
        clr.clicked.connect(self._preset_clear)
        preset_lay.addWidget(clr)

        outer.addWidget(preset_group)

        # ── فاصل ───────────────────────────────────────────────────────
        vsep = QFrame()
        vsep.setFrameShape(QFrame.VLine)
        vsep.setObjectName("separator")
        vsep.setFixedHeight(28)
        outer.addWidget(vsep)

        # ── نوع المعاملة — Pill buttons ─────────────────────────────────
        type_group = QWidget()
        type_lay = QHBoxLayout(type_group)
        type_lay.setContentsMargins(0, 0, 0, 0)
        type_lay.setSpacing(4)

        self._type_btns = {}
        type_defs = [
            ("", "🔍 " + self._("All")),
            ("export",  "📤 " + self._("export")),
            ("import",  "📥 " + self._("import")),
            ("transit", "🔄 " + self._("transit")),
        ]

        def _style_type_btn(btn, active):
            if active:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #3B82F6; color: white;
                        border: 1.5px solid #3B82F6;
                        border-radius: 14px; padding: 0 12px;
                        font-size: 11px; font-weight: 600;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent; color: #374151;
                        border: 1.5px solid #D1D5DB;
                        border-radius: 14px; padding: 0 12px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        border-color: #3B82F6; color: #1D4ED8;
                        background: #EFF6FF;
                    }
                """)

        first_btn = None
        for val, label in type_defs:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("type_val", val)
            self._type_btns[val] = btn
            if first_btn is None:
                first_btn = btn
                _style_type_btn(btn, True)
            else:
                _style_type_btn(btn, False)

            def _on_type_click(checked=False, v=val):
                for vv, b in self._type_btns.items():
                    _style_type_btn(b, vv == v)
                self._selected_type = v
                self._on_filter_changed()
            btn.clicked.connect(_on_type_click)
            type_lay.addWidget(btn)

        self._selected_type = ""
        outer.addWidget(type_group)

        # للتوافق مع الكود القديم
        self._type_combo = QComboBox()
        self._type_combo.setVisible(False)
        self._type_combo.addItem("", "")
        self._type_combo.addItem("export", "export")
        self._type_combo.addItem("import", "import")
        self._type_combo.addItem("transit", "transit")

        outer.addStretch(1)

        # ── عداد النتائج ────────────────────────────────────────────────
        self._count_lbl = QLabel()
        self._count_lbl.setObjectName("text-muted")
        self._count_lbl.setStyleSheet("font-size: 11px; color: #6B7280; padding: 0 4px;")
        outer.addWidget(self._count_lbl)

        # ── تصدير Excel ─────────────────────────────────────────────────
        btn_rich = QPushButton("📊  " + self._("export_to_excel_rich"))
        btn_rich.setObjectName("secondary-btn")
        btn_rich.setFixedHeight(32)
        btn_rich.setToolTip(self._("export_transactions_tip"))
        btn_rich.clicked.connect(self._rich_export)
        outer.addWidget(btn_rich)

        try:
            self.layout.insertWidget(1, filter_bar)
        except Exception:
            self.layout.addWidget(filter_bar)

    # ── Preset slots ─────────────────────────────────────────────────────────

    def _preset_today(self):
        today = QDate.currentDate()
        self._date_from.setDate(today)
        self._date_to.setDate(today)

    def _preset_week(self):
        today = QDate.currentDate()
        self._date_from.setDate(today.addDays(-today.dayOfWeek() + 1))
        self._date_to.setDate(today)

    def _preset_month(self):
        today = QDate.currentDate()
        self._date_from.setDate(QDate(today.year(), today.month(), 1))
        self._date_to.setDate(today)

    def _preset_clear(self):
        self._date_from.setDate(QDate.currentDate().addMonths(-3))
        self._date_to.setDate(QDate.currentDate())
        self._type_combo.setCurrentIndex(0)
        if hasattr(self, "search_bar"):
            self.search_bar.clear()

    def _on_filter_changed(self, *_):
        self.reload_data()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _get_filter_values(self):
        """Return (date_from_str, date_to_str, trx_type_str, search, status_str)."""
        d_from  = self._date_from.date().toString("yyyy-MM-dd") if hasattr(self, "_date_from")    else None
        d_to    = self._date_to.date().toString("yyyy-MM-dd")   if hasattr(self, "_date_to")      else None
        t_type  = getattr(self, "_selected_type", "") or (self._type_combo.currentData() if hasattr(self, "_type_combo") else "")
        status  = self._status_combo.currentData()              if hasattr(self, "_status_combo") else ""
        search  = self.search_bar.text().strip().lower()        if hasattr(self, "search_bar")    else ""
        return d_from, d_to, t_type or None, search, status or None

    # ── Data ──────────────────────────────────────────────────────────

    def reload_data(self):
        self._skip_base_search = True   # البحث يتم server-side أو بـ _apply_search_filter
        self._skip_base_sort   = True   # الترتيب يتم server-side أو يُدار بـ CRUD
        d_from, d_to, t_type, search, status = self._get_filter_values()
        admin = is_admin(self.current_user)

        # كل الفلاتر server-side الآن
        try:
            items = self.trx_crud.list_transactions(
                limit=1000,
                date_from=d_from,
                date_to=d_to,
                transaction_type=t_type or None,
                search=search or None,
                status=status or None,
            ) or []
        except TypeError:
            items = self.trx_crud.list_transactions(limit=1000) or []

        client_ids, company_ids, currency_ids = set(), set(), set()
        created_ids, updated_ids = set(), set()
        for t in items:
            if isinstance(getattr(t, "client_id",           None), int): client_ids.add(t.client_id)
            if isinstance(getattr(t, "exporter_company_id", None), int): company_ids.add(t.exporter_company_id)
            if isinstance(getattr(t, "importer_company_id", None), int): company_ids.add(t.importer_company_id)
            if isinstance(getattr(t, "currency_id",         None), int): currency_ids.add(t.currency_id)
            if isinstance(getattr(t, "created_by_id",       None), int): created_ids.add(t.created_by_id)
            if isinstance(getattr(t, "updated_by_id",       None), int): updated_ids.add(t.updated_by_id)

        id_to_user = {}; id_to_client = {}; id_to_company = {}
        id_to_currency = {}; entries_count = {}

        s = get_session_local()()
        try:
            if admin and (created_ids | updated_ids):
                for uid, fn, un in s.query(User.id, User.full_name, User.username).filter(User.id.in_(created_ids | updated_ids)):
                    id_to_user[uid] = fn or un or str(uid)
            if client_ids and Client:
                for cid, nar, nen, ntr in s.query(Client.id, Client.name_ar, Client.name_en, Client.name_tr).filter(Client.id.in_(client_ids)):
                    id_to_client[cid] = {"ar": nar, "en": nen, "tr": ntr}
            if company_ids and Company:
                for kid, nar, nen, ntr in s.query(Company.id, Company.name_ar, Company.name_en, Company.name_tr).filter(Company.id.in_(company_ids)):
                    id_to_company[kid] = {"ar": nar, "en": nen, "tr": ntr}
            if currency_ids and Currency:
                for cid, code, sym in s.query(Currency.id, Currency.code, Currency.symbol).filter(Currency.id.in_(currency_ids)):
                    id_to_currency[cid] = {"code": code, "symbol": sym}
            try:
                from database.models.transaction import TransactionEntry
                trx_ids = [getattr(t, "id") for t in items if getattr(t, "id", None)]
                for tid, cnt in s.query(TransactionEntry.transaction_id, func.count(TransactionEntry.id)).filter(TransactionEntry.transaction_id.in_(trx_ids)).group_by(TransactionEntry.transaction_id):
                    entries_count[int(tid)] = int(cnt)
            except Exception:
                pass
        finally:
            s.close()

        lang = TranslationManager.get_instance().get_current_language()
        rel_map = {"direct": self._("direct"), "intermediary": self._("intermediary"),
                   "by_request": self._("by_request"), "on_behalf": self._("on_behalf"),
                   "via_broker": self._("via_broker")}

        def _pick(d):
            return d.get(lang) or d.get("en") or d.get("ar") or d.get("tr") or ""

        all_rows = []
        for t in items:
            cur   = id_to_currency.get(getattr(t, "currency_id", None) or -1, {})
            tval  = getattr(t, "totals_value", None)
            tlbl  = str(tval) if tval is not None else "0"
            cc    = cur.get("code") or cur.get("symbol")
            if cc: tlbl += f" {cc}"

            client_name = _pick(id_to_client.get(getattr(t, "client_id", None) or -1, {}))

            trx_type_code = getattr(t, "transaction_type", "export") or "export"
            trx_status = getattr(t, "status", "active") or "active"
            row = {
                "id":                    getattr(t, "id", None),
                "transaction_no":        getattr(t, "transaction_no", ""),
                "transaction_type_label": self._(trx_type_code),
                "transaction_type_badge": trx_type_code,
                "transaction_date":      str(getattr(t, "transaction_date", "") or ""),
                "client_name":           client_name,
                "exporter_name":         _pick(id_to_company.get(getattr(t, "exporter_company_id", None) or -1, {})),
                "importer_name":         _pick(id_to_company.get(getattr(t, "importer_company_id", None) or -1, {})),
                "relationship_label":    rel_map.get(str(getattr(t, "relationship_type", "") or ""), str(getattr(t, "relationship_type", "") or "")),
                "entries_count":         entries_count.get(getattr(t, "id", 0), 0),
                "totals_value_label":    tlbl,
                "status":                trx_status,
                "actions":               t,
                "_client_name_raw":      client_name,
            }
            if admin:
                row.update({
                    "created_by_name": id_to_user.get(getattr(t, "created_by_id", None) or -1, ""),
                    "updated_by_name": id_to_user.get(getattr(t, "updated_by_id", None) or -1, ""),
                    "created_at":      str(getattr(t, "created_at", "") or ""),
                    "updated_at":      str(getattr(t, "updated_at", "") or ""),
                })
            all_rows.append(row)

        self.data = all_rows

        # ── Update result count ───────────────────────────────────
        if hasattr(self, "_count_lbl"):
            self._count_lbl.setText(f"({len(self.data)} " + self._("total_rows") + ")")

        self._update_footer(self.data)
        self.render_table(self.data, show_actions=bool(self.can_edit or self.can_delete))

    def render_table(self, data, show_actions=True):
        self.table.setRowCount(0)
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels([self._(c.get("label", "")) for c in self.columns])
        can_edit   = has_perm(self.current_user, self.required_permissions.get("edit",   []))
        can_delete = has_perm(self.current_user, self.required_permissions.get("delete", []))

        for ri, row in enumerate(data):
            self.table.insertRow(ri)
            for ci, col in enumerate(self.columns):
                key = col.get("key")
                if key == "actions":
                    if not show_actions: continue
                    obj    = row["actions"]
                    status = str(row.get("status", "active") or "active")
                    al = QHBoxLayout(); al.setContentsMargins(4, 2, 4, 2); al.setSpacing(4)

                    # ── Edit (مسموح فقط للمسودة والنشطة) ─────────────
                    if can_edit and status in ("draft", "active"):
                        b = QPushButton(self._("edit"))
                        b.setObjectName("primary-btn")
                        b.setFixedHeight(28)
                        b.setCursor(Qt.PointingHandCursor)
                        b.clicked.connect(lambda _=False, o=obj: self._open_edit_dialog(o))
                        al.addWidget(b)

                    # ── Workflow buttons ────────────────────────────────
                    can_workflow = has_perm(self.current_user, "close_transaction") or is_admin(self.current_user)

                    if can_workflow:
                        if status == "draft":
                            b = QPushButton("▶ " + self._("activate"))
                            b.setObjectName("success-btn")
                            b.setFixedHeight(28)
                            b.setCursor(Qt.PointingHandCursor)
                            b.clicked.connect(lambda _=False, o=obj: self._workflow_action(o, "active"))
                            al.addWidget(b)
                        elif status == "active":
                            b = QPushButton("🔒 " + self._("close"))
                            b.setObjectName("warning-btn")
                            b.setFixedHeight(28)
                            b.setCursor(Qt.PointingHandCursor)
                            b.clicked.connect(lambda _=False, o=obj: self._workflow_action(o, "closed"))
                            al.addWidget(b)
                        elif status == "closed":
                            b_reopen = QPushButton("🔓 " + self._("reopen"))
                            b_reopen.setObjectName("secondary-btn")
                            b_reopen.setFixedHeight(28)
                            b_reopen.setCursor(Qt.PointingHandCursor)
                            b_reopen.clicked.connect(lambda _=False, o=obj: self._workflow_action(o, "active"))
                            al.addWidget(b_reopen)
                            b_arch = QPushButton("📦 " + self._("archive"))
                            b_arch.setObjectName("muted-btn")
                            b_arch.setFixedHeight(28)
                            b_arch.setCursor(Qt.PointingHandCursor)
                            b_arch.clicked.connect(lambda _=False, o=obj: self._workflow_action(o, "archived"))
                            al.addWidget(b_arch)

                    # ── Delete ──────────────────────────────────────────
                    if can_delete and status not in ("closed", "archived"):
                        b = QPushButton(self._("delete"))
                        b.setObjectName("danger-btn")
                        b.setFixedHeight(28)
                        b.setCursor(Qt.PointingHandCursor)
                        b.clicked.connect(lambda _=False, o=obj: self._delete_single(o))
                        al.addWidget(b)

                    w = QWidget(); w.setLayout(al)
                    self.table.setCellWidget(ri, ci, w)
                elif key == "transaction_type_badge":
                    code   = str(row.get("transaction_type_badge", ""))
                    label  = str(row.get("transaction_type_label", code))
                    status = str(row.get("status", "active") or "active")
                    type_badge   = self._make_type_badge(code, label)
                    status_badge = self._make_status_badge(status)
                    container = QWidget()
                    cl = QHBoxLayout(container)
                    cl.setContentsMargins(4, 2, 4, 2)
                    cl.setSpacing(4)
                    cl.addStretch()
                    cl.addWidget(type_badge)
                    cl.addWidget(status_badge)
                    cl.addStretch()
                    self.table.setCellWidget(ri, ci, container)
                else:
                    item = QTableWidgetItem(str(row.get(key, "")))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(ri, ci, item)

        try:
            ai = next((i for i, c in enumerate(self.columns) if c.get("key") == "actions"), None)
            if ai is not None: self.table.setColumnHidden(ai, not show_actions)
        except Exception: pass

        # ── ضبط عروض الأعمدة ────────────────────────────────────────────────
        COL_WIDTHS = {
            "transaction_no":          110,
            "transaction_type_badge":  160,
            "transaction_date":        110,
            "client":                  160,
            "exporting_company":       160,
            "importing_company":       160,
            "relationship_label":       90,
            "linked_entries_count":     70,
            "total_value":             120,
        }
        hdr = self.table.horizontalHeader()
        from PySide6.QtWidgets import QHeaderView
        for ci, col in enumerate(self.columns):
            key = col.get("key", "")
            label = col.get("label", "")
            w = COL_WIDTHS.get(key) or COL_WIDTHS.get(label)
            if w:
                hdr.resizeSection(ci, w)
        # عمود الإجراءات: اجعل آخر عمود يمتد
        try:
            if show_actions and ai is not None:
                hdr.setSectionResizeMode(ai, QHeaderView.Fixed)
                hdr.resizeSection(ai, 220)
        except Exception:
            pass

        self._apply_admin_columns()
        self.update_pagination_label()

    # ── Actions ───────────────────────────────────────────────────────
    def add_new_item(self):
        self._open_add_window(transaction=None)

    def edit_selected_item(self):
        rows = self.get_selected_rows()
        if rows and 0 <= rows[0] < len(self.data):
            self._open_edit_dialog(self.data[rows[0]]["actions"])

    def _open_add_window(self, transaction=None, copy_from_id=None):
        try:
            dlg = AddTransactionWindow(self, current_user=self.current_user,
                                       transaction=transaction, copy_from_id=copy_from_id)
        except TypeError:
            dlg = AddTransactionWindow(self, current_user=self.current_user, transaction=transaction)
        try: dlg.saved.connect(lambda _id: self.reload_data())
        except Exception: pass
        if getattr(dlg, "exec", None): dlg.exec()
        else: dlg.show()

    def _workflow_action(self, trx_obj, new_status: str):
        """ينفذ تغيير حالة مع تأكيد + رسالة نتيجة."""
        trx_id = getattr(trx_obj, "id", None)
        if not trx_id:
            return

        # رسائل التأكيد حسب الانتقال
        confirm_msgs = {
            "active":   self._("confirm_activate_transaction"),
            "closed":   self._("confirm_close_transaction"),
            "archived": self._("confirm_archive_transaction"),
        }
        confirm_msg = confirm_msgs.get(new_status, self._("confirm_action"))
        trx_no = getattr(trx_obj, "transaction_no", str(trx_id))

        reply = QMessageBox.question(
            self,
            self._("confirm"),
            f"{confirm_msg}\n\n📋 {trx_no}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        ok, err = self.trx_crud.change_status(trx_id, new_status, self.current_user)

        if ok:
            success_msgs = {
                "active":   self._("transaction_activated"),
                "closed":   self._("transaction_closed"),
                "archived": self._("transaction_archived"),
            }
            QMessageBox.information(self, self._("success"), success_msgs.get(new_status, self._("updated")))
            self.reload_data()
        else:
            if "transition_not_allowed" in err:
                QMessageBox.warning(self, self._("error"), self._("status_transition_not_allowed"))
            else:
                QMessageBox.warning(self, self._("error"), f"{self._('error')}: {err}")

    def _open_edit_dialog(self, trx_obj):
        # حماية: المغلقة والمؤرشفة read-only
        status = getattr(trx_obj, "status", "active") or "active"
        if status in ("closed", "archived"):
            QMessageBox.information(self, self._("info"), self._("cannot_edit_closed_transaction"))
            return
        trx_id = getattr(trx_obj, "id", None) or (trx_obj.get("id") if isinstance(trx_obj, dict) else None)
        self._open_add_window(transaction=trx_id)

    def delete_selected_items(self):
        rows = self.get_selected_rows()
        if not rows: return
        if QMessageBox.question(self, self._("delete_transaction"), self._("are_you_sure_delete"),
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        for r in sorted(rows, reverse=True):
            if 0 <= r < len(self.data):
                self._delete_single(self.data[r]["actions"], confirm=False)
        QMessageBox.information(self, self._("deleted"), self._("transaction_deleted_success"))
        self.reload_data()

    def _delete_single(self, trx_obj, confirm=True):
        # حماية: المغلقة والمؤرشفة لا تُحذف
        status = getattr(trx_obj, "status", "active") or "active"
        if status in ("closed", "archived"):
            QMessageBox.warning(self, self._("error"), self._("cannot_delete_closed_transaction"))
            return
        if confirm and QMessageBox.question(self, self._("delete_transaction"), self._("are_you_sure_delete"),
                                            QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes: return
        try:
            self.trx_crud.delete_transaction(getattr(trx_obj, "id", None))
        except Exception as e:
            QMessageBox.critical(self, self._("error"), f"{self._('delete_failed')}: {e}")

    def on_row_double_clicked(self, row_index):
        try: row = int(row_index)
        except: row = getattr(row_index, "row", lambda: -1)()
        if 0 <= row < len(self.data):
            self._open_view_dialog(self.data[row]["actions"])

    def _open_view_dialog(self, trx_obj):
        from importlib import import_module
        ViewTransactionDialog = None
        for mod_path in ("ui.dialogs.view_transaction_dialog",
                         "ui.dialogs.view_details.view_transaction_dialog"):
            try:
                mod = import_module(mod_path)
                ViewTransactionDialog = getattr(mod, "ViewTransactionDialog", None)
                if ViewTransactionDialog: break
            except Exception: continue

        if not ViewTransactionDialog:
            QMessageBox.warning(self, self._("error"), self._("view_dialog_not_available"))
            return

        dlg = ViewTransactionDialog(transaction=trx_obj, current_user=self.current_user, parent=self)
        try: dlg.copy_requested.connect(self._copy_transaction)
        except Exception: pass
        try: dlg.reprice_requested.connect(self._reprice_transaction)
        except Exception: pass
        if getattr(dlg, "exec", None): dlg.exec()
        else: dlg.show()

    def _copy_transaction(self, trx_id: int):
        if not trx_id: return
        from database.models import get_session_local
        from database.models.transaction import Transaction, TransactionItem, TransactionEntry
        from sqlalchemy.orm import Session
        from datetime import datetime

        SessionLocal = get_session_local()
        session: Session = SessionLocal()
        try:
            original: Transaction = session.query(Transaction).filter(Transaction.id == trx_id).first()
            if not original: return

            from services.numbering_service import NumberingService
            new_no = NumberingService.get_next_transaction_number(session)

            new_trx = Transaction(
                transaction_no=new_no,
                transaction_date=datetime.now().date(),
                transaction_type=original.transaction_type,
                status="draft",
                client_id=original.client_id,
                exporter_company_id=original.exporter_company_id,
                importer_company_id=original.importer_company_id,
                relationship_type=original.relationship_type,
                broker_company_id=original.broker_company_id,
                origin_country_id=original.origin_country_id,
                dest_country_id=original.dest_country_id,
                currency_id=original.currency_id,
                pricing_type_id=original.pricing_type_id,
                delivery_method_id=original.delivery_method_id,
                transport_type=original.transport_type,
                transport_ref=original.transport_ref,
                notes=original.notes,
                totals_count=original.totals_count,
                totals_gross_kg=original.totals_gross_kg,
                totals_net_kg=original.totals_net_kg,
                totals_value=original.totals_value,
                created_by_id=getattr(self.current_user, "id", None),
                updated_by_id=getattr(self.current_user, "id", None),
            )
            session.add(new_trx)
            session.flush()

            for it in session.query(TransactionItem).filter(TransactionItem.transaction_id == trx_id).all():
                session.add(TransactionItem(
                    transaction_id=new_trx.id, entry_id=it.entry_id, entry_item_id=it.entry_item_id,
                    material_id=it.material_id, packaging_type_id=it.packaging_type_id,
                    quantity=it.quantity, gross_weight_kg=it.gross_weight_kg,
                    net_weight_kg=it.net_weight_kg, pricing_type_id=it.pricing_type_id,
                    unit_price=it.unit_price, currency_id=it.currency_id,
                    line_total=it.line_total, origin_country_id=it.origin_country_id,
                    source_type=it.source_type, is_manual=it.is_manual,
                    notes=it.notes, transport_ref=it.transport_ref,
                    created_by_id=getattr(self.current_user, "id", None),
                    updated_by_id=getattr(self.current_user, "id", None),
                ))

            for e in session.query(TransactionEntry).filter(TransactionEntry.transaction_id == trx_id).all():
                session.add(TransactionEntry(transaction_id=new_trx.id, entry_id=e.entry_id))

            session.commit()
            self._open_add_window(transaction=new_trx.id)

        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, self._("error"), f"Copy failed: {e}")
        finally:
            session.close()

    def _reprice_transaction(self, trx_id: int):
        if trx_id: self._open_add_window(transaction=trx_id)

    # ── Rich Excel export ─────────────────────────────────────────────
    def _rich_export(self):
        """Export current filtered transactions using ExcelService."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import os

        if not _HAS_EXCEL_SVC:
            QMessageBox.warning(self, self._("error"),
                                "ExcelService غير متاح. تأكد من تثبيت openpyxl.")
            return

        lang = TranslationManager.get_instance().get_current_language()
        default_name = f"transactions_{lang}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, self._("export_to_excel_rich"), default_name,
            "Excel Files (*.xlsx)"
        )
        if not path:
            return

        try:
            # Get active date filter
            date_from = self._date_from.date().toPython() if hasattr(self, "_date_from") else None
            date_to   = self._date_to.date().toPython()   if hasattr(self, "_date_to")   else None
            trx_type  = None
            if hasattr(self, "_type_combo"):
                v = self._type_combo.currentData()
                if v and v != "all":
                    trx_type = v

            svc = _ExcelSvc(lang=lang)
            svc.export_transactions(
                output_path=path,
                date_from=date_from,
                date_to=date_to,
                transaction_type=trx_type,
            )
            QMessageBox.information(
                self, self._("success"),
                f"{self._('export_success')}\n{path}"
            )
            try:
                os.startfile(path)
            except Exception:
                pass  # Not on Windows or file manager unavailable
        except Exception as e:
            QMessageBox.critical(self, self._("error"), str(e))

    # ── Type Badge ────────────────────────────────────────────────────
    _BADGE_STYLES = {
        "export":  ("📤", "#10b981", "#d1fae5"),   # أخضر
        "import":  ("📥", "#3b82f6", "#dbeafe"),   # أزرق
        "transit": ("🔄", "#f59e0b", "#fef3c7"),   # برتقالي
    }

    def _make_type_badge(self, code: str, label: str) -> QLabel:
        ICONS = {"export": "📤", "import": "📥", "transit": "🔄"}
        icon = ICONS.get(code, "•")
        badge = QLabel(f"{icon}  {label}")
        badge.setAlignment(Qt.AlignCenter)
        # objectName يربطه بالثيم — يستخدم لون primary/accent حسب النوع
        badge.setObjectName(f"badge-{code}" if code in ("export","import","transit") else "badge-default")
        badge.setProperty("badge_type", code)
        # ألوان مدمجة بسيطة — لا تتعارض مع الثيم
        COLORS = {
            "export":  ("#065F46", "#D1FAE5"),
            "import":  ("#1E3A5F", "#DBEAFE"),
            "transit": ("#78350F", "#FEF3C7"),
        }
        fg, bg = COLORS.get(code, ("#374151", "#F3F4F6"))
        badge.setStyleSheet(
            f"QLabel {{ color: {fg}; background: {bg};"
            f"border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: 700;"
            f"min-width: 70px; }}"
        )
        return badge

    # ── Footer / Totals ───────────────────────────────────────────────
    def _make_status_badge(self, status: str) -> QLabel:
        """Badge الحالة — بسيط وواضح."""
        STATUS_MAP = {
            "draft":    ("📝", "#4338CA", "#EEF2FF"),
            "active":   ("✅", "#065F46", "#D1FAE5"),
            "closed":   ("🔒", "#7F1D1D", "#FEE2E2"),
            "archived": ("📦", "#374151", "#F3F4F6"),
        }
        icon, color, bg = STATUS_MAP.get(status, ("⚪", "#6B7280", "#F9FAFB"))
        # ترجمة الحالة — جرب المفتاح بكلا الصيغتين
        try:
            label_text = self._(f"status_{status}")
            if label_text == f"status_{status}":
                label_text = self._(status)
        except Exception:
            label_text = status
        lbl = QLabel(f"{icon}  {label_text}")
        lbl.setStyleSheet(
            f"QLabel {{ background: {bg}; color: {color};"
            f"border-radius: 8px; padding: 2px 8px;"
            f"font-size: 10px; font-weight: 700; }}"
        )
        lbl.setAlignment(Qt.AlignCenter)
        return lbl


    def _build_footer(self):
        """شريط الإجماليات أسفل الجدول."""
        footer = QWidget()
        footer.setObjectName("transactions-footer")
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(24)

        def _stat(label_key):
            wrap = QWidget()
            wl   = QVBoxLayout(wrap)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(1)
            lbl_title = QLabel(self._(label_key))
            lbl_title.setObjectName("footer-stat-title")
            lbl_title.setAlignment(Qt.AlignCenter)
            lbl_val = QLabel("—")
            lbl_val.setObjectName("footer-stat-value")
            lbl_val.setAlignment(Qt.AlignCenter)
            wl.addWidget(lbl_title)
            wl.addWidget(lbl_val)
            lay.addWidget(wrap)
            return lbl_val

        self._ft_total    = _stat("total_rows")
        self._ft_export   = _stat("export")
        self._ft_import   = _stat("import")
        self._ft_transit  = _stat("transit")

        sep1 = QFrame(); sep1.setFrameShape(QFrame.VLine); sep1.setObjectName("separator"); sep1.setFixedHeight(30)
        sep2 = QFrame(); sep2.setFrameShape(QFrame.VLine); sep2.setObjectName("separator"); sep2.setFixedHeight(30)
        sep3 = QFrame(); sep3.setFrameShape(QFrame.VLine); sep3.setObjectName("separator"); sep3.setFixedHeight(30)
        lay.insertWidget(1, sep1)
        lay.insertWidget(3, sep2)
        lay.insertWidget(5, sep3)

        lay.addStretch()

        # إجمالي القيم المالية
        val_wrap = QWidget()
        vwl = QVBoxLayout(val_wrap)
        vwl.setContentsMargins(0, 0, 0, 0)
        vwl.setSpacing(1)
        lbl_vtitle = QLabel("Σ " + self._("total_value"))
        lbl_vtitle.setObjectName("footer-stat-title")
        lbl_vtitle.setAlignment(Qt.AlignCenter)
        self._ft_value = QLabel("—")
        self._ft_value.setObjectName("footer-stat-value-accent")
        self._ft_value.setAlignment(Qt.AlignCenter)
        vwl.addWidget(lbl_vtitle)
        vwl.addWidget(self._ft_value)
        lay.addWidget(val_wrap)

        try:
            self.layout.insertWidget(self.layout.count() - 1, footer)
        except Exception:
            self.layout.addWidget(footer)

    def _update_footer(self, rows: list):
        if not hasattr(self, "_ft_total"):
            return
        total   = len(rows)
        exports = sum(1 for r in rows if r.get("transaction_type_badge") == "export")
        imports = sum(1 for r in rows if r.get("transaction_type_badge") == "import")
        transit = sum(1 for r in rows if r.get("transaction_type_badge") == "transit")

        # مجموع القيم المالية (من النص — نستخرج الرقم فقط)
        total_val = 0.0
        for r in rows:
            try:
                raw = str(r.get("totals_value_label", "") or "").split()[0]
                total_val += float(raw)
            except Exception:
                pass

        self._ft_total.setText(str(total))
        self._ft_export.setText(str(exports))
        self._ft_import.setText(str(imports))
        self._ft_transit.setText(str(transit))
        self._ft_value.setText(f"{total_val:,.2f}" if total_val else "—")

    # ── i18n ──────────────────────────────────────────────────────────
    def retranslate_ui(self):
        super().retranslate_ui()
        parent = self.parent()
        try:
            if parent and hasattr(parent, "indexOf") and hasattr(parent, "setTabText"):
                idx = parent.indexOf(self)
                if idx != -1: parent.setTabText(idx, self._("transactions"))
        except Exception: pass
        self._apply_columns_for_current_role()
        self.reload_data()

    def _apply_admin_columns(self):
        admin_keys = ("id", "created_by_name", "updated_by_name", "created_at", "updated_at")
        apply_admin_columns_to_table(
            self.table, self.current_user,
            [i for i, c in enumerate(self.columns) if c.get("key") in admin_keys])

    def _user_display(self, rel, id_to_name, fallback_id=None) -> str:
        if isinstance(rel, User):
            return getattr(rel, "full_name", None) or getattr(rel, "username", None) or str(getattr(rel, "id", fallback_id or ""))
        if isinstance(rel, int): return id_to_name.get(rel, str(rel))
        if fallback_id is not None: return id_to_name.get(fallback_id, str(fallback_id))
        return ""