"""Light Theme Preset"""

from ..builder import ThemeBuilder


def get_stylesheet(font_size=12, font_family="Tajawal"):
    """
    Get light theme stylesheet.

    This is a preset wrapper around ThemeBuilder for backward compatibility.

    Args:
        font_size: Font size in pixels
        font_family: Font family name

    Returns:
        Complete CSS stylesheet string
    """
    theme = ThemeBuilder(
        theme_name="light",
        font_size=font_size,
        font_family=font_family
    )

    return theme.build()