"""
ui/setup_wizard.py — LOGIPORT
================================
نافذة الإعداد الأولي — تظهر مرة واحدة فقط عند أول تشغيل للتطبيق
عندما لا يوجد أي مستخدم في قاعدة البيانات.

المهمة: جمع بيانات حساب SuperAdmin الأول وإنشاؤه.
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QSizePolicy,
    QApplication, QProgressBar
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap, QIcon

logger = logging.getLogger(__name__)


class SetupWizard(QDialog):
    """
    نافذة الإعداد الأولي للتطبيق.
    تظهر مرة واحدة فقط عند أول تشغيل حين لا يوجد أي مستخدم.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SetupWizard")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        self.setModal(True)

        # نجاح الإعداد
        self.setup_done = False
        self.created_username = ""

        self._set_size()
        self._build_ui()
        self._apply_style()

    # ──────────────────────────────────────────────
    # الحجم
    # ──────────────────────────────────────────────

    def _set_size(self):
        screen = QApplication.primaryScreen()
        sg = screen.availableGeometry()
        w = min(520, int(sg.width() * 0.40))
        h = min(640, int(sg.height() * 0.75))
        self.setFixedSize(w, h)
        self.move((sg.width() - w) // 2, (sg.height() - h) // 2)

    # ──────────────────────────────────────────────
    # بناء الواجهة
    # ──────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("LOGIPORT — الإعداد الأولي")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────
        header = QFrame()
        header.setObjectName("WizardHeader")
        header.setFixedHeight(140)
        header_lay = QVBoxLayout(header)
        header_lay.setAlignment(Qt.AlignCenter)
        header_lay.setSpacing(6)

        # Logo
        from core.paths import icons_path
        logo_path = icons_path("logo.png")
        if logo_path.exists():
            logo_lbl = QLabel()
            pix = QPixmap(str(logo_path)).scaledToHeight(50, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            logo_lbl.setAlignment(Qt.AlignCenter)
            header_lay.addWidget(logo_lbl)

        title_lbl = QLabel("مرحباً بك في LOGIPORT")
        title_lbl.setObjectName("WizardTitle")
        title_lbl.setAlignment(Qt.AlignCenter)
        header_lay.addWidget(title_lbl)

        sub_lbl = QLabel("أول تشغيل — إنشاء حساب المسؤول")
        sub_lbl.setObjectName("WizardSubtitle")
        sub_lbl.setAlignment(Qt.AlignCenter)
        header_lay.addWidget(sub_lbl)

        root.addWidget(header)

        # ── Body ────────────────────────────────
        body = QFrame()
        body.setObjectName("WizardBody")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(40, 30, 40, 20)
        body_lay.setSpacing(18)

        # وصف
        desc = QLabel(
            "هذا التطبيق يعمل لأول مرة.\n"
            "أنشئ حساب المسؤول الرئيسي للتحكم الكامل بالنظام."
        )
        desc.setObjectName("WizardDesc")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(desc)

        body_lay.addSpacing(8)

        # الاسم الكامل
        self._add_field(body_lay, "👤  الاسم الكامل", "full_name_edit",
                        "أدخل الاسم الكامل…", False)

        # اسم المستخدم
        self._add_field(body_lay, "🔑  اسم المستخدم", "username_edit",
                        "أدخل اسم المستخدم (بالإنجليزية)…", False)

        # كلمة المرور
        self._add_field(body_lay, "🔒  كلمة المرور", "password_edit",
                        "أدخل كلمة مرور قوية…", True)

        # تأكيد كلمة المرور
        self._add_field(body_lay, "🔒  تأكيد كلمة المرور", "confirm_edit",
                        "أعد إدخال كلمة المرور…", True)

        # رسالة الخطأ
        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("WizardError")
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.hide()
        body_lay.addWidget(self.error_lbl)

        body_lay.addStretch()

        # زر الإنشاء
        self.create_btn = QPushButton("✅  إنشاء الحساب والبدء")
        self.create_btn.setObjectName("WizardCreateBtn")
        self.create_btn.setFixedHeight(46)
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.clicked.connect(self._on_create)
        body_lay.addWidget(self.create_btn)

        # شريط التقدم (مخفي في البداية)
        self.progress = QProgressBar()
        self.progress.setObjectName("WizardProgress")
        self.progress.setRange(0, 0)  # غير محدد
        self.progress.setFixedHeight(6)
        self.progress.hide()
        body_lay.addWidget(self.progress)

        root.addWidget(body)

        # ── Footer ──────────────────────────────
        footer = QLabel("© 2025 LOGIPORT — جميع الحقوق محفوظة")
        footer.setObjectName("WizardFooter")
        footer.setAlignment(Qt.AlignCenter)
        footer.setFixedHeight(36)
        root.addWidget(footer)

    def _add_field(self, layout: QVBoxLayout, label_text: str,
                   attr_name: str, placeholder: str, is_password: bool):
        """يضيف حقل إدخال مُصنَّف."""
        container = QFrame()
        container.setObjectName("WizardFieldContainer")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(4)

        lbl = QLabel(label_text)
        lbl.setObjectName("WizardFieldLabel")
        c_lay.addWidget(lbl)

        edit = QLineEdit()
        edit.setObjectName("WizardFieldEdit")
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(40)
        edit.setLayoutDirection(Qt.RightToLeft)
        if is_password:
            edit.setEchoMode(QLineEdit.Password)
        c_lay.addWidget(edit)

        setattr(self, attr_name, edit)
        layout.addWidget(container)

    # ──────────────────────────────────────────────
    # المنطق
    # ──────────────────────────────────────────────

    def _on_create(self):
        """التحقق من المدخلات وإنشاء الحساب."""
        self._clear_error()

        full_name = self.full_name_edit.text().strip()
        username  = self.username_edit.text().strip()
        password  = self.password_edit.text()
        confirm   = self.confirm_edit.text()

        # التحقق من المدخلات
        if not full_name:
            return self._show_error("❌  يرجى إدخال الاسم الكامل.")
        if not username:
            return self._show_error("❌  يرجى إدخال اسم المستخدم.")
        if len(username) < 3:
            return self._show_error("❌  اسم المستخدم يجب أن يكون 3 أحرف على الأقل.")
        if not username.replace("_", "").replace("-", "").isalnum():
            return self._show_error("❌  اسم المستخدم يجب أن يحتوي على أحرف وأرقام فقط (إنجليزية).")
        if not password:
            return self._show_error("❌  يرجى إدخال كلمة المرور.")
        if len(password) < 6:
            return self._show_error("❌  كلمة المرور يجب أن تكون 6 أحرف على الأقل.")
        if password != confirm:
            return self._show_error("❌  كلمة المرور وتأكيدها غير متطابقَين.")

        # تعطيل الزر وإظهار التحميل
        self.create_btn.setEnabled(False)
        self.create_btn.setText("⏳  جارٍ الإنشاء…")
        self.progress.show()
        QApplication.processEvents()

        # إنشاء الحساب
        try:
            from database.bootstrap import create_superadmin
            success = create_superadmin(
                username=username,
                password=password,
                full_name=full_name,
            )

            if success:
                self.created_username = username
                self.setup_done = True
                self._show_success(username)
            else:
                self._show_error("❌  فشل إنشاء الحساب. تحقق من السجلات.")
                self._reset_button()

        except Exception as exc:
            logger.error(f"SetupWizard: خطأ أثناء إنشاء الحساب: {exc}", exc_info=True)
            self._show_error(f"❌  خطأ: {exc}")
            self._reset_button()

    def _show_success(self, username: str):
        """يعرض رسالة النجاح ثم يُغلق النافذة."""
        self.progress.hide()
        self.create_btn.setText("✅  تم! جارٍ فتح التطبيق…")
        self.create_btn.setStyleSheet("background:#27ae60; color:white;")

        # اخفِ خانات الإدخال
        for attr in ("full_name_edit", "username_edit", "password_edit", "confirm_edit"):
            getattr(self, attr).setEnabled(False)

        # اعرض رسالة نجاح
        self._clear_error()
        success_msg = QLabel(
            f"✅  تم إنشاء حساب المسؤول بنجاح!\n"
            f"اسم المستخدم: {username}\n\n"
            f"يمكنك تغيير كلمة المرور لاحقاً من إعدادات الحساب."
        )
        success_msg.setObjectName("WizardSuccess")
        success_msg.setWordWrap(True)
        success_msg.setAlignment(Qt.AlignCenter)
        # أضف الرسالة فوق الزر
        layout = self.create_btn.parent().layout()
        idx = layout.indexOf(self.create_btn)
        layout.insertWidget(idx, success_msg)

        # أغلق بعد 2 ثانية
        QTimer.singleShot(2000, self.accept)

    def _show_error(self, msg: str):
        self.error_lbl.setText(msg)
        self.error_lbl.show()

    def _clear_error(self):
        self.error_lbl.setText("")
        self.error_lbl.hide()

    def _reset_button(self):
        self.progress.hide()
        self.create_btn.setEnabled(True)
        self.create_btn.setText("✅  إنشاء الحساب والبدء")

    # ──────────────────────────────────────────────
    # التصميم
    # ──────────────────────────────────────────────

    def _apply_style(self):
        self.setStyleSheet("""
        /* ─── الخلفية العامة ─── */
        SetupWizard {
            background: #f5f7fa;
            font-family: 'Tajawal', 'Segoe UI', sans-serif;
        }

        /* ─── الهيدر ─── */
        #WizardHeader {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #1a237e, stop:1 #1565c0
            );
            border-radius: 0px;
        }
        #WizardTitle {
            color: white;
            font-size: 20px;
            font-weight: bold;
        }
        #WizardSubtitle {
            color: rgba(255,255,255,0.85);
            font-size: 13px;
        }

        /* ─── Body ─── */
        #WizardBody {
            background: #f5f7fa;
        }
        #WizardDesc {
            color: #546e7a;
            font-size: 13px;
            line-height: 1.6;
        }

        /* ─── حقول الإدخال ─── */
        #WizardFieldLabel {
            color: #37474f;
            font-size: 13px;
            font-weight: 600;
        }
        #WizardFieldEdit {
            border: 1.5px solid #cfd8dc;
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 13px;
            background: white;
            color: #263238;
        }
        #WizardFieldEdit:focus {
            border-color: #1565c0;
            background: #e8f0fe;
        }

        /* ─── رسائل ─── */
        #WizardError {
            color: #c62828;
            font-size: 13px;
            background: #ffebee;
            border: 1px solid #ef9a9a;
            border-radius: 6px;
            padding: 8px;
        }
        #WizardSuccess {
            color: #1b5e20;
            font-size: 13px;
            background: #e8f5e9;
            border: 1px solid #a5d6a7;
            border-radius: 6px;
            padding: 10px;
        }

        /* ─── زر الإنشاء ─── */
        #WizardCreateBtn {
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #1976d2, stop:1 #1565c0
            );
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: bold;
        }
        #WizardCreateBtn:hover {
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #1e88e5, stop:1 #1976d2
            );
        }
        #WizardCreateBtn:disabled {
            background: #90a4ae;
            color: white;
        }

        /* ─── Progress Bar ─── */
        #WizardProgress {
            background: #e3f2fd;
            border-radius: 3px;
        }
        #WizardProgress::chunk {
            background: #1976d2;
            border-radius: 3px;
        }

        /* ─── Footer ─── */
        #WizardFooter {
            color: #90a4ae;
            font-size: 11px;
            background: #eceff1;
            border-top: 1px solid #cfd8dc;
        }
        """)