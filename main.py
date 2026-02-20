"""
LOGIPORT Main Entry Point
=========================
Enhanced version with bootstrap, first-run setup wizard, and Qt warnings suppression.
"""
import sys
import os

# ========== إخفاء Qt Warnings ==========
os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false;*.debug=false;qt.text.font.*=false;*.warning=false"

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from PySide6.QtCore import Qt
from core.logging_config import LoggingConfig
from core.settings_manager import SettingsManager


def main():
    # 1) Logging
    LoggingConfig.setup_logging()

    # تنظيف السجلات القديمة (أكثر من 30 يوماً)
    try:
        LoggingConfig.cleanup_old_logs(days_to_keep=30)
    except Exception:
        pass  # عدم إيقاف التطبيق بسبب خطأ في التنظيف

    # 2) إنشاء التطبيق أولاً (مطلوب قبل أي نافذة)
    app = QApplication(sys.argv)

    # 3) حمّل الإعدادات وطبّقها (لغة + اتجاه + ثيم)
    settings = SettingsManager.get_instance()
    settings.apply_all_settings()

    # 4) Bootstrap: إنشاء الجداول + البيانات الأساسية
    #    يُرجع True إذا لم يكن هناك أي مستخدم (أول تشغيل)
    try:
        from database.bootstrap import run_bootstrap
        needs_setup = run_bootstrap()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(f"Bootstrap error: {exc}", exc_info=True)
        QMessageBox.critical(
            None,
            "خطأ في تهيئة التطبيق",
            f"حدث خطأ أثناء تهيئة قاعدة البيانات:\n\n{exc}\n\n"
            "تحقق من ملف السجلات للمزيد من التفاصيل."
        )
        sys.exit(1)

    # 5) أول تشغيل → نافذة الإعداد الأولي
    if needs_setup:
        from ui.setup_wizard import SetupWizard
        wizard = SetupWizard()
        wizard.exec()

        # إذا أغلق المستخدم النافذة بدون إنشاء حساب → اخرج
        if not wizard.setup_done:
            sys.exit(0)

    # 6) نافذة تسجيل الدخول
    from ui.login_window import LoginWindow
    login_dialog = LoginWindow()

    if login_dialog.exec() == QDialog.Accepted:
        current_user = getattr(login_dialog, "user", None)

        # احفظ المستخدم على مستوى التطبيق
        app.setProperty("user", current_user)

        # 7) النافذة الرئيسية
        from ui.main_window import MainWindow
        window = MainWindow(current_user=current_user)
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()