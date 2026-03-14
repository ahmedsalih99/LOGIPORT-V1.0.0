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

# مدة الـ debounce بالملي ثانية — تمنع استدعاء loader عند كل ضغطة مفتاح
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

        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setMaxVisibleItems(10)
        self.lineEdit().setObjectName("search-field")
        self.lineEdit().setClearButtonEnabled(True)

        # completer يعرض النتائج فقط - بدون فلترة إضافية (الـ loader يفلتر)
        self._str_model = QStringListModel()
        self._completer = QCompleter(self._str_model, self)
        self._completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setMaxVisibleItems(10)
        self.setCompleter(self._completer)

        # Debounce timer — ينتظر قبل استدعاء loader
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
            return self._value_fn(self._items[idx])
        return None

    def set_value(self, value: Any, display_text: str = ""):
        for i, obj in enumerate(self._items):
            if self._value_fn(obj) == value:
                self._loading = True
                self.setCurrentIndex(i)
                self.lineEdit().setText(display_text or self.itemText(i))
                self._loading = False
                return
        # غير موجود — أضفه مؤقتاً
        self._loading = True
        self._items.insert(0, _Placeholder(value))
        self.insertItem(0, display_text)
        self.setCurrentIndex(0)
        self._loading = False

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()

    def eventFilter(self, obj, event):
        if obj is self.lineEdit() and event.type() == QEvent.FocusIn:
            if self._str_model.rowCount() > 0:
                self._completer.complete()
        return super().eventFilter(obj, event)

    # ── INTERNAL ──────────────────────────────────────────────────────────

    def _on_text_edited(self, text: str):
        if self._loading:
            return
        # Debounce: انتظر _DEBOUNCE_MS قبل الاستدعاء
        self._pending_query = text.strip()
        self._debounce.start()

    def _do_fetch(self):
        """يُستدعى بعد انقضاء الـ debounce."""
        self._fetch_and_fill(self._pending_query)

    def _on_activated(self, text: str):
        self._loading = True
        labels = self._str_model.stringList()
        try:
            idx = labels.index(text)
            self.setCurrentIndex(idx)
        except ValueError:
            pass
        self._loading = False

    def _fetch_and_fill(self, q: str):
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


class _Placeholder:
    def __init__(self, value):
        self.id = value
