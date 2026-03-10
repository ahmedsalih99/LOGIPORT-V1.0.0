"""
ui/dialogs/sync_settings_dialog.py — LOGIPORT
================================================
Dialog إعدادات المزامنة مع Supabase.

يتيح للمستخدم:
  - إدخال Supabase URL + Anon Key
  - اختيار ID المكتب الحالي
  - تفعيل/إيقاف الـ sync التلقائي
  - اختبار الاتصال
  - حفظ الإعدادات
"""
from __future__ import annotations

import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QFrame, QSpinBox, QMessageBox,
    QWidget,
)

from core.translator import TranslationManager
from core.settings_manager import SettingsManager


class SyncSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._  = TranslationManager.get_instance().translate
        self.sm = SettingsManager.get_instance()
        self.setWindowTitle("إعدادات المزامنة")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._build()
        self._load()

    # ── Build UI ─────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)

        # ── Header ──────────────────────────────────────
        title = QLabel("إعدادات مزامنة Supabase")
        title.setObjectName("dialog-title")
        title.setStyleSheet("font-size:16px; font-weight:600;")
        lay.addWidget(title)

        sub = QLabel(
            "بعد الإعداد، ستتزامن البيانات تلقائياً كل 5 دقائق بين جميع المكاتب."
        )
        sub.setObjectName("form-hint")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        lay.addWidget(self._separator())

        # ── Form ────────────────────────────────────────
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(12)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://xxxxxxxxxxxx.supabase.co")
        self._url_edit.setObjectName("form-input")
        form.addRow("رابط المشروع (Project URL):", self._url_edit)

        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText("eyJhbGci...")
        self._key_edit.setObjectName("form-input")
        self._key_edit.setEchoMode(QLineEdit.Password)
        # زر إظهار/إخفاء
        key_row = QHBoxLayout()
        key_row.addWidget(self._key_edit)
        self._show_key_btn = QPushButton("إظهار")
        self._show_key_btn.setObjectName("secondary-btn")
        self._show_key_btn.setFixedWidth(70)
        self._show_key_btn.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self._show_key_btn)
        key_widget = QWidget()
        key_widget.setLayout(key_row)
        form.addRow("Anon Key:", key_widget)

        self._office_combo = QComboBox()
        self._office_combo.setObjectName("form-combo")
        self._load_offices()
        form.addRow("المكتب الحالي:", self._office_combo)

        lay.addLayout(form)

        lay.addWidget(self._separator())

        # ── Auto-sync options ────────────────────────────
        auto_row = QHBoxLayout()
        self._auto_chk = QCheckBox("تفعيل المزامنة التلقائية")
        self._auto_chk.setObjectName("form-checkbox")
        auto_row.addWidget(self._auto_chk)
        auto_row.addStretch()

        interval_lbl = QLabel("كل")
        auto_row.addWidget(interval_lbl)
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 60)
        self._interval_spin.setValue(5)
        self._interval_spin.setSuffix(" دقيقة")
        self._interval_spin.setFixedWidth(100)
        auto_row.addWidget(self._interval_spin)
        lay.addLayout(auto_row)

        # ── Status label ────────────────────────────────
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("form-hint")
        self._status_lbl.setWordWrap(True)
        lay.addWidget(self._status_lbl)

        lay.addStretch()
        lay.addWidget(self._separator())

        # ── Buttons ─────────────────────────────────────
        btn_row = QHBoxLayout()

        self._test_btn = QPushButton("اختبار الاتصال")
        self._test_btn.setObjectName("secondary-btn")
        self._test_btn.clicked.connect(self._test_connection)

        self._save_btn = QPushButton("حفظ")
        self._save_btn.setObjectName("primary-btn")
        self._save_btn.clicked.connect(self._save)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setObjectName("secondary-btn")
        cancel_btn.clicked.connect(self.reject)

        btn_row.addWidget(self._test_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._save_btn)
        lay.addLayout(btn_row)

    # ── Load / Save ──────────────────────────────────────

    def _load(self):
        self._url_edit.setText(self.sm.get("sync_supabase_url", ""))
        self._key_edit.setText(self.sm.get("sync_anon_key", ""))
        self._auto_chk.setChecked(
            self.sm.get("sync_enabled", "false").lower() == "true"
        )
        self._interval_spin.setValue(
            int(self.sm.get("sync_interval_min", "5") or "5")
        )
        # اختيار المكتب الحالي
        saved_office = str(self.sm.get("sync_office_id", "") or "")
        for i in range(self._office_combo.count()):
            if str(self._office_combo.itemData(i)) == saved_office:
                self._office_combo.setCurrentIndex(i)
                break

    def _save(self):
        url      = self._url_edit.text().strip().rstrip("/")
        key      = self._key_edit.text().strip()
        office   = self._office_combo.currentData()
        enabled  = self._auto_chk.isChecked()
        interval = self._interval_spin.value()

        self.sm.set("sync_supabase_url",  url)
        self.sm.set("sync_anon_key",      key)
        self.sm.set("sync_office_id",     str(office) if office else "")
        self.sm.set("sync_enabled",       "true" if enabled else "false")
        self.sm.set("sync_interval_min",  str(interval))

        # إعادة تهيئة SyncService
        try:
            from services.sync_service import get_sync_service
            svc = get_sync_service()
            svc.stop_auto_sync()
            if enabled and url and key and office:
                svc.configure(
                    office_id=int(office),
                    interval_seconds=interval * 60,
                )
                svc.start_auto_sync()
        except Exception as e:
            pass

        self._show_status("✓ تم الحفظ بنجاح", success=True)
        QTimer.singleShot(800, self.accept)

    # ── Test connection ───────────────────────────────────

    def _test_connection(self):
        url = self._url_edit.text().strip().rstrip("/")
        key = self._key_edit.text().strip()

        if not url or not key:
            self._show_status("⚠ أدخل الـ URL والـ Key أولاً", success=False)
            return

        self._test_btn.setEnabled(False)
        self._show_status("جارٍ الاختبار...", success=None)

        def _do_test():
            from services.supabase_client import SupabaseClient
            client = SupabaseClient(url, key)
            ok = client.ping()
            def _apply():
                self._test_btn.setEnabled(True)
                if ok:
                    self._show_status("✓ الاتصال ناجح — السيرفر يستجيب", success=True)
                else:
                    self._show_status("✗ تعذّر الاتصال — تحقق من الـ URL والـ Key", success=False)
            QTimer.singleShot(0, _apply)

        threading.Thread(target=_do_test, daemon=True).start()

    # ── Helpers ──────────────────────────────────────────

    def _load_offices(self):
        self._office_combo.clear()
        self._office_combo.addItem("— اختر المكتب —", None)
        try:
            from database.models import get_session_local
            from sqlalchemy import text
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                rows = s.execute(
                    text("SELECT id, name_ar, code FROM offices WHERE is_active=1 ORDER BY sort_order, id")
                ).fetchall()
            for row in rows:
                self._office_combo.addItem(f"{row[1]} ({row[2]})", row[0])
        except Exception:
            pass

    def _show_status(self, msg: str, success=None):
        color = {True: "#10B981", False: "#EF4444", None: "#6B7280"}.get(success, "#6B7280")
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color: {color}; font-weight: 500;")

    def _toggle_key_visibility(self):
        if self._key_edit.echoMode() == QLineEdit.Password:
            self._key_edit.setEchoMode(QLineEdit.Normal)
            self._show_key_btn.setText("إخفاء")
        else:
            self._key_edit.setEchoMode(QLineEdit.Password)
            self._show_key_btn.setText("إظهار")

    def _separator(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setObjectName("form-separator")
        return f