"""
ui/dialogs/global_search_dialog.py
=====================================
نافذة البحث العام — Spotlight-style popup
- يفتح بـ Ctrl+F أو زر البحث في الـ topbar
- يبحث في: معاملات، عملاء، شركات، مواد، إدخالات، وثائق
- الضغط على نتيجة ينقل للتاب ويحدد السجل
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QWidget,
    QFrame, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont, QKeyEvent, QColor

from core.translator import TranslationManager
from core.settings_manager import SettingsManager


# ─── Worker thread للبحث غير المتزامن ─────────────────────────────────────

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


# ─── نافذة البحث ──────────────────────────────────────────────────────────

class GlobalSearchDialog(QDialog):
    """
    Spotlight-style search dialog.
    Signal navigate_to(entity_key, record_id) يُصدَر عند اختيار نتيجة.
    """
    navigate_to = Signal(str, int)   # (tab_key, record_id)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._      = TranslationManager.get_instance().translate
        self._lang  = SettingsManager.get_instance().get("language", "ar")
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)   # debounce 300ms
        self._timer.timeout.connect(self._do_search)
        self._thread = None
        self._worker = None

        self._setup_window()
        self._build_ui()
        self._apply_style()

    # ─── Window setup ────────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(580)
        self.setMaximumWidth(680)

        # وسط الشاشة
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(
            screen.center().x() - 300,
            screen.top() + int(screen.height() * 0.18),
            600,
            420,
        )

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # بطاقة رئيسية
        self.card = QFrame()
        self.card.setObjectName("search-card")
        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        # ── حقل البحث ──────────────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.setContentsMargins(16, 12, 16, 12)
        search_row.setSpacing(10)

        icon = QLabel("🔍")
        icon.setFont(QFont("Segoe UI Emoji", 15))
        icon.setFixedWidth(28)
        search_row.addWidget(icon)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("global-search-input")
        self.search_input.setPlaceholderText(self._("search_placeholder"))
        self.search_input.setFrame(False)
        font = QFont("Tajawal", 13)
        self.search_input.setFont(font)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._select_first)
        search_row.addWidget(self.search_input, 1)

        esc_lbl = QLabel("Esc")
        esc_lbl.setObjectName("kbd-hint")
        esc_lbl.setFixedWidth(32)
        search_row.addWidget(esc_lbl)

        card_lay.addLayout(search_row)

        # فاصل
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("separator")
        card_lay.addWidget(sep)

        # ── قائمة النتائج ──────────────────────────────────────────────────
        self.results_list = QListWidget()
        self.results_list.setObjectName("search-results-list")
        self.results_list.setFrameShape(QFrame.NoFrame)
        self.results_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_list.setSpacing(2)
        self.results_list.itemActivated.connect(self._on_item_activated)
        self.results_list.itemClicked.connect(self._on_item_activated)
        card_lay.addWidget(self.results_list)

        # ── شريط الحالة السفلي ─────────────────────────────────────────────
        footer = QHBoxLayout()
        footer.setContentsMargins(16, 8, 16, 10)

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

    # ─── Style ───────────────────────────────────────────────────────────────

    def _apply_style(self):
        try:
            from config.themes import ThemeBuilder
            theme_name = SettingsManager.get_instance().get("theme", "light")
            theme = ThemeBuilder(theme_name)
            c = theme.colors
            bg = c.get("bg_card", "#FFFFFF")
            border_c = c.get("border", "#E0E0E0")
            text_c = c.get("text_primary", "#212529")
            text_muted = c.get("text_muted", "#6C757D")
            hover_bg = c.get("bg_hover", "#F0F7FF")
        except Exception:
            bg = "#FFFFFF"; border_c = "#E0E0E0"
            text_c = "#212529"; text_muted = "#6C757D"; hover_bg = "#F0F7FF"

        self.setStyleSheet(f"""
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
                min-height  : 200px;
                max-height  : 320px;
                color       : {text_c};
            }}
            QListWidget#search-results-list::item {{
                border-radius: 8px;
                padding     : 0;
                margin      : 1px 0;
                color       : {text_c};
            }}
            QListWidget#search-results-list::item:selected,
            QListWidget#search-results-list::item:hover {{
                background  : {hover_bg};
                color       : {text_c};
            }}
            QLabel {{
                color: {text_c};
            }}
            QLabel#kbd-hint {{
                color        : {text_muted};
                border       : 1px solid {border_c};
                border-radius: 4px;
                padding      : 1px 5px;
                font-size    : 10px;
                font-family  : monospace;
            }}
        """)

    # ─── Search logic ─────────────────────────────────────────────────────────

    def _on_text_changed(self, text: str):
        self._timer.stop()
        if len(text.strip()) < 1:
            self.results_list.clear()
            self.status_lbl.setText(self._("search_hint"))
            return
        self._timer.start()

    def _do_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        self.status_lbl.setText(self._("searching") + "...")
        self.results_list.clear()

        # تشغيل في thread منفصل
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(200)

        self._thread = QThread()
        self._worker = _SearchWorker(query, self._lang)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.results_ready.connect(self._show_results)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _show_results(self, results):
        self.results_list.clear()
        if not results:
            self.status_lbl.setText(self._("no_results"))
            item = QListWidgetItem(self._("no_results_found"))
            item.setFlags(Qt.NoItemFlags)
            item.setFont(QFont("Tajawal", 10))
            self.results_list.addItem(item)
            return

        # تجميع حسب الكيان
        entity_labels = {
            "transactions": (self._("transactions"), "📦"),
            "clients":      (self._("clients"),      "👤"),
            "companies":    (self._("companies"),     "🏢"),
            "materials":    (self._("materials"),     "🔩"),
            "entries":      (self._("entries"),       "📋"),
            "documents":    (self._("documents"),     "📄"),
        }

        grouped: dict[str, list] = {}
        for r in results:
            grouped.setdefault(r.entity_key, []).append(r)

        for entity_key, entity_results in grouped.items():
            label, icon = entity_labels.get(entity_key, (entity_key, "📄"))

            # Header للمجموعة
            header = QListWidgetItem(f"  {icon}  {label}")
            header.setFlags(Qt.NoItemFlags)
            header.setFont(QFont("Tajawal", 9, QFont.Bold))
            header.setForeground(QColor("#6B7280"))
            self.results_list.addItem(header)

            for r in entity_results:
                item = self._make_item(r)
                self.results_list.addItem(item)
                self.results_list.setItemWidget(item, self._make_item_widget(r))

        count = len(results)
        self.status_lbl.setText(f"{count} {self._('results_found')}")

        # حدد أول عنصر قابل للاختيار
        for i in range(self.results_list.count()):
            it = self.results_list.item(i)
            if it and (it.flags() & Qt.ItemIsEnabled):
                self.results_list.setCurrentItem(it)
                break

    def _make_item(self, result) -> QListWidgetItem:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, (result.entity_key, result.record_id))
        item.setSizeHint(__import__('PySide6.QtCore', fromlist=['QSize']).QSize(0, 52))
        return item

    def _make_item_widget(self, result) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(10)

        # أيقونة
        icon_lbl = QLabel(result.icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 16))
        icon_lbl.setFixedWidth(30)
        icon_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon_lbl)

        # نصوص
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

        # badge الحالة
        if result.badge:
            badge = QLabel(result.badge)
            badge.setFont(QFont("Segoe UI Emoji", 14))
            badge.setAlignment(Qt.AlignCenter)
            lay.addWidget(badge)

        w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        return w

    # ─── Navigation ──────────────────────────────────────────────────────────

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
        self.accept()
        self.navigate_to.emit(entity_key, record_id)

    # ─── Keyboard ────────────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key_Escape:
            self.reject()
        elif key in (Qt.Key_Down, Qt.Key_Up):
            self._move_selection(1 if key == Qt.Key_Down else -1)
        elif key == Qt.Key_Return:
            cur = self.results_list.currentItem()
            if cur:
                self._on_item_activated(cur)
        else:
            super().keyPressEvent(event)

    def _move_selection(self, direction: int):
        count = self.results_list.count()
        if count == 0:
            return
        cur = self.results_list.currentRow()
        # ابحث عن العنصر التالي القابل للاختيار
        idx = cur
        for _ in range(count):
            idx = (idx + direction) % count
            it = self.results_list.item(idx)
            if it and (it.flags() & Qt.ItemIsEnabled):
                self.results_list.setCurrentRow(idx)
                break

    # ─── Cleanup ─────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._timer.stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(300)
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.search_input.setFocus()
        self.search_input.clear()
        self.results_list.clear()
        self.status_lbl.setText(self._("search_hint"))