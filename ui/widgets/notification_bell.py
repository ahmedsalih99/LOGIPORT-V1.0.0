"""
NotificationBell Widget - LOGIPORT
=====================================

زر جرس الإشعارات في الـ TopBar.
- Badge حمراء بعدد غير المقروء
- Popup بقائمة الإشعارات
- مرتبط بـ NotificationService + ثيم التطبيق
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QApplication
)
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QFont, QCursor

from services.notification_service import NotificationService, Notification
from core.translator import TranslationManager


# ─── colours by level (will be overridden by theme when possible) ─────────────
LEVEL_COLORS = {
    "success": ("#2ECC71", "rgba(46,204,113,0.12)"),
    "info":    ("#3498DB", "rgba(52,152,219,0.12)"),
    "warning": ("#F39C12", "rgba(243,156,18,0.12)"),
    "danger":  ("#E74C3C", "rgba(231,76,60,0.12)"),
}


class _NotifItem(QFrame):
    """Card-style row inside the popup."""

    def __init__(self, notif: Notification, on_click, parent=None):
        super().__init__(parent)
        self._notif   = notif
        self._on_click = on_click
        self.setObjectName("notif-item")
        self.setCursor(QCursor(Qt.PointingHandCursor))

        accent, bg = LEVEL_COLORS.get(notif.level, ("#3498DB", "rgba(52,152,219,0.12)"))
        read_opacity = "1" if not notif.is_read else "0.65"

        self.setStyleSheet(f"""
            QFrame#notif-item {{
                background: {bg if not notif.is_read else "transparent"};
                border-radius: 8px;
                border-right: 3px solid {accent if not notif.is_read else "transparent"};
                padding: 2px;
                opacity: {read_opacity};
            }}
            QFrame#notif-item:hover {{
                background: {bg};
                border-right: 3px solid {accent};
            }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(8)

        # icon bubble
        icon_lbl = QLabel(notif.icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 14))
        icon_lbl.setFixedSize(30, 30)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            background: {accent};
            border-radius: 15px;
            color: white;
        """)
        lay.addWidget(icon_lbl)

        # text column
        txt_col = QVBoxLayout()
        txt_col.setSpacing(2)

        msg_lbl = QLabel(notif.message)
        msg_lbl.setFont(QFont("Tajawal", 9, QFont.DemiBold if not notif.is_read else QFont.Normal))
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: inherit; background: transparent;")
        txt_col.addWidget(msg_lbl)

        time_lbl = QLabel(notif.time_ago)
        time_lbl.setFont(QFont("Tajawal", 8))
        time_lbl.setStyleSheet("color: #9CA3AF; background: transparent;")
        txt_col.addWidget(time_lbl)

        lay.addLayout(txt_col, 1)

        # unread dot
        if not notif.is_read:
            dot = QLabel("●")
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"color: {accent}; font-size: 8px; background: transparent;")
            lay.addWidget(dot, 0, Qt.AlignTop)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_click(self._notif)
        super().mousePressEvent(event)


class NotificationPopup(QFrame):
    """Floating popup that appears below the bell icon."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("notif-popup")
        self.setFixedWidth(340)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QFrame#notif-popup {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)

        self._svc = NotificationService.get_instance()
        self._ = TranslationManager.get_instance().translate

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── header ──────────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("notif-header")
        header.setStyleSheet("""
            QFrame#notif-header {
                background: transparent;
                border-bottom: 1px solid #F3F4F6;
                border-radius: 0px;
                padding: 4px 0;
            }
        """)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(14, 10, 14, 10)

        title_lbl = QLabel(f"🔔  {self._('notifications')}")
        title_lbl.setFont(QFont("Tajawal", 12, QFont.Bold))
        title_lbl.setStyleSheet("color: #1F2937; background: transparent;")
        h_lay.addWidget(title_lbl)

        h_lay.addStretch()

        mark_btn = QPushButton(self._("mark_all_read"))
        mark_btn.setFont(QFont("Tajawal", 8))
        mark_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #3498DB; padding: 2px 6px;
            }
            QPushButton:hover { color: #1D6FA4; }
        """)
        mark_btn.setCursor(Qt.PointingHandCursor)
        mark_btn.clicked.connect(self._mark_all)
        h_lay.addWidget(mark_btn)

        outer.addWidget(header)

        # ── scroll area ──────────────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll.setFixedHeight(360)
        outer.addWidget(self._scroll)

        # ── footer ───────────────────────────────────────────────────────────
        footer = QFrame()
        footer.setStyleSheet("QFrame { border-top: 1px solid #F3F4F6; background: transparent; }")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(14, 8, 14, 8)

        clear_btn = QPushButton(f"🗑️  {self._('clear_all_notifications')}")
        clear_btn.setFont(QFont("Tajawal", 9))
        clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #9CA3AF;
            }
            QPushButton:hover { color: #E74C3C; }
        """)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear)
        f_lay.addWidget(clear_btn)
        f_lay.addStretch()

        outer.addWidget(footer)

        # connect service
        self._svc.notifications_updated.connect(self._refresh)
        self._refresh()

    def _refresh(self):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)

        notifs = self._svc.notifications
        if not notifs:
            empty = QLabel(self._("no_notifications"))
            empty.setFont(QFont("Tajawal", 10))
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #9CA3AF; padding: 30px; background: transparent;")
            lay.addWidget(empty)
        else:
            for n in notifs[:30]:
                item = _NotifItem(n, self._item_clicked)
                lay.addWidget(item)

        lay.addStretch()
        self._scroll.setWidget(container)

    def _item_clicked(self, notif: Notification):
        self._svc.mark_read(notif.id)
        self._refresh()

    def _mark_all(self):
        self._svc.mark_all_read()

    def _clear(self):
        self._svc.clear_all()
        self.hide()


class NotificationBell(QWidget):
    """
    Bell icon + badge.  Drop into any layout.

    Connects automatically to NotificationService singleton.
    Object names use theme CSS (topbar-btn style).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._svc   = NotificationService.get_instance()
        self._       = TranslationManager.get_instance().translate
        self._popup: NotificationPopup | None = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # container for bell + badge overlay
        btn_container = QWidget()
        btn_container.setFixedSize(40, 36)
        c_lay = QHBoxLayout(btn_container)
        c_lay.setContentsMargins(0, 0, 0, 0)

        # bell button
        self._btn = QPushButton("🔔")
        self._btn.setObjectName("topbar-btn")
        self._btn.setFixedSize(36, 36)
        self._btn.setFont(QFont("Segoe UI Emoji", 14))
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setToolTip(self._("notifications"))
        self._btn.clicked.connect(self._toggle_popup)
        c_lay.addWidget(self._btn)

        # unread badge
        self._badge = QLabel("0")
        self._badge.setObjectName("notif-badge")
        self._badge.setFont(QFont("Tajawal", 7, QFont.Bold))
        self._badge.setAlignment(Qt.AlignCenter)
        self._badge.setFixedSize(16, 16)
        self._badge.setStyleSheet("""
            QLabel#notif-badge {
                background: #E74C3C;
                color: white;
                border-radius: 8px;
                font-size: 7px;
                font-weight: bold;
            }
        """)
        self._badge.setParent(btn_container)
        self._badge.move(22, 0)
        self._badge.hide()

        lay.addWidget(btn_container)

        # signals
        self._svc.unread_count_changed.connect(self._update_badge)
        self._update_badge(self._svc.unread_count)

    def _update_badge(self, count: int):
        if count > 0:
            self._badge.setText(str(count) if count < 100 else "99+")
            self._badge.show()
        else:
            self._badge.hide()

    def _toggle_popup(self):
        if self._popup and self._popup.isVisible():
            self._popup.hide()
            return

        if self._popup is None:
            self._popup = NotificationPopup()

        # position below the bell button
        global_pos = self._btn.mapToGlobal(QPoint(0, self._btn.height() + 4))
        # adjust so popup doesn't go off screen
        screen_rect = QApplication.primaryScreen().availableGeometry()
        px = global_pos.x() - self._popup.width() + self._btn.width()
        px = max(screen_rect.left(), min(px, screen_rect.right() - self._popup.width()))
        py = global_pos.y()

        self._popup.move(px, py)
        self._popup.show()
        self._popup.raise_()

    # ── theme reload hook ─────────────────────────────────────────────────────
    def retranslate_ui(self):
        self._ = TranslationManager.get_instance().translate
        self._btn.setToolTip(self._("notifications"))
