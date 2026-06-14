"""
Color Palettes for LOGIPORT Themes
===================================

LOGIPORT Brand Identity — Navy + Gold
Primary: #0D1B2A (Navy Midnight)
Accent:  #C9A84C (Champagne Gold)
"""

class ColorPalette:
    """
    Base color palettes for light and dark themes.

    Usage:
        >>> palette = ColorPalette.LIGHT
        >>> primary_color = palette["navy_900"]
    """

    # Light Theme Palette
    LIGHT = {
        # ── LOGIPORT Brand ──────────────────────────────────────────
        "navy_900": "#0D1B2A",   # Primary — Navy Midnight
        "navy_800": "#122337",
        "navy_700": "#1B2F4A",   # Hover
        "navy_600": "#1E3A5F",
        "navy_500": "#25496F",

        "gold_600": "#A8873A",   # Pressed
        "gold_500": "#C9A84C",   # Accent — Champagne Gold
        "gold_400": "#D4B86A",   # Hover
        "gold_100": "#F5EDD6",   # Light bg tint
        "gold_50":  "#FBF7EE",   # Softer tint

        # Blues (kept for status/info colours)
        "blue_50":  "#EFF6FF",
        "blue_100": "#DBEAFE",
        "blue_200": "#BFDBFE",
        "blue_300": "#93C5FD",
        "blue_400": "#60A5FA",
        "blue_500": "#3B82F6",
        "blue_600": "#2563EB",
        "blue_700": "#1D4ED8",
        "blue_800": "#1E40AF",
        "blue_900": "#1E3A8A",

        # Grays (Neutral)
        "gray_50":  "#F9FAFB",
        "gray_100": "#F3F4F6",
        "gray_200": "#E5E7EB",
        "gray_300": "#D1D5DB",
        "gray_400": "#9CA3AF",
        "gray_500": "#6B7280",
        "gray_600": "#4B5563",
        "gray_700": "#374151",
        "gray_800": "#1F2937",
        "gray_900": "#111827",

        # Greens (Success)
        "green_50":  "#ECFDF5",
        "green_100": "#D1FAE5",
        "green_500": "#10B981",
        "green_600": "#059669",
        "green_700": "#047857",

        # Reds (Danger)
        "red_50":  "#FEF2F2",
        "red_100": "#FEE2E2",
        "red_500": "#EF4444",
        "red_600": "#DC2626",
        "red_700": "#B91C1C",

        # Yellows (Warning)
        "yellow_50":  "#FFFBEB",
        "yellow_100": "#FEF3C7",
        "yellow_500": "#F59E0B",
        "yellow_600": "#D97706",
        "yellow_700": "#B45309",

        # Special
        "white": "#FFFFFF",
        "black": "#000000",
    }

    # Dark Theme Palette
    DARK = {
        # ── LOGIPORT Brand ──────────────────────────────────────────
        "navy_900": "#0D1B2A",   # Deepest navy (sidebar/topbar)
        "navy_800": "#122337",
        "navy_700": "#1B2F4A",   # Card bg
        "navy_600": "#1E3A5F",
        "navy_500": "#25496F",

        "gold_600": "#A8873A",   # Pressed
        "gold_500": "#C9A84C",   # Accent — Champagne Gold
        "gold_400": "#D4B86A",   # Hover
        "gold_100": "#3A2E14",   # Dark gold tint bg
        "gold_50":  "#2A2210",   # Softer dark tint

        # Blues (kept for status/info)
        "blue_400": "#60A5FA",
        "blue_500": "#3B82F6",
        "blue_600": "#2563EB",
        "blue_700": "#1D4ED8",

        # Grays (Neutral) — Darker
        "gray_50":  "#1B2430",   # Main BG
        "gray_100": "#1B2B3A",   # Card BG
        "gray_200": "#243447",   # Border
        "gray_300": "#2c3a4d",   # Border Hover
        "gray_400": "#64748B",   # Text Secondary
        "gray_500": "#94A3B8",   # Text Muted
        "gray_600": "#CBD5E1",
        "gray_700": "#E2E8F0",
        "gray_800": "#F1F5F9",
        "gray_900": "#F4F6F6",   # Text Primary

        # Greens (Success)
        "green_500": "#10B981",
        "green_600": "#059669",

        # Reds (Danger)
        "red_500": "#EF4444",
        "red_600": "#DC2626",

        # Yellows (Warning)
        "yellow_500": "#F59E0B",
        "yellow_600": "#D97706",

        # Special
        "white": "#FFFFFF",
        "black": "#000000",
    }

    @classmethod
    def get(cls, theme_name: str):
        """Get palette by name"""
        theme_name = theme_name.upper()
        if hasattr(cls, theme_name):
            return getattr(cls, theme_name)
        return cls.LIGHT  # Default


# Export for convenience
LIGHT_PALETTE = ColorPalette.LIGHT
DARK_PALETTE = ColorPalette.DARK