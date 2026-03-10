"""
ui/widgets/sync_widget.py — LOGIPORT
======================================
مؤشر حالة المزامنة في الـ TopBar.

يعرض:
  ● أيقونة cloud + نقطة ملوّنة (أخضر=متصل / رمادي=offline / أصفر=جاري)
  ● tooltip بآخر وقت مزامنة
  ● عند الضغط: يُشغّل sync يدوي أو يفتح إعدادات الـ sync
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QPushButton, QWidget, QHBoxLayout, QLabel,
    QMenu, QApplication,
)

from core.translator import TranslationManager
from ui.utils.svg_icons import set_icon


# ─────────────────────────────────────────────────────────
# _StatusDot — نقطة ملوّنة صغيرة
# ─────────────────────────────────────────────────────────

class _StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self._color = QColor("#9CA3AF")   # رمادي افتراضي

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self._color))
        p.drawEllipse(0, 0, 8, 8)


# ─────────────────────────────────────────────────────────
# SyncWidget
# ─────────────────────────────────────────────────────────

class SyncWidget(QWidget):
    """
    مؤشر المزامنة في الـ TopBar.
    استخدام:
        widget = SyncWidget()
        layout.addWidget(widget)
        widget.start()   # يبدأ polling الحالة
    """

    sync_settings_requested = Signal()   # فتح dialog إعدادات الـ sync

    # الحالات
    STATE_DISABLED  = "disabled"
    STATE_OFFLINE   = "offline"
    STATE_SYNCING   = "syncing"
    STATE_OK        = "ok"
    STATE_ERROR     = "error"

    _DOT_COLORS = {
        STATE_DISABLED: "#9CA3AF",   # رمادي
        STATE_OFFLINE:  "#F59E0B",   # أصفر
        STATE_SYNCING:  "#3B82F6",   # أزرق
        STATE_OK:       "#10B981",   # أخضر
        STATE_ERROR:    "#EF4444",   # أحمر
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._      = TranslationManager.get_instance().translate
        self._state = self.STATE_DISABLED
        self._last_sync_time: Optional[str] = None
        self._spin_angle    = 0
        self._spin_timer    = QTimer(self)
        self._spin_timer.timeout.connect(self._spin_tick)
        self._poll_timer    = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_status)
        self._build()

    # ── UI ───────────────────────────────────────────────

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        self._btn = QPushButton()
        self._btn.setObjectName("topbar-tool-btn")
        self._btn.setFixedSize(32, 32)
        self._btn.setCursor(Qt.PointingHandCursor)
        set_icon(self._btn, "sync", 17)
        self._btn.clicked.connect(self._on_click)
        self._btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self._btn.customContextMenuRequested.connect(self._show_menu)

        self._dot = _StatusDot(self._btn)
        self._dot.move(20, 20)   # bottom-right داخل الزر

        lay.addWidget(self._btn)
        self._update_tooltip()

    # ── Public ───────────────────────────────────────────

    def start(self):
        """يبدأ polling دوري كل 30 ثانية للتحقق من حالة الـ sync."""
        self._poll_status()
        self._poll_timer.start(30_000)

    def stop(self):
        self._poll_timer.stop()
        self._spin_timer.stop()

    def set_state(self, state: str, last_sync: Optional[str] = None):
        self._state = state
        if last_sync:
            self._last_sync_time = last_sync
        self._dot.set_color(self._DOT_COLORS.get(state, "#9CA3AF"))
        if state == self.STATE_SYNCING:
            self._spin_timer.start(100)
        else:
            self._spin_timer.stop()
        self._update_tooltip()

    # ── Internals ────────────────────────────────────────

    def _on_click(self):
        from services.sync_service import get_sync_service
        svc = get_sync_service()

        if not svc.is_enabled():
            self.sync_settings_requested.emit()
            return

        if svc.is_running():
            return   # لا نبدأ sync متوازي

        self.set_state(self.STATE_SYNCING)
        svc.sync_now(callback=self._on_sync_done)

    def _on_sync_done(self, result):
        # يُستدعى من thread — نستخدم QTimer.singleShot للـ UI thread
        def _update():
            ts = datetime.now().strftime("%H:%M")
            if result.success:
                self.set_state(self.STATE_OK, last_sync=ts)
            else:
                self.set_state(self.STATE_ERROR)
            self._show_toast(result.summary())
        QTimer.singleShot(0, _update)

    def _poll_status(self):
        """يتحقق من حالة الاتصال بالسيرفر."""
        from services.sync_service import get_sync_service
        svc = get_sync_service()

        if not svc.is_enabled():
            self.set_state(self.STATE_DISABLED)
            return
        if svc.is_running():
            return   # لا نتدخل

        import threading
        def _check():
            from services.supabase_client import get_supabase_client
            client = get_supabase_client()
            online = client.ping() if client else False
            def _apply():
                self.set_state(self.STATE_OK if online else self.STATE_OFFLINE)
            QTimer.singleShot(0, _apply)
        threading.Thread(target=_check, daemon=True).start()

    def _spin_tick(self):
        """تأثير دوران بسيط — يُبدّل بين أيقونتين."""
        self._spin_angle = (self._spin_angle + 1) % 2
        # نغيّر opacity الزر تأثير بسيط
        opacity = 0.6 if self._spin_angle == 0 else 1.0
        self._btn.setStyleSheet(f"opacity: {opacity};")

    def _show_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("مزامنة الآن",         self._on_click)
        menu.addAction("إعدادات المزامنة",     self.sync_settings_requested.emit)
        menu.exec(self._btn.mapToGlobal(pos))

    def _update_tooltip(self):
        labels = {
            self.STATE_DISABLED: "المزامنة غير مفعّلة",
            self.STATE_OFFLINE:  "لا يوجد اتصال بالسيرفر",
            self.STATE_SYNCING:  "جارٍ المزامنة...",
            self.STATE_OK:       "متصل",
            self.STATE_ERROR:    "فشلت المزامنة",
        }
        tip = labels.get(self._state, "")
        if self._last_sync_time and self._state == self.STATE_OK:
            tip += f"\nآخر مزامنة: {self._last_sync_time}"
        self._btn.setToolTip(tip)

    def _show_toast(self, message: str):
        """يعرض رسالة بسيطة في statusbar الـ MainWindow."""
        try:
            app = QApplication.instance()
            for w in app.topLevelWidgets():
                if hasattr(w, "statusBar"):
                    w.statusBar().showMessage(message, 4000)
                    return
        except Exception:
            pass