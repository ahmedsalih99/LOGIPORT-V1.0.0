# core/__init__.py
"""
LOGIPORT Core Module
====================

Central module providing core functionality for LOGIPORT application.

Public API:
    - Settings: SettingsManager
    - Translation: TranslationManager
    - Themes: ThemeManager
    - Permissions: PermissionManager, has_perm, is_admin
    - Base Classes: BaseTab, BaseDialog, BaseWindow
"""

# Settings & Configuration
from .settings_manager import SettingsManager
from .config import Config

# Translation
from .translator import TranslationManager

# Themes
from .theme_manager import ThemeManager

# Permissions
from .permissions import (
    PermissionManager,
    has_perm,
    is_admin,
    has_any_perm,
    has_all_perms,
    require_permission,
)

# Base Classes
from .base_tab import BaseTab
from .base_dialog import BaseDialog
from .base_window import BaseWindow
from .base_details_view import BaseDetailsView

# Utilities
from .admin_columns import apply_admin_columns_to_table
from .singleton import SingletonMeta, QObjectSingletonMixin

# Logging
from .logging_config import LoggingConfig

__all__ = [
    # Settings
    "SettingsManager",
    "Config",

    # Translation
    "TranslationManager",

    # Themes
    "ThemeManager",

    # Permissions
    "PermissionManager",
    "has_perm",
    "is_admin",
    "has_any_perm",
    "has_all_perms",
    "require_permission",

    # Base Classes
    "BaseTab",
    "BaseDialog",
    "BaseWindow",
    "BaseDetailsView",

    # Utilities
    "apply_admin_columns_to_table",
    "SingletonMeta",
    "QObjectSingletonMixin",
    "LoggingConfig",
]

__version__ = "1.1.0"
__author__ = "LOGIPORT Team"