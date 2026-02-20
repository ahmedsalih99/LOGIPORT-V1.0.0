"""
LOGIPORT Themes Module v2.0
============================

Component-based theme system with semantic colors,
typography scales, and modular styling.

Quick Start:
    >>> from config.themes import ThemeBuilder
    >>> theme = ThemeBuilder("light", font_size=13)
    >>> stylesheet = theme.build()
    >>> app.setStyleSheet(stylesheet)

Or use presets:
    >>> from config.themes.presets import light, dark
    >>> stylesheet = light.get_stylesheet(font_size=13)
"""

from .builder import ThemeBuilder
from .palettes import ColorPalette
from .semantic_colors import SemanticColors
from .typography import Typography
from .spacing import Spacing
from .border_radius import BorderRadius

__all__ = [
    "ThemeBuilder",
    "ColorPalette",
    "SemanticColors",
    "Typography",
    "Spacing",
    "BorderRadius",
]

__version__ = "2.0.0"
__author__ = "LOGIPORT Team"