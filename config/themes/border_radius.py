"""
Border Radius System
====================

Provides consistent border radius values.
"""

class BorderRadius:
    """
    Standard border radius scale.

    Usage:
        >>> btn_radius = BorderRadius.MD  # "10px"
    """

    NONE = "0"
    SM = "6px"
    MD = "10px"
    LG = "12px"
    XL = "16px"
    XXL = "22px"
    FULL = "9999px"  # Circular

    @classmethod
    def get(cls, size: str) -> str:
        """Get radius by name"""
        size_upper = size.upper()
        if hasattr(cls, size_upper):
            return getattr(cls, size_upper)
        return cls.MD


# Export
BORDER_RADIUS = BorderRadius