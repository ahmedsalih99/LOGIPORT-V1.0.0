"""
AboutDialog - LOGIPORT
========================

نافذة "عن التطبيق" تعرض:
- اسم التطبيق + الإصدار
- معلومات قاعدة البيانات (مسار، حجم، آخر تعديل)
- آخر نسخة احتياطية
- إحصائيات سريعة (عدد المعاملات، العملاء، المواد)
- معلومات النظام
- حالة الـ PDF runtime
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QWidget, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap, QIcon

from core.translator import TranslationManager

try:
    from version import VERSION as APP_VERSION, APP_NAME
except Exception:
    APP_VERSION = "1.0.0"
    APP_NAME    = "LOGIPORT"
APP_YEAR = "2025 – 2026"


class AboutDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ = TranslationManager.get_instance().translate
        self.setWindowTitle(self._("about_title").format(name=APP_NAME))
        self.setMinimumWidth(520)
        self.setObjectName("about-dialog")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowModality(Qt.ApplicationModal)
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Hero section ──────────────────────────────────────────────
        try:
            from core.theme_manager import ThemeManager
            _c   = ThemeManager.get_instance().current_theme.colors
            _pri = _c.get("primary",        "#2563EB")
            _pa  = _c.get("primary_active", "#2C5AA0")
        except Exception:
            _pri, _pa = "#2563EB", "#2C5AA0"

        hero = QFrame()
        hero.setObjectName("card")
        hero.setStyleSheet(
            f"QFrame#card {{ background: qlineargradient("
            f"x1:0,y1:0,x2:1,y2:1, stop:0 {_pa}, stop:1 {_pri});"
            f"border-radius: 0px; padding: 24px; }}"
        )
        hero_lay = QVBoxLayout(hero)
        hero_lay.setAlignment(Qt.AlignCenter)

        logo_lbl = QLabel("🚢")
        logo_lbl.setFont(QFont("Segoe UI Emoji", 42))
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent; color: white;")
        hero_lay.addWidget(logo_lbl)

        name_lbl = QLabel(APP_NAME)
        name_lbl.setFont(QFont("Tajawal", 28, QFont.Bold))
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet("background: transparent; color: white;")
        hero_lay.addWidget(name_lbl)

        sub_lbl = QLabel(self._("app_subtitle"))
        sub_lbl.setFont(QFont("Tajawal", 12))
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet("background: transparent; color: rgba(255,255,255,0.85);")
        hero_lay.addWidget(sub_lbl)

        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setFont(QFont("Tajawal", 11))
        ver_lbl.setAlignment(Qt.AlignCenter)
        ver_lbl.setStyleSheet("background: transparent; color: rgba(255,255,255,0.7);")
        hero_lay.addWidget(ver_lbl)

        main.addWidget(hero)

        # ── Info scroll area ──────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(24, 18, 24, 18)
        content_lay.setSpacing(14)

        # DB info
        content_lay.addWidget(self._section(self._("section_database"), self._get_db_rows()))

        # Backup info
        content_lay.addWidget(self._section(self._("section_backups"), self._get_backup_rows()))

        # Quick stats
        content_lay.addWidget(self._section(self._("section_quick_stats"), self._get_stats_rows()))

        # System info
        content_lay.addWidget(self._section(self._("section_system_info"), self._get_sys_rows()))

        # Health
        content_lay.addWidget(self._section(self._("section_libraries"), self._get_health_rows()))

        content_lay.addStretch()
        scroll.setWidget(content)
        main.addWidget(scroll)

        # ── Footer ────────────────────────────────────────────────────
        footer = QFrame()
        footer.setObjectName("card")
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(20, 12, 20, 12)

        copy_lbl = QLabel(self._("copyright").format(year=APP_YEAR))
        copy_lbl.setFont(QFont("Tajawal", 9))
        copy_lbl.setObjectName("text-muted")
        foot_lay.addWidget(copy_lbl)
        foot_lay.addStretch()

        self._btn_check_update = QPushButton(self._("check_for_updates"))
        self._btn_check_update.setObjectName("secondary-btn")
        self._btn_check_update.setMinimumHeight(34)
        self._btn_check_update.setFont(QFont("Tajawal", 10))
        self._btn_check_update.setCursor(Qt.PointingHandCursor)
        self._btn_check_update.clicked.connect(self._check_updates)
        foot_lay.addWidget(self._btn_check_update)

        close_btn = QPushButton(self._("close_btn"))
        close_btn.setObjectName("btn-primary")
        close_btn.setMinimumHeight(34)
        close_btn.setFont(QFont("Tajawal", 10))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        foot_lay.addWidget(close_btn)

        main.addWidget(footer)

    # ── section builder ───────────────────────────────────────────────────────

    def _section(self, title: str, rows: list) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)

        t = QLabel(title)
        t.setFont(QFont("Tajawal", 11, QFont.Bold))
        lay.addWidget(t)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setObjectName("separator")
        lay.addWidget(sep)

        for label, value in rows:
            row_w = QWidget()
            r_lay = QHBoxLayout(row_w)
            r_lay.setContentsMargins(0, 0, 0, 0)

            lbl = QLabel(label + ":")
            lbl.setFont(QFont("Tajawal", 9, QFont.DemiBold))
            lbl.setFixedWidth(160)
            lbl.setObjectName("info-label")
            r_lay.addWidget(lbl)

            val = QLabel(str(value))
            val.setFont(QFont("Tajawal", 9))
            val.setWordWrap(True)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            r_lay.addWidget(val, 1)

            lay.addWidget(row_w)

        return f

    # ── data providers ────────────────────────────────────────────────────────

    def _get_db_rows(self) -> list:
        try:
            from services.backup_service import get_db_info
            info = get_db_info()
            return [
                (self._("db_path"),         info.get("path", "—")),
                (self._("db_size_label"),          f"{info.get('size_kb', '—')} KB"),
                (self._("db_last_modified"),      info.get("modified", "—")),
                (self._("db_status"),          self._("db_available") if info.get("exists") else self._("db_not_found")),
            ]
        except Exception as e:
            return [(self._("error"), str(e))]

    def _get_backup_rows(self) -> list:
        try:
            from services.backup_service import list_backups
            backups = list_backups()
            if not backups:
                return [(self._("status"), self._("no_backups_status"))]
            last = backups[0]
            from datetime import datetime
            ts = datetime.fromtimestamp(last.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            sz = round(last.stat().st_size / 1024, 1)
            return [
                (self._("backup_count"),    str(len(backups))),
                (self._("last_backup"),     last.name),
                (self._("last_backup_date"), ts),
                (self._("last_backup_size"),  f"{sz} KB"),
            ]
        except Exception as e:
            return [(self._("error"), str(e))]

    def _get_stats_rows(self) -> list:
        try:
            from database.models import get_session_local, User, Transaction, Client, Material, Document
            with get_session_local()() as s:
                trx  = s.query(Transaction).count()
                cli  = s.query(Client).count()
                mat  = s.query(Material).count()
                usr  = s.query(User).count()
                doc  = s.query(Document).count()
            return [
                (self._("stat_transactions"),  str(trx)),
                (self._("stat_clients"),    str(cli)),
                (self._("stat_materials"),     str(mat)),
                (self._("stat_users"), str(usr)),
                (self._("stat_documents"),  str(doc)),
            ]
        except Exception as e:
            return [(self._("error"), str(e))]

    def _get_sys_rows(self) -> list:
        import sys, platform
        try:
            import PySide6
            pyside_ver = PySide6.__version__
        except Exception:
            pyside_ver = "—"
        try:
            import sqlalchemy
            sa_ver = sqlalchemy.__version__
        except Exception:
            sa_ver = "—"
        return [
            ("🐍 Python",     sys.version.split()[0]),
            (self._("sys_os"),     f"{platform.system()} {platform.release()}"),
            (self._("sys_arch"),  platform.machine()),
            ("📦 PySide6",    pyside_ver),
            ("🗃️ SQLAlchemy", sa_ver),
        ]

    # ── update check ─────────────────────────────────────────────────────────

    def _check_updates(self):
        """تحقق يدوي من التحديثات عند الضغط على الزر."""
        from PySide6.QtWidgets import QMessageBox
        self._btn_check_update.setEnabled(False)
        self._btn_check_update.setText(self._("checking_updates"))

        def _on_found(info):
            from PySide6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self, "_show_update_found",
                                     Qt.QueuedConnection)
            self._pending_update = info

        def _on_no_update():
            from PySide6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self, "_show_no_update", Qt.QueuedConnection)

        def _on_error(msg):
            from PySide6.QtCore import QMetaObject, Qt
            self._update_error = msg
            QMetaObject.invokeMethod(self, "_show_update_error", Qt.QueuedConnection)

        try:
            from services.updater_service import UpdaterService
            UpdaterService.get_instance().check_async(
                on_update_found=_on_found,
                on_no_update=_on_no_update,
                on_error=_on_error,
            )
        except Exception as e:
            self._restore_check_btn()
            QMessageBox.warning(self, self._("error"), str(e))

    def _restore_check_btn(self):
        self._btn_check_update.setEnabled(True)
        self._btn_check_update.setText(self._("check_for_updates"))

    def _show_update_found(self):
        self._restore_check_btn()
        info = getattr(self, "_pending_update", None)
        if not info:
            return
        self.accept()
        from ui.dialogs.update_dialog import UpdateDialog
        dlg = UpdateDialog(info, parent=self.parent())
        dlg.exec()

    def _show_no_update(self):
        self._restore_check_btn()
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, self._("updates"), self._("already_latest_version"))

    def _show_update_error(self):
        self._restore_check_btn()
        from PySide6.QtWidgets import QMessageBox
        msg = getattr(self, "_update_error", "Unknown error")
        QMessageBox.warning(self, self._("error"), self._("update_check_failed").format(error=msg))

    def _get_health_rows(self) -> list:
        try:
            from services.healthcheck import check_pdf_runtime
            r = check_pdf_runtime()
            rows = [
                ("QtWebEngine",  self._("lib_available") if r.qtwebengine      else self._("lib_not_available")),
                ("WeasyPrint",   self._("lib_available") if r.weasyprint_stack else self._("lib_not_available")),
                ("Cairo",        self._("lib_available") if r.cairo            else self._("lib_not_available")),
                ("Pango",        self._("lib_available") if r.pango            else self._("lib_not_available")),
                ("GDK Pixbuf",   self._("lib_available") if r.gdk_pixbuf       else self._("lib_not_available")),
            ]
            return rows
        except Exception as e:
            return [(self._("error"), str(e))]