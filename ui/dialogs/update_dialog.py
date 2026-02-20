"""
ui/dialogs/update_dialog.py — LOGIPORT
========================================
نافذة إشعار التحديث — تظهر عند اكتشاف إصدار جديد.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTextEdit, QWidget
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class UpdateDialog(QDialog):
    """
    نافذة التحديث.
    تُعرض عند اكتشاف إصدار أحدث.
    """

    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self._downloading = False

        self.setWindowTitle("تحديث متاح — LOGIPORT")
        self.setMinimumWidth(480)
        self.setModal(True)

        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        # ── العنوان ──────────────────────────────────────────────────────────
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
        self._progress.setFormat("جاري التنزيل... %p%")
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

        self._btn_update = QPushButton("تحديث الآن ⬇")
        self._btn_update.setMinimumHeight(36)
        self._btn_update.setDefault(True)
        self._btn_update.clicked.connect(self._start_download)
        btn_row.addWidget(self._btn_update)

        layout.addLayout(btn_row)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background: #1e2130; color: #e0e6f0; }
            QLabel  { color: #e0e6f0; }
            QTextEdit {
                background: #252840; border: 1px solid #3a4060;
                border-radius: 6px; color: #c0c8e0; padding: 6px;
            }
            QProgressBar {
                background: #252840; border: 1px solid #3a4060;
                border-radius: 6px; height: 20px; color: white; text-align: center;
            }
            QProgressBar::chunk { background: #4a7cf0; border-radius: 5px; }
            QPushButton {
                background: #2e3450; border: 1px solid #3a4060;
                border-radius: 8px; color: #e0e6f0; padding: 8px 20px;
                font-family: Tajawal; font-size: 10pt;
            }
            QPushButton:hover   { background: #3a4470; }
            QPushButton[default="true"] {
                background: #4a7cf0; border-color: #5a8cf8;
            }
            QPushButton[default="true"]:hover { background: #5a8cf8; }
            QPushButton:disabled { background: #252840; color: #606880; }
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
        self._status_lbl.setText("✅ تم التنزيل. سيبدأ التثبيت تلقائياً...")
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
