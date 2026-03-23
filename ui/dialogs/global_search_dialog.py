"""
ui/dialogs/global_search_dialog.py
=====================================
نافذة البحث العام — Spotlight-style popup

الإصلاحات v2:
  - c غير معرّفة في _show_results → أصبحت instance variable
  - لا يمكن الخروج → أُضيف focusOutEvent + closeEvent صحيح
  - FramelessWindowHint + WindowStaysOnTopHint
  - Escape يعمل دائماً حتى لو الـ focus على results_list
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QWidget,
    QFrame, QApplication, QPushButton,
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject, QEvent
from PySide6.QtGui import QFont, QKeyEvent, QColor

from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from core.base_dialog import BaseDialog
from ui.utils.wheel_blocker import block_wheel_in

_MAX_HISTORY = 5


# ─── Worker ───────────────────────────────────────────────────────────────────

class _SearchWorker(QObject):
    results_ready = Signal(list)
    finished      = Signal()

    def __init__(self, query: str, lang: str):
        super().__init__()
        self.query = query
        self.lang  = lang

    def run(self):
        try:
            from services.global_search_service import search_all
            results = search_all(self.query, self.lang)
        except Exception:
            results = []
        self.results_ready.emit(results)
        self.finished.emit()


# ─── Dialog ───────────────────────────────────────────────────────────────────

class GlobalSearchDialog(QDialog):
    """
    Spotlight-style search dialog.
    يُغلق بـ: Escape | Click خارج النافذة | اختيار نتيجة
    """
    navigate_to = Signal(str, int)

    _history: list[str] = []

    def __init__(self, parent=None):
        super().__init__(parent)
        self._      = TranslationManager.get_instance().translate
        self._lang  = SettingsManager.get_instance().get("language", "ar")
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._do_search)
        self._thread = None
        self._worker = None

        # ألوان الـ theme — معرّفة هنا لتكون متاحة في كل الـ methods
        self._colors = self._load_colors()

        self._setup_window()
        self._build_ui()
        self._apply_style()
        block_wheel_in(self)

    # ─── Colors ───────────────────────────────────────────────────────────────

    def _load_colors(self) -> dict:
        try:
            from config.themes import ThemeBuilder
            theme_name = SettingsManager.get_instance().get("theme", "light")
            theme = ThemeBuilder(theme_name)
            return dict(theme.colors)
        except Exception:
            return {
                "bg_card":      "#FFFFFF",
                "border":       "#E0E0E0",
                "text_primary": "#212529",
                "text_muted":   "#6C757D",
                "text_secondary":"#6C757D",
                "bg_hover":     "#F0F7FF",
                "accent":       "#2563EB",
                "primary":      "#2563EB",
            }

    def _c(self, key: str, fallback: str = "#666") -> str:
        return self._colors.get(key, fallback)

    # ─── Window ───────────────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowFlags(
            Qt.Dialog |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        # لا WA_TranslucentBackground — يسبب خلفية داكنة على بعض الـ DEs
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setModal(True)
        self.setFixedWidth(560)

        try:
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(
                screen.center().x() - 280,
                screen.top() + int(screen.height() * 0.13),
            )
        except Exception:
            pass

    # ─── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("search-card")
        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        # ── حقل البحث ─────────────────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.setContentsMargins(16, 14, 16, 14)
        search_row.setSpacing(10)

        icon = QLabel("🔍")
        icon.setFont(QFont("Segoe UI Emoji", 15))
        icon.setFixedWidth(28)
        search_row.addWidget(icon)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("global-search-input")
        self.search_input.setPlaceholderText(self._("search_placeholder"))
        self.search_input.setFrame(False)
        self.search_input.setFont(QFont("Tajawal", 13))
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._select_first)
        search_row.addWidget(self.search_input, 1)

        hint_lbl = QLabel("Esc  " + self._("close"))
        hint_lbl.setObjectName("kbd-hint")
        search_row.addWidget(hint_lbl)

        card_lay.addLayout(search_row)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setObjectName("separator")
        card_lay.addWidget(sep)

        # ── History + Results ──────────────────────────────────────────────────
        self._content_widget = QWidget()
        self._content_lay    = QVBoxLayout(self._content_widget)
        self._content_lay.setContentsMargins(0, 0, 0, 0)
        self._content_lay.setSpacing(0)

        # history
        self._history_panel = QWidget()
        hist_lay = QVBoxLayout(self._history_panel)
        hist_lay.setContentsMargins(16, 10, 16, 6)
        hist_lay.setSpacing(4)

        hist_header = QHBoxLayout()
        hist_title  = QLabel(self._("search_recent_title"))
        hist_title.setObjectName("text-muted")
        hist_title.setFont(QFont("Tajawal", 9, QFont.Bold))
        hist_header.addWidget(hist_title)
        hist_header.addStretch()

        self._clear_btn = QPushButton(self._("search_recent_clear"))
        self._clear_btn.setObjectName("link-btn")
        self._clear_btn.setFont(QFont("Tajawal", 9))
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.clicked.connect(self._clear_history)
        hist_header.addWidget(self._clear_btn)
        hist_lay.addLayout(hist_header)

        self._history_list = QListWidget()
        self._history_list.setObjectName("history-list")
        self._history_list.setFrameShape(QFrame.NoFrame)
        self._history_list.setFixedHeight(min(_MAX_HISTORY, 5) * 34)
        self._history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._history_list.itemClicked.connect(self._on_history_clicked)
        hist_lay.addWidget(self._history_list)
        self._content_lay.addWidget(self._history_panel)

        # results
        self.results_list = QListWidget()
        self.results_list.setObjectName("search-results-list")
        self.results_list.setFrameShape(QFrame.NoFrame)
        self.results_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_list.setSpacing(2)
        self.results_list.itemActivated.connect(self._on_item_activated)
        self.results_list.itemClicked.connect(self._on_item_activated)
        self._content_lay.addWidget(self.results_list)
        card_lay.addWidget(self._content_widget)

        # footer
        footer = QHBoxLayout()
        footer.setContentsMargins(16, 8, 16, 12)
        self.status_lbl = QLabel(self._("search_hint"))
        self.status_lbl.setObjectName("text-muted")
        self.status_lbl.setFont(QFont("Tajawal", 9))
        footer.addWidget(self.status_lbl)
        footer.addStretch()
        nav_hint = QLabel("↑↓  " + self._("navigate") + "   ↵  " + self._("open"))
        nav_hint.setObjectName("text-muted")
        nav_hint.setFont(QFont("Tajawal", 9))
        footer.addWidget(nav_hint)
        card_lay.addLayout(footer)

        outer.addWidget(self.card)

    # ─── Style ────────────────────────────────────────────────────────────────

    def _apply_style(self):
        bg        = self._c("bg_card",      "#FFFFFF")
        border_c  = self._c("border",       "#E0E0E0")
        text_c    = self._c("text_primary",  "#212529")
        text_muted= self._c("text_secondary","#6C757D")
        hover_bg  = self._c("bg_hover",     "#F0F7FF")
        accent    = self._c("primary",      "#2563EB")

        self.setStyleSheet(f"""
            GlobalSearchDialog {{
                background: {bg};
            }}
            QFrame#search-card {{
                background   : {bg};
                border       : 1px solid {border_c};
                border-radius: 14px;
            }}
            QLineEdit#global-search-input {{
                background  : transparent;
                border      : none;
                color       : {text_c};
                font-size   : 14px;
                padding     : 2px 0;
            }}
            QListWidget#search-results-list {{
                background  : transparent;
                border      : none;
                outline     : none;
                padding     : 4px 8px;
                min-height  : 160px;
                max-height  : 280px;
                color       : {text_c};
            }}
            QListWidget#search-results-list::item {{
                border-radius: 8px;
                padding      : 0;
                margin       : 1px 0;
                color        : {text_c};
            }}
            QListWidget#search-results-list::item:selected,
            QListWidget#search-results-list::item:hover {{
                background  : {hover_bg};
                color       : {text_c};
            }}
            QListWidget#history-list {{
                background  : transparent;
                border      : none;
                outline     : none;
                color       : {text_c};
            }}
            QListWidget#history-list::item {{
                border-radius: 6px;
                padding      : 2px 8px;
                color        : {text_c};
            }}
            QListWidget#history-list::item:hover {{
                background  : {hover_bg};
            }}
            QPushButton#link-btn {{
                background  : transparent;
                border      : none;
                color       : {accent};
                padding     : 0 4px;
            }}
            QPushButton#link-btn:hover {{ text-decoration: underline; }}
            QLabel {{ color: {text_c}; }}
            QLabel#text-muted {{ color: {text_muted}; }}
            QLabel#kbd-hint {{
                color        : {text_muted};
                border       : 1px solid {border_c};
                border-radius: 4px;
                padding      : 1px 6px;
                font-size    : 9px;
                font-family  : monospace;
            }}
        """)

    # ─── History ──────────────────────────────────────────────────────────────

    def _refresh_history(self):
        self._history_list.clear()
        history = GlobalSearchDialog._history
        if not history:
            self._history_panel.setVisible(False)
            return
        self._history_panel.setVisible(True)
        for q in reversed(history):
            item = QListWidgetItem(f"  🕐  {q}")
            item.setData(Qt.UserRole, q)
            item.setFont(QFont("Tajawal", 10))
            self._history_list.addItem(item)
        self._history_list.setFixedHeight(min(len(history), _MAX_HISTORY) * 34)

    def _add_to_history(self, query: str):
        query = query.strip()
        if not query:
            return
        h = GlobalSearchDialog._history
        if query in h:
            h.remove(query)
        h.append(query)
        if len(h) > _MAX_HISTORY:
            GlobalSearchDialog._history = h[-_MAX_HISTORY:]

    def _clear_history(self):
        GlobalSearchDialog._history.clear()
        self._refresh_history()
        self.results_list.clear()
        self.status_lbl.setText(self._("search_hint"))

    def _on_history_clicked(self, item: QListWidgetItem):
        q = item.data(Qt.UserRole)
        if q:
            self.search_input.setText(q)
            self.search_input.setFocus()

    # ─── Search ───────────────────────────────────────────────────────────────

    def _on_text_changed(self, text: str):
        self._timer.stop()
        if len(text.strip()) < 1:
            self.results_list.clear()
            self.results_list.setVisible(False)
            self._refresh_history()
            self.status_lbl.setText(self._("search_hint"))
            return
        self._history_panel.setVisible(False)
        self.results_list.setVisible(True)
        self._timer.start()

    def _do_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        self.status_lbl.setText(self._("searching") + "...")
        self.results_list.clear()

        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(300)

        self._thread = QThread(self)
        self._worker = _SearchWorker(query, self._lang)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.results_ready.connect(self._show_results)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _show_results(self, results: list):
        self.results_list.clear()
        text_muted = self._c("text_secondary", "#6B7280")

        if not results:
            self.status_lbl.setText(self._("no_results"))
            item = QListWidgetItem(self._("no_results_found"))
            item.setFlags(Qt.NoItemFlags)
            item.setFont(QFont("Tajawal", 10))
            self.results_list.addItem(item)
            return

        entity_labels = {
            "transactions":       (self._("transactions"),            "📦"),
            "container_tracking": (self._("search_containers_group"), "🚢"),
            "clients":            (self._("clients"),                 "👤"),
            "companies":          (self._("companies"),               "🏢"),
            "materials":          (self._("materials"),               "🔩"),
            "entries":            (self._("entries"),                 "📋"),
            "documents":          (self._("documents"),               "📄"),
        }

        grouped: dict[str, list] = {}
        for r in results:
            grouped.setdefault(r.entity_key, []).append(r)

        for entity_key, entity_results in grouped.items():
            label, icon = entity_labels.get(entity_key, (entity_key, "📄"))
            header = QListWidgetItem(f"  {icon}  {label}")
            header.setFlags(Qt.NoItemFlags)
            header.setFont(QFont("Tajawal", 9, QFont.Bold))
            header.setForeground(QColor(text_muted))
            self.results_list.addItem(header)
            for r in entity_results:
                item = self._make_item(r)
                self.results_list.addItem(item)
                self.results_list.setItemWidget(item, self._make_item_widget(r))

        self.status_lbl.setText(f"{len(results)} {self._('results_found')}")

        # حدد أول نتيجة قابلة للاختيار
        for i in range(self.results_list.count()):
            it = self.results_list.item(i)
            if it and (it.flags() & Qt.ItemIsEnabled):
                self.results_list.setCurrentItem(it)
                break

    def _make_item(self, result) -> QListWidgetItem:
        from PySide6.QtCore import QSize
        item = QListWidgetItem()
        item.setData(Qt.UserRole, (result.entity_key, result.record_id))
        item.setSizeHint(QSize(0, 52))
        return item

    def _make_item_widget(self, result) -> QWidget:
        w   = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(10)

        icon_lbl = QLabel(result.icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 16))
        icon_lbl.setFixedWidth(30)
        icon_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon_lbl)

        text_lay = QVBoxLayout()
        text_lay.setSpacing(1)
        text_lay.setContentsMargins(0, 0, 0, 0)

        title = QLabel(result.title)
        title.setFont(QFont("Tajawal", 11, QFont.Bold))
        text_lay.addWidget(title)

        if result.subtitle:
            sub = QLabel(result.subtitle)
            sub.setFont(QFont("Tajawal", 9))
            sub.setObjectName("text-muted")
            text_lay.addWidget(sub)

        lay.addLayout(text_lay, 1)

        if result.badge:
            badge = QLabel(result.badge)
            badge.setFont(QFont("Segoe UI Emoji", 14))
            badge.setAlignment(Qt.AlignCenter)
            lay.addWidget(badge)

        w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        return w

    # ─── Navigation ───────────────────────────────────────────────────────────

    def _select_first(self):
        for i in range(self.results_list.count()):
            it = self.results_list.item(i)
            if it and (it.flags() & Qt.ItemIsEnabled):
                self._on_item_activated(it)
                return

    def _on_item_activated(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if not data:
            return
        entity_key, record_id = data
        self._add_to_history(self.search_input.text().strip())
        self._cleanup_thread()
        self.accept()
        self.navigate_to.emit(entity_key, record_id)

    # ─── Keyboard & Focus ─────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key_Escape:
            self._safe_close()
        elif key == Qt.Key_Down:
            self._move_selection(1)
        elif key == Qt.Key_Up:
            self._move_selection(-1)
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            cur = self.results_list.currentItem()
            if cur and (cur.flags() & Qt.ItemIsEnabled):
                self._on_item_activated(cur)
            else:
                self._select_first()
        else:
            # أي حرف آخر → أعد الـ focus للـ search_input
            if not event.text().strip() == "":
                self.search_input.setFocus()
            super().keyPressEvent(event)

    def changeEvent(self, event):
        """يُغلق عند فقدان الـ activation (مثل الضغط خارج النافذة)."""
        if event.type() == QEvent.ActivationChange:
            if not self.isActiveWindow():
                self._safe_close()
        super().changeEvent(event)

    def _move_selection(self, direction: int):
        count = self.results_list.count()
        if count == 0:
            return
        cur = self.results_list.currentRow()
        idx = cur if cur >= 0 else -1
        for _ in range(count):
            idx = (idx + direction) % count
            it  = self.results_list.item(idx)
            if it and (it.flags() & Qt.ItemIsEnabled):
                self.results_list.setCurrentRow(idx)
                break

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    def _safe_close(self):
        """إغلاق آمن — ينظف الـ thread ويرفض الـ dialog."""
        self._cleanup_thread()
        self.reject()

    def _cleanup_thread(self):
        self._timer.stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(400)

    def closeEvent(self, event):
        self._cleanup_thread()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.search_input.setFocus()
        self.search_input.clear()
        self.results_list.clear()
        self.results_list.setVisible(False)
        self.status_lbl.setText(self._("search_hint"))
        self._refresh_history()