from __future__ import annotations
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import os

from PySide6.QtCore import Qt, QThread, Signal, QObject, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QComboBox, QMessageBox, QGroupBox, QGridLayout, QListWidget,
    QListWidgetItem, QProgressBar, QLineEdit, QFileDialog, QFrame,
    QSizePolicy,
)

import logging
logger = logging.getLogger(__name__)

try:
    from core.translator import TranslationManager
    _T = TranslationManager.get_instance()
    _ = _T.translate
except Exception:
    _ = lambda k: k

# =============================================================================
# Mapping: code في جدول document_types → doc_code للـ services layer
# =============================================================================
_DB_CODE_TO_DOC_CODE: Dict[str, str] = {
    "INV_EXT":                "invoice.foreign.commercial",
    "INV_NORMAL":             "invoice.normal",
    "INV_PROFORMA":           "invoice.proforma",
    "INV_PRO":                "invoice.proforma",
    "INV_SYR_TRANS":          "invoice.syrian.transit",
    "INV_SYR_INTERM":         "invoice.syrian.intermediary",
    "invoice.syrian.entry":   "invoice.syrian.entry",
    "PL_EXPORT_SIMPLE":       "packing_list.export.simple",
    "PL_EXPORT_WITH_DATES":   "packing_list.export.with_dates",
    "PL_EXPORT_WITH_LINE_ID": "packing_list.export.with_line_id",
    # ─── جديد ────────────────────────────────────────────────────────────────
    "cmr":                    "cmr",
    "form_a":                 "form_a",
}

_INVOICE_PREFIXES  = ("INV_", "invoice.")
_PACKING_PREFIXES  = ("PL_", "PACKING", "packing")
_TRANSPORT_CODES   = ("cmr",)
_ORIGIN_CERT_CODES = ("form_a", "form.a")


def _classify_doc_type(code: str) -> str:
    cu  = code.upper()
    clo = code.lower()
    if any(cu.startswith(p.upper()) for p in _INVOICE_PREFIXES):
        return "invoice"
    if any(cu.startswith(p.upper()) for p in _PACKING_PREFIXES):
        return "packing"
    if clo in _TRANSPORT_CODES:
        return "transport"
    if clo in _ORIGIN_CERT_CODES:
        return "origin_cert"
    return "other"


# =============================================================================
# Worker
# =============================================================================
@dataclass
class _JobSpec:
    doc_type: str
    lang: str
    doc_code: str
    options: Dict


class _Worker(QObject):
    done   = Signal(dict)
    failed = Signal(str)

    def __init__(self, trx_id: int, trx_no: str, jobs: List[_JobSpec],
                 shared_doc_no: str | None = None):
        super().__init__()
        self.trx_id        = trx_id
        self.trx_no        = trx_no
        self.jobs          = jobs
        self.shared_doc_no = shared_doc_no

    def run(self):
        try:
            from services import render_document, check_pdf_runtime

            report = check_pdf_runtime()
            force_html_only = not (report.weasyprint_stack or report.playwright)

            files = []
            for j in self.jobs:
                res = render_document(
                    transaction_id  = self.trx_id,
                    transaction_no  = self.trx_no,
                    doc_code        = j.doc_code,
                    lang            = j.lang,
                    force_html_only = force_html_only,
                    explicit_doc_no = self.shared_doc_no,
                )
                out_path = str(res.out_pdf or res.out_html)
                files.append({"doc_type": j.doc_type, "language": j.lang, "path": out_path})

            self.done.emit({"files": files, "html_only": force_html_only})
        except Exception as e:
            self.failed.emit(str(e))


# =============================================================================
# Results Dialog
# =============================================================================
class _ResultsDialog(QDialog):
    def __init__(self, files: List[dict], html_only: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("generated_files"))
        self.setMinimumWidth(580)
        v = QVBoxLayout(self)
        v.setSpacing(10)
        v.setContentsMargins(14, 14, 14, 14)

        if html_only:
            hint = QLabel(_("pdf_runtime_missing_html_only"))
            hint.setWordWrap(True)
            hint.setObjectName("warning-label")
            v.addWidget(hint)

        lbl = QLabel(f"✅  {_('done')} — {len(files)} {_('document_type')}")
        lbl.setObjectName("section-title")
        v.addWidget(lbl)

        self.listw = QListWidget()
        self.listw.setAlternatingRowColors(True)
        self.listw.setMinimumHeight(140)
        for f in files:
            fname = os.path.basename(f.get("path", ""))
            label = f"📄  {f.get('doc_type','?')} | {f.get('language','?').upper()}   →  {fname}"
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, f.get("path", ""))
            it.setToolTip(f.get("path", ""))
            self.listw.addItem(it)
        if self.listw.count():
            self.listw.setCurrentRow(0)
        v.addWidget(self.listw)

        btns = QHBoxLayout()
        self.btn_open        = QPushButton("📂  " + _("open_file"))
        self.btn_open_folder = QPushButton("🗂  " + _("open_folder"))
        self.btn_close       = QPushButton(_("close"))
        self.btn_open.setObjectName("primary-btn")
        self.btn_open_folder.setObjectName("secondary-btn")
        btns.addWidget(self.btn_open)
        btns.addWidget(self.btn_open_folder)
        btns.addStretch()
        btns.addWidget(self.btn_close)
        v.addLayout(btns)

        self.btn_open.clicked.connect(self._open_selected)
        self.btn_open_folder.clicked.connect(self._open_folder)
        self.btn_close.clicked.connect(self.accept)
        self.listw.itemDoubleClicked.connect(self._open_item)

    def _open_item(self, it: QListWidgetItem):
        path = it.data(Qt.UserRole)
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _open_selected(self):
        it = self.listw.currentItem()
        if it:
            self._open_item(it)

    def _open_folder(self):
        it = self.listw.currentItem()
        if not it:
            return
        path = it.data(Qt.UserRole)
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))


# =============================================================================
# Main Generation Dialog — v3  (+ CMR / Form A)
# =============================================================================
class GenerateDocumentDialog(QDialog):
    """
    حوار توليد المستندات — الإصدار الثالث:
    - يدعم الفواتير + قوائم التعبئة + CMR + شهادة المنشأ (Form A)
    """

    def __init__(
        self,
        transaction_id: int,
        transaction_no: str,
        parent=None,
        preselected_doc_types: Optional[List[int]] = None,
        preselected_doc_codes: Optional[List[str]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(_("generate_documents"))
        self.setMinimumWidth(480)
        self.trx_id   = transaction_id
        self.trx_no   = transaction_no
        self._thread: QThread | None = None
        self._preselected       = preselected_doc_types or []
        self._preselected_codes = preselected_doc_codes or []

        try:
            self._lang = TranslationManager.get_instance().get_current_language()
        except Exception:
            self._lang = "ar"

        self._doc_lang_default  = self._get_documents_language()
        self._output_path_default = self._get_output_path()

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # ── 1) أنواع المستندات ────────────────────────────────────────
        types_box = QGroupBox(_("document_types"))
        hb_types  = QHBoxLayout(types_box)

        self.chk_invoice   = QCheckBox(_("invoice"))
        self.chk_packing   = QCheckBox(_("packing_list"))
        self.chk_cmr       = QCheckBox("CMR")
        self.chk_forma     = QCheckBox(_("form_a_certificate"))   # "شهادة المنشأ"

        self.chk_invoice.setChecked(True)

        hb_types.addWidget(self.chk_invoice)
        hb_types.addWidget(self.chk_packing)
        hb_types.addWidget(self.chk_cmr)
        hb_types.addWidget(self.chk_forma)
        layout.addWidget(types_box)

        # ── 2) اللغات ────────────────────────────────────────────────
        langs_box = QGroupBox(_("languages"))
        grid = QGridLayout(langs_box)
        self.chk_lang_all = QCheckBox(_("select_all"))
        self.chk_lang_ar  = QCheckBox("العربية")
        self.chk_lang_en  = QCheckBox("English")
        self.chk_lang_tr  = QCheckBox("Türkçe")
        self._apply_default_lang()
        grid.addWidget(self.chk_lang_all, 0, 0, 1, 3)
        grid.addWidget(self.chk_lang_ar,  1, 0)
        grid.addWidget(self.chk_lang_en,  1, 1)
        grid.addWidget(self.chk_lang_tr,  1, 2)
        layout.addWidget(langs_box)
        self.chk_lang_all.toggled.connect(self._toggle_all_langs)

        # ── 3) نوع الفاتورة ───────────────────────────────────────────
        layout.addWidget(QLabel(_("invoice_type")))
        self.cmb_invoice_type = QComboBox()
        self.cmb_invoice_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.cmb_invoice_type)

        # ── 4) نوع قائمة التعبئة ──────────────────────────────────────
        layout.addWidget(QLabel(_("packing_list_type")))
        self.cmb_pl_type = QComboBox()
        self.cmb_pl_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.cmb_pl_type)

        # ── 5) نوع CMR ────────────────────────────────────────────────
        self.lbl_cmr_type = QLabel("CMR — " + _("consignment_note"))
        layout.addWidget(self.lbl_cmr_type)
        self.cmb_cmr_type = QComboBox()
        self.cmb_cmr_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.cmb_cmr_type)

        # ── 6) نوع Form A ─────────────────────────────────────────────
        self.lbl_forma_type = QLabel(_("form_a_certificate") + " (GSP)")
        layout.addWidget(self.lbl_forma_type)
        self.cmb_forma_type = QComboBox()
        self.cmb_forma_type.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.cmb_forma_type)

        # ربط الـ visibility بالـ checkboxes
        self.chk_invoice.toggled.connect(lambda v: (
            self.cmb_invoice_type.setVisible(v)
        ))
        self.chk_packing.toggled.connect(lambda v: (
            self.cmb_pl_type.setVisible(v)
        ))
        self.chk_cmr.toggled.connect(lambda v: (
            self.lbl_cmr_type.setVisible(v),
            self.cmb_cmr_type.setVisible(v),
        ))
        self.chk_forma.toggled.connect(lambda v: (
            self.lbl_forma_type.setVisible(v),
            self.cmb_forma_type.setVisible(v),
        ))
        # حالة أولية
        self.lbl_cmr_type.setVisible(False)
        self.cmb_cmr_type.setVisible(False)
        self.lbl_forma_type.setVisible(False)
        self.cmb_forma_type.setVisible(False)

        self._load_document_types_from_db()
        self._apply_preselected()

        # ── 7) مسار الحفظ ─────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        layout.addWidget(QLabel(_("documents_output_path")))
        path_row = QHBoxLayout()
        self.txt_output_path = QLineEdit()
        self.txt_output_path.setPlaceholderText(_("default_output_path_hint"))
        self.txt_output_path.setText(self._output_path_default)
        self.btn_browse = QPushButton(_("browse"))
        self.btn_browse.setObjectName("secondary-btn")
        self.btn_browse.setFixedWidth(80)
        path_row.addWidget(self.txt_output_path)
        path_row.addWidget(self.btn_browse)
        layout.addLayout(path_row)
        self.btn_browse.clicked.connect(self._browse_path)

        # ── 8) شريط التقدم ────────────────────────────────────────────
        self.progress   = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.lbl_status = QLabel("")
        self.lbl_status.setVisible(False)
        self.lbl_status.setObjectName("status-label")
        layout.addWidget(self.lbl_status)

        # ── 9) الأزرار ────────────────────────────────────────────────
        btns = QHBoxLayout()
        self.btn_generate = QPushButton("▶  " + _("generate"))
        self.btn_cancel   = QPushButton(_("cancel"))
        self.btn_generate.setObjectName("primary-btn")
        self.btn_generate.setMinimumHeight(38)
        btns.addWidget(self.btn_generate)
        btns.addStretch()
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_cancel.clicked.connect(self._on_cancel)

    # =========================================================================
    # Settings helpers
    # =========================================================================
    def _get_documents_language(self) -> str:
        try:
            from core.settings_manager import SettingsManager
            lang = SettingsManager.get_instance().get("documents_language", "ar")
            return lang if lang in ("ar", "en", "tr") else "ar"
        except Exception:
            return "ar"

    def _get_output_path(self) -> str:
        try:
            from core.settings_manager import SettingsManager
            return SettingsManager.get_instance().get_documents_output_path() or ""
        except Exception:
            return ""

    def _apply_default_lang(self):
        lang = self._doc_lang_default
        self.chk_lang_ar.setChecked(lang == "ar")
        self.chk_lang_en.setChecked(lang == "en")
        self.chk_lang_tr.setChecked(lang == "tr")

    # =========================================================================
    # تحميل أنواع المستندات من DB
    # =========================================================================
    def _load_document_types_from_db(self) -> None:
        try:
            from database.crud.document_types_crud import DocumentTypesCRUD
            all_types = DocumentTypesCRUD().get_all_types()
        except Exception as e:
            logger.error("[GenerateDocumentDialog] DB fetch failed: %s", e)
            self._load_fallback_types()
            return

        invoices:   List[Tuple[str, str, int | None]] = []
        packings:   List[Tuple[str, str, int | None]] = []
        transports: List[Tuple[str, str, int | None]] = []
        origin_certs: List[Tuple[str, str, int | None]] = []

        for dt in all_types:
            if not getattr(dt, "is_active", 1):
                continue
            code     = getattr(dt, "code", "") or ""
            db_id    = getattr(dt, "id", None)
            doc_code = _DB_CODE_TO_DOC_CODE.get(code)
            if not doc_code:
                continue
            label    = self._doc_type_label(dt) or code
            category = _classify_doc_type(code)
            if category == "invoice":
                invoices.append((label, doc_code, db_id))
            elif category == "packing":
                packings.append((label, doc_code, db_id))
            elif category == "transport":
                transports.append((label, doc_code, db_id))
            elif category == "origin_cert":
                origin_certs.append((label, doc_code, db_id))

        self.cmb_invoice_type.clear()
        for label, dc, db_id in invoices:
            self.cmb_invoice_type.addItem(label, (dc, db_id))
        if not invoices:
            self._load_fallback_invoices()

        self.cmb_pl_type.clear()
        for label, dc, db_id in packings:
            self.cmb_pl_type.addItem(label, (dc, db_id))
        if not packings:
            self._load_fallback_packings()

        self.cmb_cmr_type.clear()
        for label, dc, db_id in transports:
            self.cmb_cmr_type.addItem(label, (dc, db_id))
        if not transports:
            self.cmb_cmr_type.addItem("CMR", ("cmr", None))

        self.cmb_forma_type.clear()
        for label, dc, db_id in origin_certs:
            self.cmb_forma_type.addItem(label, (dc, db_id))
        if not origin_certs:
            self.cmb_forma_type.addItem("Form A (GSP)", ("form_a", None))

    def _doc_type_label(self, dt) -> str:
        lang = self._lang
        if lang == "ar":
            return (getattr(dt, "name_ar", None) or getattr(dt, "name_en", None) or getattr(dt, "name_tr", None) or "")
        if lang == "tr":
            return (getattr(dt, "name_tr", None) or getattr(dt, "name_en", None) or getattr(dt, "name_ar", None) or "")
        return (getattr(dt, "name_en", None) or getattr(dt, "name_ar", None) or getattr(dt, "name_tr", None) or "")

    def _apply_preselected(self):
        has_invoice = has_packing = has_cmr = has_forma = False

        def _match_cmb(cmb: QComboBox, codes: list, ids: list) -> bool:
            for i in range(cmb.count()):
                data = cmb.itemData(i)
                code = data[0] if isinstance(data, tuple) else data
                db_id = data[1] if isinstance(data, tuple) else None
                if code in codes or (db_id is not None and db_id in ids):
                    cmb.setCurrentIndex(i)
                    return True
            return False

        if self._preselected_codes:
            has_invoice = _match_cmb(self.cmb_invoice_type, self._preselected_codes, [])
            has_packing = _match_cmb(self.cmb_pl_type,      self._preselected_codes, [])
            has_cmr     = _match_cmb(self.cmb_cmr_type,     self._preselected_codes, [])
            has_forma   = _match_cmb(self.cmb_forma_type,   self._preselected_codes, [])
        elif self._preselected:
            has_invoice = _match_cmb(self.cmb_invoice_type, [], self._preselected)
            has_packing = _match_cmb(self.cmb_pl_type,      [], self._preselected)
            has_cmr     = _match_cmb(self.cmb_cmr_type,     [], self._preselected)
            has_forma   = _match_cmb(self.cmb_forma_type,   [], self._preselected)

        if any([has_invoice, has_packing, has_cmr, has_forma]):
            self.chk_invoice.setChecked(has_invoice)
            self.chk_packing.setChecked(has_packing)
            self.chk_cmr.setChecked(has_cmr)
            self.chk_forma.setChecked(has_forma)
            # مزامنة الـ visibility
            self.lbl_cmr_type.setVisible(has_cmr)
            self.cmb_cmr_type.setVisible(has_cmr)
            self.lbl_forma_type.setVisible(has_forma)
            self.cmb_forma_type.setVisible(has_forma)

    # Fallbacks
    def _load_fallback_invoices(self) -> None:
        for label, doc_code in [
            ("External Invoice",       "invoice.foreign.commercial"),
            ("Normal Invoice",         "invoice.normal"),
            ("Proforma Invoice",       "invoice.proforma"),
            ("Syrian – Transit",       "invoice.syrian.transit"),
            ("Syrian – Intermediary",  "invoice.syrian.intermediary"),
            ("Syrian – Entry",         "invoice.syrian.entry"),
        ]:
            self.cmb_invoice_type.addItem(label, (doc_code, None))

    def _load_fallback_packings(self) -> None:
        for label, doc_code in [
            ("Simple",                        "packing_list.export.simple"),
            ("With Dates",                    "packing_list.export.with_dates"),
            ("With Container/Truck per line", "packing_list.export.with_line_id"),
        ]:
            self.cmb_pl_type.addItem(label, (doc_code, None))

    def _load_fallback_types(self) -> None:
        self.cmb_invoice_type.clear()
        self.cmb_pl_type.clear()
        self.cmb_cmr_type.clear()
        self.cmb_forma_type.clear()
        self._load_fallback_invoices()
        self._load_fallback_packings()
        self.cmb_cmr_type.addItem("CMR",         ("cmr",    None))
        self.cmb_forma_type.addItem("Form A (GSP)", ("form_a", None))

    # =========================================================================
    # UI helpers
    # =========================================================================
    def _toggle_all_langs(self, checked: bool):
        self.chk_lang_ar.setChecked(checked)
        self.chk_lang_en.setChecked(checked)
        self.chk_lang_tr.setChecked(checked)

    def _browse_path(self):
        folder = QFileDialog.getExistingDirectory(
            self, _("browse"),
            self.txt_output_path.text().strip() or os.path.expanduser("~"),
        )
        if folder:
            self.txt_output_path.setText(folder)

    def _selected(self) -> Tuple[List[str], List[str]]:
        types = []
        if self.chk_invoice.isChecked(): types.append("invoice")
        if self.chk_packing.isChecked(): types.append("packing_list")
        if self.chk_cmr.isChecked():     types.append("cmr")
        if self.chk_forma.isChecked():   types.append("origin_cert")
        langs = []
        if self.chk_lang_ar.isChecked(): langs.append("ar")
        if self.chk_lang_en.isChecked(): langs.append("en")
        if self.chk_lang_tr.isChecked(): langs.append("tr")
        return types, langs

    @staticmethod
    def _compat_doc_code(code: str) -> str:
        if code == "invoice.commercial":
            return "invoice.foreign.commercial"
        return code

    def _get_doc_code(self, cmb: QComboBox) -> str | None:
        data = cmb.currentData()
        if isinstance(data, tuple):
            return data[0]
        return data

    def _build_jobs(self, types: List[str], langs: List[str]) -> List[_JobSpec]:
        jobs: List[_JobSpec] = []
        inv_code   = self._get_doc_code(self.cmb_invoice_type)
        pl_code    = self._get_doc_code(self.cmb_pl_type)
        cmr_code   = self._get_doc_code(self.cmb_cmr_type)
        forma_code = self._get_doc_code(self.cmb_forma_type)

        for t in types:
            if t == "invoice":
                if not inv_code:
                    raise ValueError(_("please_select_invoice_type"))
                code = self._compat_doc_code(inv_code)
            elif t == "packing_list":
                if not pl_code:
                    raise ValueError(_("please_select_packing_list_type"))
                code = pl_code
            elif t == "cmr":
                code = cmr_code or "cmr"
            elif t == "origin_cert":
                code = forma_code or "form_a"
            else:
                continue
            for lg in langs:
                jobs.append(_JobSpec(doc_type=t, lang=lg, doc_code=code, options={}))
        return jobs

    # =========================================================================
    # Precheck
    # =========================================================================
    def _precheck_transaction_requirements(self, doc_codes: list) -> List[str]:
        from sqlalchemy import text as _sql
        from database.models import get_session_local as _gs

        warnings: List[str] = []
        s = _gs()()
        try:
            t = s.execute(_sql(
                "SELECT id, delivery_method_id FROM transactions WHERE id=:i"
            ), {"i": int(self.trx_id)}).mappings().first()

            if not t:
                raise ValueError(_("transaction_not_found"))

            if t["delivery_method_id"] is None:
                warnings.append("⚠  " + _("transaction_missing_delivery"))

            rows = s.execute(_sql(
                "SELECT id, currency_id, pricing_type_id, packaging_type_id, unit_price "
                "FROM transaction_items WHERE transaction_id=:tid"
            ), {"tid": int(self.trx_id)}).mappings().all()

            if not rows:
                raise ValueError(_("transaction_has_no_items"))

            # CMR / Form A لا تحتاج سعراً — أسقط تحذيرات السعر لها
            is_transport_only = all(
                c in ("cmr", "form_a") for c in doc_codes
            )

            currencies   = set()
            missing_price = []
            for r in rows:
                if r["currency_id"] is None and not is_transport_only:
                    warnings.append("⚠  " + _("row_missing_currency").format(id=r["id"]))
                else:
                    currencies.add(r["currency_id"])
                if r["pricing_type_id"] is None and not is_transport_only:
                    warnings.append("⚠  " + _("row_missing_pricing").format(id=r["id"]))
                if r["packaging_type_id"] is None:
                    warnings.append("⚠  " + _("row_missing_packaging").format(id=r["id"]))
                if r["unit_price"] in (None, 0) and not is_transport_only:
                    missing_price.append(str(r["id"]))

            if missing_price:
                warnings.append("⚠  " + _("row_missing_price").format(id=", ".join(missing_price[:5])))

            if len(currencies) > 1:
                warnings.append("⚠  " + _("multiple_currencies_not_supported"))

            # تحذير خاص بـ CMR: هل يوجد transport_details؟
            if any(c == "cmr" for c in doc_codes):
                td = s.execute(_sql(
                    "SELECT truck_plate, carrier_company_id FROM transport_details WHERE transaction_id=:i"
                ), {"i": int(self.trx_id)}).mappings().first()
                if not td or not td.get("truck_plate"):
                    warnings.append("⚠  " + _("cmr_truck_plate_missing"))
                if not td or not td.get("carrier_company_id"):
                    warnings.append("⚠  " + _("cmr_carrier_missing"))

            # تحذير خاص بـ Form A: هل يوجد certificate_no؟
            if any(c == "form_a" for c in doc_codes):
                td2 = s.execute(_sql(
                    "SELECT certificate_no FROM transport_details WHERE transaction_id=:i"
                ), {"i": int(self.trx_id)}).mappings().first()
                if not td2 or not td2.get("certificate_no"):
                    warnings.append("⚠  " + _("form_a_certificate_no_missing"))

        finally:
            s.close()

        return warnings

    # =========================================================================
    # Actions
    # =========================================================================
    def _on_generate(self):
        types, langs = self._selected()
        if not types or not langs:
            QMessageBox.warning(self, _("warning"), _("select_at_least_one"))
            return

        try:
            jobs = self._build_jobs(types, langs)
        except ValueError as e:
            QMessageBox.warning(self, _("warning"), str(e))
            return

        try:
            unique_codes = sorted({j.doc_code for j in jobs})
            warnings = self._precheck_transaction_requirements(unique_codes)
        except ValueError as e:
            QMessageBox.critical(self, _("error"), str(e))
            return
        except Exception as e:
            logger.warning("precheck failed: %s", e)
            warnings = []

        if warnings:
            reply = QMessageBox.question(
                self,
                _("precheck_warnings_title"),
                "\n".join(warnings) + "\n\n" + _("proceed_despite_warnings"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        from services.persist_generated_doc import allocate_group_doc_no
        prefix = "INVPL" if len(types) > 1 else (
            "INV" if "invoice" in types else (
            "CMR" if "cmr" in types else (
            "FA"  if "origin_cert" in types else "PL")))
        try:
            shared_no = allocate_group_doc_no(self.trx_id, prefix=prefix)
        except Exception:
            shared_no = None

        output_path = self.txt_output_path.text().strip()
        if output_path:
            try:
                from core.settings_manager import SettingsManager
                SettingsManager.get_instance().set_documents_output_path(output_path)
            except Exception as e:
                logger.warning("Could not save output path to settings: %s", e)

        self._thread = QThread(self)
        self._worker = _Worker(
            self.trx_id, self.trx_no, jobs,
            shared_doc_no=shared_no,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.done.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)

        self.btn_generate.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(True)
        self.lbl_status.setText(_("documents_are_being_generated_please_wait"))
        self.lbl_status.setVisible(True)
        self._thread.start()

    def _on_done(self, result: dict):
        self.progress.setVisible(False)
        self.lbl_status.setVisible(False)
        files     = result.get("files", [])
        html_only = result.get("html_only", False)
        if not files:
            QMessageBox.information(self, _("done"), _("nothing_generated"))
            return
        _ResultsDialog(files, html_only, self).exec()

    def _on_failed(self, err: str):
        self.progress.setVisible(False)
        self.lbl_status.setVisible(False)
        QMessageBox.critical(self, _("error"), err)

    def _on_thread_finished(self):
        self.btn_generate.setEnabled(True)
        self.btn_cancel.setEnabled(True)

    def _on_cancel(self):
        if self._thread and self._thread.isRunning():
            QMessageBox.information(
                self, _("please_wait"),
                _("documents_are_being_generated_please_wait"),
            )
            return
        self.reject()