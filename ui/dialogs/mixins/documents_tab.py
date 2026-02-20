# -*- coding: utf-8 -*-
"""
documents_tab.py — v2 (UX محسّن + ربط مع GenerateDocumentDialog)

التطويرات:
- كاردات بدل checkboxes عادية (اسم + وصف + أيقونة)
- تصنيف المستندات: فواتير / قوائم تعبئة
- تمييز المستندات المدعومة من غير المدعومة
- get_documents_data() تُرجع list[int] كما كانت
- get_documents_codes() جديدة: تُرجع dict {id: code} للربط مع GenerateDocumentDialog

API:
    * _build_documents_tab()
    * get_documents_data() -> list[int]          — للحفظ في DB
    * get_documents_codes() -> list[str]          — للتمرير لـ GenerateDocumentDialog
    * prefill_documents(transaction)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QFrame, QCheckBox,
    QPushButton, QHBoxLayout, QLabel, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

try:
    from database.crud.document_types_crud import DocumentTypesCRUD
except Exception:
    DocumentTypesCRUD = None  # type: ignore

# Codes that have a working generator
_SUPPORTED_CODES = {
    "INV_EXT", "INV_NORMAL", "INV_PROFORMA", "INV_PRO",
    "INV_SYR_TRANS", "INV_SYR_INTERM", "invoice.syrian.entry",
    "PL_EXPORT_SIMPLE", "PL_EXPORT_WITH_DATES", "PL_EXPORT_WITH_LINE_ID",
}

_INVOICE_PREFIXES  = ("INV_", "invoice.")
_PACKING_PREFIXES  = ("PL_",  "PACKING", "packing")

_DOC_ICONS = {
    "invoice":  "🧾",
    "packing":  "📦",
    "other":    "📄",
}


def _classify(code: str) -> str:
    cu = code.upper()
    if any(cu.startswith(p.upper()) for p in _INVOICE_PREFIXES):
        return "invoice"
    if any(cu.startswith(p.upper()) for p in _PACKING_PREFIXES):
        return "packing"
    return "other"


class DocumentsTabMixin:
    """Mixin لتبويب المستندات — نسخة v2 مع UX محسّن."""

    # ─────────────────────────────── build ──────────────────────────────────
    def _build_documents_tab(self) -> None:
        self.tab_docs = QWidget()
        self.tab_docs.setObjectName("documents-tab")
        self.tabs.addTab(self.tab_docs, self._("documents"))

        root = QVBoxLayout(self.tab_docs)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── header ──────────────────────────────────────────────────────────
        header = QLabel(self._("select_documents_to_generate"))
        header.setObjectName("tab-header")
        header.setAlignment(Qt.AlignCenter)
        root.addWidget(header)

        # ── toolbar ─────────────────────────────────────────────────────────
        tools = QHBoxLayout()
        tools.setSpacing(8)
        self.btn_select_all_docs = QPushButton("✔  " + self._("select_all"))
        self.btn_select_all_docs.setObjectName("primary-btn")
        self.btn_clear_all_docs  = QPushButton("✕  " + self._("clear_all"))
        self.btn_clear_all_docs.setObjectName("secondary-btn")
        self.lbl_selected_count = QLabel("")
        self.lbl_selected_count.setObjectName("selected-count-label")
        tools.addWidget(self.btn_select_all_docs)
        tools.addWidget(self.btn_clear_all_docs)
        tools.addStretch()
        tools.addWidget(self.lbl_selected_count)
        root.addLayout(tools)

        # ── scroll area ──────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setObjectName("docs-scroll-area")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        cont = QWidget()
        cont.setObjectName("docs-scroll-content")
        vlay = QVBoxLayout(cont)
        vlay.setContentsMargins(4, 4, 4, 4)
        vlay.setSpacing(6)

        # ── load & render ────────────────────────────────────────────────────
        self.doc_checkboxes: List[QCheckBox] = []
        self._doc_code_map: Dict[int, str]   = {}  # id → code
        documents = self._load_document_types()

        # تصنيف
        invoices = [d for d in documents if d.get("_cat") == "invoice"]
        packings = [d for d in documents if d.get("_cat") == "packing"]
        others   = [d for d in documents if d.get("_cat") == "other"]

        for group_label, group_icon, group_docs in [
            (self._("invoice"),      "🧾", invoices),
            (self._("packing_list"), "📦", packings),
            (self._("other") if self._("other") != "other" else "أخرى", "📄", others),
        ]:
            if not group_docs:
                continue

            # group header
            g_hdr = QLabel(f"{group_icon}  {group_label}")
            g_hdr.setObjectName("doc-group-header")
            g_hdr_font = QFont()
            g_hdr_font.setBold(True)
            g_hdr.setFont(g_hdr_font)
            vlay.addWidget(g_hdr)

            # grid: 2 columns
            grid_w  = QWidget()
            grid_lay = QGridLayout(grid_w)
            grid_lay.setContentsMargins(0, 0, 0, 0)
            grid_lay.setSpacing(6)
            row = col = 0

            for d in group_docs:
                cb = self._make_doc_card(d)
                grid_lay.addWidget(cb, row, col)
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

            grid_lay.setRowStretch(row + 1, 1)
            vlay.addWidget(grid_w)

        vlay.addStretch()
        scroll.setWidget(cont)
        root.addWidget(scroll)

        # ── connect ──────────────────────────────────────────────────────────
        self.btn_select_all_docs.clicked.connect(lambda: self._toggle_all_docs(True))
        self.btn_clear_all_docs.clicked.connect(lambda: self._toggle_all_docs(False))
        self._update_selected_count()

    # ─────────────────────────────── card widget ────────────────────────────
    def _make_doc_card(self, d: Dict[str, Any]) -> QCheckBox:
        """يصنع card-style checkbox لنوع مستند."""
        doc_id   = d.get("id")
        code     = d.get("code", "") or ""
        label    = self._doc_label(d)
        supported = code in _SUPPORTED_CODES

        # أيقونة + حالة الدعم
        if supported:
            display_label = f"{_DOC_ICONS.get(d.get('_cat','other'), '📄')}  {label}"
        else:
            display_label = f"⚠  {label}"

        cb = QCheckBox(display_label)
        cb.setObjectName("doc-checkbox-card")
        cb.setProperty("doc_id",   doc_id)
        cb.setProperty("doc_code", code)
        cb.setProperty("supported", supported)
        cb.setMinimumHeight(38)
        cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if not supported:
            cb.setEnabled(False)
            cb.setToolTip(
                self._("doc_not_supported_yet") if self._("doc_not_supported_yet") != "doc_not_supported_yet"
                else "⚠ هذا النوع غير مدعوم للتوليد حالياً"
            )

        if doc_id is not None:
            self._doc_code_map[doc_id] = code

        cb.stateChanged.connect(self._update_selected_count)
        self.doc_checkboxes.append(cb)
        return cb

    # ─────────────────────────────── Data API ───────────────────────────────
    def get_documents_data(self) -> List[int]:
        """يعيد IDs المستندات المختارة (للحفظ في DB)."""
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
        """
        يعيد codes المستندات المختارة المدعومة.
        يُستخدم لتمريرها لـ GenerateDocumentDialog كـ preselected_doc_types.
        """
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
        """يملأ التحديدات من معاملة موجودة."""
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
        self.lbl_selected_count.setText(f"{self._('selected')}: {count}/{total}")
        if hasattr(self.lbl_selected_count, "setProperty"):
            state = "none" if count == 0 else ("all" if count == total else "some")
            self.lbl_selected_count.setProperty("count_state", state)
            self.lbl_selected_count.style().unpolish(self.lbl_selected_count)
            self.lbl_selected_count.style().polish(self.lbl_selected_count)

    def _load_document_types(self) -> List[Dict[str, Any]]:
        """يحمل أنواع المستندات من DB ويضيف تصنيف _cat."""
        try:
            if DocumentTypesCRUD:
                docs = (DocumentTypesCRUD()).get_all_types() or []
                result = []
                for d in docs:
                    code = getattr(d, "code", "") or ""
                    result.append({
                        "id":       getattr(d, "id",       None),
                        "code":     code,
                        "name_en":  getattr(d, "name_en",  None),
                        "name_ar":  getattr(d, "name_ar",  None),
                        "name_tr":  getattr(d, "name_tr",  None),
                        "is_active": getattr(d, "is_active", 1),
                        "_cat":     _classify(code),
                    })
                # فلتر النشطة فقط
                return [r for r in result if r.get("is_active", 1)]
        except Exception:
            pass
        # Fallback
        return [
            {"id": 1,  "code": "INV_EXT",               "name_ar": "فاتورة خارجية",         "name_en": "External Invoice",        "_cat": "invoice", "is_active": 1},
            {"id": 16, "code": "INV_NORMAL",             "name_ar": "فاتورة عادية",           "name_en": "Normal Invoice",          "_cat": "invoice", "is_active": 1},
            {"id": 9,  "code": "INV_PRO",                "name_ar": "بروفورما إنفويس",         "name_en": "Proforma Invoice",        "_cat": "invoice", "is_active": 1},
            {"id": 11, "code": "INV_SYR_TRANS",          "name_ar": "فاتورة سورية – عبور",     "name_en": "Syrian Transit Invoice",  "_cat": "invoice", "is_active": 1},
            {"id": 12, "code": "INV_SYR_INTERM",         "name_ar": "فاتورة سورية – وسيط",     "name_en": "Syrian Intermediary Inv", "_cat": "invoice", "is_active": 1},
            {"id": 10, "code": "invoice.syrian.entry",   "name_ar": "فاتورة سورية – إدخال",    "name_en": "Syrian Entry Invoice",    "_cat": "invoice", "is_active": 1},
            {"id": 13, "code": "PL_EXPORT_SIMPLE",       "name_ar": "قائمة تعبئة – بسيطة",    "name_en": "Packing List – Simple",   "_cat": "packing", "is_active": 1},
            {"id": 14, "code": "PL_EXPORT_WITH_DATES",   "name_ar": "قائمة تعبئة – مع تواريخ","name_en": "Packing List – With Dates","_cat": "packing", "is_active": 1},
            {"id": 17, "code": "PL_EXPORT_WITH_LINE_ID", "name_ar": "قائمة تعبئة مع رقم سطر", "name_en": "Packing List – Line ID",  "_cat": "packing", "is_active": 1},
        ]

    def _doc_label(self, d: Dict[str, Any]) -> str:
        lang = getattr(self, "_lang", "ar") or "ar"
        for key in (f"name_{lang}", "name_en", "name_ar", "name_tr"):
            val = d.get(key)
            if val:
                return str(val)
        return str(d.get("code") or d.get("id", ""))

    def refresh_language_documents(self) -> None:
        if not hasattr(self, "tab_docs"):
            return
        idx = self.tabs.indexOf(self.tab_docs)
        if idx != -1:
            self.tabs.removeTab(idx)
        self.doc_checkboxes = []
        self._doc_code_map  = {}
        self._build_documents_tab()