"""
searchable_combo.py — LOGIPORT
QComboBox قابل للبحث مع debounce — الـ loader هو المسؤول عن البحث بكل اللغات.
الـ completer يعرض النتائج فقط بدون فلترة إضافية.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, List, Optional

from PySide6.QtWidgets import QComboBox, QCompleter
from PySide6.QtCore    import Qt, QStringListModel, QEvent, QTimer
from PySide6.QtGui     import QWheelEvent

from core.translator import TranslationManager

_DEBOUNCE_MS = 250


class SearchableComboBox(QComboBox):

    def __init__(self, parent=None, page_size: int = 50):
        super().__init__(parent)

        self._loader:   Optional[Callable] = None
        self._display:  Optional[Callable] = None
        self._value_fn: Optional[Callable] = None
        self._items:    List[Any] = []
        self._page_size = page_size
        self._loading   = False
        self._tracked_value: Any = None   # آخر قيمة اختارها المستخدم

        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setMaxVisibleItems(12)
        self.lineEdit().setObjectName("search-field")
        self.lineEdit().setClearButtonEnabled(True)

        # completer بدون فلترة — الـ loader يفلتر، الـ completer يعرض فقط
        self._str_model = QStringListModel()
        self._completer = QCompleter(self._str_model, self)
        self._completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setMaxVisibleItems(12)
        self.setCompleter(self._completer)

        # Debounce timer
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._do_fetch)
        self._pending_query: str = ""

        self._completer.activated[str].connect(self._on_activated)
        self.lineEdit().textEdited.connect(self._on_text_edited)
        self.lineEdit().installEventFilter(self)

    # ── PUBLIC API ────────────────────────────────────────────────────────

    def set_loader(self, loader: Callable, display: Callable, value: Callable):
        self._loader   = loader
        self._display  = display
        self._value_fn = value
        self._fetch_and_fill("")
        return self

    def current_value(self) -> Any:
        idx = self.currentIndex()
        if 0 <= idx < len(self._items):
            val = self._value_fn(self._items[idx])
            self._tracked_value = val
            return val
        # fallback: القيمة المحفوظة من آخر اختيار صحيح
        return self._tracked_value

    def set_value(self, value: Any, display_text: str = ""):
        for i, obj in enumerate(self._items):
            if self._value_fn(obj) == value:
                self._loading = True
                self.setCurrentIndex(i)
                self.lineEdit().setText(display_text or self.itemText(i))
                self._tracked_value = value
                self._loading = False
                return
        # غير موجود — أضفه مؤقتاً
        self._loading = True
        self._items.insert(0, _Placeholder(value))
        self.insertItem(0, display_text)
        self.setCurrentIndex(0)
        self._tracked_value = value
        self._loading = False

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()

    def eventFilter(self, obj, event):
        if obj is self.lineEdit() and event.type() == QEvent.FocusIn:
            # عند الـ focus: أظهر النتائج بعد لحظة قصيرة
            # singleShot(0) ينتظر انتهاء حدث الـ FocusIn ثم يُظهر الـ popup
            QTimer.singleShot(50, self._show_popup_if_ready)
        return super().eventFilter(obj, event)

    # ── INTERNAL ──────────────────────────────────────────────────────────

    def _show_popup_if_ready(self):
        """يُظهر الـ popup إذا كان فيه بيانات والـ widget لا يزال focused."""
        if not self.lineEdit().hasFocus():
            return
        if self._str_model.rowCount() > 0:
            self._completer.complete()
        elif self._loader:
            # البيانات لم تُحمَّل بعد — اجلبها الآن ثم أظهر
            self._fetch_and_fill("", show_popup_after=True)

    def _on_text_edited(self, text: str):
        if self._loading:
            return
        # إذا مسح المستخدم الحقل كلياً → صفّر الاختيار المحفوظ
        if not text.strip():
            self._tracked_value = None
        self._pending_query = text.strip()
        self._debounce.start()

    def _do_fetch(self):
        self._fetch_and_fill(self._pending_query, show_popup_after=True)

    def _on_activated(self, text: str):
        self._loading = True
        labels = self._str_model.stringList()
        try:
            idx = labels.index(text)
            self.setCurrentIndex(idx)
            if 0 <= idx < len(self._items):
                self._tracked_value = self._value_fn(self._items[idx])
        except ValueError:
            pass
        self._loading = False

    def _fetch_and_fill(self, q: str, show_popup_after: bool = False):
        if not self._loader:
            return

        lang = TranslationManager.get_instance().get_current_language()

        try:
            sig    = inspect.signature(self._loader)
            params = [
                p for name, p in sig.parameters.items()
                if name != "self"
                and p.kind not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD,
                )
            ]
            raw = self._loader(q) if params else self._loader()
        except Exception:
            raw = []

        self._items = list(raw)[: self._page_size]
        labels = [self._display(obj, lang) or "" for obj in self._items]

        self._str_model.setStringList(labels)

        self._loading = True
        self.blockSignals(True)
        self.clear()
        for label in labels:
            self.addItem(label)
        self.blockSignals(False)
        self.setCurrentIndex(-1)
        self.lineEdit().blockSignals(True)
        self.lineEdit().setText(q)
        self.lineEdit().blockSignals(False)
        self._loading = False

        # أظهر الـ popup بعد تحديث البيانات
        if show_popup_after and self.lineEdit().hasFocus() and labels:
            QTimer.singleShot(0, self._completer.complete)


class _Placeholder:
    def __init__(self, value):
        self.id = value