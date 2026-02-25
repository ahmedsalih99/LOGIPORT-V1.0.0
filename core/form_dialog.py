"""
FormDialog - LOGIPORT
=====================
Base class for all add/edit dialogs.

الميزات:
  - Header: عنوان + subtitle اختياري
  - Scrollable form body (QFormLayout)
  - Footer: أزرار Cancel + Save
  - إعادة ترجمة تلقائية عند تغيير اللغة — بدون أي كود في الـ subclass

كيف تعمل الترجمة التلقائية:
  - add_row(label_key, widget)  ← يحتفظ بـ label_key
  - add_section(title_key)      ← يحتفظ بـ title_key
  - عند تغيير اللغة → retranslate_ui() تُعيد ترجمة كل شيء تلقائياً

الـ subclass يمكنه دائماً تجاوز retranslate_ui() لو أراد سلوكاً مخصصاً.
"""
from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget, QScrollArea, QSizePolicy,
    QFormLayout, QLineEdit, QComboBox, QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.base_dialog import BaseDialog


class FormDialog(BaseDialog):
    """
    Unified form dialog with automatic retranslation on language change.

    Usage:
        class MyDialog(FormDialog):
            def __init__(self, parent=None):
                super().__init__(parent, title_key="my_dialog_title")
                self.name_field = QLineEdit()
                self.add_row("name_label_key", self.name_field)
    """

    def __init__(
        self,
        parent=None,
        title_key: str = "",        # مفتاح الترجمة للعنوان (يُترجم تلقائياً)
        subtitle_key: str = "",     # مفتاح الترجمة للـ subtitle (اختياري)
        title: str = "",            # نص ثابت للعنوان (للتوافق الخلفي)
        subtitle: str = "",         # نص ثابت للـ subtitle (للتوافق الخلفي)
        min_width: int = 440,
        save_key: str = "save",     # مفتاح ترجمة زر الحفظ (قابل للتخصيص)
        cancel_key: str = "cancel", # مفتاح ترجمة زر الإلغاء
    ):
        # نحتفظ بالمفاتيح قبل super().__init__ لأن _build_shell يحتاجها
        self._title_key_form    = title_key
        self._subtitle_key_form = subtitle_key
        self._title_static      = title       # توافق خلفي
        self._subtitle_static   = subtitle    # توافق خلفي
        self._min_width         = min_width
        self._save_key          = save_key
        self._cancel_key        = cancel_key

        # سجل الـ rows: قائمة من (QLabel | None, translation_key | None)
        # None = row بدون label (مثل spacer أو section)
        self._row_registry: list[_RowEntry] = []

        super().__init__(parent)
        self._build_shell()

    # ─────────────────────────────────────────────────────────────────────────
    # Shell
    # ─────────────────────────────────────────────────────────────────────────

    def _build_shell(self):
        self.setMinimumWidth(self._min_width)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        self._header = QWidget()
        self._header.setObjectName("form-dialog-header")
        h_lay = QVBoxLayout(self._header)
        h_lay.setContentsMargins(24, 20, 24, 16)
        h_lay.setSpacing(4)

        self._lbl_title = QLabel()
        self._lbl_title.setObjectName("form-dialog-title")
        font = QFont()
        font.setPointSize(14)
        font.setWeight(QFont.Bold)
        self._lbl_title.setFont(font)
        h_lay.addWidget(self._lbl_title)

        # subtitle — يُنشأ دائماً لكن يُخفى إذا لم يكن هناك نص
        self._lbl_subtitle = QLabel()
        self._lbl_subtitle.setObjectName("form-dialog-subtitle")
        self._lbl_subtitle.setVisible(False)
        h_lay.addWidget(self._lbl_subtitle)

        # separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("form-dialog-sep")
        sep.setFixedHeight(1)

        # ── Scroll area with form body ─────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("form-dialog-scroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._body = QWidget()
        self._body.setObjectName("form-dialog-body")
        self._form_layout = QFormLayout(self._body)
        self._form_layout.setContentsMargins(24, 20, 24, 20)
        self._form_layout.setSpacing(16)
        self._form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        scroll.setWidget(self._body)

        # ── Footer ────────────────────────────────────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("form-dialog-sep")
        sep2.setFixedHeight(1)

        footer = QWidget()
        footer.setObjectName("form-dialog-footer")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(24, 14, 24, 14)
        f_lay.setSpacing(10)
        f_lay.addStretch()

        self.btn_cancel = QPushButton()
        self.btn_cancel.setObjectName("secondary-btn")
        self.btn_cancel.setMinimumWidth(90)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton()
        self.btn_save.setObjectName("primary-btn")
        self.btn_save.setMinimumWidth(90)
        self.btn_save.clicked.connect(self.accept)

        f_lay.addWidget(self.btn_cancel)
        f_lay.addWidget(self.btn_save)

        # ── Assemble ──────────────────────────────────────────────────────
        root.addWidget(self._header)
        root.addWidget(sep)
        root.addWidget(scroll, 1)
        root.addWidget(sep2)
        root.addWidget(footer)

        # ترجمة أولية
        self.retranslate_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # Public helpers — add rows to form
    # ─────────────────────────────────────────────────────────────────────────

    def add_row(self, label_key: str, widget: QWidget) -> QWidget:
        """
        أضف row بـ label مترجم + widget.

        label_key: مفتاح الترجمة (مثل "arabic_name") أو نص ثابت.
        الـ label يُترجم تلقائياً عند تغيير اللغة.
        """
        lbl = QLabel()
        lbl.setObjectName("form-dialog-label")
        font = lbl.font()
        font.setWeight(QFont.DemiBold)
        lbl.setFont(font)
        self._form_layout.addRow(lbl, widget)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # سجّل للترجمة التلقائية
        self._row_registry.append(_RowEntry(kind="row", label=lbl, key=label_key))
        # ترجم فوراً
        lbl.setText(self._(label_key))

        return widget

    def add_spacer(self):
        """أضف مسافة بصرية بين أقسام الفورم."""
        spacer = QWidget()
        spacer.setFixedHeight(8)
        self._form_layout.addRow(spacer)
        self._row_registry.append(_RowEntry(kind="spacer"))

    def add_section(self, title_key: str):
        """
        أضف فاصل قسم بعنوان مترجم.
        title_key: مفتاح الترجمة أو نص ثابت.
        """
        sep_widget = QWidget()
        sep_lay = QVBoxLayout(sep_widget)
        sep_lay.setContentsMargins(0, 8, 0, 4)
        sep_lay.setSpacing(4)

        lbl = QLabel()
        lbl.setObjectName("form-section-title")
        f = lbl.font()
        f.setWeight(QFont.Bold)
        f.setPointSize(10)
        lbl.setFont(f)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("form-dialog-sep")

        sep_lay.addWidget(lbl)
        sep_lay.addWidget(line)
        self._form_layout.addRow(sep_widget)

        # سجّل للترجمة التلقائية
        self._row_registry.append(_RowEntry(kind="section", label=lbl, key=title_key))
        # ترجم فوراً
        lbl.setText(self._(title_key))

    # ─────────────────────────────────────────────────────────────────────────
    # Convenience setters (backward-compatible API)
    # ─────────────────────────────────────────────────────────────────────────

    def set_title(self, text: str):
        """
        ضع نصاً ثابتاً للعنوان (بدون ترجمة تلقائية).
        استخدم title_key في __init__ للترجمة التلقائية.
        """
        self._title_static = text
        self._title_key_form = ""   # يوقف الترجمة التلقائية للعنوان
        self._lbl_title.setText(text)

    def set_save_text(self, text: str):
        """
        ضع نصاً ثابتاً لزر الحفظ (بدون ترجمة تلقائية).
        استخدم save_key في __init__ للترجمة التلقائية.
        """
        self._save_key = ""   # يوقف الترجمة التلقائية للزر
        self.btn_save.setText(text)

    def set_title_key(self, key: str):
        """غيّر مفتاح ترجمة العنوان وطبّقه فوراً (مفيد لـ add/edit)."""
        self._title_key_form = key
        self._lbl_title.setText(self._(key))
        self.setWindowTitle(self._(key))

    def set_save_key(self, key: str):
        """غيّر مفتاح ترجمة زر الحفظ وطبّقه فوراً."""
        self._save_key = key
        self.btn_save.setText(self._(key))

    # ─────────────────────────────────────────────────────────────────────────
    # Retranslation — يُستدعى تلقائياً من BaseDialog عند تغيير اللغة
    # ─────────────────────────────────────────────────────────────────────────

    def retranslate_ui(self):
        """
        يُعيد ترجمة كل عناصر FormDialog تلقائياً.
        يُستدعى من BaseDialog._retranslate_ui() عند تغيير اللغة.
        الـ subclass يمكنه تجاوزه لكن يجب استدعاء super().retranslate_ui() أولاً.
        """
        # ── العنوان ──────────────────────────────────────────────────────
        if self._title_key_form:
            text = self._(self._title_key_form)
            self._lbl_title.setText(text)
            self.setWindowTitle(text)
        elif self._title_static:
            self._lbl_title.setText(self._title_static)

        # ── الـ subtitle ──────────────────────────────────────────────────
        if self._subtitle_key_form:
            text = self._(self._subtitle_key_form)
            self._lbl_subtitle.setText(text)
            self._lbl_subtitle.setVisible(bool(text))
        elif self._subtitle_static:
            self._lbl_subtitle.setText(self._subtitle_static)
            self._lbl_subtitle.setVisible(True)

        # ── أزرار Footer ──────────────────────────────────────────────────
        if self._save_key:
            self.btn_save.setText(self._(self._save_key))
        if self._cancel_key:
            self.btn_cancel.setText(self._(self._cancel_key))

        # ── كل الـ rows المسجّلة ──────────────────────────────────────────
        for entry in self._row_registry:
            if entry.label is not None and entry.key:
                entry.label.setText(self._(entry.key))


# ─────────────────────────────────────────────────────────────────────────────
# Internal data class — لتسجيل كل row مع مفتاحه
# ─────────────────────────────────────────────────────────────────────────────

class _RowEntry:
    """سجل داخلي يربط QLabel بمفتاح الترجمة."""
    __slots__ = ("kind", "label", "key")

    def __init__(
        self,
        kind: str,                      # "row" | "section" | "spacer"
        label: Optional[QLabel] = None,
        key: Optional[str] = None,
    ):
        self.kind  = kind
        self.label = label
        self.key   = key
