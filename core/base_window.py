"""
Base Window - LOGIPORT
Enhanced base class for all main windows

Features:
- Settings management
- Translation support
- User context
- Logging
- Lifecycle management
"""
import logging
from typing import Optional, Any, List, Tuple
from PySide6.QtWidgets import QMainWindow, QApplication, QWidget
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal

from core.settings_manager import SettingsManager
from core.translator import TranslationManager

logger = logging.getLogger(__name__)


class BaseWindow(QMainWindow):
    """
    Enhanced base class for all main windows in LOGIPORT.

    Features:
    - User context management
    - Translation support with auto-updates
    - Settings integration
    - Event logging
    - Default window size
    - Permission updates

    Signals:
        user_changed: Emitted when user changes
        language_changed: Emitted when language changes
    """

    # Qt Signals
    user_changed = Signal(object)
    language_changed = Signal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        user: Optional[Any] = None
    ):
        """
        Initialize base window.

        Args:
            parent: Parent widget
            user: Current user object
        """
        super().__init__(parent)

        # Core managers
        self.settings = SettingsManager.get_instance()
        self.translator = TranslationManager.get_instance()
        self._ = self.translator.translate

        # User context
        self.current_user = user or self._get_current_user()

        # Internal state
        self._title_key: Optional[str] = None
        self._status_message_key: Optional[str] = None
        self._last_title: Optional[str] = None
        self._translatable_actions: List[Tuple] = []

        # Setup
        self.apply_settings()

        # Connect to translation changes
        self.translator.language_changed.connect(self._on_language_changed)

        # Initial translation
        self.retranslate_ui()

        logger.info(f"Initialized {self.__class__.__name__}")

    # --------- User Management ---------

    def _get_current_user(self) -> Any:
        """
        Get current user from settings or app property.

        Returns:
            User object or empty dict
        """
        try:
            # Try from QApplication first
            app = QApplication.instance()
            if app:
                user = app.property("user")
                if user:
                    return user

            # Try from settings (if available)
            if hasattr(self, 'settings') and self.settings:
                user = self.settings.get("user")
                if user:
                    return user

            return {}

        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            return {}

    def get_current_user(self) -> Any:
        """Get current user (public method)"""
        return self.current_user

    def set_current_user(self, user: Any) -> None:
        """
        Set current user and update permissions.

        Args:
            user: User object
        """
        if user == self.current_user:
            return

        old_user = self.current_user
        self.current_user = user

        try:
            # Update QApplication property
            app = QApplication.instance()
            if app:
                app.setProperty("user", user)

            # Update settings
            self.settings.set("user", user)

            # Update permissions
            self.update_user_permissions()

            # Emit signal
            self.user_changed.emit(user)

            logger.info(f"User changed from {old_user} to {user}")

        except Exception as e:
            logger.error(f"Error setting current user: {e}")

    def update_user_permissions(self) -> None:
        """
        Update UI based on user permissions.

        Override this method in subclasses to implement
        permission-based UI updates.
        """
        logger.debug("Updating user permissions (override this method)")

    # --------- Window Configuration ---------

    def set_default_size(self, width: int = 1280, height: int = 800) -> None:
        """
        Set default window size.

        Args:
            width: Window width in pixels
            height: Window height in pixels
        """
        self.resize(width, height)
        logger.debug(f"Window size set to {width}x{height}")

    def center_on_screen(self) -> None:
        """Center window on screen"""
        try:
            app = QApplication.instance()
            if app:
                screen = app.primaryScreen()
                if screen:
                    screen_geometry = screen.availableGeometry()
                    x = (screen_geometry.width() - self.width()) // 2
                    y = (screen_geometry.height() - self.height()) // 2
                    self.move(x, y)
                    logger.debug("Window centered on screen")
        except Exception as e:
            logger.error(f"Error centering window: {e}")

    # --------- Translation ---------

    def set_translated_title(self, key: str) -> None:
        """
        Set window title from translation key.
        Auto-updates when language changes.

        Args:
            key: Translation key for title
        """
        self._title_key = key
        new_title = self._(key)

        # Avoid unnecessary updates
        if getattr(self, "_last_title", None) == new_title:
            return

        self._last_title = new_title
        self.setWindowTitle(new_title)
        logger.debug(f"Window title set: {key}")

    def add_translatable_action(
        self,
        action: QAction,
        text_key: str,
        tooltip_key: Optional[str] = None
    ) -> None:
        """
        Add action to translation list.

        Args:
            action: QAction to translate
            text_key: Translation key for action text
            tooltip_key: Translation key for tooltip (optional)
        """
        if tooltip_key:
            self._translatable_actions.append((action, text_key, tooltip_key))
        else:
            self._translatable_actions.append((action, text_key))

    def retranslate_ui(self) -> None:
        """
        Re-translate all UI elements.

        Override this method in subclasses to add custom
        translation logic. Don't forget to call super().retranslate_ui()
        """
        try:
            # Update window title
            if self._title_key:
                self.setWindowTitle(self._(self._title_key))
            else:
                # Fallback
                self.setWindowTitle(self._("main_window_title"))

            # Update translatable actions
            for item in self._translatable_actions:
                try:
                    if len(item) == 2:
                        action, text_key = item
                        if action:
                            action.setText(self._(text_key))
                            if action.toolTip():
                                action.setToolTip(self._(text_key))
                    elif len(item) == 3:
                        action, text_key, tooltip_key = item
                        if action:
                            action.setText(self._(text_key))
                            if tooltip_key:
                                action.setToolTip(self._(tooltip_key))
                except Exception as e:
                    logger.error(f"Error translating action: {e}")

            # Update sidebar (if exists)
            if hasattr(self, "sidebar") and hasattr(self.sidebar, "retranslate_ui"):
                self.sidebar.retranslate_ui()

            # Update topbar (if exists)
            if hasattr(self, "topbar") and hasattr(self.topbar, "retranslate_ui"):
                self.topbar.retranslate_ui()

            # Update status bar message (if set)
            if hasattr(self, "statusBar"):
                status_bar = self.statusBar()
                if status_bar and self._status_message_key:
                    status_bar.showMessage(self._(self._status_message_key), 3000)

            logger.debug("UI retranslated")

        except Exception as e:
            logger.warning(f"Error retranslating UI: {e}")

    def _on_language_changed(self) -> None:
        """Handle language change event"""
        lang = self.translator.get_current_language()
        self.retranslate_ui()
        self.language_changed.emit(lang)
        logger.info(f"Language changed to: {lang}")

    def change_language(self, lang_code: str) -> bool:
        """
        Change application language.

        Args:
            lang_code: Language code (e.g., 'ar', 'en', 'tr')

        Returns:
            True if language changed successfully
        """
        return self.translator.set_language(lang_code)

    # --------- Settings ---------

    def apply_settings(self) -> None:
        """Apply application settings — مرة واحدة فقط عند الحاجة"""
        try:
            from core.theme_manager import ThemeManager
            tm = ThemeManager.get_instance()
            if not getattr(tm, "_theme_applied", False):
                self.settings.apply_all_settings(force=True)
            else:
                logger.debug("Theme already applied, skipping")
        except Exception as e:
            logger.error(f"Failed to apply settings: {e}")

    def open_settings_dialog(self) -> None:
        """
        Open settings dialog.

        Override this method in subclasses to implement
        custom settings dialog.
        """
        logger.info("Settings dialog requested (override this method)")

    # --------- UI Rebuilding ---------

    def rebuild_ui(self) -> None:
        """
        Rebuild all UI elements.

        Useful when major settings change or after re-login.
        Override this method in subclasses.
        """
        logger.info("Rebuilding UI (override this method)")

    # --------- Logging ---------

    def log_event(
        self,
        message: str,
        level: str = "info",
        exc: Optional[Exception] = None
    ) -> None:
        """
        Log event with user context.

        Args:
            message: Log message
            level: Log level ('info', 'warning', 'error', 'debug')
            exc: Optional exception object
        """
        # Build user info
        user_info = "[User: None]"
        if self.current_user:
            try:
                if isinstance(self.current_user, dict):
                    name = (
                        self.current_user.get("username") or
                        self.current_user.get("full_name") or
                        "Unknown"
                    )
                    uid = self.current_user.get("id", "?")
                else:
                    name = (
                        getattr(self.current_user, "username", None) or
                        getattr(self.current_user, "full_name", None) or
                        "Unknown"
                    )
                    uid = getattr(self.current_user, "id", "?")

                user_info = f"[User: {name}#{uid}]"
            except Exception:
                user_info = "[User: Error]"

        # Build full message
        msg = f"{self.__class__.__name__}: {user_info} {message}"
        if exc:
            msg += f" | Exception: {exc}"

        # Log with appropriate level
        if level == "error":
            logger.error(msg)
        elif level == "warning":
            logger.warning(msg)
        elif level == "debug":
            logger.debug(msg)
        else:
            logger.info(msg)

    # --------- Event Handlers ---------

    def showEvent(self, event) -> None:
        """Handle window show event"""
        self.log_event("Window opened", level="debug")
        super().showEvent(event)

    def closeEvent(self, event) -> None:
        """Handle window close event"""
        self.log_event("Window closed", level="debug")
        super().closeEvent(event)


# Example window using BaseWindow
class ExampleWindow(BaseWindow):
    """Example window demonstrating BaseWindow usage"""

    def __init__(self, parent=None, user=None):
        super().__init__(parent, user)

        self.set_translated_title("example_window_title")
        self.init_ui()
        self.center_on_screen()

    def init_ui(self):
        """Initialize UI"""
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Set window size
        self.set_default_size(800, 600)

    def update_user_permissions(self):
        """Update UI based on user permissions"""
        super().update_user_permissions()
        # Custom permission logic here
        self.log_event("Permissions updated", level="debug")