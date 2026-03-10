"""
NotificationBell Widget - LOGIPORT
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QApplication
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QCursor
from services.notification_service import NotificationService, Notification
from core.translator import TranslationManager
from ui.utils.svg_icons import set_icon


def _theme_colors() -> dict:
    try:
        from core.theme_manager import ThemeManager
        from core.settings_manager import SettingsManager
        theme_name = SettingsManager.get_instance().get("theme", "light")
        from config.themes.semantic_colors import SemanticColors
        return SemanticColors.get(theme_name)
    except Exception:
        return {}


def _level_styles(c: dict) -> dict:
    return {
        "success": (c.get("success","#2ECC71"), c.get("success_light","rgba(46,204,113,0.12)")),
        "info":    (c.get("info",   "#3498DB"), c.get("info_light",   "rgba(52,152,219,0.12)")),
        "warning": (c.get("warning","#F39C12"), c.get("warning_light","rgba(243,156,18,0.12)")),
        "danger":  (c.get("danger", "#E74C3C"), c.get("danger_light", "rgba(231,76,60,0.12)")),
    }


class _NotifItem(QFrame):
    def __init__(self, notif: Notification, on_click, parent=None):
        super().__init__(parent)
        self._notif = notif
        self._on_click = on_click
        self.setObjectName("notif-item")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        c = _theme_colors()
        levels = _level_styles(c)
        accent, bg = levels.get(notif.level, levels["info"])
        text_c  = c.get("text_primary", "#1F2937")
        muted_c = c.get("text_muted",   "#6B7280")
        bg_normal = bg if not notif.is_read else "transparent"
        border_c  = accent if not notif.is_read else "transparent"
        self.setStyleSheet(f"""
            QFrame#notif-item {{
                background: {bg_normal}; border-radius: 8px;
                border-right: 3px solid {border_c}; padding: 2px;
            }}
            QFrame#notif-item:hover {{ background: {bg}; border-right: 3px solid {accent}; }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(8)
        icon_lbl = QLabel(notif.icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 14))
        icon_lbl.setFixedSize(30, 30)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"background: {accent}; border-radius: 15px; color: white;")
        lay.addWidget(icon_lbl)
        txt_col = QVBoxLayout()
        txt_col.setSpacing(2)
        w = QFont.DemiBold if not notif.is_read else QFont.Normal
        msg_lbl = QLabel(notif.message)
        msg_lbl.setFont(QFont("Tajawal", 9, w))
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(f"color: {text_c}; background: transparent;")
        txt_col.addWidget(msg_lbl)
        time_lbl = QLabel(notif.time_ago)
        time_lbl.setFont(QFont("Tajawal", 8))
        time_lbl.setStyleSheet(f"color: {muted_c}; background: transparent;")
        txt_col.addWidget(time_lbl)
        lay.addLayout(txt_col, 1)
        if not notif.is_read:
            dot = QLabel("●")
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"color: {accent}; font-size: 8px; background: transparent;")
            lay.addWidget(dot, 0, Qt.AlignTop)

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                self._on_click(self._notif)
            super().mousePressEvent(event)
        except RuntimeError:
            pass  # C++ object already deleted — ignore safely


class NotificationPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("notif-popup")
        self.setFixedWidth(340)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._svc = NotificationService.get_instance()
        self._ = TranslationManager.get_instance().translate
        c = _theme_colors()
        bg_card    = c.get("bg_card",       "#FFFFFF")
        border_c   = c.get("border",        "#E5E7EB")
        border_sub = c.get("border_subtle", "#F3F4F6")
        text_prim  = c.get("text_primary",  "#1F2937")
        text_muted = c.get("text_muted",    "#9CA3AF")
        primary_c  = c.get("primary",       "#3498DB")
        primary_hov= c.get("primary_active","#1D6FA4")
        danger_c   = c.get("danger",        "#E74C3C")
        self.setStyleSheet(f"QFrame#notif-popup {{ background: {bg_card}; border: 1px solid {border_c}; border-radius: 12px; }}")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        # header
        header = QFrame()
        header.setObjectName("notif-header")
        header.setStyleSheet(f"QFrame#notif-header {{ background: transparent; border-bottom: 1px solid {border_sub}; border-radius: 0px; padding: 4px 0; }}")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(14, 10, 14, 10)
        title_lbl = QLabel(f"🔔  {self._('notifications')}")
        title_lbl.setFont(QFont("Tajawal", 12, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {text_prim}; background: transparent;")
        h_lay.addWidget(title_lbl)
        h_lay.addStretch()
        mark_btn = QPushButton(self._("mark_all_read"))
        mark_btn.setFont(QFont("Tajawal", 8))
        mark_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {primary_c}; padding: 2px 6px; }} QPushButton:hover {{ color: {primary_hov}; }}")
        mark_btn.setCursor(Qt.PointingHandCursor)
        mark_btn.clicked.connect(self._mark_all)
        h_lay.addWidget(mark_btn)
        outer.addWidget(header)
        # scroll
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll.setFixedHeight(360)
        outer.addWidget(self._scroll)
        # footer
        footer = QFrame()
        footer.setStyleSheet(f"QFrame {{ border-top: 1px solid {border_sub}; background: transparent; }}")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(14, 8, 14, 8)
        clear_btn = QPushButton(f"🗑️  {self._('clear_all_notifications')}")
        clear_btn.setFont(QFont("Tajawal", 9))
        clear_btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; color: {text_muted}; }} QPushButton:hover {{ color: {danger_c}; }}")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear)
        f_lay.addWidget(clear_btn)
        f_lay.addStretch()
        outer.addWidget(footer)
        self._svc.notifications_updated.connect(self._refresh)
        self._refresh()

    def _refresh(self):
        c = _theme_colors()
        muted_c = c.get("text_muted", "#9CA3AF")
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
            empty.setStyleSheet(f"color: {muted_c}; padding: 30px; background: transparent;")
            lay.addWidget(empty)
        else:
            for n in notifs[:30]:
                lay.addWidget(_NotifItem(n, self._item_clicked))
        lay.addStretch()
        self._scroll.setWidget(container)

    def _item_clicked(self, notif):
        self._svc.mark_read(notif.id)
        self._refresh()

    def _mark_all(self):
        self._svc.mark_all_read()

    def _clear(self):
        self._svc.clear_all()
        self.hide()


class NotificationBell(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._svc = NotificationService.get_instance()
        self._ = TranslationManager.get_instance().translate
        self._popup = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        btn_container = QWidget()
        btn_container.setFixedSize(38, 34)
        c_lay = QHBoxLayout(btn_container)
        c_lay.setContentsMargins(0, 0, 0, 0)
        self._btn = QPushButton()
        self._btn.setObjectName("topbar-tool-btn")
        self._btn.setFixedSize(34, 34)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setToolTip(self._("notifications"))
        self._btn.clicked.connect(self._toggle_popup)
        set_icon(self._btn, "bell", size=18)
        c_lay.addWidget(self._btn)
        c = _theme_colors()
        danger = c.get("danger", "#E74C3C")
        self._badge = QLabel("0")
        self._badge.setObjectName("notif-badge")
        self._badge.setFont(QFont("Tajawal", 7, QFont.Bold))
        self._badge.setAlignment(Qt.AlignCenter)
        self._badge.setFixedSize(16, 16)
        self._badge.setStyleSheet(f"QLabel#notif-badge {{ background: {danger}; color: white; border-radius: 8px; font-size: 7px; font-weight: bold; }}")
        self._badge.setParent(btn_container)
        self._badge.move(20, 0)
        self._badge.hide()
        lay.addWidget(btn_container)
        self._svc.unread_count_changed.connect(self._update_badge)
        self._update_badge(self._svc.unread_count)
        # ربط تغيير الثيم
        try:
            from core.theme_manager import ThemeManager
            ThemeManager.get_instance().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

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
        # نعيد الإنشاء في كل مرة حتى يأخذ ألوان الثيم الحالي
        if self._popup is not None:
            self._popup.deleteLater()
        self._popup = NotificationPopup()
        global_pos = self._btn.mapToGlobal(QPoint(0, self._btn.height() + 4))
        screen_rect = QApplication.primaryScreen().availableGeometry()
        px = global_pos.x() - self._popup.width() + self._btn.width()
        px = max(screen_rect.left(), min(px, screen_rect.right() - self._popup.width()))
        self._popup.move(px, global_pos.y())
        self._popup.show()
        self._popup.raise_()

    def retranslate_ui(self):
        self._ = TranslationManager.get_instance().translate
        self._btn.setToolTip(self._("notifications"))

    def _on_theme_changed(self, _=None):
        set_icon(self._btn, "bell", 18)