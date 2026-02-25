"""
Theme Manager - LOGIPORT v3.0 (NEW SYSTEM ONLY)
==============================================

• Uses ONLY the new ThemeBuilder system (config/themes)
• No legacy fallback
• Clean PyCharm warnings
• Safe QApplication handling
"""

import logging
from typing import Optional, Dict
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal
from core.singleton import QObjectSingletonMixin

logger = logging.getLogger(__name__)

# --------------------------------------------------
# Font size mapping
# --------------------------------------------------
FONT_SIZE_MAP: Dict[str, int] = {
    "small": 10,
    "medium": 12,
    "large": 14,
    "xlarge": 16,
}

# --------------------------------------------------
# Defaults
# --------------------------------------------------
DEFAULT_THEME = "light"
DEFAULT_FONT_SIZE = 12
DEFAULT_FONT_FAMILY = "Tajawal"

AVAILABLE_THEMES = ["light", "dark"]


class ThemeManager(QObject, QObjectSingletonMixin):
    """Centralized Theme Manager (Singleton)."""

    theme_changed = Signal(str)   # يُطلق بعد تطبيق theme جديد — يحمل اسمه

    def __init__(self) -> None:
        super().__init__()
        self.current_theme = DEFAULT_THEME
        self._theme_applied = False  # True بعد أول apply_theme ناجح
        self.current_font_size = DEFAULT_FONT_SIZE
        self.current_font_family = DEFAULT_FONT_FAMILY

    # --------------------------------------------------
    # Apply theme
    # --------------------------------------------------
    def apply_theme(
        self,
        theme_name: Optional[str] = None,
        font_size: Optional[int | str] = None,
        font_family: Optional[str] = None,
    ) -> bool:
        try:
            from core.settings_manager import SettingsManager
            from config.themes import ThemeBuilder

            settings = SettingsManager.get_instance()

            theme_name = theme_name or settings.get("theme", DEFAULT_THEME)
            font_family = font_family or settings.get("font_family", DEFAULT_FONT_FAMILY)
            font_size_input = font_size or settings.get("font_size", DEFAULT_FONT_SIZE)

            if isinstance(font_size_input, str):
                font_size = FONT_SIZE_MAP.get(font_size_input, DEFAULT_FONT_SIZE)
            else:
                font_size = int(font_size_input)

            logger.info("=" * 60)
            logger.info("🎨 LOGIPORT THEME SYSTEM v3.0 (NEW ONLY)")
            logger.info(f"📋 Requested: {theme_name} | {font_family} {font_size}px")
            logger.info("=" * 60)

            theme = ThemeBuilder(
                theme_name=theme_name,
                font_size=font_size,
                font_family=font_family,
            )

            stylesheet = theme.build()
            if not stylesheet or len(stylesheet) < 200:
                raise ValueError("Generated stylesheet is invalid or too short")

            app = QApplication.instance()
            if app is None:
                raise RuntimeError("QApplication not initialized")

            assert isinstance(app, QApplication)
            app.setStyleSheet(stylesheet)

            self.current_theme = theme_name
            self._theme_applied = True
            self.current_font_size = font_size
            self.current_font_family = font_family

            logger.info("✅ Theme applied successfully")
            self.theme_changed.emit(theme_name)
            return True

        except (ImportError, RuntimeError, ValueError) as exc:
            logger.exception("❌ Theme application failed")
            return False

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------
    def apply_current_theme(self) -> bool:
        return self.apply_theme(
            self.current_theme,
            self.current_font_size,
            self.current_font_family,
        )

    def get_current_theme(self) -> str:
        return self.current_theme

    def get_current_font_size(self) -> int:
        return self.current_font_size

    def get_current_font_family(self) -> str:
        return self.current_font_family

    def get_available_themes(self) -> list[str]:
        return AVAILABLE_THEMES.copy()

    def get_available_font_sizes(self) -> Dict[str, int]:
        return FONT_SIZE_MAP.copy()

    # --------------------------------------------------
    # Custom styles
    # --------------------------------------------------
    def set_custom_stylesheet(self, stylesheet: str) -> bool:
        try:
            app = QApplication.instance()
            if app is None:
                raise RuntimeError("QApplication not initialized")

            assert isinstance(app, QApplication)
            app.setStyleSheet(stylesheet)
            return True

        except RuntimeError:
            logger.exception("Failed to apply custom stylesheet")
            return False

    def append_stylesheet(self, additional_css: str) -> bool:
        try:
            app = QApplication.instance()
            if app is None:
                raise RuntimeError("QApplication not initialized")

            assert isinstance(app, QApplication)
            app.setStyleSheet(app.styleSheet() + "\n" + additional_css)
            return True

        except RuntimeError:
            logger.exception("Failed to append stylesheet")
            return False


# --------------------------------------------------
# Convenience functions
# --------------------------------------------------
def get_theme_manager() -> ThemeManager:
    return ThemeManager.get_instance()


def apply_theme(
    theme_name: Optional[str] = None,
    font_size: Optional[int | str] = None,
    font_family: Optional[str] = None,
) -> bool:
    return ThemeManager.get_instance().apply_theme(theme_name, font_size, font_family)


def get_current_theme() -> str:
    return ThemeManager.get_instance().get_current_theme()