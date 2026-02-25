"""
Base Dialog - LOGIPORT

Enhanced base class for all dialogs with:
- Translation support
- Settings management
- User context
- Logging
- Message boxes
- Keyboard shortcuts
"""
import logging
from typing import Optional, Any
from PySide6.QtWidgets import (
    QDialog, QMessageBox, QApplication,
    QDialogButtonBox, QVBoxLayout, QWidget, QLineEdit)

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt, Signal

from core.settings_manager import SettingsManager
from core.translator import TranslationManager
from base64 import b64encode, b64decode

logger = logging.getLogger(__name__)


class BaseDialog(QDialog):

    # Qt Signals
    dialog_opened = Signal()
    dialog_closed = Signal()

    def __init__(
        self,
        parent=None,
        user: Optional[Any] = None,
        title_key: Optional[str] = None,
        auto_center: bool = False
    ):

        super().__init__(parent)
        self._loading_counter = 0
        self._auto_center = auto_center
        self.settings = SettingsManager.get_instance()
        self.current_user = user or self._get_current_user()
        self.translator = TranslationManager.get_instance()
        self._ = self.translator.translate

        # Title management
        self._title_key = None
        if title_key:
            self.set_translated_title(title_key)

        # Connect to translation changes
        self.translator.language_changed.connect(self._retranslate_ui)

        # Apply settings
        if QApplication.instance():
            self._apply_settings()
            self._restore_geometry()


        # Setup keyboard shortcuts
        self._setup_shortcuts()

        # Set default style
        self._set_default_style()

        logger.debug(f"Initialized {self.__class__.__name__}")

    # --------- Settings & Translation ---------

    def _apply_settings(self) -> None:
        """Apply application settings to dialog"""
        try:
            # Settings will be applied by the main app
            # This is here for future extension
            pass
        except Exception as e:
            logger.error(f"Failed to apply settings: {e}")

    def set_translated_title(self, title_key: str) -> None:
        try:
            self._title_key = title_key
            self.setWindowTitle(self._(title_key))
        except Exception as e:
            logger.warning(f"Failed to set translated title: {e}")
            self.setWindowTitle(title_key)  # Fallback to key itself

    def _retranslate_ui(self) -> None:
        """Re-translate UI elements when language changes"""
        try:
            # Update window title
            if self._title_key:
                self.setWindowTitle(self._(self._title_key))

            # Call custom retranslate if exists
            if hasattr(self, 'retranslate_ui'):
                self.retranslate_ui()

        except Exception as e:
            logger.warning(f"Failed to retranslate dialog: {e}")

    def _apply_layout_direction(self):
        try:
            lang = getattr(self.translator, "current_language", "en")
            if lang.startswith("ar"):
                self.setLayoutDirection(Qt.RightToLeft)
            else:
                self.setLayoutDirection(Qt.LeftToRight)
        except Exception:
            pass

# ==============================
# GEOMETRY
# ==============================

    def _geometry_key(self):
        return f"dialog_geometry_{self.__class__.__name__}"

    def _restore_geometry(self):
        try:
            encoded = self.settings.get(self._geometry_key())
            if encoded:
                geometry = b64decode(encoded.encode("utf-8"))
                self.restoreGeometry(geometry)
        except Exception as e:
            logger.warning(f"Failed restoring geometry: {e}")


    def _save_geometry(self):
        try:
            geometry = self.saveGeometry()
            encoded = b64encode(bytes(geometry)).decode("utf-8")
            self.settings.set(self._geometry_key(), encoded)
        except Exception as e:
            logger.warning(f"Failed saving geometry: {e}")

    # ==============================
    # LOADING STATE
    # ==============================

    def set_loading(self, loading: bool):
        """
        Safe loading state with stacking protection
        """
        if loading:
            self._loading_counter += 1
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.setEnabled(False)
        else:
            self._loading_counter = max(0, self._loading_counter - 1)
            if self._loading_counter == 0:
                QApplication.restoreOverrideCursor()
                self.setEnabled(True)

    # ==============================
    # VALIDATION HOOK
    # ==============================

    def validate(self) -> bool:
        """
        Override in subclasses.
        Return False to prevent accept().
        """
        return True

    # --------- User Management ---------

    def _get_current_user(self) -> Any:
        """
        Get current user from settings or app.

        Returns:
            User object or empty dict
        """
        try:
            # Try from settings first (if available)
            if hasattr(self, 'settings') and self.settings:
                user = self.settings.get("user")
                if user:
                    return user

            # Try from QApplication
            app = QApplication.instance()
            if app:
                user = app.property("user")
                if user:
                    return user

            return {}

        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            return {}

    def get_user_info(self) -> str:
        """
        Get formatted user info string for logging.

        Returns:
            User info string like "[User: admin#1]"
        """
        if not self.current_user:
            return "[User: None]"

        try:
            # Extract user info
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

            return f"[User: {name}#{uid}]"

        except Exception:
            return "[User: Error]"

    # --------- Styling & Layout ---------

    def _set_default_style(
        self,
        min_width: int = 380,
        min_height: Optional[int] = None
    ) -> None:
        """
        Set default dialog style.

        Args:
            min_width: Minimum width in pixels
            min_height: Minimum height in pixels (optional)
        """
        self.setMinimumWidth(min_width)

        if min_height:
            self.setMinimumHeight(min_height)

        # Set window flags
        self.setWindowFlag(Qt.Window, True)

        # Set modal by default
        self.setModal(True)

    def set_responsive_size(self, base_width: int = 600, base_height: int = 400) -> None:
        """
        Set responsive dialog size based on screen.

        Args:
            base_width: Base width
            base_height: Base height
        """
        try:
            app = QApplication.instance()
            if app:
                screen = app.primaryScreen()
                if screen:
                    screen_size = screen.availableGeometry()

                    # Use 70% of screen size if larger than base
                    width = min(base_width, int(screen_size.width() * 0.7))
                    height = min(base_height, int(screen_size.height() * 0.7))

                    self.resize(width, height)
                    return

            # Fallback
            self.resize(base_width, base_height)

        except Exception as e:
            logger.error(f"Error setting responsive size: {e}")
            self.resize(base_width, base_height)

    # --------- Keyboard Shortcuts ---------

    def _setup_shortcuts(self) -> None:
        """Setup default keyboard shortcuts"""
        # Escape to close
        QShortcut(QKeySequence("Escape"), self, self.close)

        # Ctrl+W to close (common shortcut)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close)

    def add_shortcut(self, key: str, callback) -> QShortcut:
        """
        Add custom keyboard shortcut.

        Args:
            key: Key sequence (e.g., "Ctrl+S")
            callback: Function to call

        Returns:
            QShortcut instance
        """
        shortcut = QShortcut(QKeySequence(key), self)
        shortcut.activated.connect(callback)
        return shortcut

    # --------- Message Boxes ---------

    def show_info(
        self,
        title: str,
        message: str,
        use_translate: bool = True
    ) -> None:
        """
        Show information message box.

        Args:
            title: Title (or translation key)
            message: Message (or translation key)
            use_translate: Whether to translate title and message
        """
        if use_translate:
            title = self._(title)
            message = self._(message)

        QMessageBox.information(self, title, message)
        self.log_event(f"Info shown: {title}")

    def show_warning(
        self,
        title: str,
        message: str,
        use_translate: bool = True
    ) -> None:
        """
        Show warning message box.

        Args:
            title: Title (or translation key)
            message: Message (or translation key)
            use_translate: Whether to translate title and message
        """
        if use_translate:
            title = self._(title)
            message = self._(message)

        QMessageBox.warning(self, title, message)
        self.log_event(f"Warning shown: {title}", level="warning")

    def show_error(
        self,
        title: str,
        message: str,
        use_translate: bool = True
    ) -> None:
        """
        Show error message box.

        Args:
            title: Title (or translation key)
            message: Message (or translation key)
            use_translate: Whether to translate title and message
        """
        if use_translate:
            title = self._(title)
            message = self._(message)

        QMessageBox.critical(self, title, message)
        self.log_event(f"Error shown: {title}", level="error")

    def show_confirm(
        self,
        title: str,
        message: str,
        use_translate: bool = True
    ) -> bool:
        """
        Show confirmation dialog.

        Args:
            title: Title (or translation key)
            message: Message (or translation key)
            use_translate: Whether to translate title and message

        Returns:
            True if user clicked Yes, False otherwise
        """
        if use_translate:
            title = self._(title)
            message = self._(message)

        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # Default to No for safety
        )

        result = (reply == QMessageBox.Yes)
        self.log_event(
            f"Confirm dialog: {title} - Result: {'Yes' if result else 'No'}"
        )

        return result

    def show_question(
        self,
        title: str,
        message: str,
        buttons: int = QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        default_button: int = QMessageBox.Cancel
    ) -> int:
        """
        Show question dialog with custom buttons.

        Args:
            title: Dialog title
            message: Dialog message
            buttons: Button combination
            default_button: Default selected button

        Returns:
            Button that was clicked
        """
        return QMessageBox.question(self, title, message, buttons, default_button)

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
            level: Log level ('info', 'warning', 'error')
            exc: Optional exception object
        """
        user_info = self.get_user_info()
        msg = f"{self.__class__.__name__}: {user_info} {message}"

        if exc:
            msg += f" | Exception: {exc}"

        if level == "error":
            logger.error(msg)
        elif level == "warning":
            logger.warning(msg)
        else:
            logger.info(msg)

    # --------- Event Handlers ---------

    def showEvent(self, event):
        super().showEvent(event)

        if getattr(self, "_auto_center", False):
            self.center_on_parent()

        self._focus_first_input()

        self.log_event("Dialog opened")
        self.dialog_opened.emit()

    def closeEvent(self, event):
        self._save_geometry()
        self.log_event("Dialog closed")
        self.dialog_closed.emit()
        super().closeEvent(event)

    def accept(self):
        if not self.validate():
            return
        self.log_event("Accepted")
        super().accept()

    def reject(self):
        self.log_event("Rejected")
        super().reject()

    # --------- Helper Methods ---------

    def _focus_first_input(self):
        for widget in self.findChildren(QLineEdit):
            if widget.isVisible() and widget.isEnabled():
                widget.setFocus()
                break


    def center_on_screen(self) -> None:
        """Center dialog on screen"""
        try:
            app = QApplication.instance()
            if app:
                screen = app.primaryScreen()
                if screen:
                    screen_geometry = screen.availableGeometry()
                    x = (screen_geometry.width() - self.width()) // 2
                    y = (screen_geometry.height() - self.height()) // 2
                    self.move(x, y)
        except Exception as e:
            logger.error(f"Error centering dialog: {e}")

    def center_on_parent(self) -> None:
        """Center dialog on parent widget"""
        try:
            if self.parent():
                parent_geometry = self.parent().geometry()
                x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
                y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
                self.move(x, y)
            else:
                self.center_on_screen()
        except Exception as e:
            logger.error(f"Error centering on parent: {e}")