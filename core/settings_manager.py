"""
Settings Manager - LOGIPORT
Enhanced with better error handling, caching, and integration with config.py
"""
import json
import os
import logging
from typing import Any, Optional, Dict
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class SettingsManager(QObject):
    """
    Centralized settings management for LOGIPORT.

    Features:
    - Qt Signals for reactive updates
    - Singleton pattern
    - User preference management
    - Permission-based updates
    - Import/Export functionality
    - Integration with theme and translation

    Signals:
        setting_changed(str, object): Emitted when a setting changes
        settings_loaded(dict): Emitted when settings are loaded from file
        settings_exported(str): Emitted when settings are exported
        settings_imported(str): Emitted when settings are imported
    """

    # Qt Signals
    setting_changed = Signal(str, object)
    settings_loaded = Signal(dict)
    settings_exported = Signal(str)
    settings_imported = Signal(str)

    _instance = None

    # Default settings
    DEFAULT_SETTINGS = {
        # Language & Localization
        "language": "ar",
        "direction": "rtl",           # rtl | ltr — يُحسب تلقائياً من اللغة
        "documents_language": "ar",   # لغة المستندات المولّدة

        # Theme & UI
        "theme": "light",
        "font_size": "medium",        # small | medium | large | xlarge (string)
        "font_family": "Tajawal",

        # Paths
        "document_path": "documents/generated/",
        "documents_output_path": "",  # مسار حفظ المستندات (فارغ = داخل مجلد التطبيق)
        "backup_path": "backups/",
        "log_path": "logs/",

        # Application
        "offline_mode": True,
        "auto_save": True,
        "auto_backup": False,
        "backup_interval_days": 7,

        # Metadata
        "last_modified": "",
        "last_modified_by": "",
        "app_version": "1.0.0",
    }

    DYNAMIC_PREFIXES = (
        "dialog_geometry_",
        "window_geometry_",
        "ui_state_",
    )

    # Settings that users can change without special permissions
    USER_SETTINGS = {
        "language", "direction", "documents_language",
        "theme", "font_size", "font_family",
    }

    # Settings that require admin/manager permission
    ADMIN_SETTINGS = {
        "document_path", "documents_output_path", "backup_path", "log_path",
        "offline_mode", "auto_backup", "backup_interval_days"
    }

    def __init__(self):
        """Initialize settings manager (use get_instance() instead)"""
        super().__init__()
        from core.paths import get_user_data_dir
        self.settings_file = Path(get_user_data_dir()) / "settings.json"
        self.settings: Dict[str, Any] = self.DEFAULT_SETTINGS.copy()
        self._pending_theme_apply = False
        self.load()

    @classmethod
    def get_instance(cls) -> 'SettingsManager':
        """
        Get singleton instance of SettingsManager.

        Returns:
            SettingsManager instance
        """
        if cls._instance is None:
            cls._instance = SettingsManager()
        return cls._instance

    def load(self) -> bool:
        """
        Load settings from JSON file.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.settings_file.exists():
            logger.info("Settings file not found, using defaults")
            return False

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                content = f.read().strip()

                if not content:
                    logger.warning("Settings file is empty")
                    return False

                loaded_settings = json.loads(content)

                # Validate and merge
                validated_settings = self._validate_settings(loaded_settings)
                self.settings.update(validated_settings)

                logger.info(f"Loaded {len(validated_settings)} settings from file")
                self.settings_loaded.emit(self.settings)
                return True

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in settings file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return False

    def save(self) -> bool:
        """
        Save settings to JSON file.

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Create copy without temporary data
            to_save = self.settings.copy()

            # Remove user object (not serializable)
            to_save.pop("user", None)

            # Ensure directory exists
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(to_save, f, indent=4, ensure_ascii=False)

            logger.info("Settings saved successfully")
            return True

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value.

        Args:
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value or default
        """
        if default is None:
            default = self.DEFAULT_SETTINGS.get(key)

        return self.settings.get(key, default)

    def get_default(self, key: str) -> Any:
        """
        Get default value for a setting.

        Args:
            key: Setting key

        Returns:
            Default value or None
        """
        return self.DEFAULT_SETTINGS.get(key)

    def set(self, key: str, value: Any, user: Any = None) -> bool:
        """
        Set setting value.

        Args:
            key: Setting key
            value: Setting value
            user: Current user (for permission check)

        Returns:
            True if set successfully, False otherwise
        """
        old_value = self.settings.get(key)

        # Special handling for user object
        if key == "user":
            self.settings[key] = value
            return True  # Don't save user to file

        # Check permissions
        if not self._has_permission_to_set(key, user):
            logger.warning(f"User does not have permission to set '{key}'")
            return False

        # Set the value
        self.settings[key] = value

        # Save to file
        if not self.save():
            logger.error(f"Failed to save setting '{key}'")
            return False

        # Emit signal
        self.setting_changed.emit(key, value)

        # Apply side effects
        self._apply_setting_side_effects(key, value)

        logger.info(f"Setting '{key}' changed from {old_value} to {value}")
        return True

    def get_all(self) -> Dict[str, Any]:
        """
        Get all settings.

        Returns:
            Copy of all settings
        """
        return self.settings.copy()

    def set_all(self, new_settings: Dict[str, Any], user: Any = None) -> bool:
        """
        Set multiple settings at once.

        Args:
            new_settings: Dictionary of settings to update
            user: Current user (for permission check)

        Returns:
            True if all settings were set successfully
        """
        # Check permissions for all settings
        for key in new_settings.keys():
            if not self._has_permission_to_set(key, user):
                logger.warning(f"User does not have permission to set '{key}'")
                return False

        # Update all settings
        self.settings.update(new_settings)

        # Save
        if not self.save():
            return False

        # Emit signals
        for key, value in new_settings.items():
            self.setting_changed.emit(key, value)

        # Mark theme for reapplication
        self._pending_theme_apply = True

        logger.info(f"Updated {len(new_settings)} settings")
        return True

    def reset_to_default(self, key: str) -> bool:
        """
        Reset a setting to its default value.

        Args:
            key: Setting key

        Returns:
            True if reset successfully
        """
        if key not in self.DEFAULT_SETTINGS:
            logger.warning(f"No default value for setting '{key}'")
            return False

        return self.set(key, self.DEFAULT_SETTINGS[key])

    def reset_all_to_default(self) -> bool:
        """
        Reset all settings to default values.

        Returns:
            True if reset successfully
        """
        self.settings = self.DEFAULT_SETTINGS.copy()
        return self.save()

    def export_settings(self, path: str) -> bool:
        """
        Export settings to a file.

        Args:
            path: File path to export to

        Returns:
            True if exported successfully
        """
        try:
            export_path = Path(path)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)

            self.settings_exported.emit(str(export_path))
            logger.info(f"Settings exported to: {export_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            return False

    def import_settings(self, path: str, user: Any = None) -> bool:
        """
        Import settings from a file.

        Args:
            path: File path to import from
            user: Current user (for permission check)

        Returns:
            True if imported successfully
        """
        try:
            import_path = Path(path)

            if not import_path.exists():
                logger.error(f"Import file not found: {import_path}")
                return False

            with open(import_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            # Validate and set
            if not self.set_all(loaded, user):
                return False

            self.settings_imported.emit(str(import_path))
            logger.info(f"Settings imported from: {import_path}")
            return True

        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return False

    def get_language(self) -> str:
        """Get current language"""
        return self.get("language", "ar")

    def set_language(self, lang: str) -> bool:
        """Set language and apply changes"""
        return self.set("language", lang)

    def apply_all_settings(self, force: bool = False) -> None:
        """Apply all settings (theme, language, direction)"""
        # ── Debounce: تجنّب تطبيق الإعدادات أكثر من مرة خلال نفس الدورة ──
        import time as _time
        now = _time.monotonic()
        if not force and (now - getattr(self, "_last_apply_ts", 0.0)) < 0.5:
            return  # تم التطبيق منذ أقل من 500ms، تجاهل الطلب
        self._last_apply_ts = now

        try:
            # Apply language
            self._apply_language(self.get("language"))

            # Apply theme
            self._pending_theme_apply = True
            self.apply_pending_theme()

            logger.info("All settings applied successfully")

        except Exception as e:
            logger.error(f"Error applying settings: {e}")

    def apply_pending_theme(self) -> None:
        """Apply pending theme changes"""
        if not self._pending_theme_apply:
            return

        try:
            from core.theme_manager import ThemeManager

            ThemeManager.get_instance().apply_theme(
                self.get("theme"),
                font_size=self.get("font_size"),
                font_family=self.get("font_family"),
            )

            self._apply_direction(self.get("direction"))
            self._pending_theme_apply = False

            logger.info("Theme applied successfully")

        except Exception as e:
            logger.warning(f"Failed to apply theme: {e}")

    # --------- Private Methods ---------

    def _validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate loaded settings.

        Args:
            settings: Settings to validate

        Returns:
            Validated settings (invalid ones removed)
        """
        validated = {}

        for key, value in settings.items():
            # Check if key exists in defaults
            # Allow dynamic UI-related settings
            if key not in self.DEFAULT_SETTINGS:
                if any(key.startswith(p) for p in self.DYNAMIC_PREFIXES) or key in (
                        "window_geometry",
                        "window_state",
                ):
                    validated[key] = value
                    continue

                logger.debug(f"Unknown setting '{key}' will be ignored")
                continue

            # ─── ترحيل font_size من int إلى string ───────────────────────
            if key == "font_size" and isinstance(value, int):
                if value <= 10:
                    value = "small"
                elif value <= 12:
                    value = "medium"
                elif value <= 14:
                    value = "large"
                else:
                    value = "xlarge"
                logger.info(f"Migrated font_size from int to '{value}'")

            # ─── التحقق من النوع ──────────────────────────────────────────
            default_type = type(self.DEFAULT_SETTINGS[key])
            if not isinstance(value, default_type):
                logger.warning(
                    f"Setting '{key}' has wrong type. "
                    f"Expected {default_type.__name__}, got {type(value).__name__}. "
                    f"Using default."
                )
                # استخدم القيمة الافتراضية بدل الرفض الكامل
                validated[key] = self.DEFAULT_SETTINGS[key]
                continue

            validated[key] = value

        return validated

    def _has_permission_to_set(self, key: str, user: Any = None) -> bool:
        """
        Check if user has permission to set a setting.

        Args:
            key: Setting key
            user: User object

        Returns:
            True if user has permission
        """
        # User settings can be changed by anyone
        if key in self.USER_SETTINGS:
            return True

        # Admin settings require admin or manager role
        if key in self.ADMIN_SETTINGS:
            # Try to get user from parameter
            if user is None:
                # Try to get from QApplication
                app = QApplication.instance()
                if app:
                    user = app.property("user")

            if user is None:
                logger.warning("No user context for permission check")
                return False

            # Check role
            from core.permissions import is_admin
            from database.crud.users_crud import UsersCRUD

            if is_admin(user):
                return True

            # Check if manager
            role_id = getattr(user, "role_id", None)
            if role_id:
                role_name = UsersCRUD.get_role_name_by_id(role_id)
                if role_name in ("Admin", "Manager"):
                    return True

            return False

        # Unknown setting - allow for flexibility
        return True

    def _apply_setting_side_effects(self, key: str, value: Any) -> None:
        """
        Apply side effects when a setting changes.

        Args:
            key: Setting key
            value: New value
        """
        try:
            # Language change
            if key == "language":
                self._apply_language(value)

                # Update direction automatically
                direction = "rtl" if value == "ar" else "ltr"
                if self.settings.get("direction") != direction:
                    # استخدم set() لضمان الحفظ في الملف
                    self.settings["direction"] = direction
                    self.save()
                    self.setting_changed.emit("direction", direction)
                    self._apply_direction(direction)

            # Theme-related changes
            if key in ("theme", "font_size", "font_family", "direction"):
                from core.theme_manager import ThemeManager

                ThemeManager.get_instance().apply_theme(
                    self.get("theme"),
                    font_size=self.get("font_size"),
                    font_family=self.get("font_family"),
                )

                if key == "direction":
                    self._apply_direction(value)

                self._pending_theme_apply = False

        except Exception as e:
            logger.error(f"Error applying side effects for '{key}': {e}")

    def _apply_language(self, lang: str) -> None:
        """Apply language change"""
        try:
            from core.translator import TranslationManager
            TranslationManager.get_instance().set_language(lang)
            logger.info(f"Language changed to: {lang}")
        except Exception as e:
            logger.warning(f"Failed to apply language: {e}")

    def _apply_direction(self, direction: str) -> None:
        """Apply layout direction change"""
        try:
            app = QApplication.instance()
            if app is None:
                return

            dir_value = Qt.RightToLeft if direction == "rtl" else Qt.LeftToRight
            app.setLayoutDirection(dir_value)
            logger.info(f"Direction changed to: {direction}")

        except Exception as e:
            logger.warning(f"Failed to apply direction: {e}")


    def get_documents_output_path(self) -> str:
        """مسار حفظ المستندات المُخصَّص (فارغ = داخل مجلد التطبيق)"""
        try:
            from database.models import get_session_local
            from sqlalchemy import text
            session_factory = get_session_local()
            session = session_factory()
            try:
                result = session.execute(
                    text("SELECT value FROM app_settings WHERE key = 'documents_output_path'")
                ).fetchone()
                if result and result[0]:
                    return str(result[0]).strip()
                return ""
            finally:
                session.close()
        except Exception:
            return self.settings.get("documents_output_path", "")

    def set_documents_output_path(self, path: str) -> bool:
        """تحديث مسار حفظ المستندات"""
        try:
            from database.models import get_session_local
            from sqlalchemy import text
            session_factory = get_session_local()
            session = session_factory()
            try:
                exists = session.execute(
                    text("SELECT COUNT(*) FROM app_settings WHERE key = 'documents_output_path'")
                ).scalar()
                if exists:
                    session.execute(
                        text("UPDATE app_settings SET value=:val, updated_at=CURRENT_TIMESTAMP WHERE key='documents_output_path'"),
                        {"val": path}
                    )
                else:
                    session.execute(
                        text("INSERT INTO app_settings (key,value,category,description) VALUES ('documents_output_path',:val,'storage','مسار حفظ المستندات')"),
                        {"val": path}
                    )
                session.commit()
                self.settings["documents_output_path"] = path
                self.setting_changed.emit("documents_output_path", path)
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Error setting documents_output_path: {e}")
                return False
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error in set_documents_output_path: {e}")
            return False

    def get_transaction_last_number(self) -> int:
        """الحصول على آخر رقم معاملة"""
        try:
            from database.models import get_session_local
            from sqlalchemy import text

            session_factory = get_session_local()
            session = session_factory()  # ⭐ إنشاء session صح

            try:
                result = session.execute(
                    text("SELECT value FROM app_settings WHERE key = 'transaction_last_number'")
                ).fetchone()

                if result and result[0]:
                    return int(result[0])
                return 0
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error getting transaction last number: {e}")
            return 0

    def set_transaction_last_number(self, number: int) -> bool:
        """تحديث آخر رقم معاملة"""
        try:
            from database.models import get_session_local
            from sqlalchemy import text

            session_factory = get_session_local()
            session = session_factory()  # ⭐

            try:
                # التحقق
                exists = session.execute(
                    text("SELECT COUNT(*) FROM app_settings WHERE key = 'transaction_last_number'")
                ).scalar()

                if exists:
                    session.execute(
                        text(
                            "UPDATE app_settings SET value = :val, updated_at = CURRENT_TIMESTAMP WHERE key = 'transaction_last_number'"),
                        {"val": str(number)}
                    )
                else:
                    session.execute(
                        text(
                            "INSERT INTO app_settings (key, value, category, description) VALUES ('transaction_last_number', :val, 'numbering', 'آخر رقم معاملة')"),
                        {"val": str(number)}
                    )

                session.commit()
                self.setting_changed.emit("transaction_last_number", number)
                return True

            except Exception as e:
                session.rollback()
                logger.error(f"Error setting transaction last number: {e}")
                return False
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error in set_transaction_last_number: {e}")
            return False

    def get_transaction_prefix(self) -> str:
        """الحصول على البادئة"""
        try:
            from database.models import get_session_local
            from sqlalchemy import text

            session_factory = get_session_local()
            session = session_factory()  # ⭐

            try:
                result = session.execute(
                    text("SELECT value FROM app_settings WHERE key = 'transaction_prefix'")
                ).fetchone()

                if result and result[0]:
                    return str(result[0])
                return ""
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error getting transaction prefix: {e}")
            return ""

    def set_transaction_prefix(self, prefix: str) -> bool:
        """تحديث البادئة"""
        try:
            from database.models import get_session_local
            from sqlalchemy import text

            session_factory = get_session_local()
            session = session_factory()  # ⭐

            try:
                exists = session.execute(
                    text("SELECT COUNT(*) FROM app_settings WHERE key = 'transaction_prefix'")
                ).scalar()

                if exists:
                    session.execute(
                        text(
                            "UPDATE app_settings SET value = :val, updated_at = CURRENT_TIMESTAMP WHERE key = 'transaction_prefix'"),
                        {"val": prefix}
                    )
                else:
                    session.execute(
                        text(
                            "INSERT INTO app_settings (key, value, category, description) VALUES ('transaction_prefix', :val, 'numbering', 'بادئة رقم المعاملة')"),
                        {"val": prefix}
                    )

                session.commit()
                self.setting_changed.emit("transaction_prefix", prefix)
                return True

            except Exception as e:
                session.rollback()
                logger.error(f"Error setting transaction prefix: {e}")
                return False
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error in set_transaction_prefix: {e}")
            return False

    def get_transaction_next_preview(self) -> str:
        """معاينة الرقم القادم"""
        try:
            last_number = self.get_transaction_last_number()
            prefix = self.get_transaction_prefix()
            next_number = last_number + 1
            return f"{prefix}{next_number}" if prefix else str(next_number)
        except Exception as e:
            logger.error(f"Error getting transaction preview: {e}")
            return "---"


# Convenience functions
def get_settings() -> SettingsManager:
    """Get SettingsManager instance"""
    return SettingsManager.get_instance()


def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value"""
    return SettingsManager.get_instance().get(key, default)


def set_setting(key: str, value: Any, user: Any = None) -> bool:
    """Set a setting value"""
    return SettingsManager.get_instance().set(key, value, user)