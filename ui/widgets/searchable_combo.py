"""
searchable_combo.py — LOGIPORT
================================
SearchableComboBox: ComboBox قابل للبحث مع popup طائر غير حاجب.

الاستخدام:
    combo = SearchableComboBox(parent=self)
    combo.set_loader(
        loader=lambda q: ClientsCRUD().list_clients(),
        display=lambda c, lang: c.name_ar or c.name_en,
        value=lambda c: c.id,
    )
    client_id = combo.current_value()
    combo.set_value(client_id, display_text="اسم الزبون")
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QFrame, QAbstractItemView, QApplication,
)
from PySide6.QtCore import Qt, QTimer, QPoint, QEvent
from PySide6.QtGui  import QWheelEvent

from core.translator import TranslationManager


class _PopupList(QListWidget):
    """
    QListWidget يطفو فوق كل العناصر بدون حجب النافذة الأم.
    - Qt.Tool + Qt.FramelessWindowHint → يطفو بدون modal
    - WA_ShowWithoutActivating → لا يسرق الـ focus من الـ edit
    """

    def __init__(self, owner: "SearchableComboBox"):
        super().__init__(None)
        self._owner = owner

        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.NoDropShadowWindowHint |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setObjectName("data-table")
        self.setFrameShape(QFrame.StyledPanel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setFocusPolicy(Qt.NoFocus)

        self.itemClicked.connect(owner._on_item_clicked)
        self.itemDoubleClicked.connect(owner._on_item_clicked)

    def mousePressEvent(self, event):
        # نسجّل الاختيار عند الضغط مباشرة (قبل أي focus change)
        item = self.itemAt(event.position().toPoint())
        if item:
            self._owner._on_item_clicked(item)
        else:
            super().mousePressEvent(event)


class SearchableComboBox(QWidget):
    """
    Widget بحث مع dropdown طائر غير حاجب.

    المنطق:
    - QLineEdit للكتابة/العرض
    - _PopupList تطفو بـ Qt.Tool → لا تحجب النافذة الأم
    - WA_ShowWithoutActivating → السكرول وباقي التفاعل يشتغل عادي
    - الإغلاق يدوي: عند انتقال focus لخارج الـ combo
    """

    def __init__(self, parent=None, page_size: int = 50):
        super().__init__(parent)

        self._loader:   Optional[Callable] = None
        self._display:  Optional[Callable] = None
        self._value_fn: Optional[Callable] = None

        self._items:     List[Any] = []
        self._cur_value: Any = None
        self._page_size  = page_size
        self._selecting  = False

        self._build_ui()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._do_search)

        # مراقبة focus على مستوى التطبيق لإغلاق الـ popup عند الخروج
        QApplication.instance().focusChanged.connect(self._on_app_focus_changed)

    # ─────────────────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._edit = QLineEdit()
        self._edit.setObjectName("search-field")
        self._edit.setClearButtonEnabled(True)
        self._edit.installEventFilter(self)
        layout.addWidget(self._edit)

        # الـ popup منفصل — لا يدخل في أي layout
        self._popup = _PopupList(owner=self)

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────

    def set_loader(self, loader: Callable, display: Callable, value: Callable):
        self._loader   = loader
        self._display  = display
        self._value_fn = value
        self._do_search(silent=True)
        return self

    def current_value(self) -> Any:
        return self._cur_value

    def set_value(self, value: Any, display_text: str = ""):
        self._cur_value = value
        self._selecting = True
        self._edit.setText(display_text or (str(value) if value else ""))
        self._selecting = False
        self._hide_popup()

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()

    # ─────────────────────────────────────────────────────────────────────
    # FOCUS MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────

    def _on_app_focus_changed(self, old_widget, new_widget):
        """
        يُغلق الـ popup إذا انتقل focus لأي widget خارج هذا الـ combo.
        لا يُغلق إذا الـ focus بقي على الـ _edit (كتابة/بحث).
        """
        if not self._popup.isVisible():
            return
        # new_widget = None يعني ضغط على شيء بدون focus (مثل _popup بـ NoFocus)
        # نتركه مفتوحاً في هذه الحالة
        if new_widget is None:
            return
        if new_widget is self._edit:
            return
        # أي widget آخر → أغلق
        self._hide_popup()

    def eventFilter(self, obj, event):
        if obj is self._edit:
            if event.type() == QEvent.FocusIn:
                if not self._edit.text().strip():
                    self._do_search(silent=True)
                self._show_popup()
        return super().eventFilter(obj, event)

    # ─────────────────────────────────────────────────────────────────────
    # SEARCH & POPULATE
    # ─────────────────────────────────────────────────────────────────────

    def _on_text_edited(self, text: str):
        if self._selecting:
            return
        if not text.strip():
            self._cur_value = None
        self._timer.start()

    def _do_search(self, silent=False):
        if not self._loader:
            return

        q    = self._edit.text().strip()
        lang = TranslationManager.get_instance().get_current_language()

        try:
            sig    = inspect.signature(self._loader)
            params = list(sig.parameters)
            raw    = self._loader(q) if params else self._loader()
            if not params and q:
                raw = [
                    obj for obj in raw
                    if q.casefold() in (self._display(obj, lang) or "").casefold()
                ]
        except Exception:
            raw = []

        self._items = raw[: self._page_size]
        self._fill_popup(lang)

        if not silent:
            self._show_popup()

    def _fill_popup(self, lang: str):
        self._popup.blockSignals(True)
        self._popup.clear()
        for obj in self._items:
            text = self._display(obj, lang) or ""
            val  = self._value_fn(obj)
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, val)
            self._popup.addItem(item)
        self._popup.blockSignals(False)

    # ─────────────────────────────────────────────────────────────────────
    # POPUP SHOW / HIDE
    # ─────────────────────────────────────────────────────────────────────

    def _show_popup(self):
        if self._popup.count() == 0:
            self._hide_popup()
            return

        # موقع مباشرة تحت الـ _edit بالإحداثيات العالمية
        global_pos: QPoint = self._edit.mapToGlobal(QPoint(0, self._edit.height()))

        width = self.width()

        row_h = self._popup.sizeHintForRow(0) if self._popup.count() else 28
        if row_h <= 0:
            row_h = 28
        rows   = min(self._popup.count(), 7)
        height = rows * row_h + 4

        # تأكد أن الـ popup لا يخرج عن الشاشة للأسفل
        screen = QApplication.primaryScreen().availableGeometry()
        if global_pos.y() + height > screen.bottom():
            # اعرضه فوق الـ widget
            global_pos = self._edit.mapToGlobal(QPoint(0, -height))

        self._popup.setGeometry(global_pos.x(), global_pos.y(), width, height)
        self._popup.show()
        self._popup.raise_()

    def _hide_popup(self):
        self._popup.hide()

    # ─────────────────────────────────────────────────────────────────────
    # SELECTION
    # ─────────────────────────────────────────────────────────────────────

    def _on_item_clicked(self, item: QListWidgetItem):
        self._selecting = True
        self._cur_value = item.data(Qt.UserRole)
        self._edit.setText(item.text())
        self._selecting = False
        self._hide_popup()
        self._edit.setFocus()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Down, Qt.Key_Up):
            if self._popup.isVisible():
                count   = self._popup.count()
                current = self._popup.currentRow()
                if key == Qt.Key_Down:
                    self._popup.setCurrentRow(min(current + 1, count - 1))
                else:
                    self._popup.setCurrentRow(max(current - 1, 0))
                return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            item = self._popup.currentItem()
            if item:
                self._on_item_clicked(item)
                return
        if key == Qt.Key_Escape:
            self._hide_popup()
            return
        super().keyPressEvent(event)

    # ─────────────────────────────────────────────────────────────────────
    # CLEANUP
    # ─────────────────────────────────────────────────────────────────────

    def hideEvent(self, event):
        self._hide_popup()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._hide_popup()
        super().closeEvent(event)

    def deleteLater(self):
        try:
            QApplication.instance().focusChanged.disconnect(self._on_app_focus_changed)
        except Exception:
            pass
        self._hide_popup()
        super().deleteLater()