# -*- coding: utf-8 -*-
"""
documents_tab.py — v3 (Side Panel دائم بدل تبويب)

بدلاً من تبويب رابع مخفي، المستندات تظهر الآن كـ side panel
على يمين التبويبات، دائمة الظهور ومتاحة في أي وقت.

التغييرات من v2:
- _build_documents_panel() بدل _build_documents_tab()
- يُرجع QWidget مباشرة (يضعه window.py في splitter أفقي)
- نفس API الداخلية: get_documents_data(), get_documents_codes(), prefill_documents()
- تصميم أكثر كثافة (compact) يناسب المساحة الجانبية الضيقة
- badge عداد المختارين مدمج في header الـ panel

API الخارجية (لـ window.py):
    * build_documents_panel() -> QWidget   ← جديد
    * get_documents_data()    -> list[int]
    * get_documents_codes()   -> list[str]
    * prefill_documents(transaction)
"""

from __future__ import annotations
from typing import Any, Dict, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QCheckBox, QPushButton, QLabel, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

try:
    from database.crud.document_types_crud import DocumentTypesCRUD
except Exception:
    DocumentTypesCRUD = None  # type: ignore

# ── كودات تملك generator فعلي ───────────────────────────────────────────────
_SUPPORTED_CODES = {
    "INV_EXT", "INV_NORMAL", "INV_PROFORMA", "INV_PRO",
    "INV_SYR_TRANS", "INV_SYR_INTERM", "invoice.syrian.entry",
    "PL_EXPORT_SIMPLE", "PL_EXPORT_WITH_DATES", "PL_EXPORT_WITH_LINE_ID",
}

_INVOICE_PREFIXES = ("INV_", "invoice.")
_PACKING_PREFIXES = ("PL_", "PACKING", "packing")

_DOC_ICONS = {"invoice": "🧾", "packing": "📦", "other": "📄"}


def _classify(code: str) -> str:
    cu = code.upper()
    if any(cu.startswith(p.upper()) for p in _INVOICE_PREFIXES):
        return "invoice"
    if any(cu.startswith(p.upper()) for p in _PACKING_PREFIXES):
        return "packing"
    return "other"


class DocumentsTabMixin:
    """
    Mixin لـ side panel المستندات — نسخة v3.
    يُبنى عبر build_documents_panel() ويُدمج في window.py كـ QWidget جانبي.
    """

    # ─────────────────────────────── build panel ────────────────────────────
    def build_documents_panel(self) -> QWidget:
        """
        يبني الـ side panel ويرجعه كـ QWidget.
        يستدعيه window.py ويضعه في QSplitter أفقي بجانب التبويبات.
        """
        self._docs_panel = QWidget()
        self._docs_panel.setObjectName("documents-side-panel")
        self._docs_panel.setMinimumWidth(200)
        self._docs_panel.setMaximumWidth(300)
        self._docs_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        root = QVBoxLayout(self._docs_panel)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── Header ──────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        lbl_title = QLabel("📄 " + self._get_tr("documents"))
        lbl_title.setObjectName("docs-panel-title")
        f = QFont()
        f.setBold(True)
        lbl_title.setFont(f)

        self.lbl_selected_count = QLabel("0/0")
        self.lbl_selected_count.setObjectName("docs-count-badge")
        self.lbl_selected_count.setAlignment(Qt.AlignCenter)
        self.lbl_selected_count.setFixedSize(42, 20)

        header_row.addWidget(lbl_title)
        header_row.addStretch()
        header_row.addWidget(self.lbl_selected_count)
        root.addLayout(header_row)

        # ── separator ───────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("docs-separator")
        root.addWidget(sep)

        # ── Select All / Clear ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        self.btn_select_all_docs = QPushButton("✔ " + self._get_tr("select_all"))
        self.btn_select_all_docs.setObjectName("topbar-btn")
        self.btn_select_all_docs.setMinimumHeight(26)
        self.btn_clear_all_docs = QPushButton("✕ " + self._get_tr("clear_all"))
        self.btn_clear_all_docs.setObjectName("topbar-btn")
        self.btn_clear_all_docs.setMinimumHeight(26)
        btn_row.addWidget(self.btn_select_all_docs)
        btn_row.addWidget(self.btn_clear_all_docs)
        root.addLayout(btn_row)

        # ── Scroll area للـ checkboxes ────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setObjectName("docs-scroll-area")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        cont = QWidget()
        cont.setObjectName("docs-scroll-content")
        self._docs_vlay = QVBoxLayout(cont)
        self._docs_vlay.setContentsMargins(2, 2, 2, 2)
        self._docs_vlay.setSpacing(4)

        # ── load & render ────────────────────────────────────────────────────
        self.doc_checkboxes: List[QCheckBox] = []
        self._doc_code_map: Dict[int, str] = {}
        documents = self._load_document_types()

        invoices = [d for d in documents if d.get("_cat") == "invoice"]
        packings = [d for d in documents if d.get("_cat") == "packing"]
        others   = [d for d in documents if d.get("_cat") == "other"]

        for group_label, group_icon, group_docs in [
            (self._get_tr("invoice"),      "🧾", invoices),
            (self._get_tr("packing_list"), "📦", packings),
            (self._get_tr("other") if self._get_tr("other") != "other" else "أخرى", "📄", others),
        ]:
            if not group_docs:
                continue

            g_hdr = QLabel(f"{group_icon} {group_label}")
            g_hdr.setObjectName("doc-group-header")
            gf = QFont()
            gf.setBold(True)
            gf.setPointSize(8)
            g_hdr.setFont(gf)
            self._docs_vlay.addWidget(g_hdr)

            for d in group_docs:
                cb = self._make_doc_checkbox(d)
                self._docs_vlay.addWidget(cb)

        self._docs_vlay.addStretch()
        scroll.setWidget(cont)
        root.addWidget(scroll)

        # ── hint ────────────────────────────────────────────────────────────
        hint = QLabel(self._get_tr("docs_panel_hint") if self._get_tr("docs_panel_hint") != "docs_panel_hint"
                      else "✓ اختر المستندات\nثم اضغط حفظ")
        hint.setObjectName("docs-hint-label")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        root.addWidget(hint)

        # ── Connect ──────────────────────────────────────────────────────────
        self.btn_select_all_docs.clicked.connect(lambda: self._toggle_all_docs(True))
        self.btn_clear_all_docs.clicked.connect(lambda: self._toggle_all_docs(False))
        self._update_selected_count()

        return self._docs_panel

    # ─────────────────────────────── checkbox widget ────────────────────────
    def _make_doc_checkbox(self, d: Dict[str, Any]) -> QCheckBox:
        doc_id    = d.get("id")
        code      = d.get("code", "") or ""
        label     = self._doc_label(d)
        supported = code in _SUPPORTED_CODES

        if supported:
            display_label = f"{_DOC_ICONS.get(d.get('_cat', 'other'), '📄')} {label}"
        else:
            display_label = f"⚠ {label}"

        cb = QCheckBox(display_label)
        cb.setObjectName("doc-checkbox-card")
        cb.setProperty("doc_id",   doc_id)
        cb.setProperty("doc_code", code)
        cb.setProperty("supported", supported)
        cb.setMinimumHeight(32)
        cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cb.setWordWrap(True)

        if not supported:
            cb.setEnabled(False)
            fallback = "⚠ هذا النوع غير مدعوم للتوليد حالياً"
            tip = self._get_tr("doc_not_supported_yet")
            cb.setToolTip(tip if tip != "doc_not_supported_yet" else fallback)

        if doc_id is not None:
            self._doc_code_map[doc_id] = code

        cb.stateChanged.connect(self._update_selected_count)
        self.doc_checkboxes.append(cb)
        return cb

    # ─────────────────────────────── Data API ───────────────────────────────
    def get_documents_data(self) -> List[int]:
        out: List[int] = []
        for cb in getattr(self, "doc_checkboxes", []) or []:
            try:
                if cb.isChecked():
                    did = cb.property("doc_id")
                    if isinstance(did, int):
                        out.append(did)
            except Exception:
                pass
        return out

    def get_documents_codes(self) -> List[str]:
        codes: List[str] = []
        for cb in getattr(self, "doc_checkboxes", []) or []:
            try:
                if cb.isChecked() and cb.property("supported"):
                    code = cb.property("doc_code")
                    if code:
                        codes.append(code)
            except Exception:
                pass
        return codes

    def prefill_documents(self, transaction: Any) -> None:
        if not transaction:
            return
        ids: List[int] = []
        try:
            if isinstance(transaction, dict):
                cand = transaction.get("document_type_ids")
                if isinstance(cand, (list, tuple, set)):
                    ids.extend([int(x) for x in cand if x is not None])
        except Exception:
            pass
        try:
            if isinstance(transaction, dict) and not ids:
                for d in (transaction.get("documents") or []):
                    did = d.get("document_type_id") if isinstance(d, dict) else getattr(d, "document_type_id", None)
                    if did is not None:
                        ids.append(int(did))
        except Exception:
            pass
        try:
            if not ids:
                for d in (getattr(transaction, "documents", None) or []):
                    did = getattr(d, "document_type_id", None)
                    if did is not None:
                        ids.append(int(did))
        except Exception:
            pass

        id_set = set(ids)
        for cb in getattr(self, "doc_checkboxes", []) or []:
            did = cb.property("doc_id")
            cb.setChecked(bool(isinstance(did, int) and did in id_set))
        self._update_selected_count()

    # ─────────────────────────────── helpers ────────────────────────────────
    def _toggle_all_docs(self, checked: bool) -> None:
        for cb in getattr(self, "doc_checkboxes", []) or []:
            try:
                if cb.isEnabled():
                    cb.setChecked(checked)
            except Exception:
                pass
        self._update_selected_count()

    def _update_selected_count(self) -> None:
        if not hasattr(self, "lbl_selected_count"):
            return
        enabled = [cb for cb in (getattr(self, "doc_checkboxes", []) or []) if cb.isEnabled()]
        count = sum(1 for cb in enabled if cb.isChecked())
        total = len(enabled)
        self.lbl_selected_count.setText(f"{count}/{total}")
        if hasattr(self.lbl_selected_count, "setProperty"):
            state = "none" if count == 0 else ("all" if count == total else "some")
            self.lbl_selected_count.setProperty("count_state", state)
            self.lbl_selected_count.style().unpolish(self.lbl_selected_count)
            self.lbl_selected_count.style().polish(self.lbl_selected_count)

    def _load_document_types(self) -> List[Dict[str, Any]]:
        try:
            if DocumentTypesCRUD:
                docs = (DocumentTypesCRUD()).get_all_types() or []
                result = []
                for d in docs:
                    code = getattr(d, "code", "") or ""
                    result.append({
                        "id":        getattr(d, "id",       None),
                        "code":      code,
                        "name_en":   getattr(d, "name_en",  None),
                        "name_ar":   getattr(d, "name_ar",  None),
                        "name_tr":   getattr(d, "name_tr",  None),
                        "is_active": getattr(d, "is_active", 1),
                        "_cat":      _classify(code),
                    })
                return [r for r in result if r.get("is_active", 1)]
        except Exception:
            pass
        return [
            {"id": 1,  "code": "INV_EXT",               "name_ar": "فاتورة خارجية",          "name_en": "External Invoice",        "_cat": "invoice", "is_active": 1},
            {"id": 16, "code": "INV_NORMAL",             "name_ar": "فاتورة عادية",            "name_en": "Normal Invoice",          "_cat": "invoice", "is_active": 1},
            {"id": 9,  "code": "INV_PRO",                "name_ar": "بروفورما إنفويس",          "name_en": "Proforma Invoice",        "_cat": "invoice", "is_active": 1},
            {"id": 11, "code": "INV_SYR_TRANS",          "name_ar": "فاتورة سورية – عبور",      "name_en": "Syrian Transit Invoice",  "_cat": "invoice", "is_active": 1},
            {"id": 12, "code": "INV_SYR_INTERM",         "name_ar": "فاتورة سورية – وسيط",      "name_en": "Syrian Intermediary Inv", "_cat": "invoice", "is_active": 1},
            {"id": 10, "code": "invoice.syrian.entry",   "name_ar": "فاتورة سورية – إدخال",     "name_en": "Syrian Entry Invoice",    "_cat": "invoice", "is_active": 1},
            {"id": 13, "code": "PL_EXPORT_SIMPLE",       "name_ar": "قائمة تعبئة – بسيطة",     "name_en": "Packing List – Simple",   "_cat": "packing", "is_active": 1},
            {"id": 14, "code": "PL_EXPORT_WITH_DATES",   "name_ar": "قائمة تعبئة – مع تواريخ", "name_en": "Packing List – With Dates","_cat": "packing", "is_active": 1},
            {"id": 17, "code": "PL_EXPORT_WITH_LINE_ID", "name_ar": "قائمة تعبئة مع رقم سطر",  "name_en": "Packing List – Line ID",  "_cat": "packing", "is_active": 1},
        ]

    def _doc_label(self, d: Dict[str, Any]) -> str:
        lang = getattr(self, "_lang", "ar") or "ar"
        for key in (f"name_{lang}", "name_en", "name_ar", "name_tr"):
            val = d.get(key)
            if val:
                return str(val)
        return str(d.get("code") or d.get("id", ""))

    def _get_tr(self, key: str) -> str:
        """مترجم آمن — يستخدم self._ لو موجود."""
        try:
            return self._(key)  # type: ignore[attr-defined]
        except Exception:
            return key

    # ─────────────────────────────── backward compat ────────────────────────
    def _build_documents_tab(self) -> None:
        """
        متوافق مع الكود القديم — لو نُودي عليه يبني الـ panel مكان التبويب.
        window.py الجديد يستخدم build_documents_panel() مباشرة.
        """
        if not hasattr(self, "tabs"):
            return
        panel = self.build_documents_panel()
        self.tab_docs = panel
        try:
            self.tabs.addTab(panel, self._get_tr("documents"))
        except Exception:
            pass

    def refresh_language_documents(self) -> None:
        """إعادة بناء المحتوى عند تغيير اللغة."""
        if not hasattr(self, "_docs_panel"):
            return
        # امسح الـ checkboxes وأعد البناء
        self.doc_checkboxes = []
        self._doc_code_map = {}
        if hasattr(self, "_docs_vlay"):
            while self._docs_vlay.count():
                item = self._docs_vlay.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
        # أعد تحميل المستندات
        documents = self._load_document_types()
        invoices = [d for d in documents if d.get("_cat") == "invoice"]
        packings = [d for d in documents if d.get("_cat") == "packing"]
        others   = [d for d in documents if d.get("_cat") == "other"]
        for group_label, group_icon, group_docs in [
            (self._get_tr("invoice"),      "🧾", invoices),
            (self._get_tr("packing_list"), "📦", packings),
            (self._get_tr("other") if self._get_tr("other") != "other" else "أخرى", "📄", others),
        ]:
            if not group_docs:
                continue
            g_hdr = QLabel(f"{group_icon} {group_label}")
            g_hdr.setObjectName("doc-group-header")
            gf = QFont(); gf.setBold(True); gf.setPointSize(8)
            g_hdr.setFont(gf)
            self._docs_vlay.addWidget(g_hdr)
            for d in group_docs:
                cb = self._make_doc_checkbox(d)
                self._docs_vlay.addWidget(cb)
        self._docs_vlay.addStretch()
        self._update_selected_count()