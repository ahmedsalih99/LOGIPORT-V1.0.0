"""
ui/dialogs/sync_settings_dialog.py — LOGIPORT
================================================
Dialog إعدادات المزامنة مع Supabase.

إصلاحات:
  - [BUG FIX] لا يُغلق الـ dialog تلقائياً بعد الحفظ
  - [BUG FIX] البيانات لا تُمسح عند فتح الـ dialog
      (textChanged كان يُطلق _on_credentials_changed أثناء _load → يمسح combo)
  - [BUG FIX] اختبار الاتصال يعرض خطأ واضح ولا يعلق
  - [BUG FIX] timeout قصير لاختبار الاتصال (5 ثوان)
"""
from __future__ import annotations

import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QFrame, QSpinBox,
    QWidget,
)

from core.translator import TranslationManager
from core.settings_manager import SettingsManager
from core.base_dialog import BaseDialog
from ui.utils.wheel_blocker import block_wheel_in


class SyncSettingsDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._           = TranslationManager.get_instance().translate
        self.sm          = SettingsManager.get_instance()
        self._loading    = False   # [FIX] flag لمنع textChanged أثناء _load
        self._test_thread: threading.Thread | None = None
        self.setWindowTitle(self._("sync_settings_title"))
        self.setMinimumWidth(520)
        self.setModal(True)
        self._build()
        self._load()

    # ── Build UI ─────────────────────────────────────────

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)

        # Header
        title = QLabel(self._("sync_supabase_title"))
        title.setObjectName("dialog-title")
        title.setStyleSheet("font-size:16px; font-weight:600;")
        lay.addWidget(title)

        sub = QLabel(self._("sync_settings_desc"))
        sub.setObjectName("form-hint")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        lay.addWidget(self._separator())

        # Form
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(12)

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://xxxxxxxxxxxx.supabase.co")
        self._url_edit.setObjectName("form-input")
        # [FIX] textChanged يمسح فقط رسالة الحالة — لا يمس الـ combo
        self._url_edit.textChanged.connect(self._on_credentials_changed)
        form.addRow(self._("sync_project_url_label"), self._url_edit)

        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText("eyJhbGci...")
        self._key_edit.setObjectName("form-input")
        self._key_edit.setEchoMode(QLineEdit.Password)
        self._key_edit.textChanged.connect(self._on_credentials_changed)

        key_row = QHBoxLayout()
        key_row.addWidget(self._key_edit)
        self._show_key_btn = QPushButton(self._("show_key"))
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
        form.addRow(self._("sync_office_label"), self._office_combo)

        lay.addLayout(form)

        lay.addWidget(self._separator())

        # Auto-sync options
        auto_row = QHBoxLayout()
        self._auto_chk = QCheckBox(self._("sync_auto_enable"))
        self._auto_chk.setObjectName("form-checkbox")
        auto_row.addWidget(self._auto_chk)
        auto_row.addStretch()

        interval_lbl = QLabel(self._("sync_interval_prefix"))
        auto_row.addWidget(interval_lbl)
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 60)
        self._interval_spin.setValue(5)
        self._interval_spin.setSuffix(" " + self._("sync_interval_suffix"))
        self._interval_spin.setFixedWidth(100)
        auto_row.addWidget(self._interval_spin)
        lay.addLayout(auto_row)

        # Status label
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("form-hint")
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setMinimumHeight(20)
        lay.addWidget(self._status_lbl)

        lay.addStretch()
        lay.addWidget(self._separator())

        # Buttons
        btn_row = QHBoxLayout()

        self._test_btn = QPushButton(self._("sync_test_connection"))
        self._test_btn.setObjectName("secondary-btn")
        self._test_btn.clicked.connect(self._test_connection)

        self._save_btn = QPushButton(self._("save"))
        self._save_btn.setObjectName("primary-btn")
        self._save_btn.clicked.connect(self._save)

        cancel_btn = QPushButton(self._("cancel"))
        cancel_btn.setObjectName("secondary-btn")
        cancel_btn.clicked.connect(self.reject)

        btn_row.addWidget(self._test_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._save_btn)
        lay.addLayout(btn_row)

    # ── Load / Save ──────────────────────────────────────

    def _load(self):
        # [FIX] نرفع الـ flag حتى textChanged لا يُنفّذ _on_credentials_changed
        self._loading = True
        try:
            self._url_edit.setText(self.sm.get("sync_supabase_url", ""))
            self._key_edit.setText(self.sm.get("sync_anon_key", ""))
            self._auto_chk.setChecked(
                self.sm.get("sync_enabled", "false").lower() == "true"
            )
            self._interval_spin.setValue(
                int(self.sm.get("sync_interval_min", "5") or "5")
            )
            # اختيار المكتب المحفوظ
            saved_office = str(self.sm.get("sync_office_id", "") or "")
            for i in range(self._office_combo.count()):
                if str(self._office_combo.itemData(i)) == saved_office:
                    self._office_combo.setCurrentIndex(i)
                    break
        finally:
            self._loading = False

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
        except Exception:
            pass

        # [FIX] لا يُغلق الـ dialog — يعرض رسالة نجاح فقط
        self._show_status(self._("sync_status_saved"), success=True)

    # ── Test connection ───────────────────────────────────

    def _test_connection(self):
        url = self._url_edit.text().strip().rstrip("/")
        key = self._key_edit.text().strip()

        if not url or not key:
            self._show_status(self._("sync_status_url_key_required"), success=False)
            return

        # منع تشغيل اختبارين متوازيين
        if self._test_thread and self._test_thread.is_alive():
            return

        self._test_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        self._show_status(self._("sync_status_testing"), success=None)

        # [FIX] نحفظ reference للـ widget قبل الـ thread
        test_btn  = self._test_btn
        save_btn  = self._save_btn
        status_fn = self._show_status

        def _do_test():
            import urllib.error
            from services.supabase_client import SupabaseClient, SupabaseError

            result_ok    = False
            result_error = ""

            try:
                # test_credentials يتحقق فعلياً من الـ key (يُطلق 401 إذا خاطئ)
                client = SupabaseClient(url, key, ping_timeout=8)
                result_ok = client.test_credentials()

            except SupabaseError as e:
                if e.status == 401:
                    result_error = self._("sync_error_unauthorized")
                elif e.status == 404:
                    result_error = self._("sync_error_not_found")
                else:
                    result_error = f"HTTP {e.status}"

            except urllib.error.URLError as e:
                result_error = self._("sync_error_network")

            except OSError:
                result_error = self._("sync_error_network")

            except Exception as e:
                result_error = str(e)[:80]

            def _apply():
                if not test_btn or not test_btn.isVisible():
                    return
                test_btn.setEnabled(True)
                save_btn.setEnabled(True)
                if result_ok:
                    status_fn(self._("sync_status_connected"), success=True)
                else:
                    status_fn(result_error or self._("sync_status_failed"), success=False)

            QTimer.singleShot(0, _apply)

        self._test_thread = threading.Thread(target=_do_test, daemon=True)
        self._test_thread.start()

    # ── Helpers ──────────────────────────────────────────

    def _on_credentials_changed(self):
        # [FIX] لا نُنفّذ أثناء _load() — ولا نمس الـ combo أبداً
        if self._loading:
            return
        self._status_lbl.clear()

    def _load_offices(self):
        self._office_combo.clear()
        self._office_combo.addItem(self._("sync_select_office"), None)
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
            self._show_key_btn.setText(self._("sync_hide_key"))
        else:
            self._key_edit.setEchoMode(QLineEdit.Password)
            self._show_key_btn.setText(self._("show_key"))

    def _separator(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setObjectName("form-separator")
        block_wheel_in(self)
        return f