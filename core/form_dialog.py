"""
FormDialog - LOGIPORT
=====================
Base class for all add/edit dialogs.

الميزات:
  - Header: عنوان + subtitle اختياري
  - Scrollable form body (QFormLayout)
  - Footer: أزرار Cancel + Save
  - Inline validation: show_field_error / clear_field_error / clear_all_errors
  - إعادة ترجمة تلقائية عند تغيير اللغة — بدون أي كود في الـ subclass

كيف يعمل الـ inline validation:
  - add_row(..., required=True)          → يضيف * حمراء على الـ label
  - show_field_error(widget, "رسالة")   → يُلوّن border الحقل + يظهر النص تحته
  - clear_field_error(widget)            → يُعيد الحقل لوضعه الطبيعي
  - clear_all_errors()                   → يُنظف كل الأخطاء دفعة واحدة
  - validate_required(widget, key)       → True/False ويعرض الخطأ تلقائياً
  - validate_email(widget)               → True/False ويعرض الخطأ تلقائياً
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
    Unified form dialog with automatic retranslation and inline validation.

    Usage:
        class MyDialog(FormDialog):
            def __init__(self, parent=None):
                super().__init__(parent, title_key="my_dialog_title")
                self.name_field = QLineEdit()
                self.add_row("name_label_key", self.name_field, required=True)

            def accept(self):
                self.clear_all_errors()
                if not self.validate_required(self.name_field, "name_label_key"):
                    return
                super().accept()
    """

    def __init__(
        self,
        parent=None,
        title_key: str = "",
        subtitle_key: str = "",
        title: str = "",
        subtitle: str = "",
        min_width: int = 440,
        save_key: str = "save",
        cancel_key: str = "cancel",
        icon: str = "",          # emoji / unicode للأيقونة في الـ header
        icon_bg: str = "",       # لون خلفية الأيقونة (اختياري)
    ):
        self._title_key_form    = title_key
        self._subtitle_key_form = subtitle_key
        self._title_static      = title
        self._subtitle_static   = subtitle
        self._min_width         = min_width
        self._save_key          = save_key
        self._cancel_key        = cancel_key
        self._icon              = icon
        self._icon_bg           = icon_bg

        # سجل الـ rows للترجمة التلقائية
        self._row_registry: list[_RowEntry] = []

        # خريطة id(widget) → QLabel (رسالة الخطأ)
        self._error_labels: dict[int, QLabel] = {}

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

        # صف أفقي: أيقونة (اختياري) + عنوان/subtitle
        h_outer = QHBoxLayout(self._header)
        h_outer.setContentsMargins(24, 18, 24, 14)
        h_outer.setSpacing(12)

        # أيقونة contextual — تظهر فقط إذا أُعطيت
        self._header_icon_lbl = QLabel()
        self._header_icon_lbl.setObjectName("form-dialog-icon")
        self._header_icon_lbl.setFixedSize(36, 36)
        self._header_icon_lbl.setAlignment(Qt.AlignCenter)
        self._header_icon_lbl.setVisible(False)
        h_outer.addWidget(self._header_icon_lbl)

        # عمود: عنوان + subtitle
        h_text = QVBoxLayout()
        h_text.setSpacing(2)

        self._lbl_title = QLabel()
        self._lbl_title.setObjectName("form-dialog-title")
        font = QFont()
        font.setPointSize(13)
        font.setWeight(QFont.Bold)
        self._lbl_title.setFont(font)
        h_text.addWidget(self._lbl_title)

        self._lbl_subtitle = QLabel()
        self._lbl_subtitle.setObjectName("form-dialog-subtitle")
        self._lbl_subtitle.setVisible(False)
        h_text.addWidget(self._lbl_subtitle)

        h_outer.addLayout(h_text, 1)

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
        self._form_layout.setSpacing(12)
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

        self.retranslate_ui()

        # تطبيق الأيقونة إذا أُعطيت عند الإنشاء
        if self._icon:
            self.set_header_icon(self._icon, self._icon_bg)


    # ─────────────────────────────────────────────────────────────────────────
    # Public helpers — add rows to form
    # ─────────────────────────────────────────────────────────────────────────

    def add_row(self, label_key: str, widget: QWidget, *, required: bool = False) -> QWidget:
        """
        أضف row بـ label مترجم + widget.

        label_key : مفتاح الترجمة أو نص ثابت.
        required  : إذا True يُضاف * حمراء بجانب الـ label.
        """
        # container: field + error label
        container = QWidget()
        container.setObjectName("form-field-container")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(2)

        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        c_lay.addWidget(widget)

        # Error label — مخفي افتراضياً
        err_lbl = QLabel()
        err_lbl.setObjectName("form-field-error")
        err_lbl.setVisible(False)
        err_lbl.setWordWrap(True)
        c_lay.addWidget(err_lbl)

        self._error_labels[id(widget)] = err_lbl

        # label مع * اختياري
        lbl = QLabel()
        lbl.setObjectName("form-dialog-label")
        f = lbl.font()
        f.setWeight(QFont.DemiBold)
        lbl.setFont(f)

        self._form_layout.addRow(lbl, container)

        self._row_registry.append(_RowEntry(
            kind="row", label=lbl, key=label_key, required=required
        ))
        self._apply_label_text(lbl, label_key, required)

        return widget

    def add_spacer(self):
        """أضف مسافة بصرية بين أقسام الفورم."""
        spacer = QWidget()
        spacer.setFixedHeight(8)
        self._form_layout.addRow(spacer)
        self._row_registry.append(_RowEntry(kind="spacer"))

    def add_section(self, title_key: str):
        """أضف فاصل قسم بعنوان مترجم."""
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

        self._row_registry.append(_RowEntry(kind="section", label=lbl, key=title_key))
        lbl.setText(self._(title_key))

    # ─────────────────────────────────────────────────────────────────────────
    # Inline validation API
    # ─────────────────────────────────────────────────────────────────────────

    def show_field_error(self, widget: QWidget, message: str) -> None:
        """
        أظهر رسالة خطأ inline تحت الحقل وألوّن border بالأحمر.
        """
        widget.setProperty("has_error", True)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

        err_lbl = self._error_labels.get(id(widget))
        if err_lbl:
            err_lbl.setText(message)
            err_lbl.setVisible(True)

        try:
            widget.setFocus()
        except Exception:
            pass

    def clear_field_error(self, widget: QWidget) -> None:
        """أعد الحقل لوضعه الطبيعي."""
        widget.setProperty("has_error", False)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

        err_lbl = self._error_labels.get(id(widget))
        if err_lbl:
            err_lbl.setVisible(False)
            err_lbl.setText("")

    def clear_all_errors(self) -> None:
        """أزل جميع رسائل الخطأ — استدعِه أول شيء في accept()."""
        for err_lbl in self._error_labels.values():
            err_lbl.setVisible(False)
            err_lbl.setText("")
        from PySide6.QtWidgets import QWidget as _W
        for child in self._body.findChildren(_W):
            if child.property("has_error"):
                child.setProperty("has_error", False)
                child.style().unpolish(child)
                child.style().polish(child)

    def validate_required(self, widget: QWidget, label_key: str) -> bool:
        """
        تحقق من أن الحقل غير فارغ.
        يعرض الخطأ inline تلقائياً ويعيد False إذا كان فارغاً.
        """
        value = self._get_widget_value(widget)
        if value:
            self.clear_field_error(widget)
            return True
        field_name = self._(label_key)
        msg_template = self._("field_required_msg")
        if "{field}" in msg_template:
            msg = msg_template.format(field=field_name)
        else:
            msg = f"{field_name}: {self._('required')}"
        self.show_field_error(widget, msg)
        return False

    def validate_email(self, widget: QLineEdit) -> bool:
        """
        تحقق من صحة البريد الإلكتروني.
        يعيد True إذا كان فارغاً (اختياري) أو صالحاً.
        """
        value = (widget.text() or "").strip()
        if not value:
            return True
        if "@" in value and "." in value.split("@")[-1]:
            self.clear_field_error(widget)
            return True
        self.show_field_error(widget, self._("invalid_email"))
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Convenience setters (backward-compatible API)
    # ─────────────────────────────────────────────────────────────────────────

    def set_header_icon(self, svg_or_emoji: str, bg_color: str = "") -> None:
        """
        أضف أيقونة contextual في الـ header بجانب العنوان.

        svg_or_emoji : نص Unicode / emoji (مثل "👤" "📦" "🏢")
                       أو HTML مثل '<img src="...">'
        bg_color     : لون خلفية الأيقونة (اختياري، مثل "#EFF6FF")
        """
        lbl = self._header_icon_lbl
        lbl.setText(svg_or_emoji)
        lbl.setTextFormat(Qt.RichText)
        style = "border-radius: 8px; font-size: 18px;"
        if bg_color:
            style += f" background: {bg_color};"
        lbl.setStyleSheet(style)
        lbl.setVisible(True)

    def set_title(self, text: str):
        self._title_static = text
        self._title_key_form = ""
        self._lbl_title.setText(text)

    def set_save_text(self, text: str):
        self._save_key = ""
        self.btn_save.setText(text)

    def set_title_key(self, key: str):
        self._title_key_form = key
        self._lbl_title.setText(self._(key))
        self.setWindowTitle(self._(key))

    def set_save_key(self, key: str):
        self._save_key = key
        self.btn_save.setText(self._(key))

    # ─────────────────────────────────────────────────────────────────────────
    # Retranslation
    # ─────────────────────────────────────────────────────────────────────────

    def retranslate_ui(self):
        """يُعيد ترجمة كل عناصر FormDialog تلقائياً."""
        try:
            lang = self.translator.get_current_language()
            if lang.startswith("ar"):
                self._form_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            else:
                self._form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        except Exception:
            pass

        if self._title_key_form:
            text = self._(self._title_key_form)
            self._lbl_title.setText(text)
            self.setWindowTitle(text)
        elif self._title_static:
            self._lbl_title.setText(self._title_static)

        if self._subtitle_key_form:
            text = self._(self._subtitle_key_form)
            self._lbl_subtitle.setText(text)
            self._lbl_subtitle.setVisible(bool(text))
        elif self._subtitle_static:
            self._lbl_subtitle.setText(self._subtitle_static)
            self._lbl_subtitle.setVisible(True)

        if self._save_key:
            self.btn_save.setText(self._(self._save_key))
        if self._cancel_key:
            self.btn_cancel.setText(self._(self._cancel_key))

        for entry in self._row_registry:
            if entry.label is not None and entry.key:
                if entry.kind == "row":
                    self._apply_label_text(entry.label, entry.key, entry.required)
                else:
                    entry.label.setText(self._(entry.key))

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_label_text(self, lbl: QLabel, key: str, required: bool) -> None:
        text = self._(key)
        if required:
            lbl.setText(f'{text} <span style="color:#EF4444;">*</span>')
            lbl.setTextFormat(Qt.RichText)
        else:
            lbl.setText(text)
            lbl.setTextFormat(Qt.AutoText)

    def _get_widget_value(self, widget: QWidget) -> str:
        """استخرج قيمة نصية من أي نوع widget شائع."""
        from PySide6.QtWidgets import (
            QLineEdit as _LE, QTextEdit as _TE,
            QPlainTextEdit as _PTE, QComboBox as _CB, QAbstractSpinBox as _SB,
        )
        if isinstance(widget, _LE):
            return (widget.text() or "").strip()
        if isinstance(widget, (_TE, _PTE)):
            return (widget.toPlainText() or "").strip()
        if isinstance(widget, _CB):
            return "" if widget.currentData() is None else str(widget.currentData())
        if isinstance(widget, _SB):
            return str(widget.value())
        if hasattr(widget, "current_value"):
            v = widget.current_value()
            return "" if v is None else str(v)
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Internal data class
# ─────────────────────────────────────────────────────────────────────────────

class _RowEntry:
    __slots__ = ("kind", "label", "key", "required")

    def __init__(
        self,
        kind: str,
        label: Optional[QLabel] = None,
        key: Optional[str] = None,
        required: bool = False,
    ):
        self.kind     = kind
        self.label    = label
        self.key      = key
        self.required = required