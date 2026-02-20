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
    QDateEdit, QComboBox, QLabel, QFrame, QSizePolicy
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
                {"label": "transaction_type",     "key": "transaction_type_label"},
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
        """Inject a date-range + type filter bar above the base_tab search bar."""
        filter_bar = QWidget()
        filter_bar.setObjectName("filter-bar")
        lay = QHBoxLayout(filter_bar)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(8)

        # ── Date From ──
        lbl_from = QLabel("📅 " + self._("date_from") + ":")
        lbl_from.setFont(QFont("Tajawal", 9))
        lay.addWidget(lbl_from)

        self._date_from = QDateEdit()
        self._date_from.setObjectName("form-input")
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        self._date_from.setDate(QDate.currentDate().addMonths(-3))
        self._date_from.setMinimumWidth(110)
        self._date_from.dateChanged.connect(self._on_filter_changed)
        lay.addWidget(self._date_from)

        # ── Date To ──
        lbl_to = QLabel("→ " + self._("date_to") + ":")
        lbl_to.setFont(QFont("Tajawal", 9))
        lay.addWidget(lbl_to)

        self._date_to = QDateEdit()
        self._date_to.setObjectName("form-input")
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setMinimumWidth(110)
        self._date_to.dateChanged.connect(self._on_filter_changed)
        lay.addWidget(self._date_to)

        # separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setObjectName("separator")
        sep.setFixedWidth(1)
        sep.setFixedHeight(24)
        lay.addWidget(sep)

        # ── Type combo ──
        lbl_type = QLabel("🔖 " + self._("transaction_type") + ":")
        lbl_type.setFont(QFont("Tajawal", 9))
        lay.addWidget(lbl_type)

        self._type_combo = QComboBox()
        self._type_combo.setObjectName("form-input")
        self._type_combo.setMinimumWidth(110)
        self._type_combo.addItem(self._("All"), "")
        self._type_combo.addItem("📤 " + self._("export"), "export")
        self._type_combo.addItem("📥 " + self._("import"), "import")
        self._type_combo.addItem("🔄 " + self._("transit"), "transit")
        self._type_combo.currentIndexChanged.connect(self._on_filter_changed)
        lay.addWidget(self._type_combo)

        # separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setObjectName("separator")
        sep2.setFixedWidth(1)
        sep2.setFixedHeight(24)
        lay.addWidget(sep2)

        # ── Quick presets ──
        for label, slot in (
            ("📅 " + self._("today"),        self._preset_today),
            ("📅 " + self._("this_week"),    self._preset_week),
            ("📅 " + self._("this_month"),   self._preset_month),
        ):
            btn = QPushButton(label)
            btn.setObjectName("topbar-btn")
            btn.setMinimumHeight(30)
            btn.setFont(QFont("Tajawal", 9))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(slot)
            lay.addWidget(btn)

        # Clear filters
        clr = QPushButton("✖ " + self._("clear"))
        clr.setObjectName("topbar-btn")
        clr.setMinimumHeight(30)
        clr.setFont(QFont("Tajawal", 9))
        clr.setCursor(Qt.PointingHandCursor)
        clr.clicked.connect(self._preset_clear)
        lay.addWidget(clr)

        # result count label
        self._count_lbl = QLabel()
        self._count_lbl.setFont(QFont("Tajawal", 9))
        self._count_lbl.setObjectName("text-muted")
        lay.addWidget(self._count_lbl)

        # ── Rich Excel export ──
        btn_rich = QPushButton("📊 " + self._("export_to_excel_rich"))
        btn_rich.setObjectName("secondary-btn")
        btn_rich.setToolTip(self._("export_transactions_tip"))
        btn_rich.clicked.connect(self._rich_export)
        lay.addWidget(btn_rich)

        lay.addStretch()

        # Insert before the table — base_tab exposes self.layout (QVBoxLayout)
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
        """Return (date_from_str, date_to_str, trx_type_str)."""
        d_from = self._date_from.date().toString("yyyy-MM-dd") if hasattr(self, "_date_from") else None
        d_to   = self._date_to.date().toString("yyyy-MM-dd")   if hasattr(self, "_date_to")   else None
        t_type = self._type_combo.currentData()                if hasattr(self, "_type_combo") else ""
        # also apply search_bar text as client-side filter key
        search = self.search_bar.text().strip().lower()        if hasattr(self, "search_bar")  else ""
        return d_from, d_to, t_type or None, search

    # ── Data ──────────────────────────────────────────────────────────

    def reload_data(self):
        d_from, d_to, t_type, search = self._get_filter_values()
        admin = is_admin(self.current_user)

        # Fetch with server-side date + type filters
        try:
            items = self.trx_crud.list_transactions(
                limit=1000,
                date_from=d_from,
                date_to=d_to,
            ) or []
        except TypeError:
            # fallback if CRUD doesn't support date params yet
            items = self.trx_crud.list_transactions(limit=1000) or []

        # Client-side type filter
        if t_type:
            items = [t for t in items if getattr(t, "transaction_type", "") == t_type]

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

            row = {
                "id":                    getattr(t, "id", None),
                "transaction_no":        getattr(t, "transaction_no", ""),
                "transaction_type_label": self._(getattr(t, "transaction_type", "export")),
                "transaction_date":      str(getattr(t, "transaction_date", "") or ""),
                "client_name":           client_name,
                "exporter_name":         _pick(id_to_company.get(getattr(t, "exporter_company_id", None) or -1, {})),
                "importer_name":         _pick(id_to_company.get(getattr(t, "importer_company_id", None) or -1, {})),
                "relationship_label":    rel_map.get(str(getattr(t, "relationship_type", "") or ""), str(getattr(t, "relationship_type", "") or "")),
                "entries_count":         entries_count.get(getattr(t, "id", 0), 0),
                "totals_value_label":    tlbl,
                "actions":               t,
                "_client_name_raw":      client_name,  # for search
            }
            if admin:
                row.update({
                    "created_by_name": id_to_user.get(getattr(t, "created_by_id", None) or -1, ""),
                    "updated_by_name": id_to_user.get(getattr(t, "updated_by_id", None) or -1, ""),
                    "created_at":      str(getattr(t, "created_at", "") or ""),
                    "updated_at":      str(getattr(t, "updated_at", "") or ""),
                })
            all_rows.append(row)

        # ── Client-side search filter ──────────────────────────────
        if search:
            all_rows = [
                r for r in all_rows
                if search in str(r.get("transaction_no", "")).lower()
                or search in str(r.get("_client_name_raw", "")).lower()
                or search in str(r.get("exporter_name", "")).lower()
            ]

        self.data = all_rows

        # ── Update result count ───────────────────────────────────
        if hasattr(self, "_count_lbl"):
            self._count_lbl.setText(f"({len(self.data)} " + self._("total_rows") + ")")

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
                    obj = row["actions"]
                    al  = QHBoxLayout(); al.setContentsMargins(4,4,4,4); al.setSpacing(8)
                    if can_edit:
                        b = QPushButton(self._("edit")); b.setObjectName("primary-btn")
                        b.setCursor(Qt.PointingHandCursor)
                        b.clicked.connect(lambda _=False, o=obj: self._open_edit_dialog(o))
                        al.addWidget(b)
                    if can_delete:
                        b = QPushButton(self._("delete")); b.setObjectName("danger-btn")
                        b.setCursor(Qt.PointingHandCursor)
                        b.clicked.connect(lambda _=False, o=obj: self._delete_single(o))
                        al.addWidget(b)
                    w = QWidget(); w.setLayout(al)
                    self.table.setCellWidget(ri, ci, w)
                else:
                    item = QTableWidgetItem(str(row.get(key, "")))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(ri, ci, item)

        try:
            ai = next((i for i, c in enumerate(self.columns) if c.get("key") == "actions"), None)
            if ai is not None: self.table.setColumnHidden(ai, not show_actions)
        except Exception: pass
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

    def _open_edit_dialog(self, trx_obj):
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