"""
Typography Scale System
=======================

Provides consistent font sizing across the application.
"""

class Typography:
    """
    Font size scale based on base size.

    Usage:
        >>> sizes = Typography.scale(12)
        >>> title_size = sizes["3xl"]  # 21px
    """

    @staticmethod
    def scale(base_size: int = 12) -> dict:
        """
        Generate font size scale.

        Args:
            base_size: Base font size in pixels (typically 12-14)

        Returns:
            Dictionary with size names and pixel values

        Example:
            >>> sizes = Typography.scale(12)
            >>> sizes
            {
                'xs': 10,
                'sm': 11,
                'base': 12,
                'md': 13,
                'lg': 14,
                'xl': 16,
                '2xl': 18,
                '3xl': 21,
                '4xl': 24
            }
        """
        return {
            "xs": base_size - 2,      # 10px (base=12)
            "sm": base_size - 1,      # 11px
            "base": base_size,        # 12px
            "md": base_size + 1,      # 13px
            "lg": base_size + 2,      # 14px
            "xl": base_size + 4,      # 16px
            "2xl": base_size + 6,     # 18px
            "3xl": base_size + 9,     # 21px
            "4xl": base_size + 12,    # 24px
        }

    @staticmethod
    def get_font_weights() -> dict:
        """Standard font weights"""
        return {
            "normal": 400,
            "medium": 500,
            "semibold": 600,
            "bold": 700,
            "extrabold": 800,
        }


# Export for convenience
def get_typography_scale(base_size: int = 12):
    """Shorthand function"""
    return Typography.scale(base_size)