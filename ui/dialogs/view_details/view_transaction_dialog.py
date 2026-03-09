# -*- coding: utf-8 -*-
"""
view_transaction_dialog.py — نسخة مُصلَحة
==========================================
المشاكل المُصلَحة:
  1. البيانات تظهر كـ IDs بدل أسماء:
     - Transaction model ليس فيه relationships لـ client/company/country/currency
     - الحل: نجلب كل البيانات من DB مباشرة بـ SQL في دالة _load_related_data()
  2. عمود "source" في جدول items كان يُقرأ بـ _get(it, "source")
     لكن اسمه الحقيقي في DB هو source_type
  3. entry_no كان يُقرأ من TransactionItem لكنه غير موجود فيه
     الحل: نجلبه من جدول entries عبر entry_id
  4. copy_requested و reprice_requested كانا متصلَين بـ lambda: None
     (معالَجة في transactions_tab.py)
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
    QWidget, QLabel, QTableWidget, QTableWidgetItem,
    QListWidget, QListWidgetItem, QScrollArea, QCheckBox,
    QHeaderView
)

from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from core.settings_manager import SettingsManager

try:
    from database.models import get_session_local
except Exception:
    get_session_local = None


# ─── helpers ───────────────────────────────────────────────────────────────
def _get(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _fmt_dt(val) -> str:
    if val is None:
        return ""
    s = str(val)
    return s[:16].replace("T", " ") if "T" in s else s[:16]


def _name_by_lang(obj, lang: str) -> str:
    """يجلب الاسم المناسب من ORM object أو dict حسب اللغة."""
    if obj is None:
        return ""
    if isinstance(obj, dict):
        return (obj.get(f"name_{lang}") or obj.get("name_en")
                or obj.get("name_ar") or obj.get("name_tr") or "")
    return (getattr(obj, f"name_{lang}", None)
            or getattr(obj, "name_en", None)
            or getattr(obj, "name_ar", None)
            or getattr(obj, "name_tr", None) or "")


# ─── الكلاس الرئيسي ────────────────────────────────────────────────────────
class ViewTransactionDialog(BaseDialog):
    """عرض المعاملة — للقراءة فقط — مع tabs وأزرار actions."""

    copy_requested     = Signal(int)
    reprice_requested  = Signal(int)
    generate_documents = Signal(list)

    def __init__(self, transaction, current_user=None, parent=None):
        _user = current_user or SettingsManager.get_instance().get("user")
        super().__init__(parent, user=_user)
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()
        self.current_user = _user
        self.trx = transaction
        self.trx_id = _get(self.trx, "id")

        # ── جلب البيانات المرتبطة من DB (الحل الجوهري) ──
        self._rel = self._load_related_data()

        self.setWindowTitle(self._("transaction_view"))

        # ── اتجاه الواجهة حسب اللغة ──────────────────────────────────────────
        from PySide6.QtCore import Qt as _Qt
        self.setLayoutDirection(
            _Qt.RightToLeft if self._lang == "ar" else _Qt.LeftToRight
        )

        # حجم يراعي الشاشة (لا يتجاوز 90%) مع حد أدنى مناسب
        try:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().availableGeometry()
            w = min(980, int(screen.width() * 0.85))
            h = min(680, int(screen.height() * 0.85))
            self.resize(w, h)
        except Exception:
            self.resize(980, 680)

        self._build_ui()
        self._fill_all()

    # ──────────────────────────────────────────── جلب العلاقات من DB
    def _load_related_data(self) -> dict:
        """
        يجلب كل البيانات المرتبطة بالمعاملة من DB مرة واحدة.

        السبب: Transaction model لا يملك relationships لـ
        client / exporter_company / importer_company / broker_company /
        origin_country / dest_country / currency / delivery_method.
        فقط يملك FKs (client_id, exporter_company_id, ...).

        إذا حاولنا قراءة t.client سنحصل على None دائماً →
        الـ dialog يعرض client_id الرقم بدل الاسم.
        """
        rel = {
            "client":           None,
            "exporter_company": None,
            "importer_company": None,
            "broker_company":   None,
            "origin_country":   None,
            "dest_country":     None,
            "currency":         None,
            "delivery_method":  None,
            "created_by_user":  None,
            "updated_by_user":  None,
        }

        if not get_session_local or not self.trx:
            return rel

        t = self.trx
        try:
            from sqlalchemy import text as sql_text
            SessionLocal = get_session_local()
            with SessionLocal() as s:

                def _fetch_one(table: str, row_id) -> dict | None:
                    if not row_id:
                        return None
                    try:
                        row = s.execute(
                            sql_text(f"SELECT * FROM {table} WHERE id = :id"),
                            {"id": int(row_id)}
                        ).mappings().first()
                        return dict(row) if row else None
                    except Exception:
                        return None

                rel["client"]           = _fetch_one("clients",          _get(t, "client_id"))
                rel["exporter_company"] = _fetch_one("companies",         _get(t, "exporter_company_id"))
                rel["importer_company"] = _fetch_one("companies",         _get(t, "importer_company_id"))
                rel["broker_company"]   = _fetch_one("companies",         _get(t, "broker_company_id"))
                rel["origin_country"]   = _fetch_one("countries",         _get(t, "origin_country_id"))
                rel["dest_country"]     = _fetch_one("countries",         _get(t, "dest_country_id"))
                rel["currency"]         = _fetch_one("currencies",        _get(t, "currency_id"))
                rel["delivery_method"]  = _fetch_one("delivery_methods",  _get(t, "delivery_method_id"))
                rel["created_by_user"]  = _fetch_one("users",             _get(t, "created_by_id"))
                rel["updated_by_user"]  = _fetch_one("users",             _get(t, "updated_by_id"))

        except Exception:
            pass

        return rel

    def _rel_name(self, key: str) -> str:
        """يرجع اسم العلاقة حسب اللغة الحالية."""
        return _name_by_lang(self._rel.get(key), self._lang)

    # ──────────────────────────────────────────── بناء الواجهة
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # ── أزرار الرأس ──
        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_copy = QPushButton(self._("copy_transaction"))
        self.btn_copy.setObjectName("secondary-btn")
        self.btn_edit = QPushButton(self._("edit_transaction"))
        self.btn_edit.setObjectName("primary-btn")
        self.btn_generate_docs = QPushButton(self._("generate_documents"))
        self.btn_generate_docs.setObjectName("primary-btn")
        self.btn_close = QPushButton(self._("close"))
        self.btn_close.setObjectName("secondary-btn")
        for b in (self.btn_copy, self.btn_edit,
                  self.btn_generate_docs, self.btn_close):
            actions.addWidget(b)
        root.addLayout(actions)

        # ── التبويبات ──
        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("MainTabs")
        try:
            self.tabs.tabBar().setObjectName("MainTabBar")
        except Exception:
            pass
        root.addWidget(self.tabs)

        self.tab_overview = self._build_overview_tab()
        self.tab_parties  = self._build_parties_tab()
        self.tab_geo      = self._build_geography_tab()
        self.tab_log      = self._build_logistics_tab()
        self.tab_items    = self._build_items_tab()
        self.tab_docs     = self._build_documents_tab()
        self.tab_audit    = self._build_audit_tab()

        self.tabs.addTab(self.tab_overview, self._("overview"))
        self.tabs.addTab(self.tab_parties,  self._("parties"))
        self.tabs.addTab(self.tab_geo,      self._("geography"))
        self.tabs.addTab(self.tab_log,      self._("logistics"))
        self.tabs.addTab(self.tab_items,    self._("items"))
        self.tabs.addTab(self.tab_docs,     self._("documents"))
        self.tabs.addTab(self.tab_audit,    self._("audit"))

        # ── ربط الأزرار ──
        self.btn_close.clicked.connect(self.reject)
        self.btn_copy.clicked.connect(
            lambda: self.copy_requested.emit(int(self.trx_id or 0)))
        self.btn_edit.clicked.connect(
            lambda: self.reprice_requested.emit(int(self.trx_id or 0)))
        self.btn_generate_docs.clicked.connect(self._emit_generate_documents)

    # ──────────────────────────────────────────── بناء التبويبات
    def _build_overview_tab(self) -> QWidget:
        tab = QWidget(); v = QVBoxLayout(tab)
        self._view_overview = BaseDetailsView(tab)
        v.addWidget(self._view_overview); v.addStretch()
        return tab

    def _build_parties_tab(self) -> QWidget:
        tab = QWidget(); v = QVBoxLayout(tab)
        self._view_parties = BaseDetailsView(tab)
        v.addWidget(self._view_parties); v.addStretch()
        return tab

    def _build_geography_tab(self) -> QWidget:
        tab = QWidget(); v = QVBoxLayout(tab)
        self._view_geo = BaseDetailsView(tab)
        v.addWidget(self._view_geo); v.addStretch()
        return tab

    def _build_logistics_tab(self) -> QWidget:
        tab = QWidget(); v = QVBoxLayout(tab)
        self._view_log = BaseDetailsView(tab)
        v.addWidget(self._view_log)
        entries_lbl = QLabel(self._("entries"))
        entries_lbl.setObjectName("section-title")
        v.addWidget(entries_lbl)
        self.entries_list = QListWidget(tab)
        v.addWidget(self.entries_list, 1)
        return tab

    def _build_items_tab(self) -> QWidget:
        tab = QWidget(); v = QVBoxLayout(tab)
        self.tbl_items = QTableWidget(0, 14, tab)
        self.tbl_items.setObjectName("entries-table")
        headers = [
            self._("source"),        self._("entry_no"),
            self._("material"),      self._("packaging_type"),
            self._("quantity"),      self._("gross_weight"),
            self._("net_weight"),    self._("pricing_type"),
            self._("unit_price"),    self._("currency"),
            self._("line_total"),    self._("origin_country"),
            self._("notes"),         self._("transport_ref"),
        ]
        self.tbl_items.setHorizontalHeaderLabels(headers)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.setAlternatingRowColors(True)
        self.tbl_items.setSelectionMode(QTableWidget.NoSelection)
        self.tbl_items.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_items.horizontalHeader().setStretchLastSection(True)
        self.tbl_items.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        v.addWidget(self.tbl_items, 1)
        self.lbl_totals = QLabel("")
        self.lbl_totals.setObjectName("detail-value-financial")
        v.addWidget(self.lbl_totals)
        return tab

    def _build_documents_tab(self) -> QWidget:
        tab = QWidget(); v = QVBoxLayout(tab)
        scroll = QScrollArea(tab); scroll.setWidgetResizable(True)
        cont = QWidget(); lay = QVBoxLayout(cont)
        self.doc_checkboxes: list[QCheckBox] = []
        for d in self._load_document_types():
            cb = QCheckBox(self._doc_label(d))
            cb.setProperty("doc_id", d.get("id"))
            self.doc_checkboxes.append(cb)
            lay.addWidget(cb)
        lay.addStretch()
        scroll.setWidget(cont)
        v.addWidget(scroll)
        return tab

    def _build_audit_tab(self) -> QWidget:
        tab = QWidget(); v = QVBoxLayout(tab)
        self._view_audit = BaseDetailsView(tab)
        v.addWidget(self._view_audit); v.addStretch()
        return tab

    # ──────────────────────────────────────────── تعبئة البيانات
    def _fill_all(self):
        t    = self.trx
        lang = self._lang
        _    = self._

        rel_map = {
            "direct":       _("direct"),
            "intermediary": _("intermediary"),
            "by_request":   _("by_request"),
            "on_behalf":    _("on_behalf"),
            "via_broker":   _("via_broker"),
        }

        # ── Overview ──
        ov = self._view_overview
        ov.begin_section("general_info", icon="📋")
        ov.add_row("transaction_no",   _get(t, "transaction_no"),   icon="🔖")
        ov.add_row("transaction_date", _get(t, "transaction_date"), icon="📅")
        ov.add_row("transaction_type", _get(t, "transaction_type"), icon="🔄", is_badge=True)
        ov.add_row("status",           _get(t, "status"),           icon="🟢", is_badge=True)
        notes = _get(t, "notes")
        if notes:
            ov.add_row("notes", notes, icon="📝", copyable=False)

        # ── Parties ──
        pv = self._view_parties
        pv.begin_section("parties", icon="👥")
        pv.add_row("client",
                   self._rel_name("client") or str(_get(t, "client_id", "")),
                   icon="👤")
        pv.add_row("exporting_company",
                   self._rel_name("exporter_company") or str(_get(t, "exporter_company_id", "")),
                   icon="🏭")
        pv.add_row("importing_company",
                   self._rel_name("importer_company") or str(_get(t, "importer_company_id", "")),
                   icon="🏢")
        rcode = str(_get(t, "relationship_type", "direct") or "direct")
        pv.add_row("relationship_type", rel_map.get(rcode, rcode), icon="🔗", is_badge=True)
        broker_name = self._rel_name("broker_company")
        if broker_name:
            pv.add_row("broker_company", broker_name, icon="🤝")

        # ── Geography ──
        gv = self._view_geo
        gv.begin_section("geography_transport", icon="🌍")
        gv.add_row("origin_country",
                   self._rel_name("origin_country") or str(_get(t, "origin_country_id", "")),
                   icon="📍")
        gv.add_row("dest_country",
                   self._rel_name("dest_country") or str(_get(t, "dest_country_id", "")),
                   icon="🎯")
        gv.add_row("delivery_method",
                   self._rel_name("delivery_method") or str(_get(t, "delivery_method_id", "")),
                   icon="🚚")

        # ── Logistics ──
        lv = self._view_log
        lv.begin_section("logistics", icon="🚛")
        transport_type = _get(t, "transport_type", "") or ""
        lv.add_row("transport_type",
                   _(transport_type) if transport_type else "-",
                   icon="🚛")
        lv.add_row("transport_ref", _get(t, "transport_ref"), icon="🏷️")
        self._fill_entries_list()

        # ── Items ──
        self._fill_items_table()

        # ── Audit ──
        av = self._view_audit
        av.begin_section("audit_info", icon="🕐")
        created_user = self._rel.get("created_by_user") or {}
        updated_user = self._rel.get("updated_by_user") or {}
        av.add_row("created_by",
                   _get(created_user, "full_name") or _get(created_user, "username") or str(_get(t, "created_by_id", "")),
                   icon="👤", copyable=False)
        av.add_row("created_at", _fmt_dt(_get(t, "created_at")), icon="🕐", copyable=False)
        av.add_row("updated_by",
                   _get(updated_user, "full_name") or _get(updated_user, "username") or str(_get(t, "updated_by_id", "")),
                   icon="👤", copyable=False)
        av.add_row("updated_at", _fmt_dt(_get(t, "updated_at")), icon="🕐", copyable=False)

        # ── Totals (في Overview) ──
        ov.begin_section("totals", icon="📊")
        cnt = _get(t, "totals_count")
        grs = _get(t, "totals_gross_kg")
        net = _get(t, "totals_net_kg")
        ov.add_row("count",           f"{float(cnt):,.0f}"    if cnt else None, icon="📦")
        ov.add_row("gross_weight_kg", f"{float(grs):,.2f} kg" if grs else None, icon="⚖️")
        ov.add_row("net_weight_kg",   f"{float(net):,.2f} kg" if net else None, icon="⚖️")

        # ── Financial ──
        if self._can_view_financial():
            cur_data = self._rel.get("currency") or {}
            cur_code = _get(cur_data, "code") or ""
            cur_sym  = _get(cur_data, "symbol") or ""
            val      = _get(t, "totals_value")
            cur_label = cur_code or cur_sym or str(_get(t, "currency_id", ""))
            ov.begin_section("financial_info", icon="💰")
            ov.add_row("currency",    cur_label,                                          icon="💵", is_financial=True)
            ov.add_row("total_value", f"{float(val):,.2f} {cur_label}".strip() if val else None, icon="💰", is_financial=True)

    # ──────────────────────────────────────────── تعبئة قائمة الإدخالات
    def _fill_entries_list(self):
        self.entries_list.clear()
        entries = []
        if get_session_local and self.trx_id:
            try:
                from sqlalchemy import text as sql_text
                SessionLocal = get_session_local()
                with SessionLocal() as s:
                    rows = s.execute(
                        sql_text("""
                            SELECT e.id, e.entry_no, e.transport_ref, e.entry_date
                            FROM transaction_entries te
                            JOIN entries e ON e.id = te.entry_id
                            WHERE te.transaction_id = :tid
                            ORDER BY e.id
                        """),
                        {"tid": int(self.trx_id)}
                    ).mappings().all()
                    entries = [dict(r) for r in rows]
            except Exception:
                pass

        for e in entries:
            eid    = e.get("id")
            e_no   = e.get("entry_no") or f"#{eid}"
            t_ref  = e.get("transport_ref") or ""
            e_date = str(e.get("entry_date") or "")[:10]
            label  = f"{e_no}"
            if t_ref:  label += f"  |  {t_ref}"
            if e_date: label += f"  |  {e_date}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, int(eid or 0))
            self.entries_list.addItem(item)

    # ──────────────────────────────────────────── تعبئة جدول العناصر
    def _fill_items_table(self):
        self.tbl_items.setRowCount(0)
        items = self._load_items_from_db()
        for it in items:
            row = self.tbl_items.rowCount()
            self.tbl_items.insertRow(row)

            # col 0: source_type (كان "_get(it,'source')" لكن العمود اسمه source_type)
            src = _get(it, "source_type") or _get(it, "source") or ""
            self._set_cell(row, 0,  src)

            # col 1: entry_no (من entries عبر entry_id — ليس موجوداً على TransactionItem)
            self._set_cell(row, 1,  _get(it, "entry_no") or "")

            # col 2-3: material, packaging_type
            self._set_cell(row, 2,  _get(it, "material_name")        or _get(it, "material_id",        ""))
            self._set_cell(row, 3,  _get(it, "packaging_type_name")  or _get(it, "packaging_type_id",  ""))

            # col 4-6: كميات وأوزان
            self._set_cell(row, 4,  _get(it, "quantity",         ""))
            self._set_cell(row, 5,  _get(it, "gross_weight_kg",  ""))
            self._set_cell(row, 6,  _get(it, "net_weight_kg",    ""))

            # col 7-9: تسعير، سعر، عملة
            self._set_cell(row, 7,  _get(it, "pricing_type_name")    or _get(it, "pricing_type_id",    ""))
            self._set_cell(row, 8,  _get(it, "unit_price",       ""))
            self._set_cell(row, 9,  _get(it, "currency_code")        or _get(it, "currency_id",        ""))

            # col 10-12: إجمالي، بلد منشأ، ملاحظات
            self._set_cell(row, 10, _get(it, "line_total",        ""))
            self._set_cell(row, 11, _get(it, "origin_country_name") or _get(it, "origin_country_id",  ""))
            self._set_cell(row, 12, _get(it, "notes",             ""))

            # col 13: transport_ref (كان "actions" بدون قيمة — الآن يعرض مرجع النقل)
            self._set_cell(row, 13, _get(it, "transport_ref",     ""))

        self._recalc_totals()

    def _load_items_from_db(self) -> list[dict]:
        """
        يجلب عناصر المعاملة مع أسماء العلاقات بـ JOIN واحد.

        السبب: joinedload على TransactionItem يتطلب session مفتوحة
        وإدارة SQLAlchemy معقدة. SQL مباشر أسرع وأكثر أماناً هنا.
        """
        if not get_session_local or not self.trx_id:
            return []
        lang = self._lang
        name_col = f"name_{lang}" if lang in ("ar", "en", "tr") else "name_en"

        try:
            from sqlalchemy import text as sql_text
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                rows = s.execute(sql_text(f"""
                    SELECT
                        ti.id,
                        ti.source_type,
                        ti.entry_id,
                        COALESCE(e.entry_no, '#' || CAST(e.id AS TEXT)) AS entry_no,
                        ti.material_id,
                        COALESCE(m.{name_col}, m.name_ar, m.name_en)   AS material_name,
                        ti.packaging_type_id,
                        COALESCE(pt.{name_col}, pt.name_ar, pt.name_en) AS packaging_type_name,
                        ti.quantity,
                        ti.gross_weight_kg,
                        ti.net_weight_kg,
                        ti.pricing_type_id,
                        COALESCE(prt.{name_col}, prt.name_ar, prt.code) AS pricing_type_name,
                        ti.unit_price,
                        ti.currency_id,
                        COALESCE(c.code, CAST(ti.currency_id AS TEXT))  AS currency_code,
                        ti.line_total,
                        ti.origin_country_id,
                        COALESCE(oc.{name_col}, oc.name_ar, oc.name_en) AS origin_country_name,
                        ti.notes,
                        ti.transport_ref,
                        ti.is_manual
                    FROM transaction_items ti
                    LEFT JOIN entries         e   ON e.id   = ti.entry_id
                    LEFT JOIN materials       m   ON m.id   = ti.material_id
                    LEFT JOIN packaging_types pt  ON pt.id  = ti.packaging_type_id
                    LEFT JOIN pricing_types   prt ON prt.id = ti.pricing_type_id
                    LEFT JOIN currencies      c   ON c.id   = ti.currency_id
                    LEFT JOIN countries       oc  ON oc.id  = ti.origin_country_id
                    WHERE ti.transaction_id = :tid
                    ORDER BY ti.id
                """), {"tid": int(self.trx_id)}).mappings().all()
                return [dict(r) for r in rows]
        except Exception:
            return []

    # ──────────────────────────────────────────── مساعدات
    def _can_view_financial(self) -> bool:
        if not self.current_user:
            return False
        perms = set(getattr(self.current_user, "_permissions", []) or [])
        return "view_values" in perms or "view_pricing" in perms or is_admin(self.current_user)

    def _set_cell(self, row: int, col: int, text, userdata=None):
        item = QTableWidgetItem(str(text or ""))
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        if userdata is not None:
            item.setData(Qt.UserRole, userdata)
        if col >= self.tbl_items.columnCount():
            self.tbl_items.setColumnCount(col + 1)
        self.tbl_items.setItem(row, col, item)

    def _recalc_totals(self):
        def _f(r, c):
            it = self.tbl_items.item(r, c)
            try:
                return float(it.text()) if it and it.text() else 0.0
            except Exception:
                return 0.0

        total_qty = total_gross = total_net = total_val = 0.0
        for r in range(self.tbl_items.rowCount()):
            total_qty   += _f(r, 4)
            total_gross += _f(r, 5)
            total_net   += _f(r, 6)
            total_val   += _f(r, 10)

        self.lbl_totals.setText(
            self._("totals_template").format(
                qty=f"{total_qty:,.2f}",
                gross=f"{total_gross:,.2f}",
                net=f"{total_net:,.2f}",
                value=f"{total_val:,.2f}",
            )
        )

    def _emit_generate_documents(self):
        ids = [cb.property("doc_id") for cb in self.doc_checkboxes if cb.isChecked()]
        if ids:
            self.generate_documents.emit(ids)

    def _load_document_types(self) -> list:
        try:
            from database.crud.document_types_crud import DocumentTypesCRUD
            docs = DocumentTypesCRUD().get_all() or []
            return [
                {"id":      getattr(d, "id",      None),
                 "name_en": getattr(d, "name_en", None),
                 "name_ar": getattr(d, "name_ar", None),
                 "name_tr": getattr(d, "name_tr", None)}
                for d in docs
            ]
        except Exception:
            if get_session_local:
                try:
                    from sqlalchemy import text as sql_text
                    SessionLocal = get_session_local()
                    with SessionLocal() as s:
                        rows = s.execute(
                            sql_text("SELECT id, name_ar, name_en, name_tr FROM document_types ORDER BY id")
                        ).mappings().all()
                        return [dict(r) for r in rows]
                except Exception:
                    pass
            return []

    def _doc_label(self, d: dict) -> str:
        return (d.get(f"name_{self._lang}")
                or d.get("name_en")
                or d.get("name_ar")
                or d.get("name_tr")
                or str(d.get("id", "")))