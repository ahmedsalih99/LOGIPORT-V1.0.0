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
from core.data_bus import DataBus
from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from core.permissions import has_perm, is_admin
from core.admin_columns import apply_admin_columns_to_table

from database.crud.transactions_crud import TransactionsCRUD
from database.models import get_session_local, User

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

# فونت bold مشترك لخلايا الجدول
_BOLD_ITEM_FONT = QFont()
_BOLD_ITEM_FONT.setBold(True)
from datetime import date, timedelta


class TransactionsTab(BaseTab):
    # ثابت على مستوى الكلاس — لا يُعاد بناؤه عند كل render
    _COL_WIDTHS = {
        "transaction_no":         110,
        "transaction_type_badge": 160,
        "transaction_date":       110,
        "client":                 160,
        "exporting_company":      160,
        "importing_company":      160,
        "office_name":            140,
    }

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
                {"label": "office",             "key": "office_name"},
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
        DataBus.get_instance().subscribe('transactions', self.reload_data)
        DataBus.get_instance().subscribe('clients', self.reload_data)

    # ── Filter bar ────────────────────────────────────────────────────────

    def _build_filter_bar(self):
        """شريط الفلترة — يستخدم DateRangeBar من البيس."""
        from core.base_tab import DateRangeBar

        self._date_bar = DateRangeBar(self, default_months=3)
        self._date_bar.changed.connect(self._on_filter_changed)

        # ── أزرار نوع المعاملة (Pill) ─────────────────────────────────
        self._type_btns   = {}
        self._selected_type = ""
        self._type_defs = lambda: [
            ("",        "🔍 " + self._("all_types")),
            ("export",  "📤 " + self._("export")),
            ("import",  "📥 " + self._("import")),
            ("transit", "🔄 " + self._("transit")),
        ]
        for val, label in self._type_defs():
            btn = QPushButton(label)
            btn.setObjectName("filter-preset-btn")
            btn.setFixedHeight(30)
            btn.setCheckable(True)
            btn.setChecked(val == "")
            btn.setCursor(Qt.PointingHandCursor)
            self._type_btns[val] = btn
            def _on_type(checked=False, v=val):
                for vv, b in self._type_btns.items():
                    b.setChecked(vv == v)
                self._selected_type = v
                self._on_filter_changed()
            btn.clicked.connect(_on_type)
            self._date_bar.add_widget(btn)

        # backward-compat
        self._type_combo = QComboBox()
        self._type_combo.setVisible(False)

        # ── فلتر المكتب ───────────────────────────────────────────────
        try:
            from core.office_context import OfficeContext
            _has_office = OfficeContext.get_id() is not None
        except Exception:
            _has_office = False

        if _has_office:
            self._my_office_btn = QPushButton()
            self._my_office_btn.setObjectName("filter-preset-btn")
            self._my_office_btn.setFixedHeight(30)
            self._my_office_btn.setCheckable(True)
            self._my_office_btn.setCursor(Qt.PointingHandCursor)
            _default_my_office = not is_admin(self.current_user)
            self._office_filter_active = _default_my_office
            self._my_office_btn.setChecked(_default_my_office)
            self._refresh_office_btn_text()
            self._my_office_btn.toggled.connect(self._on_office_filter_toggled)
            self._date_bar.add_widget(self._my_office_btn)
        else:
            self._my_office_btn = None
            self._office_filter_active = False

        # ── تصدير Excel ───────────────────────────────────────────────
        btn_rich = QPushButton("📊  " + self._("export_to_excel_rich"))
        btn_rich.setObjectName("secondary-btn")
        btn_rich.setFixedHeight(30)
        btn_rich.setToolTip(self._("export_transactions_tip"))
        btn_rich.clicked.connect(self._rich_export)
        self._date_bar.add_widget(btn_rich)

        # alias للتوافق مع _get_filter_values
        self._date_from = self._date_bar._date_from
        self._date_to   = self._date_bar._date_to

        try:
            self.layout.insertWidget(1, self._date_bar)
        except Exception:
            self.layout.addWidget(self._date_bar)


    # ── Preset slots ─────────────────────────────────────────────────────────

    def _on_filter_changed(self, *_):
        self.reload_data()

    # ── office filter helpers ─────────────────────────────────────────────────

    def _refresh_office_btn_text(self):
        """يحدّث نص زر المكتب حسب الحالة الحالية."""
        if not getattr(self, "_my_office_btn", None):
            return
        try:
            from core.office_context import OfficeContext
            office_name = OfficeContext.get_name(
                self.settings.get("language") or "ar"
            ) if hasattr(self, "settings") else ""
        except Exception:
            office_name = ""
        active = getattr(self, "_office_filter_active", False)
        label = office_name or self._("my_office")
        icon  = "🏢 " if active else "🌐 "
        self._my_office_btn.setText(icon + label)

    def _on_office_filter_toggled(self, checked: bool):
        """يُفعَّل عند الضغط على زر المكتب."""
        self._office_filter_active = checked
        self._refresh_office_btn_text()
        self.reload_data()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _get_filter_values(self):
        """Return (date_from_str, date_to_str, trx_type_str, search, status_str, office_id)."""
        d_from  = self._date_from.date().toString("yyyy-MM-dd") if hasattr(self, "_date_from")    else None
        d_to    = self._date_to.date().toString("yyyy-MM-dd")   if hasattr(self, "_date_to")      else None
        t_type  = getattr(self, "_selected_type", "") or (self._type_combo.currentData() if hasattr(self, "_type_combo") else "")
        status  = self._status_combo.currentData()              if hasattr(self, "_status_combo") else ""
        search  = self.search_bar.text().strip().lower()        if hasattr(self, "search_bar")    else ""
        # office filter — Admin يرى الكل دائماً بغض النظر عن الزر
        office_id = None
        if getattr(self, "_office_filter_active", False) and not is_admin(self.current_user):
            try:
                from core.office_context import OfficeContext
                office_id = OfficeContext.get_id()
            except Exception:
                pass
        return d_from, d_to, t_type or None, search, status or None, office_id

    # ── Data ──────────────────────────────────────────────────────────

    def reload_data(self):
        self._skip_base_search = True   # البحث يتم server-side أو بـ _apply_search_filter
        self._skip_base_sort   = True   # الترتيب يتم server-side أو يُدار بـ CRUD
        d_from, d_to, t_type, search, status, office_id = self._get_filter_values()
        admin = is_admin(self.current_user)

        # pagination server-side
        filters = dict(
            date_from        = d_from,
            date_to          = d_to,
            transaction_type = t_type or None,
            search           = search or None,
            status           = status or None,
            office_id        = office_id,
        )
        try:
            self.total_rows  = self.trx_crud.count_transactions(**filters)
        except Exception:
            self.total_rows  = 0
        self.total_pages = max(1, -(-self.total_rows // self.rows_per_page))  # ceiling div
        self.current_page = min(self.current_page, self.total_pages)

        try:
            items = self.trx_crud.list_transactions(
                limit  = self.rows_per_page,
                offset = (self.current_page - 1) * self.rows_per_page,
                **filters,
            ) or []
        except TypeError:
            items = self.trx_crud.list_transactions(limit=self.rows_per_page) or []

        client_ids, company_ids, currency_ids, office_ids = set(), set(), set(), set()
        created_ids, updated_ids = set(), set()
        for t in items:
            if isinstance(getattr(t, "client_id",           None), int): client_ids.add(t.client_id)
            if isinstance(getattr(t, "exporter_company_id", None), int): company_ids.add(t.exporter_company_id)
            if isinstance(getattr(t, "importer_company_id", None), int): company_ids.add(t.importer_company_id)
            if isinstance(getattr(t, "currency_id",         None), int): currency_ids.add(t.currency_id)
            if isinstance(getattr(t, "office_id",           None), int): office_ids.add(t.office_id)
            if isinstance(getattr(t, "created_by_id",       None), int): created_ids.add(t.created_by_id)
            if isinstance(getattr(t, "updated_by_id",       None), int): updated_ids.add(t.updated_by_id)

        id_to_user = {}; id_to_client = {}; id_to_company = {}
        id_to_currency = {}; id_to_office = {}

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
            if office_ids:
                try:
                    from database.models.office import Office as _Office
                    for oid, nar, nen, ntr, code in s.query(
                        _Office.id, _Office.name_ar, _Office.name_en,
                        _Office.name_tr if hasattr(_Office, "name_tr") else _Office.name_ar,
                        _Office.code
                    ).filter(_Office.id.in_(office_ids)):
                        id_to_office[oid] = {"ar": nar, "en": nen or nar, "tr": ntr or nar, "code": code}
                except Exception:
                    pass
        finally:
            s.close()

        lang = TranslationManager.get_instance().get_current_language()

        def _pick(d):
            return d.get(lang) or d.get("en") or d.get("ar") or d.get("tr") or ""

        all_rows = []
        for t in items:
            office_d = id_to_office.get(getattr(t, "office_id", None) or -1, {})
            office_name = _pick(office_d) or office_d.get("code") or ""

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
                "office_name":           office_name,
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
        hdr = self.table.horizontalHeader()
        from PySide6.QtWidgets import QHeaderView

        # ── تجميد الرسم أثناء التحميل — يمنع redraw مع كل صف ──────────
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        try:
            # col 0 محجوز للـ checkbox — الأعمدة تبدأ من 1
            self.table.setColumnCount(len(self.columns) + 1)
            self.table.setHorizontalHeaderLabels(
                [""] + [self._(c.get("label", "")) for c in self.columns]
            )
            # تثبيت عمود الـ checkbox
            hdr.setSectionResizeMode(0, QHeaderView.Fixed)
            self.table.setColumnWidth(0, 42)
            self.table.setRowCount(len(data))

            can_edit   = getattr(self, "can_edit",   False)
            can_delete = getattr(self, "can_delete", False)
            can_wf     = has_perm(self.current_user, "close_transaction") or is_admin(self.current_user)

            for ri, row in enumerate(data):
                status = str(row.get("status", "active") or "active")
                obj    = row.get("actions")
                # col 0: checkbox
                self._set_row_checkbox(ri)

                for ci, col in enumerate(self.columns):
                    key    = col.get("key")
                    real_c = ci + 1   # offset بسبب checkbox في col 0

                    if key == "actions":
                        if not show_actions:
                            continue
                        al = QHBoxLayout()
                        al.setContentsMargins(4, 2, 4, 2)
                        al.setSpacing(4)

                        if can_edit and status in ("draft", "active"):
                            b = QPushButton(self._("edit"))
                            b.setObjectName("table-edit")
                            b.setFixedHeight(28)
                            b.setCursor(Qt.PointingHandCursor)
                            b.clicked.connect(lambda _=False, o=obj: self._open_edit_dialog(o))
                            al.addWidget(b)

                        if can_wf:
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

                        if can_delete and status not in ("closed", "archived"):
                            b = QPushButton(self._("delete"))
                            b.setObjectName("table-delete")
                            b.setFixedHeight(28)
                            b.setCursor(Qt.PointingHandCursor)
                            b.clicked.connect(lambda _=False, o=obj: self._delete_single(o))
                            al.addWidget(b)

                        w = QWidget()
                        w.setLayout(al)
                        self.table.setCellWidget(ri, real_c, w)

                    elif key == "transaction_type_badge":
                        # ✅ نص + لون بـ QTableWidgetItem بدل setCellWidget (أسرع بكثير)
                        code   = str(row.get("transaction_type_badge", ""))
                        label  = str(row.get("transaction_type_label", code))
                        status_label = self._(status) if status else ""
                        item = QTableWidgetItem(f"{label}  |  {status_label}")
                        item.setTextAlignment(Qt.AlignCenter)
                        # لون الخلفية حسب النوع والحالة
                        from PySide6.QtGui import QColor, QBrush
                        bg = {"export": "#E8F5E9", "import": "#E3F2FD", "transit": "#FFF8E1"}.get(code, "#F5F5F5")
                        if status == "closed":    bg = "#ECEFF1"
                        elif status == "archived": bg = "#F3E5F5"
                        elif status == "draft":    bg = "#FFF9C4"
                        item.setBackground(QBrush(QColor(bg)))
                        item.setFont(_BOLD_ITEM_FONT)
                        self.table.setItem(ri, real_c, item)

                    else:
                        item = QTableWidgetItem(str(row.get(key, "") or ""))
                        item.setTextAlignment(Qt.AlignCenter)
                        item.setFont(_BOLD_ITEM_FONT)
                        self.table.setItem(ri, real_c, item)

        finally:
            self.table.setUpdatesEnabled(True)
            self.table.setSortingEnabled(True)

        # ── إخفاء/إظهار عمود actions ────────────────────────────────────
        try:
            ai = next((i for i, c in enumerate(self.columns) if c.get("key") == "actions"), None)
            if ai is not None:
                real_ai = ai + 1   # offset بسبب checkbox في col 0
                self.table.setColumnHidden(real_ai, not show_actions)
                hdr.setSectionResizeMode(real_ai, QHeaderView.Fixed)
                hdr.resizeSection(real_ai, 220)
        except Exception:
            pass

        # ── عروض الأعمدة ────────────────────────────────────────────────
        for ci, col in enumerate(self.columns):
            key = col.get("key", "")
            w = self._COL_WIDTHS.get(key) or self._COL_WIDTHS.get(col.get("label", ""))
            if w:
                hdr.resizeSection(ci + 1, w)   # +1 offset بسبب checkbox

        self._apply_admin_columns()
        self.update_pagination_label()
        self._stretch_columns()

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
        DataBus.get_instance().emit('transactions')
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
        from database.models.transport_details import TransportDetails
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

            # ── نسخ بيانات تبويب الشحن (TransportDetails) ──────────────────
            orig_td = session.query(TransportDetails).filter(
                TransportDetails.transaction_id == trx_id
            ).first()
            if orig_td and not orig_td.is_empty():
                session.add(TransportDetails(
                    transaction_id=new_trx.id,
                    carrier_company_id=orig_td.carrier_company_id,
                    truck_plate=orig_td.truck_plate,
                    driver_name=orig_td.driver_name,
                    loading_place=orig_td.loading_place,
                    delivery_place=orig_td.delivery_place,
                    origin_country=orig_td.origin_country,
                    dest_country=orig_td.dest_country,
                    shipment_date=orig_td.shipment_date,
                    attached_documents=orig_td.attached_documents,
                    certificate_no=orig_td.certificate_no,
                    issuing_authority=orig_td.issuing_authority,
                    certificate_date=orig_td.certificate_date,
                ))

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
                                self._("excel_service_unavailable"))
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
            trx_type  = getattr(self, "_selected_type", None) or None

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

        self._ft_total.setText(str(total))
        self._ft_export.setText(str(exports))
        self._ft_import.setText(str(imports))
        self._ft_transit.setText(str(transit))

    # ── i18n ──────────────────────────────────────────────────────────
    def retranslate_ui(self):
        super().retranslate_ui()
        parent = self.parent()
        try:
            if parent and hasattr(parent, "indexOf") and hasattr(parent, "setTabText"):
                idx = parent.indexOf(self)
                if idx != -1: parent.setTabText(idx, self._("transactions"))
        except Exception: pass

        # تحديث نصوص أزرار نوع المعاملة
        if hasattr(self, "_type_btns") and hasattr(self, "_type_defs"):
            for val, label in self._type_defs():
                btn = self._type_btns.get(val)
                if btn:
                    btn.setText(label)

        # تحديث الـ combo الاحتياطي
        if hasattr(self, "_type_combo"):
            self._type_combo.setItemText(1, self._("export"))
            self._type_combo.setItemText(2, self._("import"))
            self._type_combo.setItemText(3, self._("transit"))

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