# -*- coding: utf-8 -*-
"""
view_transaction_dialog.py — نسخة v4 (مُنظَّمة)
================================================
تغييرات v4:
  - تقليل التبويبات من 7 إلى 3:
      Tab 1: نظرة عامة (رقم + تاريخ + أطراف + جغرافيا + مالية + تدقيق)
      Tab 2: العناصر (جدول المواد)
      Tab 3: المستندات
  - جدول العناصر: عرض تلقائي للأعمدة + stretch مناسب
  - إزالة tab_logistics المنفصل (الإدخالات تظهر في نظرة عامة)
  - إزالة tab_parties و tab_geo المنفصلَين (مدمجَين في نظرة عامة)
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QSplitter,
    QWidget, QLabel, QTableWidget, QTableWidgetItem,
    QListWidget, QListWidgetItem, QScrollArea, QCheckBox,
    QHeaderView, QFrame,
)

from core.base_dialog import BaseDialog
from core.base_details_view import BaseDetailsView
from core.translator import TranslationManager
from core.permissions import is_admin
from core.settings_manager import SettingsManager
from ui.utils.wheel_blocker import block_wheel_in

try:
    from ui.dialogs.view_details._view_helpers import build_dialog_table, make_bold_cell
except Exception:
    build_dialog_table = None
    make_bold_cell     = None

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
    """عرض المعاملة — للقراءة فقط."""

    copy_requested     = Signal(int)
    reprice_requested  = Signal(int)
    generate_documents = Signal(list)

    # أعمدة جدول العناصر: (key, label_key, min_width, stretch)
    _ITEM_COLS = [
        ("source_type",         "source",          80,  False),
        ("entry_no",            "entry_no",        90,  False),
        ("material_name",       "material",        160, True),
        ("packaging_type_name", "packaging_type",  110, False),
        ("quantity",            "quantity",         70, False),
        ("gross_weight_kg",     "gross_weight",     80, False),
        ("net_weight_kg",       "net_weight",       80, False),
        ("pricing_type_name",   "pricing_type",    100, False),
        ("unit_price",          "unit_price",       80, False),
        ("currency_code",       "currency",         70, False),
        ("line_total",          "line_total",       90, False),
        ("origin_country_name", "origin_country",  110, False),
        ("notes",               "notes",           120, True),
        ("transport_ref",       "transport_ref",   100, False),
    ]

    def __init__(self, transaction, current_user=None, parent=None):
        _user = current_user or SettingsManager.get_instance().get("user")
        super().__init__(parent, user=_user)
        self._ = TranslationManager.get_instance().translate
        self._lang = TranslationManager.get_instance().get_current_language()
        self.current_user = _user
        self.trx = transaction
        self.trx_id = _get(self.trx, "id")

        self._rel = self._load_related_data()
        self.setWindowTitle(self._("transaction_view"))

        from PySide6.QtCore import Qt as _Qt
        self.setLayoutDirection(
            _Qt.RightToLeft if self._lang == "ar" else _Qt.LeftToRight
        )

        try:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().availableGeometry()
            w = min(1100, int(screen.width()  * 0.88))
            h = min(720,  int(screen.height() * 0.88))
            self.resize(w, h)
        except Exception:
            self.resize(1100, 720)

        self.setSizeGripEnabled(True)
        self._build_ui()
        block_wheel_in(self)
        self._fill_all()

    # ── جلب العلاقات ──────────────────────────────────────────────────────
    def _load_related_data(self) -> dict:
        rel = {k: None for k in [
            "client", "exporter_company", "importer_company", "broker_company",
            "origin_country", "dest_country", "currency", "delivery_method",
            "created_by_user", "updated_by_user",
        ]}
        if not get_session_local or not self.trx:
            return rel
        try:
            from sqlalchemy import text as sql_text
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                def _one(table, row_id):
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

                t = self.trx
                rel["client"]           = _one("clients",         _get(t, "client_id"))
                rel["exporter_company"] = _one("companies",        _get(t, "exporter_company_id"))
                rel["importer_company"] = _one("companies",        _get(t, "importer_company_id"))
                rel["broker_company"]   = _one("companies",        _get(t, "broker_company_id"))
                rel["origin_country"]   = _one("countries",        _get(t, "origin_country_id"))
                rel["dest_country"]     = _one("countries",        _get(t, "dest_country_id"))
                rel["currency"]         = _one("currencies",       _get(t, "currency_id"))
                rel["delivery_method"]  = _one("delivery_methods", _get(t, "delivery_method_id"))
                rel["created_by_user"]  = _one("users",            _get(t, "created_by_id"))
                rel["updated_by_user"]  = _one("users",            _get(t, "updated_by_id"))
        except Exception:
            pass
        return rel

    def _rel_name(self, key: str) -> str:
        return _name_by_lang(self._rel.get(key), self._lang)

    # ── بناء الواجهة ──────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header, sep = self._build_primary_header(
            title=self._("transaction_view"),
            subtitle=str(_get(self.trx, "transaction_no") or "")
        )
        root.addWidget(header)
        root.addWidget(sep)

        # أزرار
        actions_w = QWidget()
        actions_w.setObjectName("form-dialog-footer")
        actions = QHBoxLayout(actions_w)
        actions.setContentsMargins(16, 10, 16, 10)
        actions.setSpacing(8)
        actions.addStretch()

        self.btn_copy         = QPushButton(self._("copy_transaction"))
        self.btn_copy.setObjectName("secondary-btn")
        self.btn_edit         = QPushButton(self._("edit_transaction"))
        self.btn_edit.setObjectName("primary-btn")
        self.btn_generate_docs = QPushButton(self._("generate_documents"))
        self.btn_generate_docs.setObjectName("primary-btn")
        self.btn_close        = QPushButton(self._("close"))
        self.btn_close.setObjectName("secondary-btn")

        for b in (self.btn_copy, self.btn_edit,
                  self.btn_generate_docs, self.btn_close):
            b.setMinimumWidth(100)
            actions.addWidget(b)

        root.addWidget(actions_w)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("form-dialog-sep")
        sep2.setFixedHeight(1)
        root.addWidget(sep2)

        # 3 تبويبات
        self.tabs = QTabWidget()
        self.tabs.setObjectName("transaction-view-tabs")
        self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs, 1)

        self.tabs.addTab(self._build_overview_tab(), self._("overview"))
        self.tabs.addTab(self._build_items_tab(),    self._("items"))
        self.tabs.addTab(self._build_documents_tab(),self._("documents"))

        # ربط الأزرار
        self.btn_close.clicked.connect(self.reject)
        self.btn_copy.clicked.connect(
            lambda: self.copy_requested.emit(int(self.trx_id or 0)))
        self.btn_edit.clicked.connect(
            lambda: self.reprice_requested.emit(int(self.trx_id or 0)))
        self.btn_generate_docs.clicked.connect(self._emit_generate_documents)

    # ── Tab 1: نظرة عامة (Splitter أفقي: تفاصيل | إدخالات) ───────────────
    def _build_overview_tab(self) -> QWidget:
        tab = QWidget()
        h_split = QSplitter(Qt.Horizontal, tab)
        h_split.setChildrenCollapsible(False)

        # يسار: تفاصيل
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        detail_w = QWidget()
        v = QVBoxLayout(detail_w)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        self._view_general  = BaseDetailsView(detail_w)
        self._view_parties  = BaseDetailsView(detail_w)
        self._view_geo      = BaseDetailsView(detail_w)
        self._view_financial = BaseDetailsView(detail_w)
        self._view_audit    = BaseDetailsView(detail_w)

        for view in (self._view_general, self._view_parties,
                     self._view_geo, self._view_financial, self._view_audit):
            v.addWidget(view)
        v.addStretch()
        scroll.setWidget(detail_w)

        # يمين: إدخالات
        entries_w = QWidget()
        entries_v = QVBoxLayout(entries_w)
        entries_v.setContentsMargins(8, 12, 8, 8)
        entries_v.setSpacing(6)
        lbl = QLabel(self._("entries"))
        lbl.setObjectName("form-section-title")
        self.entries_list = QListWidget()
        entries_v.addWidget(lbl)
        entries_v.addWidget(self.entries_list, 1)

        h_split.addWidget(scroll)
        h_split.addWidget(entries_w)
        h_split.setStretchFactor(0, 3)
        h_split.setStretchFactor(1, 1)
        h_split.setSizes([750, 250])

        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(h_split)
        return tab

    # ── Tab 2: العناصر ────────────────────────────────────────────────────
    def _build_items_tab(self) -> QWidget:
        tab = QWidget()
        v = QVBoxLayout(tab)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        headers = [self._(col[1]) for col in self._ITEM_COLS]

        if build_dialog_table:
            self.tbl_items = build_dialog_table(
                headers, tab,
                object_name="entries-table",
                select_rows=False,
            )
        else:
            self.tbl_items = QTableWidget(0, len(headers), tab)
            self.tbl_items.setObjectName("entries-table")
            self.tbl_items.setHorizontalHeaderLabels(headers)
            self.tbl_items.verticalHeader().setVisible(False)
            self.tbl_items.setAlternatingRowColors(True)
            self.tbl_items.setSelectionMode(QTableWidget.SingleSelection)
            self.tbl_items.setSelectionBehavior(QTableWidget.SelectRows)
            self.tbl_items.setEditTriggers(QTableWidget.NoEditTriggers)

        # عرض الأعمدة
        hdr = self.tbl_items.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        for i, (_, _, min_w, stretch) in enumerate(self._ITEM_COLS):
            self.tbl_items.setColumnWidth(i, min_w)
            if stretch:
                hdr.setSectionResizeMode(i, QHeaderView.Stretch)

        v.addWidget(self.tbl_items, 1)

        self.lbl_totals = QLabel("")
        self.lbl_totals.setObjectName("detail-value-financial")
        v.addWidget(self.lbl_totals)
        return tab

    # ── Tab 3: المستندات ──────────────────────────────────────────────────
    def _build_documents_tab(self) -> QWidget:
        tab = QWidget()
        v = QVBoxLayout(tab)
        v.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setSpacing(4)

        self.doc_checkboxes: list[QCheckBox] = []
        for d in self._load_document_types():
            cb = QCheckBox(self._doc_label(d))
            cb.setProperty("doc_id", d.get("id"))
            cb.setMinimumHeight(28)
            self.doc_checkboxes.append(cb)
            lay.addWidget(cb)
        lay.addStretch()
        scroll.setWidget(cont)
        v.addWidget(scroll)
        return tab

    # ── تعبئة البيانات ────────────────────────────────────────────────────
    def _fill_all(self):
        t    = self.trx
        _    = self._

        rel_map = {
            "direct":       _("direct"),
            "intermediary": _("intermediary"),
            "by_request":   _("by_request"),
            "on_behalf":    _("on_behalf"),
            "via_broker":   _("via_broker"),
        }

        # ── General ──
        gv = self._view_general
        gv.begin_section("general_info", icon="📋")
        gv.add_row("transaction_no",   _get(t, "transaction_no"),   icon="🔖")
        gv.add_row("transaction_date", _get(t, "transaction_date"), icon="📅")
        gv.add_row("transaction_type", _get(t, "transaction_type"), icon="🔄", is_badge=True)
        gv.add_row("status",           _get(t, "status"),           icon="🟢", is_badge=True)
        notes = _get(t, "notes")
        if notes:
            gv.add_row("notes", notes, icon="📝", copyable=False)

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
        broker = self._rel_name("broker_company")
        if broker:
            pv.add_row("broker_company", broker, icon="🤝")

        # ── Geography + Transport ──
        gv2 = self._view_geo
        gv2.begin_section("geography_transport", icon="🌍")
        gv2.add_row("origin_country",
                    self._rel_name("origin_country") or str(_get(t, "origin_country_id", "")),
                    icon="📍")
        gv2.add_row("dest_country",
                    self._rel_name("dest_country") or str(_get(t, "dest_country_id", "")),
                    icon="🎯")
        gv2.add_row("delivery_method",
                    self._rel_name("delivery_method") or str(_get(t, "delivery_method_id", "")),
                    icon="🚚")
        transport_type = _get(t, "transport_type", "") or ""
        if transport_type:
            gv2.add_row("transport_type", _(transport_type), icon="🚛")
        transport_ref = _get(t, "transport_ref")
        if transport_ref:
            gv2.add_row("transport_ref", transport_ref, icon="🏷️")

        # ── Financial ──
        if self._can_view_financial():
            fv = self._view_financial
            cur_data  = self._rel.get("currency") or {}
            cur_code  = _get(cur_data, "code") or ""
            cur_sym   = _get(cur_data, "symbol") or ""
            cur_label = cur_code or cur_sym or str(_get(t, "currency_id", ""))
            val = _get(t, "totals_value")

            fv.begin_section("financial_info", icon="💰")
            fv.add_row("currency",    cur_label, icon="💵", is_financial=True)
            if val:
                fv.add_row("total_value",
                           f"{float(val):,.2f} {cur_label}".strip(),
                           icon="💰", is_financial=True)
            cnt = _get(t, "totals_count")
            grs = _get(t, "totals_gross_kg")
            net = _get(t, "totals_net_kg")
            if cnt: fv.add_row("count",           f"{float(cnt):,.0f}",     icon="📦")
            if grs: fv.add_row("gross_weight_kg", f"{float(grs):,.2f} kg",  icon="⚖️")
            if net: fv.add_row("net_weight_kg",   f"{float(net):,.2f} kg",  icon="⚖️")

        # ── Audit ──
        av = self._view_audit
        av.begin_section("audit_info", icon="🕐")
        cu = self._rel.get("created_by_user") or {}
        uu = self._rel.get("updated_by_user") or {}
        av.add_row("created_by",
                   _get(cu, "full_name") or _get(cu, "username") or str(_get(t, "created_by_id", "")),
                   icon="👤", copyable=False)
        av.add_row("created_at", _fmt_dt(_get(t, "created_at")), icon="🕐", copyable=False)
        av.add_row("updated_by",
                   _get(uu, "full_name") or _get(uu, "username") or str(_get(t, "updated_by_id", "")),
                   icon="👤", copyable=False)
        av.add_row("updated_at", _fmt_dt(_get(t, "updated_at")), icon="🕐", copyable=False)

        # ── Entries list ──
        self._fill_entries_list()

        # ── Items ──
        self._fill_items_table()

    def _fill_entries_list(self):
        self.entries_list.clear()
        if not get_session_local or not self.trx_id:
            return
        try:
            from sqlalchemy import text as sql_text
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                rows = s.execute(sql_text("""
                    SELECT e.id, e.entry_no, e.transport_ref, e.entry_date
                    FROM transaction_entries te
                    JOIN entries e ON e.id = te.entry_id
                    WHERE te.transaction_id = :tid
                    ORDER BY e.id
                """), {"tid": int(self.trx_id)}).mappings().all()
                entries = [dict(r) for r in rows]
        except Exception:
            return

        for e in entries:
            eid    = e.get("id")
            e_no   = e.get("entry_no") or f"#{eid}"
            t_ref  = e.get("transport_ref") or ""
            e_date = str(e.get("entry_date") or "")[:10]
            label  = e_no
            if t_ref:  label += f"  |  {t_ref}"
            if e_date: label += f"  |  {e_date}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, int(eid or 0))
            self.entries_list.addItem(item)

    def _fill_items_table(self):
        self.tbl_items.setRowCount(0)
        items = self._load_items_from_db()
        for it in items:
            row = self.tbl_items.rowCount()
            self.tbl_items.insertRow(row)
            for col_idx, (key, _, _, _) in enumerate(self._ITEM_COLS):
                val = _get(it, key, "")
                self._set_cell(row, col_idx, val)
        self._recalc_totals()

    def _load_items_from_db(self) -> list:
        if not get_session_local or not self.trx_id:
            return []
        lang = self._lang
        nc   = f"name_{lang}" if lang in ("ar", "en", "tr") else "name_en"
        try:
            from sqlalchemy import text as sql_text
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                rows = s.execute(sql_text(f"""
                    SELECT
                        ti.id, ti.source_type, ti.entry_id,
                        COALESCE(e.entry_no, '#' || CAST(e.id AS TEXT))    AS entry_no,
                        ti.material_id,
                        COALESCE(m.{nc},  m.name_ar, m.name_en)            AS material_name,
                        ti.packaging_type_id,
                        COALESCE(pt.{nc}, pt.name_ar, pt.name_en)          AS packaging_type_name,
                        ti.quantity, ti.gross_weight_kg, ti.net_weight_kg,
                        ti.pricing_type_id,
                        COALESCE(prt.{nc}, prt.name_ar, prt.code)          AS pricing_type_name,
                        ti.unit_price, ti.currency_id,
                        COALESCE(c.code, CAST(ti.currency_id AS TEXT))      AS currency_code,
                        ti.line_total, ti.origin_country_id,
                        COALESCE(oc.{nc}, oc.name_ar, oc.name_en)          AS origin_country_name,
                        ti.notes, ti.transport_ref, ti.is_manual
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

    # ── مساعدات ───────────────────────────────────────────────────────────
    def _can_view_financial(self) -> bool:
        if not self.current_user:
            return False
        perms = set(getattr(self.current_user, "_permissions", []) or [])
        return "view_values" in perms or "view_pricing" in perms or is_admin(self.current_user)

    def _set_cell(self, row: int, col: int, text, userdata=None):
        if make_bold_cell:
            item = make_bold_cell(str(text or ""))
        else:
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
                return float(it.text().replace(",", "")) if it and it.text() else 0.0
            except Exception:
                return 0.0

        # col indices: qty=4, gross=5, net=6, total=10
        col_qty, col_gross, col_net, col_total = 4, 5, 6, 10
        total_qty = total_gross = total_net = total_val = 0.0
        for r in range(self.tbl_items.rowCount()):
            total_qty   += _f(r, col_qty)
            total_gross += _f(r, col_gross)
            total_net   += _f(r, col_net)
            total_val   += _f(r, col_total)

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
            return [{"id": getattr(d, "id", None),
                     "name_en": getattr(d, "name_en", None),
                     "name_ar": getattr(d, "name_ar", None),
                     "name_tr": getattr(d, "name_tr", None)} for d in docs]
        except Exception:
            pass
        if not get_session_local:
            return []
        try:
            from sqlalchemy import text as sql_text
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                rows = s.execute(sql_text(
                    "SELECT id, name_ar, name_en, name_tr FROM document_types ORDER BY id"
                )).mappings().all()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def _doc_label(self, d: dict) -> str:
        return (d.get(f"name_{self._lang}") or d.get("name_en")
                or d.get("name_ar") or d.get("name_tr")
                or str(d.get("id", "")))