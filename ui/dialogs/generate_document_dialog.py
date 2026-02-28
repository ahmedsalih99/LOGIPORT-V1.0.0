"""
GenerateDocumentDialog — v4  (Card-Based Design)
=================================================
تصميم جديد:
  - كل نوع مستند بطاقة قابلة للنقر (toggle card)
  - الخيارات الفرعية تظهر داخل البطاقة عند تفعيلها
  - اللغات كـ pill-buttons أفقية
  - CMR مخصوم من قائمة اللغات تلقائياً (English only)
  - مسار الحفظ في أعلى الفوتر بشكل واضح
"""
from __future__ import annotations
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import os

from PySide6.QtCore import Qt, QThread, Signal, QObject, QUrl, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QDesktopServices, QFont, QColor, QPalette
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox, QProgressBar, QLineEdit, QFileDialog,
    QFrame, QSizePolicy, QWidget, QScrollArea, QListWidget,
    QListWidgetItem,
)

import logging
logger = logging.getLogger(__name__)

try:
    from core.translator import TranslationManager
    _T = TranslationManager.get_instance()
    _ = _T.translate
except Exception:
    _ = lambda k: k

try:
    from core.base_dialog import BaseDialog as _BaseDialog
except Exception:
    from PySide6.QtWidgets import QDialog as _BaseDialog

# ── Mappings (نفس v3) ────────────────────────────────────────────────────────
_DB_CODE_TO_DOC_CODE: Dict[str, str] = {
    "INV_EXT":                "invoice.foreign.commercial",
    "INV_NORMAL":             "invoice.normal",
    "INV_PROFORMA":           "invoice.proforma",
    "INV_SYR_TRANS":          "invoice.syrian.transit",
    "INV_SYR_INTERM":         "invoice.syrian.intermediary",
    "INV_SYR_ENTRY":          "invoice.syrian.entry",
    "invoice.syrian.entry":   "invoice.syrian.entry",
    "PL_EXPORT_SIMPLE":       "packing_list.export.simple",
    "PL_EXPORT_WITH_DATES":   "packing_list.export.with_dates",
    "PL_EXPORT_WITH_LINE_ID": "packing_list.export.with_line_id",
    "cmr":                    "cmr",
    "form_a":                 "form_a",
}
_INVOICE_PREFIXES  = ("INV_", "invoice.")
_PACKING_PREFIXES  = ("PL_", "PACKING", "packing")
_TRANSPORT_CODES   = ("cmr",)
_ORIGIN_CERT_CODES = ("form_a", "form.a")

# doc codes that are always English-only (no language choice)
_ENGLISH_ONLY_CODES = frozenset({"cmr"})


def _classify_doc_type(code: str) -> str:
    cu = code.upper(); clo = code.lower()
    if any(cu.startswith(p.upper()) for p in _INVOICE_PREFIXES): return "invoice"
    if any(cu.startswith(p.upper()) for p in _PACKING_PREFIXES): return "packing"
    if clo in _TRANSPORT_CODES:   return "transport"
    if clo in _ORIGIN_CERT_CODES: return "origin_cert"
    return "other"


# =============================================================================
# Worker (نفس v3)
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

    def __init__(self, trx_id, trx_no, jobs, shared_doc_no=None):
        super().__init__()
        self.trx_id = trx_id; self.trx_no = trx_no
        self.jobs = jobs; self.shared_doc_no = shared_doc_no

    def run(self):
        try:
            from services import render_document, check_pdf_runtime
            report = check_pdf_runtime()
            force_html_only = not (report.weasyprint_stack or report.playwright)
            files = []
            for j in self.jobs:
                res = render_document(
                    transaction_id=self.trx_id, transaction_no=self.trx_no,
                    doc_code=j.doc_code, lang=j.lang,
                    force_html_only=force_html_only,
                    explicit_doc_no=self.shared_doc_no,
                )
                files.append({"doc_type": j.doc_type, "language": j.lang,
                               "path": str(res.out_pdf or res.out_html)})
            self.done.emit({"files": files, "html_only": force_html_only})
        except Exception as e:
            self.failed.emit(str(e))


# =============================================================================
# Results Dialog (محسّن بسيط)
# =============================================================================
class _ResultsDialog(QDialog):
    def __init__(self, files, html_only, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("generated_files"))
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        v.setSpacing(12); v.setContentsMargins(20, 20, 20, 20)

        # Header
        hdr = QLabel(f"✅  {_('done')} — {len(files)} {_('document_type')}")
        hdr.setObjectName("form-section-title")
        hdr_font = QFont(); hdr_font.setPointSize(13); hdr_font.setBold(True)
        hdr.setFont(hdr_font)
        v.addWidget(hdr)

        if html_only:
            warn = QLabel("⚠  " + _("pdf_runtime_missing_html_only"))
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #F39C12; background: rgba(243,156,18,0.1); "
                               "padding: 8px 12px; border-radius: 8px;")
            v.addWidget(warn)

        self.listw = QListWidget()
        self.listw.setAlternatingRowColors(True)
        self.listw.setMinimumHeight(160)
        self.listw.setFrameShape(QFrame.NoFrame)
        for f in files:
            fname = os.path.basename(f.get("path", ""))
            lang  = f.get("language", "").upper()
            dtype = f.get("doc_type", "?")
            it = QListWidgetItem(f"📄  {dtype}  [{lang}]   →   {fname}")
            it.setData(Qt.UserRole, f.get("path", ""))
            it.setToolTip(f.get("path", ""))
            self.listw.addItem(it)
        if self.listw.count():
            self.listw.setCurrentRow(0)
        v.addWidget(self.listw)

        btns = QHBoxLayout()
        btn_open   = QPushButton("📂  " + _("open_file"))
        btn_folder = QPushButton("🗂  " + _("open_folder"))
        btn_close  = QPushButton(_("close"))
        btn_open.setObjectName("primary-btn")
        btn_folder.setObjectName("secondary-btn")
        btn_open.setMinimumHeight(36); btn_folder.setMinimumHeight(36)
        btn_close.setMinimumHeight(36)
        btns.addWidget(btn_open); btns.addWidget(btn_folder)
        btns.addStretch(); btns.addWidget(btn_close)
        v.addLayout(btns)

        btn_open.clicked.connect(lambda: self._open(self.listw.currentItem()))
        btn_folder.clicked.connect(self._open_folder)
        btn_close.clicked.connect(self.accept)
        self.listw.itemDoubleClicked.connect(self._open)

    def _open(self, it):
        if it:
            QDesktopServices.openUrl(QUrl.fromLocalFile(it.data(Qt.UserRole)))

    def _open_folder(self):
        it = self.listw.currentItem()
        if it:
            QDesktopServices.openUrl(QUrl.fromLocalFile(
                os.path.dirname(it.data(Qt.UserRole))))


# =============================================================================
# DocCard — بطاقة مستند مع multi-select (checkboxes)
# =============================================================================
class _DocCard(QFrame):
    """
    بطاقة قابلة للنقر لنوع مستند.
    - Header: أيقونة + اسم + toggle
    - Body  : checkboxes للأنواع الفرعية (multi-select) إذا أكثر من خيار
              أو label ثابت إذا خيار واحد فقط
    """

    def __init__(self, icon: str, title: str, subtitle: str,
                 choices: List[Tuple[str, str]], english_only: bool = False,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("doc-card")
        self._enabled = False
        self._english_only = english_only
        self._choices = choices          # [(label, doc_code), ...]
        self._checkboxes: List = []      # QCheckBox instances
        self._build(icon, title, subtitle)

    def _build(self, icon, title, subtitle):
        from PySide6.QtWidgets import QCheckBox
        self.setMinimumHeight(56)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(0)

        # ── Header row ──────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(10)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setFixedSize(36, 36)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet(
            "background: rgba(74,126,200,0.12); border-radius: 18px; font-size: 17px;"
        )
        hdr.addWidget(self._icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        self._title_lbl = QLabel(title)
        title_f = QFont(); title_f.setBold(True); title_f.setPointSize(11)
        self._title_lbl.setFont(title_f)
        self._title_lbl.setObjectName("form-dialog-label")
        text_col.addWidget(self._title_lbl)

        if subtitle:
            self._sub_lbl = QLabel(subtitle)
            self._sub_lbl.setObjectName("form-dialog-subtitle")
            sub_f = QFont(); sub_f.setPointSize(9)
            self._sub_lbl.setFont(sub_f)
            text_col.addWidget(self._sub_lbl)
        hdr.addLayout(text_col, 1)

        # toggle button
        self._toggle = QPushButton("＋")
        self._toggle.setObjectName("secondary-btn")
        self._toggle.setFixedSize(34, 34)
        self._toggle.setCheckable(True)
        self._toggle.setCursor(Qt.PointingHandCursor)
        self._toggle.clicked.connect(self._on_toggle)
        hdr.addWidget(self._toggle)

        root.addLayout(hdr)

        # ── Body (hidden by default) ─────────────────────────────────────────
        self._body = QWidget()
        self._body.setVisible(False)
        body_lay = QVBoxLayout(self._body)
        body_lay.setContentsMargins(46, 8, 0, 4)
        body_lay.setSpacing(4)

        if len(self._choices) == 1:
            # خيار واحد: label ثابت بدون checkbox
            lbl = QLabel(self._choices[0][0])
            lbl.setStyleSheet("color: #555; font-size: 11px;")
            body_lay.addWidget(lbl)
            # checkbox داخلي غير مرئي نحتاجه لـ selected_codes
            cb = QCheckBox()
            cb.setChecked(True)
            cb.setProperty("doc_code", self._choices[0][1])
            cb.setVisible(False)
            body_lay.addWidget(cb)
            self._checkboxes.append(cb)
        else:
            # أكثر من خيار: checkbox لكل نوع — الأول محدد افتراضياً
            for idx, (label, code) in enumerate(self._choices):
                cb = QCheckBox(label)
                cb.setProperty("doc_code", code)
                cb.setChecked(idx == 0)   # الأول محدد افتراضياً
                cb.setCursor(Qt.PointingHandCursor)
                body_lay.addWidget(cb)
                self._checkboxes.append(cb)

        # تنبيه English-only
        if self._english_only:
            note = QLabel("🌐  English only — CMR is an international document")
            note.setStyleSheet("color: #3498DB; font-size: 11px;")
            body_lay.addWidget(note)

        root.addWidget(self._body)
        self._update_style()

    def _on_toggle(self, checked: bool):
        self._enabled = checked
        self._toggle.setText("✕" if checked else "＋")
        self._body.setVisible(checked)
        self._update_style()
        # notify parent dialog لإعادة حساب اللغات
        p = self.parent()
        while p:
            if hasattr(p, "_on_card_toggled"):
                p._on_card_toggled()
                break
            p = p.parent()

    def _update_style(self):
        if self._enabled:
            self.setStyleSheet("""
                QFrame#doc-card {
                    border: 2px solid #4A7EC8;
                    border-radius: 12px;
                    background: rgba(74,126,200,0.06);
                }
            """)
            self._icon_lbl.setStyleSheet(
                "background: rgba(74,126,200,0.25); border-radius: 18px; font-size: 17px;"
            )
        else:
            self.setStyleSheet("""
                QFrame#doc-card {
                    border: 1px solid #E0E0E0;
                    border-radius: 12px;
                    background: transparent;
                }
                QFrame#doc-card:hover { border-color: #4A7EC8; }
            """)
            self._icon_lbl.setStyleSheet(
                "background: rgba(74,126,200,0.08); border-radius: 18px; font-size: 17px;"
            )

    @property
    def is_active(self) -> bool:
        return self._enabled

    @property
    def selected_code(self) -> str:
        """أول كود محدد — للتوافق مع الكود القديم"""
        codes = self.selected_codes
        return codes[0] if codes else ""

    @property
    def selected_codes(self) -> List[str]:
        """كل الأكواد المحددة (checkboxes مفعّلة)"""
        return [
            cb.property("doc_code")
            for cb in self._checkboxes
            if cb.isChecked() and cb.property("doc_code")
        ]

    @property
    def english_only(self) -> bool:
        return self._english_only

    def set_active(self, active: bool):
        self._toggle.setChecked(active)
        self._on_toggle(active)


# =============================================================================
# LangPill — زر لغة pill
# =============================================================================
class _LangPill(QPushButton):
    def __init__(self, label: str, lang_code: str, parent=None):
        super().__init__(label, parent)
        self.lang_code = lang_code
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(34)
        self.setMinimumWidth(80)
        self._update_style()
        self.toggled.connect(lambda _: self._update_style())

    def _update_style(self):
        if self.isChecked():
            self.setStyleSheet("""
                QPushButton {
                    background: #4A7EC8; color: white; border: 2px solid #4A7EC8;
                    border-radius: 17px; font-weight: 700; font-size: 12px; padding: 0 16px;
                }
                QPushButton:hover { background: #5B8ED8; border-color: #5B8ED8; }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #495057;
                    border: 1.5px solid #CED4DA; border-radius: 17px;
                    font-weight: 500; font-size: 12px; padding: 0 16px;
                }
                QPushButton:hover { border-color: #4A7EC8; color: #4A7EC8; }
            """)


# =============================================================================
# Main Dialog — v4
# =============================================================================
class GenerateDocumentDialog(_BaseDialog):

    def __init__(self, transaction_id: int, transaction_no: str,
                 parent=None,
                 preselected_doc_types: Optional[List[int]] = None,
                 preselected_doc_codes: Optional[List[str]] = None):
        super().__init__(parent)
        self.setWindowTitle(_("generate_documents"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(480)
        # حجم افتراضي عند أول فتح — BaseDialog يحفظه تلقائياً بعدها
        try:
            if not self.settings.get(f"dialog_geometry_{self.__class__.__name__}"):
                self.resize(560, 640)
        except Exception:
            self.resize(560, 640)
        self.trx_id = transaction_id
        self.trx_no = transaction_no
        self._thread: QThread | None = None
        self._preselected       = preselected_doc_types or []
        self._preselected_codes = preselected_doc_codes or []

        try:
            self._ui_lang = TranslationManager.get_instance().get_current_language()
        except Exception:
            self._ui_lang = "ar"

        self._doc_lang_default    = self._get_documents_language()
        self._output_path_default = self._get_output_path()

        self._cards: List[_DocCard] = []
        self._lang_pills: List[_LangPill] = []

        self._build_ui()
        self._load_document_types_from_db()
        self._apply_preselected()
        self._apply_default_lang()

    # =========================================================================
    # UI Build
    # =========================================================================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr_w = QWidget()
        hdr_w.setObjectName("form-dialog-header")
        hdr_lay = QVBoxLayout(hdr_w)
        hdr_lay.setContentsMargins(22, 18, 22, 14)
        hdr_lay.setSpacing(2)
        t = QLabel(_("generate_documents"))
        t.setObjectName("form-dialog-title")
        tf = QFont(); tf.setPointSize(14); tf.setBold(True)
        t.setFont(tf)
        hdr_lay.addWidget(t)
        sub = QLabel(f"#{self.trx_no}")
        sub.setObjectName("form-dialog-subtitle")
        hdr_lay.addWidget(sub)
        sep0 = QFrame(); sep0.setFrameShape(QFrame.HLine)
        sep0.setObjectName("form-dialog-sep"); sep0.setFixedHeight(1)

        root.addWidget(hdr_w)
        root.addWidget(sep0)

        # ── Scrollable body ───────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("form-dialog-scroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        body_w = QWidget()
        body_w.setObjectName("form-dialog-body")
        body_lay = QVBoxLayout(body_w)
        body_lay.setContentsMargins(20, 18, 20, 10)
        body_lay.setSpacing(14)

        # ── Section title ─────────────────────────────────────────────────────
        sec1 = QLabel(_("select_documents_to_generate"))
        sec1.setObjectName("form-section-title")
        sf = QFont(); sf.setBold(True); sf.setPointSize(10)
        sec1.setFont(sf)
        body_lay.addWidget(sec1)

        # ── Two-column layout: يسار (فاتورة+تعبئة) | يمين (CMR+Form A+لغات) ──
        two_col = QHBoxLayout()
        two_col.setSpacing(14)

        # العمود الأيمن — المستندات الرئيسية
        left_col = QVBoxLayout()
        left_col.setSpacing(8)
        self._cards_layout = left_col   # ← invoice + packing يضافان هنا

        # العمود الأيسر — مستندات النقل + اللغات
        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        self._cards_layout_right = right_col  # ← CMR + Form A يضافان هنا

        # اللغات تحت العمود الأيسر
        sec2 = QLabel(_("languages"))
        sec2.setObjectName("form-section-title")
        sec2.setFont(sf)
        right_col.addWidget(sec2)

        self._lang_note = QLabel()
        self._lang_note.setObjectName("form-dialog-subtitle")
        self._lang_note.setVisible(False)
        right_col.addWidget(self._lang_note)

        pills_row = QHBoxLayout()
        pills_row.setSpacing(6)
        for code, label in [("ar", "🇸🇾 AR"), ("en", "🌐 EN"), ("tr", "🇹🇷 TR")]:
            pill = _LangPill(label, code)
            pills_row.addWidget(pill)
            self._lang_pills.append(pill)
        pills_row.addStretch()
        right_col.addLayout(pills_row)
        right_col.addStretch(1)

        two_col.addLayout(left_col, 1)

        # خط فاصل رأسي بين العمودين
        vline = QFrame()
        vline.setFrameShape(QFrame.VLine)
        vline.setObjectName("form-dialog-sep")
        two_col.addWidget(vline)

        two_col.addLayout(right_col, 1)
        body_lay.addLayout(two_col)

        body_lay.addStretch(1)
        scroll.setWidget(body_w)
        root.addWidget(scroll, 1)

        # ── Footer ────────────────────────────────────────────────────────────
        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("form-dialog-sep")
        root.addWidget(sep2)

        footer = QWidget()
        footer.setObjectName("form-dialog-footer")
        foot_lay = QVBoxLayout(footer)
        foot_lay.setContentsMargins(20, 14, 20, 16)
        foot_lay.setSpacing(10)

        # مسار الحفظ
        path_lbl = QLabel(_("documents_output_path"))
        path_lbl.setObjectName("form-dialog-label")
        foot_lay.addWidget(path_lbl)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.txt_output_path = QLineEdit()
        self.txt_output_path.setPlaceholderText(_("default_output_path_hint"))
        self.txt_output_path.setText(self._output_path_default)
        self.btn_browse = QPushButton("📁  " + _("browse"))
        self.btn_browse.setObjectName("secondary-btn")
        self.btn_browse.setMinimumHeight(36)
        self.btn_browse.setFixedWidth(110)
        path_row.addWidget(self.txt_output_path)
        path_row.addWidget(self.btn_browse)
        foot_lay.addLayout(path_row)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setMaximumHeight(4)
        foot_lay.addWidget(self.progress)

        self.lbl_status = QLabel()
        self.lbl_status.setObjectName("form-dialog-subtitle")
        self.lbl_status.setVisible(False)
        foot_lay.addWidget(self.lbl_status)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_generate = QPushButton("▶  " + _("generate"))
        self.btn_generate.setObjectName("primary-btn")
        self.btn_generate.setMinimumHeight(40)
        self.btn_cancel = QPushButton(_("cancel"))
        self.btn_cancel.setMinimumHeight(40)
        btn_row.addWidget(self.btn_generate, 1)
        btn_row.addWidget(self.btn_cancel)
        foot_lay.addLayout(btn_row)

        root.addWidget(footer)

        # Signals
        self.btn_browse.clicked.connect(self._browse_path)
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_cancel.clicked.connect(self._on_cancel)

    # =========================================================================
    # Card creation
    # =========================================================================
    def _add_card(self, icon, title, subtitle, choices,
                  english_only=False, right_col=False) -> _DocCard:
        """إضافة بطاقة — right_col=True لوضعها في العمود الأيسر (CMR / Form A)"""
        card = _DocCard(icon, title, subtitle, choices, english_only, parent=self)
        layout = getattr(self, '_cards_layout_right', self._cards_layout) if right_col else self._cards_layout
        layout.addWidget(card)
        self._cards.append(card)
        return card

    # =========================================================================
    # Load from DB
    # =========================================================================
    def _load_document_types_from_db(self):
        try:
            from database.crud.document_types_crud import DocumentTypesCRUD
            all_types = DocumentTypesCRUD().get_all_types()
        except Exception as e:
            logger.error("[GenerateDocumentDialog] DB fetch failed: %s", e)
            self._load_fallback_types()
            return

        invoices = []; packings = []; transports = []; origin_certs = []
        for dt in all_types:
            if not getattr(dt, "is_active", 1):
                continue
            code     = getattr(dt, "code", "") or ""
            doc_code = _DB_CODE_TO_DOC_CODE.get(code)
            if not doc_code:
                continue
            label    = self._doc_type_label(dt) or code
            category = _classify_doc_type(code)
            if category == "invoice":       invoices.append((label, doc_code))
            elif category == "packing":     packings.append((label, doc_code))
            elif category == "transport":   transports.append((label, doc_code))
            elif category == "origin_cert": origin_certs.append((label, doc_code))

        if not invoices:   self._load_fallback_invoices_list(invoices)
        if not packings:   self._load_fallback_packings_list(packings)
        if not transports: transports = [("CMR", "cmr")]
        if not origin_certs: origin_certs = [("Form A (GSP)", "form_a")]

        self._card_invoice   = self._add_card("🧾", _("invoice"),       _("invoice_type"),       invoices)
        self._card_packing   = self._add_card("📦", _("packing_list"),   _("packing_list_type"),  packings)
        self._card_cmr       = self._add_card("🚚", "CMR",               _("cmr_section_title"),  transports, english_only=True, right_col=True)
        self._card_forma     = self._add_card("📋", "Form A",            _("forma_section_title"), origin_certs, right_col=True)

    def _doc_type_label(self, dt) -> str:
        lang = self._ui_lang
        if lang == "ar": return (getattr(dt,"name_ar",None) or getattr(dt,"name_en",None) or getattr(dt,"name_tr",None) or "")
        if lang == "tr": return (getattr(dt,"name_tr",None) or getattr(dt,"name_en",None) or getattr(dt,"name_ar",None) or "")
        return (getattr(dt,"name_en",None) or getattr(dt,"name_ar",None) or getattr(dt,"name_tr",None) or "")

    def _load_fallback_invoices_list(self, lst):
        for label, code in [
            (_("invoice") + " — Commercial",       "invoice.foreign.commercial"),
            (_("invoice") + " — Normal",           "invoice.normal"),
            (_("invoice") + " — Proforma",         "invoice.proforma"),
            (_("invoice") + " — Syrian Transit",   "invoice.syrian.transit"),
            (_("invoice") + " — Syrian Entry",     "invoice.syrian.entry"),
            (_("invoice") + " — Intermediary",     "invoice.syrian.intermediary"),
        ]: lst.append((label, code))

    def _load_fallback_packings_list(self, lst):
        for label, code in [
            (_("packing_list") + " — Simple",        "packing_list.export.simple"),
            (_("packing_list") + " — With Dates",    "packing_list.export.with_dates"),
            (_("packing_list") + " — With Line ID",  "packing_list.export.with_line_id"),
        ]: lst.append((label, code))

    def _load_fallback_types(self):
        inv = []; pl = []
        self._load_fallback_invoices_list(inv)
        self._load_fallback_packings_list(pl)
        self._card_invoice = self._add_card("🧾", _("invoice"),     _("invoice_type"),      inv)
        self._card_packing = self._add_card("📦", _("packing_list"), _("packing_list_type"), pl)
        self._card_cmr     = self._add_card("🚚", "CMR",             _("cmr_section_title"), [("CMR", "cmr")], english_only=True, right_col=True)
        self._card_forma   = self._add_card("📋", "Form A",          _("forma_section_title"), [("Form A (GSP)", "form_a")], right_col=True)

    # =========================================================================
    # Preselected & defaults
    # =========================================================================
    def _apply_preselected(self):
        if not self._preselected_codes and not self._preselected:
            self._card_invoice.set_active(True)
            return

        def _check_and_activate(card, codes):
            """فعّل البطاقة وحدد الـ checkboxes المطلوبة"""
            card_codes = [cb.property("doc_code") for cb in card._checkboxes]
            matching = [c for c in card_codes if c in codes]
            if matching:
                card.set_active(True)
                # حدد فقط الأنواع المطلوبة
                for cb in card._checkboxes:
                    cb.setChecked(cb.property("doc_code") in codes)
                return True
            return False

        activated = any([
            _check_and_activate(self._card_invoice, self._preselected_codes),
            _check_and_activate(self._card_packing,  self._preselected_codes),
            _check_and_activate(self._card_cmr,      self._preselected_codes),
            _check_and_activate(self._card_forma,    self._preselected_codes),
        ])
        if not activated:
            self._card_invoice.set_active(True)

    def _apply_default_lang(self):
        lang = self._doc_lang_default
        for pill in self._lang_pills:
            pill.setChecked(pill.lang_code == lang)

    # =========================================================================
    # Card toggled → update lang pills visibility
    # =========================================================================
    def _on_card_toggled(self):
        """إذا CMR وحدها فعّالة → أخفي pills اللغة وأظهر ملاحظة"""
        active_cards = [c for c in self._cards if c.is_active]
        all_english_only = active_cards and all(c.english_only for c in active_cards)
        has_english_only = any(c.english_only for c in active_cards)
        has_multilang    = any(not c.english_only for c in active_cards)

        for pill in self._lang_pills:
            pill.setEnabled(not all_english_only)

        if all_english_only:
            self._lang_note.setText("🌐  CMR — English only (international standard)")
            self._lang_note.setVisible(True)
            for pill in self._lang_pills:
                pill.setChecked(pill.lang_code == "en")
        elif has_english_only and has_multilang:
            self._lang_note.setText("ℹ  CMR will be generated in English only")
            self._lang_note.setVisible(True)
        else:
            self._lang_note.setVisible(False)

    # =========================================================================
    # Settings helpers
    # =========================================================================
    def _get_documents_language(self) -> str:
        try:
            from core.settings_manager import SettingsManager
            lang = SettingsManager.get_instance().get("documents_language", "ar")
            return lang if lang in ("ar", "en", "tr") else "ar"
        except Exception: return "ar"

    def _get_output_path(self) -> str:
        try:
            from core.settings_manager import SettingsManager
            return SettingsManager.get_instance().get_documents_output_path() or ""
        except Exception: return ""

    def _browse_path(self):
        folder = QFileDialog.getExistingDirectory(
            self, _("browse"),
            self.txt_output_path.text().strip() or os.path.expanduser("~"))
        if folder:
            self.txt_output_path.setText(folder)

    # =========================================================================
    # Build jobs
    # =========================================================================
    def _build_jobs(self) -> List[_JobSpec]:
        active_cards = [c for c in self._cards if c.is_active]
        if not active_cards:
            raise ValueError(_("select_at_least_one"))

        selected_langs = [p.lang_code for p in self._lang_pills if p.isChecked()]
        if not selected_langs:
            raise ValueError(_("select_at_least_one"))

        jobs = []
        for card in active_cards:
            codes = card.selected_codes   # multi-select: قائمة بكل الأنواع المحددة
            if not codes:
                continue
            # CMR دائماً English فقط
            langs = ["en"] if card.english_only else selected_langs
            for code in codes:
                for lg in langs:
                    jobs.append(_JobSpec(
                        doc_type=code.split(".")[0],
                        lang=lg, doc_code=code, options={}))
        return jobs

    # =========================================================================
    # Precheck
    # =========================================================================
    def _precheck_transaction_requirements(self, doc_codes) -> List[str]:
        from sqlalchemy import text as _sql
        from database.models import get_session_local as _gs
        warnings = []
        s = _gs()()
        try:
            rows = s.execute(_sql(
                "SELECT id, currency_id, pricing_type_id, packaging_type_id, unit_price "
                "FROM transaction_items WHERE transaction_id=:tid"),
                {"tid": int(self.trx_id)}).mappings().all()
            if not rows: raise ValueError(_("transaction_has_no_items"))

            is_transport_only = all(c in ("cmr", "form_a") for c in doc_codes)
            # العملة per-item — لا نطلب currency_id على مستوى المعاملة
            missing_price = []
            for r in rows:
                if r["pricing_type_id"] is None and not is_transport_only:
                    warnings.append("⚠  " + _("row_missing_pricing").format(id=r["id"]))
                if r["packaging_type_id"] is None:
                    warnings.append("⚠  " + _("row_missing_packaging").format(id=r["id"]))
                if r["unit_price"] in (None, 0) and not is_transport_only:
                    missing_price.append(str(r["id"]))
            if missing_price:
                warnings.append("⚠  " + _("row_missing_price").format(id=", ".join(missing_price[:5])))

            if any(c == "cmr" for c in doc_codes):
                td = s.execute(_sql(
                    "SELECT truck_plate, carrier_company_id FROM transport_details WHERE transaction_id=:i"),
                    {"i": int(self.trx_id)}).mappings().first()
                if not td or not td.get("truck_plate"):
                    warnings.append("⚠  CMR: " + _("cmr_truck_plate_missing") if "cmr_truck_plate_missing" in dir() else "⚠  CMR: رقم لوحة الشاحنة غير موجود")
                if not td or not td.get("carrier_company_id"):
                    warnings.append("⚠  CMR: " + "شركة الناقل غير محددة")
            if any(c == "form_a" for c in doc_codes):
                td2 = s.execute(_sql(
                    "SELECT certificate_no FROM transport_details WHERE transaction_id=:i"),
                    {"i": int(self.trx_id)}).mappings().first()
                if not td2 or not td2.get("certificate_no"):
                    warnings.append("⚠  Form A: رقم الشهادة غير موجود")
        finally:
            s.close()
        return warnings

    # =========================================================================
    # Actions
    # =========================================================================
    def _on_generate(self):
        try:
            jobs = self._build_jobs()
        except ValueError as e:
            QMessageBox.warning(self, _("warning"), str(e)); return

        try:
            unique_codes = sorted({j.doc_code for j in jobs})
            warnings = self._precheck_transaction_requirements(unique_codes)
        except ValueError as e:
            QMessageBox.critical(self, _("error"), str(e)); return
        except Exception as e:
            logger.warning("precheck failed: %s", e); warnings = []

        if warnings:
            reply = QMessageBox.question(
                self, _("precheck_warnings_title"),
                "\n".join(warnings) + "\n\n" + _("proceed_despite_warnings"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes: return

        from services.persist_generated_doc import allocate_group_doc_no
        types_in_jobs = {j.doc_type for j in jobs}
        prefix = "INVPL" if len(types_in_jobs) > 1 else (
            "INV" if "invoice" in types_in_jobs else (
            "CMR" if "cmr"     in types_in_jobs else (
            "FA"  if "form_a"  in types_in_jobs else "PL")))
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
                logger.warning("Could not save output path: %s", e)

        self._thread = QThread(self)
        self._worker = _Worker(self.trx_id, self.trx_no, jobs, shared_doc_no=shared_no)
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

    def _on_done(self, result):
        self.progress.setVisible(False); self.lbl_status.setVisible(False)
        files = result.get("files", [])
        if not files:
            QMessageBox.information(self, _("done"), _("nothing_generated")); return
        _ResultsDialog(files, result.get("html_only", False), self).exec()

    def _on_failed(self, err):
        self.progress.setVisible(False); self.lbl_status.setVisible(False)
        QMessageBox.critical(self, _("error"), err)

    def _on_thread_finished(self):
        self.btn_generate.setEnabled(True); self.btn_cancel.setEnabled(True)

    def _on_cancel(self):
        if self._thread and self._thread.isRunning():
            QMessageBox.information(self, _("please_wait"),
                                    _("documents_are_being_generated_please_wait")); return
        self.reject()
