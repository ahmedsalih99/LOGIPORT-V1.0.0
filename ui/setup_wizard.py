"""
ui/setup_wizard.py — LOGIPORT
================================
نافذة الإعداد الأولي — تظهر مرة واحدة فقط عند أول تشغيل.

وضعان:
  ① إعداد جديد: إنشاء حساب SuperAdmin (للتثبيت الأول)
  ② ربط بمكتب موجود: إدخال بيانات Supabase ومزامنة البيانات
     (للكمبيوتر الجديد الذي يريد الاتصال بقاعدة بيانات موجودة)
"""

import logging
import threading

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QSizePolicy,
    QApplication, QProgressBar, QComboBox, QStackedWidget,
    QSpinBox, QWidget,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap

from core.translator import TranslationManager
from core.base_dialog import BaseDialog

logger = logging.getLogger(__name__)


class SetupWizard(BaseDialog):
    """
    نافذة الإعداد الأولي للتطبيق.
    تظهر مرة واحدة فقط عند أول تشغيل حين لا يوجد أي مستخدم.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SetupWizard")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        self.setModal(True)

        self.setup_done       = False
        self.created_username = ""

        self._ = TranslationManager.get_instance().translate
        TranslationManager.get_instance().language_changed.connect(self._retranslate)
        self._set_size()
        self._build_ui()
        self._apply_style()

    def _set_size(self):
        screen = QApplication.primaryScreen()
        sg = screen.availableGeometry()
        w = min(560, int(sg.width() * 0.42))
        h = min(700, int(sg.height() * 0.85))
        self.setFixedSize(w, h)

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle(self._("setup_wizard_title"))
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("WizardHeader")
        header.setFixedHeight(130)
        h_lay = QVBoxLayout(header)
        h_lay.setAlignment(Qt.AlignCenter)
        h_lay.setSpacing(4)
        try:
            from core.paths import icons_path
            logo_path = icons_path("logo.png")
            if logo_path.exists():
                logo_lbl = QLabel()
                pix = QPixmap(str(logo_path)).scaledToHeight(46, Qt.SmoothTransformation)
                logo_lbl.setPixmap(pix)
                logo_lbl.setAlignment(Qt.AlignCenter)
                h_lay.addWidget(logo_lbl)
        except Exception:
            pass
        title_lbl = QLabel(self._("setup_welcome_title"))
        title_lbl.setObjectName("WizardTitle")
        title_lbl.setAlignment(Qt.AlignCenter)
        h_lay.addWidget(title_lbl)
        root.addWidget(header)

        # Mode selector
        mode_frame = QFrame()
        mode_frame.setObjectName("WizardModeBar")
        mode_lay = QHBoxLayout(mode_frame)
        mode_lay.setContentsMargins(16, 10, 16, 10)
        mode_lay.setSpacing(8)

        self.btn_new    = QPushButton("🆕  " + self._("setup_mode_new"))
        self.btn_connect = QPushButton("🔗  " + self._("setup_mode_connect"))
        for btn in (self.btn_new, self.btn_connect):
            btn.setObjectName("WizardModeBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(36)
        self.btn_new.setChecked(True)
        self.btn_new.clicked.connect(lambda: self._switch_mode(0))
        self.btn_connect.clicked.connect(lambda: self._switch_mode(1))
        mode_lay.addWidget(self.btn_new)
        mode_lay.addWidget(self.btn_connect)
        root.addWidget(mode_frame)

        # Stack — page 0: new setup | page 1: connect
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_page_new())
        self.stack.addWidget(self._build_page_connect())
        root.addWidget(self.stack, 1)

        # Footer
        footer = QFrame()
        footer.setObjectName("WizardFooter")
        footer.setFixedHeight(30)
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(16, 0, 16, 0)
        ver_lbl = QLabel("LOGIPORT v1.0")
        ver_lbl.setObjectName("WizardFooter")
        f_lay.addWidget(ver_lbl)
        f_lay.addStretch()
        root.addWidget(footer)

    def _switch_mode(self, idx: int):
        self.btn_new.setChecked(idx == 0)
        self.btn_connect.setChecked(idx == 1)
        self.stack.setCurrentIndex(idx)

    # ── Page 0: إنشاء حساب جديد ──────────────────────────────

    def _build_page_new(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(10)

        desc = QLabel(self._("setup_desc_new"))
        desc.setObjectName("WizardDesc")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        self._add_field(lay, "👤  " + self._("setup_field_full_name"),
                        "full_name_edit", self._("setup_placeholder_full_name"), False)
        self._add_field(lay, "🔑  " + self._("setup_field_username"),
                        "username_edit",  self._("setup_placeholder_username"),  False)
        self._add_field(lay, "🔒  " + self._("setup_field_password"),
                        "password_edit",  self._("setup_placeholder_password"),  True)
        self._add_field(lay, "🔒  " + self._("setup_field_confirm"),
                        "confirm_edit",   self._("setup_placeholder_confirm"),   True)

        self.error_lbl_new = QLabel()
        self.error_lbl_new.setObjectName("WizardError")
        self.error_lbl_new.setWordWrap(True)
        self.error_lbl_new.hide()
        lay.addWidget(self.error_lbl_new)

        self.progress_new = QProgressBar()
        self.progress_new.setObjectName("WizardProgress")
        self.progress_new.setRange(0, 0)
        self.progress_new.setFixedHeight(4)
        self.progress_new.hide()
        lay.addWidget(self.progress_new)

        lay.addStretch()
        self.create_btn = QPushButton(self._("setup_create_btn"))
        self.create_btn.setObjectName("WizardCreateBtn")
        self.create_btn.setFixedHeight(46)
        self.create_btn.clicked.connect(self._on_create)
        lay.addWidget(self.create_btn)

        return page

    # ── Page 1: ربط بـ Supabase ──────────────────────────────

    def _build_page_connect(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(10)

        desc = QLabel(self._("setup_desc_connect"))
        desc.setObjectName("WizardDesc")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        # URL
        lay.addWidget(self._label("🌐  " + self._("sync_project_url_label")))
        self.conn_url = QLineEdit()
        self.conn_url.setObjectName("WizardFieldEdit")
        self.conn_url.setPlaceholderText("https://xxxxxxxxxxxx.supabase.co")
        lay.addWidget(self.conn_url)

        # Anon Key
        lay.addWidget(self._label("🔑  Anon Key:"))
        key_row = QHBoxLayout()
        self.conn_key = QLineEdit()
        self.conn_key.setObjectName("WizardFieldEdit")
        self.conn_key.setPlaceholderText("eyJhbGci...")
        self.conn_key.setEchoMode(QLineEdit.Password)
        show_btn = QPushButton(self._("show_key"))
        show_btn.setObjectName("WizardModeBtn")
        show_btn.setFixedWidth(60)
        show_btn.clicked.connect(lambda: (
            self.conn_key.setEchoMode(
                QLineEdit.Normal if self.conn_key.echoMode() == QLineEdit.Password
                else QLineEdit.Password
            )
        ))
        key_row.addWidget(self.conn_key)
        key_row.addWidget(show_btn)
        lay.addLayout(key_row)

        # Office selector
        lay.addWidget(self._label("🏢  " + self._("sync_office_label")))
        self.conn_office = QComboBox()
        self.conn_office.setObjectName("WizardFieldEdit")
        self.conn_office.addItem(self._("sync_select_office"), None)
        lay.addWidget(self.conn_office)

        # زر جلب المكاتب
        fetch_btn = QPushButton("🔍  " + self._("setup_fetch_offices"))
        fetch_btn.setObjectName("WizardModeBtn")
        fetch_btn.setFixedHeight(32)
        fetch_btn.clicked.connect(self._fetch_offices)
        lay.addWidget(fetch_btn)

        self.error_lbl_conn = QLabel()
        self.error_lbl_conn.setObjectName("WizardError")
        self.error_lbl_conn.setWordWrap(True)
        self.error_lbl_conn.hide()
        lay.addWidget(self.error_lbl_conn)

        self.progress_conn = QProgressBar()
        self.progress_conn.setObjectName("WizardProgress")
        self.progress_conn.setRange(0, 0)
        self.progress_conn.setFixedHeight(4)
        self.progress_conn.hide()
        lay.addWidget(self.progress_conn)

        lay.addStretch()

        self.connect_btn = QPushButton("🔗  " + self._("setup_connect_btn"))
        self.connect_btn.setObjectName("WizardCreateBtn")
        self.connect_btn.setFixedHeight(46)
        self.connect_btn.clicked.connect(self._on_connect)
        lay.addWidget(self.connect_btn)

        return page

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("WizardFieldLabel")
        return lbl

    def _add_field(self, layout, label_text, attr_name, placeholder, is_password):
        layout.addWidget(self._label(label_text))
        edit = QLineEdit()
        edit.setObjectName("WizardFieldEdit")
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(38)
        if is_password:
            edit.setEchoMode(QLineEdit.Password)
        setattr(self, attr_name, edit)
        layout.addWidget(edit)

    # ── Logic: إنشاء حساب جديد ───────────────────────────────

    def _on_create(self):
        self._clear_error(0)
        full_name = self.full_name_edit.text().strip()
        username  = self.username_edit.text().strip()
        password  = self.password_edit.text()
        confirm   = self.confirm_edit.text()

        if not full_name:
            return self._show_error(0, "❌  " + self._("setup_err_full_name_required"))
        if not username:
            return self._show_error(0, "❌  " + self._("setup_err_username_required"))
        if len(username) < 3:
            return self._show_error(0, "❌  " + self._("setup_err_username_short"))
        if not username.replace("_","").replace("-","").isalnum():
            return self._show_error(0, "❌  " + self._("setup_err_username_invalid"))
        if not password:
            return self._show_error(0, "❌  " + self._("setup_err_password_required"))
        if len(password) < 6:
            return self._show_error(0, "❌  " + self._("setup_err_password_short"))
        if password != confirm:
            return self._show_error(0, "❌  " + self._("setup_err_password_mismatch"))

        self.create_btn.setEnabled(False)
        self.create_btn.setText(self._("setup_creating"))
        self.progress_new.show()
        QApplication.processEvents()

        try:
            from database.bootstrap import create_superadmin
            success = create_superadmin(username=username, password=password, full_name=full_name)
            if success:
                self.created_username = username
                self.setup_done = True
                self._show_success_new(username)
            else:
                self._show_error(0, self._("setup_failed"))
                self._reset_btn(0)
        except Exception as exc:
            logger.error("SetupWizard create error: %s", exc, exc_info=True)
            self._show_error(0, "❌  " + self._("setup_err_generic").format(error=exc))
            self._reset_btn(0)

    def _show_success_new(self, username: str):
        self.progress_new.hide()
        self.create_btn.setText(self._("setup_done"))
        for attr in ("full_name_edit","username_edit","password_edit","confirm_edit"):
            getattr(self, attr).setEnabled(False)
        self._clear_error(0)
        msg = QLabel(self._("setup_success_msg").format(username=username))
        msg.setObjectName("WizardSuccess")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignCenter)
        lay = self.create_btn.parent().layout()
        lay.insertWidget(lay.indexOf(self.create_btn), msg)
        QTimer.singleShot(2000, self.accept)

    # ── Logic: ربط بـ Supabase ────────────────────────────────

    def _fetch_offices(self):
        """يجلب قائمة المكاتب من Supabase."""
        url = self.conn_url.text().strip().rstrip("/")
        key = self.conn_key.text().strip()
        if not url or not key:
            return self._show_error(1, "❌  " + self._("sync_status_url_key_required"))

        self._clear_error(1)
        self.progress_conn.show()
        QApplication.processEvents()

        def _do():
            try:
                from services.supabase_client import SupabaseClient
                client = SupabaseClient(url, key)
                rows = client.select("offices", columns="id,name_ar,code",
                                     filters={"is_active": "eq.true"}, limit=50)
                def _apply():
                    self.progress_conn.hide()
                    self.conn_office.clear()
                    self.conn_office.addItem(self._("sync_select_office"), None)
                    for r in rows:
                        label = f"{r.get('name_ar','')} ({r.get('code','')})"
                        self.conn_office.addItem(label, r["id"])
                    if rows:
                        self._show_error(1, f"✓ تم جلب {len(rows)} مكاتب", success=True)
                    else:
                        self._show_error(1, "⚠ لا توجد مكاتب — تحقق من URL والـ Key")
                QTimer.singleShot(0, _apply)
            except Exception as e:
                def _err():
                    self.progress_conn.hide()
                    self._show_error(1, f"❌ {e}")
                QTimer.singleShot(0, _err)

        threading.Thread(target=_do, daemon=True).start()

    def _on_connect(self):
        """يحفظ بيانات Supabase ويُشغّل مزامنة أولية لجلب البيانات."""
        url     = self.conn_url.text().strip().rstrip("/")
        key     = self.conn_key.text().strip()
        office  = self.conn_office.currentData()

        if not url or not key:
            return self._show_error(1, "❌  " + self._("sync_status_url_key_required"))
        if not office:
            return self._show_error(1, "❌  " + self._("setup_err_select_office"))

        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("⏳  " + self._("setup_syncing"))
        self.progress_conn.show()
        QApplication.processEvents()

        def _do_sync():
            try:
                # ① حفظ الإعدادات
                from core.settings_manager import SettingsManager
                sm = SettingsManager.get_instance()
                sm.set("sync_supabase_url",  url)
                sm.set("sync_anon_key",      key)
                sm.set("sync_office_id",     str(office))
                sm.set("sync_enabled",       "true")
                sm.set("sync_interval_min",  "5")

                # ② مزامنة كاملة — pull فقط لجلب البيانات
                from services.supabase_client import SupabaseClient
                from services.sync_service import get_sync_service
                svc = get_sync_service()
                svc.configure(office_id=int(office), interval_seconds=300)

                # pull كل الجداول يدوياً
                client = SupabaseClient(url, key, office_id=int(office))
                result = self._initial_pull(client, int(office))

                def _done():
                    self.progress_conn.hide()
                    if result["users"] > 0:
                        self.connect_btn.setText(self._("setup_done"))
                        self.setup_done = True
                        msg_text = self._("setup_connect_success").format(
                            users=result["users"],
                            tables=result["tables"],
                        )
                        self._show_error(1, msg_text, success=True)
                        # بعد ثانيتين نغلق
                        QTimer.singleShot(2000, self.accept)
                    else:
                        self._show_error(1, "⚠ " + self._("setup_connect_no_users"))
                        self._reset_btn(1)

                QTimer.singleShot(0, _done)

            except Exception as exc:
                logger.error("SetupWizard connect error: %s", exc, exc_info=True)
                def _err():
                    self.progress_conn.hide()
                    self._show_error(1, f"❌ {exc}")
                    self._reset_btn(1)
                QTimer.singleShot(0, _err)

        threading.Thread(target=_do_sync, daemon=True).start()

    def _initial_pull(self, client, office_id: int) -> dict:
        """يسحب البيانات الأساسية من Supabase لقاعدة البيانات المحلية."""
        from services.sync_service import (
            PULL_ONLY_TABLES, TWO_WAY_TABLES,
            _local, _apply_col_mapping_to_local,
        )
        from database.models import get_session_local
        from sqlalchemy import text

        SessionLocal = get_session_local()
        pulled_tables = 0
        pulled_users  = 0

        # قائمة الجداول بالترتيب الصحيح
        all_pull = (
            ["offices", "countries", "currencies", "material_types", "packaging_types",
             "delivery_methods", "pricing_types", "document_types", "roles",
             "permissions", "role_permissions", "company_roles", "materials"]
            + [t for t in PULL_ONLY_TABLES]
            + [t for t, _ in TWO_WAY_TABLES]
            + ["users"]
        )
        # نزيل المكررات مع الحفاظ على الترتيب
        seen = set()
        ordered = []
        for t in all_pull:
            if t not in seen:
                seen.add(t)
                ordered.append(t)

        for local_tbl in ordered:
            from services.sync_service import _remote
            remote_tbl = _remote(local_tbl)
            try:
                rows = client.select(remote_tbl, limit=2000)
                if not rows:
                    continue

                with SessionLocal() as s:
                    for row in rows:
                        local_row = _apply_col_mapping_to_local(remote_tbl, row)
                        self._upsert_row(s, local_tbl, local_row)
                    s.commit()

                pulled_tables += 1
                if local_tbl == "users":
                    pulled_users = len(rows)

            except Exception as e:
                logger.warning("Initial pull %s: %s", local_tbl, e)

        return {"tables": pulled_tables, "users": pulled_users}

    def _upsert_row(self, s, local_table: str, row: dict):
        """يُدرج أو يُحدِّث سجل في SQLite."""
        from sqlalchemy import text

        # نجلب أعمدة الجدول
        if not hasattr(self, '_col_cache'):
            self._col_cache = {}
        if local_table not in self._col_cache:
            cols_raw = s.execute(text(f"PRAGMA table_info({local_table})")).fetchall()
            self._col_cache[local_table] = {r[1] for r in cols_raw}
        local_cols = self._col_cache[local_table]

        # نصفي البيانات
        data = {k: v for k, v in row.items() if k in local_cols}
        if not data:
            return

        # نحاول INSERT OR REPLACE
        cols = ", ".join(data.keys())
        vals = ", ".join(f":{k}" for k in data.keys())
        try:
            s.execute(
                text(f"INSERT OR REPLACE INTO [{local_table}] ({cols}) VALUES ({vals})"),
                data,
            )
        except Exception:
            pass

    # ── Helpers ──────────────────────────────────────────────

    def _show_error(self, page: int, msg: str, success: bool = False):
        lbl = self.error_lbl_new if page == 0 else self.error_lbl_conn
        color = "#1b5e20" if success else "#c62828"
        bg    = "#e8f5e9" if success else "#ffebee"
        lbl.setStyleSheet(f"color:{color}; background:{bg}; border:1px solid {color}50; border-radius:6px; padding:8px;")
        lbl.setText(msg)
        lbl.show()

    def _clear_error(self, page: int):
        lbl = self.error_lbl_new if page == 0 else self.error_lbl_conn
        lbl.setText("")
        lbl.hide()

    def _reset_btn(self, page: int):
        if page == 0:
            self.progress_new.hide()
            self.create_btn.setEnabled(True)
            self.create_btn.setText(self._("setup_create_btn"))
        else:
            self.progress_conn.hide()
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("🔗  " + self._("setup_connect_btn"))

    def _retranslate(self):
        self.setWindowTitle(self._("setup_wizard_title"))

    # ── Style ─────────────────────────────────────────────────

    def _apply_style(self):
        try:
            from core.theme_manager import ThemeManager
            c   = ThemeManager.get_instance().current_theme.colors
            bg  = c.get("bg_primary",    "#f5f7fa")
            bg2 = c.get("bg_secondary",  "#eceff1")
            pri = c.get("primary",       "#2563EB")
            prh = c.get("primary_hover", "#1D4ED8")
            pra = c.get("primary_active","#1e40af")
            prl = c.get("primary_light", "#EFF6FF")
            tp  = c.get("text_primary",  "#263238")
            ts  = c.get("text_secondary","#546e7a")
            tm  = c.get("text_muted",    "#90a4ae")
            tw  = c.get("text_white",    "white")
            bdr = c.get("border",        "#cfd8dc")
            dis = c.get("bg_disabled",   "#90a4ae")
        except Exception:
            bg=bg2="#f5f7fa"; bg2="#eceff1"
            pri="#2563EB"; prh="#1D4ED8"; pra="#1e40af"; prl="#EFF6FF"
            tp="#263238"; ts="#546e7a"; tm="#90a4ae"; tw="white"
            bdr="#cfd8dc"; dis="#90a4ae"

        self.setStyleSheet(f"""
        SetupWizard {{ background:{bg}; font-family:'Tajawal','Segoe UI',sans-serif; }}

        #WizardHeader {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {pra},stop:1 {pri});
        }}
        #WizardTitle {{ color:{tw}; font-size:19px; font-weight:bold; }}

        #WizardModeBar {{ background:{bg2}; border-bottom:1px solid {bdr}; }}
        #WizardModeBtn {{
            background:{bg}; color:{tp}; border:1.5px solid {bdr};
            border-radius:8px; font-size:13px; padding:4px 8px;
        }}
        #WizardModeBtn:checked {{
            background:{prl}; color:{pri}; border-color:{pri};
            font-weight:600;
        }}
        #WizardModeBtn:hover {{ border-color:{pri}; }}

        #WizardDesc {{ color:{ts}; font-size:13px; line-height:1.6; }}
        #WizardFieldLabel {{ color:{tp}; font-size:13px; font-weight:600; }}
        #WizardFieldEdit {{
            border:1.5px solid {bdr}; border-radius:8px;
            padding:6px 12px; font-size:13px;
            background:{bg}; color:{tp};
        }}
        #WizardFieldEdit:focus {{ border-color:{pri}; background:{prl}; }}

        #WizardCreateBtn {{
            background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {pri},stop:1 {pra});
            color:{tw}; border:none; border-radius:10px;
            font-size:15px; font-weight:bold;
        }}
        #WizardCreateBtn:hover {{
            background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {prh},stop:1 {pri});
        }}
        #WizardCreateBtn:disabled {{ background:{dis}; color:{tw}; }}

        #WizardProgress {{
            background:{prl}; border-radius:3px;
        }}
        #WizardProgress::chunk {{ background:{pri}; border-radius:3px; }}

        #WizardFooter {{ color:{tm}; font-size:11px; background:{bg2}; border-top:1px solid {bdr}; }}
        """)