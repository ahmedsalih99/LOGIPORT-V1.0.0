"""
ui/widgets/pdf_preview_dialog.py — LOGIPORT
=============================================
نافذة معاينة PDF/HTML داخل التطبيق — المرحلة 3.

الاستخدام:
    dlg = PdfPreviewDialog(html_path=".../doc.html", pdf_path=".../doc.pdf", parent=self)
    dlg.exec()

    # أو من HTML string مباشرة:
    dlg = PdfPreviewDialog(html_string="<html>...</html>", base_url="/path/to/static", parent=self)
    dlg.exec()

المحرّك:
    - QtWebEngineWidgets لعرض HTML (الأسرع والأموثق)
    - fallback: رسالة خطأ مع زر "فتح خارجي"

الأزرار:
    - طباعة  → QWebEngineView.page().print() عبر printer dialog
    - حفظ نسخة  → QFileDialog لاختيار مكان الحفظ
    - فتح خارجي  → QDesktopServices
"""
from __future__ import annotations

import os
import shutil
import logging
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QWidget, QSizePolicy, QFileDialog, QMessageBox,
    QProgressBar,
)

logger = logging.getLogger(__name__)


def _has_webengine() -> bool:
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa
        return True
    except Exception:
        return False


from core.base_dialog import BaseDialog

class PdfPreviewDialog(BaseDialog):
    """
    نافذة معاينة مستند داخلية.

    المعاملات:
        html_path   : مسار ملف HTML المولَّد (للعرض)
        pdf_path    : مسار ملف PDF (للطباعة والحفظ)
        html_string : HTML كنص مباشر (بديل عن html_path)
        base_url    : مسار المجلد لتحميل الموارد (CSS/fonts)
        title       : عنوان النافذة
    """

    def __init__(
        self,
        html_path: str | None = None,
        pdf_path:  str | None = None,
        html_string: str | None = None,
        base_url: str | None = None,
        title: str = "",
        parent=None,
    ):
        super().__init__(parent)
        try:
            from core.translator import TranslationManager
            self._ = TranslationManager.get_instance().translate
        except Exception:
            self._ = lambda k: k

        self._html_path   = html_path
        self._pdf_path    = pdf_path
        self._html_string = html_string
        self._base_url    = base_url
        self._doc_title   = title or self._("pdf_preview_title")

        self._view = None   # QWebEngineView (if available)

        self.setWindowTitle(self._("pdf_preview_title"))
        self.setMinimumSize(820, 680)
        self.resize(920, 760)
        self.setModal(True)

        # ESC يغلق
        esc = QShortcut(QKeySequence("Escape"), self)
        esc.activated.connect(self.reject)

        self._build_ui()
        self._load_content()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── شريط الأدوات ───────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setObjectName("form-dialog-header")
        toolbar.setFixedHeight(52)
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(16, 8, 16, 8)
        bar.setSpacing(8)

        # عنوان المستند
        self._title_lbl = QLabel(self._doc_title)
        from PySide6.QtGui import QFont
        f = QFont("Tajawal", 11)
        f.setBold(True)
        self._title_lbl.setFont(f)
        self._title_lbl.setObjectName("form-dialog-title")
        bar.addWidget(self._title_lbl)
        bar.addStretch()

        # أزرار
        self._btn_print = self._make_btn("🖨️  " + self._("pdf_preview_print"), "primary-btn")
        self._btn_save  = self._make_btn("💾  " + self._("pdf_preview_save"),  "secondary-btn")
        self._btn_ext   = self._make_btn("📂  " + self._("pdf_preview_open_ext"), "secondary-btn")
        self._btn_close = self._make_btn("✕  " + self._("close"), "secondary-btn")

        for btn in (self._btn_print, self._btn_save, self._btn_ext, self._btn_close):
            bar.addWidget(btn)

        self._btn_print.clicked.connect(self._on_print)
        self._btn_save.clicked.connect(self._on_save)
        self._btn_ext.clicked.connect(self._on_open_ext)
        self._btn_close.clicked.connect(self.reject)

        root.addWidget(toolbar)

        # separator
        from PySide6.QtWidgets import QFrame
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        root.addWidget(sep)

        # ── منطقة المحتوى ──────────────────────────────────────────────────
        self._content_area = QWidget()
        content_lay = QVBoxLayout(self._content_area)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)

        # Progress bar (تحميل)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setMaximumHeight(3)
        self._progress.setTextVisible(False)
        self._progress.setObjectName("loading-bar")
        content_lay.addWidget(self._progress)

        if _has_webengine():
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self._view = QWebEngineView()
            self._view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._view.loadFinished.connect(self._on_load_finished)
            self._view.loadStarted.connect(lambda: self._progress.setVisible(True))
            content_lay.addWidget(self._view)
        else:
            # fallback: رسالة نصية
            self._no_engine_label = QLabel(self._("pdf_preview_no_engine"))
            self._no_engine_label.setAlignment(Qt.AlignCenter)
            self._no_engine_label.setObjectName("text-muted")
            content_lay.addWidget(self._no_engine_label)
            self._btn_print.setEnabled(False)

        root.addWidget(self._content_area, 1)

        self._apply_style()

    def _make_btn(self, text: str, obj_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setMinimumHeight(34)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _apply_style(self):
        try:
            from core.settings_manager import SettingsManager
            from config.themes import ThemeBuilder
            theme_name = SettingsManager.get_instance().get("theme", "light")
            theme = ThemeBuilder(theme_name)
            c = theme.colors
            bg      = c.get("bg_card", "#FFFFFF")
            toolbar_bg = c.get("bg_secondary", "#F8F9FA")
            border  = c.get("border", "#E0E0E0")
        except Exception:
            bg = "#FFFFFF"; toolbar_bg = "#F8F9FA"; border = "#E0E0E0"

        self.setStyleSheet(f"""
            /* toolbar now uses form-dialog-header CSS from theme */
            QLabel#form-dialog-title {{
                color: #ffffff;
                font-weight: 700;
            }}
            QProgressBar#loading-bar {{
                border: none;
                background: transparent;
            }}
            QProgressBar#loading-bar::chunk {{
                background: #2563EB;
            }}
        """)

    # ─── Content Loading ──────────────────────────────────────────────────────

    def _load_content(self):
        if not self._view:
            return

        if self._html_string:
            # عرض HTML string مباشرة
            if self._base_url:
                from PySide6.QtCore import QUrl
                base = QUrl.fromLocalFile(str(Path(self._base_url).resolve()) + "/")
                self._view.setHtml(self._html_string, base)
            else:
                self._view.setHtml(self._html_string)

        elif self._html_path and Path(self._html_path).exists():
            url = QUrl.fromLocalFile(str(Path(self._html_path).resolve()))
            self._view.load(url)

        elif self._pdf_path and Path(self._pdf_path).exists():
            # PDF — نحمّله مباشرة (WebEngine يدعم PDF natively)
            url = QUrl.fromLocalFile(str(Path(self._pdf_path).resolve()))
            self._view.load(url)

        else:
            if self._view:
                self._view.setHtml(
                    f"<html><body style='font-family:Tajawal;text-align:center;padding:60px'>"
                    f"<p style='color:#6B7280'>{self._('pdf_preview_no_engine')}</p></body></html>"
                )

    def _on_load_finished(self, ok: bool):
        self._progress.setVisible(False)
        if not ok:
            logger.warning("PdfPreviewDialog: page load failed")

    # ─── Actions ─────────────────────────────────────────────────────────────

    def _on_print(self):
        """طباعة عبر print dialog."""
        if not self._view:
            return
        try:
            from PySide6.QtPrintSupport import QPrinter, QPrintDialog
            printer = QPrinter(QPrinter.HighResolution)
            dialog  = QPrintDialog(printer, self)
            if dialog.exec() == QPrintDialog.Accepted:
                self._view.page().print(printer, lambda ok: None)
        except Exception as e:
            # Fallback: فتح PDF خارجياً للطباعة
            logger.warning(f"Print dialog failed: {e}")
            self._on_open_ext()

    def _on_save(self):
        """حفظ نسخة من الملف."""
        # نفضّل PDF، ثم HTML
        source = self._pdf_path or self._html_path
        if not source or not Path(source).exists():
            QMessageBox.warning(self, self._("warning"), self._("file_missing"))
            return

        ext  = Path(source).suffix
        dest, _ = QFileDialog.getSaveFileName(
            self,
            self._("pdf_preview_save"),
            str(Path.home() / Path(source).name),
            f"{'PDF' if ext == '.pdf' else 'HTML'} (*{ext})",
        )
        if dest:
            try:
                shutil.copy2(source, dest)
            except Exception as e:
                QMessageBox.critical(self, self._("error"), str(e))

    def _on_open_ext(self):
        """فتح بالبرنامج الخارجي."""
        target = self._pdf_path or self._html_path
        if target and Path(target).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(target).resolve())))
        else:
            QMessageBox.warning(self, self._("warning"), self._("file_missing"))

    # ─── Update title ─────────────────────────────────────────────────────────

    def set_document_title(self, title: str):
        self._doc_title = title
        self._title_lbl.setText(title)
