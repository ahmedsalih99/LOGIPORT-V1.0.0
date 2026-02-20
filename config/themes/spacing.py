"""
Spacing System
==============

Provides consistent spacing values.
"""

class Spacing:
    """
    Standard spacing scale.

    Usage:
        >>> padding = f"{Spacing.SM} {Spacing.LG}"  # "8px 16px"
    """

    # Spacing values
    NONE = "0"
    XS = "4px"
    SM = "8px"
    MD = "12px"
    LG = "16px"
    XL = "20px"
    XXL = "24px"
    XXXL = "32px"

    @classmethod
    def get(cls, size: str) -> str:
        """
        Get spacing value by name.

        Args:
            size: Size name (xs, sm, md, lg, xl, xxl, xxxl)

        Returns:
            CSS spacing value

        Example:
            >>> Spacing.get("md")
            '12px'
        """
        size_upper = size.upper()
        if hasattr(cls, size_upper):
            return getattr(cls, size_upper)
        return cls.MD  # Default

    @classmethod
    def scale(cls, multiplier: float = 1.0) -> dict:
        """
        Generate scaled spacing.

        Args:
            multiplier: Scale factor (e.g., 1.5 for 1.5x spacing)

        Returns:
            Dictionary of scaled values
        """
        base_values = {
            "xs": 4,
            "sm": 8,
            "md": 12,
            "lg": 16,
            "xl": 20,
            "xxl": 24,
            "xxxl": 32,
        }

        return {
            key: f"{int(value * multiplier)}px"
            for key, value in base_values.items()
        }


# Export
SPACING = Spacing