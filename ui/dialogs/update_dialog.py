"""
ui/dialogs/update_dialog.py — LOGIPORT
========================================
نافذة إشعار التحديث — تظهر عند اكتشاف إصدار جديد.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTextEdit, QWidget
)
from PySide6.QtCore import Qt, Signal, QThread, Q_ARG
from PySide6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


from core.base_dialog import BaseDialog

class UpdateDialog(BaseDialog):
    """
    نافذة التحديث.
    تُعرض عند اكتشاف إصدار أحدث.
    """

    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self._downloading = False

        self.setWindowTitle(self._("update_available_title"))
        self.setMinimumWidth(480)
        self.setModal(True)

        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Primary header ────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setObjectName("form-dialog-header")
        hl = QVBoxLayout(hdr)
        hl.setContentsMargins(24, 18, 24, 14)
        hl.setSpacing(4)
        title_lbl = QLabel(self._("update_available_title"))
        title_lbl.setObjectName("form-dialog-title")
        from PySide6.QtGui import QFont as _QFont
        f = _QFont(); f.setPointSize(13); f.setBold(True); title_lbl.setFont(f)
        hl.addWidget(title_lbl)
        root.addWidget(hdr)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setObjectName("form-dialog-sep"); sep.setFixedHeight(1)
        root.addWidget(sep)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 18, 24, 20)
        layout.setSpacing(16)
        root.addLayout(layout)
        root.addStretch()

        # ── المحتوى ───────────────────────────────────────────────────────
        title = QLabel("🎉  يتوفر إصدار جديد من LOGIPORT")
        title.setFont(QFont("Tajawal", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # ── رقم الإصدار ──────────────────────────────────────────────────────
        try:
            from version import VERSION as current
        except Exception:
            current = "—"

        version_lbl = QLabel(f"الإصدار الحالي: {current}   →   الإصدار الجديد: {self.update_info.version}")
        version_lbl.setAlignment(Qt.AlignCenter)
        version_lbl.setFont(QFont("Tajawal", 10))
        layout.addWidget(version_lbl)

        # ── ملاحظات الإصدار ───────────────────────────────────────────────────
        if self.update_info.notes:
            notes_lbl = QLabel("ما الجديد:")
            notes_lbl.setFont(QFont("Tajawal", 10, QFont.Bold))
            layout.addWidget(notes_lbl)

            notes_box = QTextEdit()
            notes_box.setReadOnly(True)
            notes_box.setPlainText(self.update_info.notes)
            notes_box.setMaximumHeight(120)
            notes_box.setFont(QFont("Tajawal", 9))
            layout.addWidget(notes_box)

        # ── شريط التقدم ───────────────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._progress.setTextVisible(True)
        self._progress.setFormat(self._("update_downloading"))
        layout.addWidget(self._progress)

        self._status_lbl = QLabel("")
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setVisible(False)
        layout.addWidget(self._status_lbl)

        # ── الأزرار ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._btn_later = QPushButton("لاحقاً")
        self._btn_later.setMinimumHeight(36)
        self._btn_later.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_later)

        self._btn_update = QPushButton(self._("update_now_btn"))
        self._btn_update.setMinimumHeight(36)
        self._btn_update.setDefault(True)
        self._btn_update.clicked.connect(self._start_download)
        btn_row.addWidget(self._btn_update)

        layout.addLayout(btn_row)

    def _apply_style(self):
        try:
            from core.theme_manager import ThemeManager
            c = ThemeManager.get_instance().current_theme.colors
            bg     = c.get("bg_primary",     "#1e2130")
            bg2    = c.get("bg_secondary",   "#252840")
            bg3    = c.get("bg_card",        "#2e3450")
            bdr    = c.get("border",         "#3a4060")
            txt_p  = c.get("text_primary",   "#e0e6f0")
            txt_s  = c.get("text_secondary", "#c0c8e0")
            txt_d  = c.get("text_disabled",  "#606880")
            txt_w  = c.get("text_white",     "white")
            pri    = c.get("primary",        "#4a7cf0")
            pri_h  = c.get("primary_hover",  "#5a8cf8")
            bg_h   = c.get("bg_hover",       "#3a4470")
        except Exception:
            bg, bg2, bg3     = "#1e2130", "#252840", "#2e3450"
            bdr               = "#3a4060"
            txt_p, txt_s      = "#e0e6f0", "#c0c8e0"
            txt_d, txt_w      = "#606880", "white"
            pri, pri_h, bg_h  = "#4a7cf0", "#5a8cf8", "#3a4470"

        self.setStyleSheet(f"""
            QDialog {{ background: {bg}; color: {txt_p}; }}
            QLabel  {{ color: {txt_p}; }}
            QTextEdit {{
                background: {bg2}; border: 1px solid {bdr};
                border-radius: 6px; color: {txt_s}; padding: 6px;
            }}
            QProgressBar {{
                background: {bg2}; border: 1px solid {bdr};
                border-radius: 6px; height: 20px; color: {txt_w}; text-align: center;
            }}
            QProgressBar::chunk {{ background: {pri}; border-radius: 5px; }}
            QPushButton {{
                background: {bg3}; border: 1px solid {bdr};
                border-radius: 8px; color: {txt_p}; padding: 8px 20px;
                font-family: Tajawal; font-size: 10pt;
            }}
            QPushButton:hover   {{ background: {bg_h}; }}
            QPushButton[default="true"] {{
                background: {pri}; border-color: {pri_h};
            }}
            QPushButton[default="true"]:hover {{ background: {pri_h}; }}
            QPushButton:disabled {{ background: {bg2}; color: {txt_d}; }}
        """)

    def _start_download(self):
        if self._downloading:
            return
        self._downloading = True

        self._btn_update.setEnabled(False)
        self._btn_later.setEnabled(False)
        self._progress.setVisible(True)

        from services.updater_service import UpdaterService
        UpdaterService.get_instance().download_and_install(
            self.update_info,
            on_progress=self._on_progress,
            on_done=self._on_done,
        )

    def _on_progress(self, percent: int):
        # يُستدعى من thread آخر — نستخدم QMetaObject للأمان
        from PySide6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(
            self._progress, "setValue",
            Qt.QueuedConnection,
            Q_ARG(int, percent),
        )

    def _on_done(self, success: bool, message: str):
        from PySide6.QtCore import QMetaObject, Qt
        if success:
            QMetaObject.invokeMethod(self, "_show_success", Qt.QueuedConnection)
        else:
            QMetaObject.invokeMethod(
                self, "_show_error",
                Qt.QueuedConnection,
                Q_ARG(str, message),
            )

    def _show_success(self):
        self._status_lbl.setText(self._("update_done"))
        self._status_lbl.setVisible(True)
        self._progress.setValue(100)
        # أغلق النافذة بعد ثانيتين
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, self.accept)

    def _show_error(self, message: str):
        self._status_lbl.setText(f"❌ فشل التنزيل: {message}")
        self._status_lbl.setVisible(True)
        self._btn_later.setEnabled(True)
        self._btn_update.setEnabled(True)
        self._downloading = False