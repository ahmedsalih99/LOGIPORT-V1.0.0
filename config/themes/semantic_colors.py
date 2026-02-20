"""
Semantic Color System - LOGIPORT v3.0 PROFESSIONAL
===================================================

Professional color scheme with blue sidebar.
"""

from .palettes import ColorPalette


class SemanticColors:
    """
    Professional semantic color mapping with blue sidebar.
    """

    @staticmethod
    def get_light():
        """Get semantic colors for LIGHT theme - PROFESSIONAL BLUE"""
        palette = ColorPalette.LIGHT

        return {
            # ========== Primary (Blue) - Professional ==========
            "primary": "#4A7EC8",              # Professional blue - matches sidebar
            "primary_hover": "#5B8ED8",        # Lighter on hover
            "primary_active": "#3A6EB8",       # Darker on press
            "primary_light": "rgba(74, 126, 200, 0.1)",
            "primary_lighter": "rgba(74, 126, 200, 0.05)",

            # ========== Success (Green) ==========
            "success": "#2ECC71",
            "success_hover": "#48E68B",
            "success_active": "#27AE60",
            "success_light": "rgba(46, 204, 113, 0.1)",

            # ========== Warning (Orange) ==========
            "warning": "#F39C12",
            "warning_hover": "#FFB836",
            "warning_active": "#E67E00",
            "warning_light": "rgba(243, 156, 18, 0.1)",

            # ========== Danger (Red) ==========
            "danger": "#E74C3C",
            "danger_hover": "#FF6B5C",
            "danger_active": "#C0392B",
            "danger_light": "rgba(231, 76, 60, 0.1)",

            # ========== Info (Cyan) ==========
            "info": "#3498DB",
            "info_hover": "#5DADE2",
            "info_active": "#2874A6",
            "info_light": "rgba(52, 152, 219, 0.1)",

            # ========== Backgrounds ==========
            "bg_main": "#FFFFFF",              # Pure white background
            "bg_card": "#FFFFFF",              # Pure white cards
            "bg_hover": "#F0F7FF",             # Light blue hover
            "bg_active": "#E3F2FF",            # Light blue active
            "bg_disabled": "#F3F4F6",          # Light gray disabled
            "bg_selected": "#E3F2FF",          # Light blue selected

            # Gradient backgrounds
            "bg_main_gradient_start": "#FFFFFF",
            "bg_main_gradient_end": "#F8F9FA",
            "bg_elevated": "#FFFFFF",
            "bg_sidebar": "#4A7EC8",           # Blue sidebar - lighter professional
            "bg_topbar": "#FFFFFF",            # White topbar
            "bg_input": "#FFFFFF",

            # ========== Sidebar Colors ==========
            "sidebar_text": "#FFFFFF",         # White text
            "sidebar_text_hover": "#FFFFFF",   # White on hover
            "sidebar_item_hover": "rgba(255, 255, 255, 0.2)",
            "sidebar_item_active": "rgba(255, 255, 255, 0.3)",

            # ========== Topbar Colors ==========
            "topbar_text": "#495057",          # Dark gray text
            "topbar_icon": "#495057",          # Dark gray icons

            # ========== Text Colors ==========
            "text_primary": "#212529",         # Almost black
            "text_secondary": "#495057",       # Dark gray
            "text_muted": "#6C757D",           # Medium gray
            "text_disabled": "#ADB5BD",        # Light gray
            "text_white": "#FFFFFF",           # Pure white
            "text_inverse": "#FFFFFF",         # Inverse

            # ========== Borders ==========
            "border": "#E0E0E0",               # Clear gray border
            "border_subtle": "#F0F0F0",        # Subtle
            "border_hover": "#4A7EC8",         # Blue on hover - matches sidebar
            "border_focus": "#4A7EC8",         # Blue when focused - matches sidebar
            "border_error": "#E74C3C",         # Red for errors

            # ========== Shadows ==========
            "shadow": "rgba(0, 0, 0, 0.1)",
            "shadow_sm": "rgba(0, 0, 0, 0.05)",
            "shadow_md": "rgba(0, 0, 0, 0.1)",
            "shadow_lg": "rgba(0, 0, 0, 0.15)",
            "shadow_xl": "rgba(0, 0, 0, 0.2)",

            # ========== Special Effects ==========
            "glass_bg": "rgba(255, 255, 255, 0.8)",
            "glass_border": "rgba(255, 255, 255, 0.2)",
            "overlay": "rgba(0, 0, 0, 0.5)",

            # ========== Backgrounds (aliases) ==========
            "bg_primary": "#FFFFFF",
            "bg_secondary": "#FFFFFF",
            "bg_surface": "#FFFFFF",

            # ========== Accent System ==========
            "accent": "#4A7EC8",
            "accent_hover": "#5B8ED8",
            "accent_active": "#3A6EB8",
            "accent_soft": "rgba(74, 126, 200, 0.15)",

            # ========== Inputs ==========
            "input_bg": "#FFFFFF",
        }

    @staticmethod
    def get_dark():
        """Get semantic colors for DARK theme"""
        palette = ColorPalette.DARK

        return {
            # ========== Primary (Blue) ==========
            "primary": "#3D6DB3",
            "primary_hover": "#5484C7",
            "primary_active": "#2C5AA0",
            "primary_light": "rgba(61, 109, 179, 0.15)",
            "primary_lighter": "rgba(61, 109, 179, 0.08)",

            # ========== Success (Green) ==========
            "success": "#2ECC71",
            "success_hover": "#48E68B",
            "success_active": "#27AE60",
            "success_light": "rgba(46, 204, 113, 0.15)",

            # ========== Warning (Orange) ==========
            "warning": "#F39C12",
            "warning_hover": "#FFB836",
            "warning_active": "#E67E00",
            "warning_light": "rgba(243, 156, 18, 0.15)",

            # ========== Danger (Red) ==========
            "danger": "#E74C3C",
            "danger_hover": "#FF6B5C",
            "danger_active": "#C0392B",
            "danger_light": "rgba(231, 76, 60, 0.15)",

            # ========== Info (Cyan) ==========
            "info": "#3498DB",
            "info_hover": "#5DADE2",
            "info_active": "#2874A6",
            "info_light": "rgba(52, 152, 219, 0.15)",

            # ========== Backgrounds ==========
            "bg_main": "#111827",
            "bg_card": "#1F2937",
            "bg_hover": "#374151",
            "bg_active": "#4B5563",
            "bg_disabled": "#1F2937",
            "bg_selected": "#1E3A8A",

            # Gradient backgrounds
            "bg_main_gradient_start": "#1a1f2e",
            "bg_main_gradient_end": "#0f1419",
            "bg_elevated": "#1a1f2e",
            "bg_sidebar": "#1a2332",
            "bg_topbar": "#1F2937",
            "bg_input": "#1e2430",

            # ========== Sidebar Colors ==========
            "sidebar_text": "#FFFFFF",
            "sidebar_text_hover": "#FFFFFF",
            "sidebar_item_hover": "rgba(255, 255, 255, 0.1)",
            "sidebar_item_active": "rgba(255, 255, 255, 0.2)",

            # ========== Topbar Colors ==========
            "topbar_text": "#FFFFFF",
            "topbar_icon": "#FFFFFF",

            # ========== Text Colors ==========
            "text_primary": "#F9FAFB",
            "text_secondary": "#D1D5DB",
            "text_muted": "#9CA3AF",
            "text_disabled": "#6B7280",
            "text_white": "#FFFFFF",
            "text_inverse": "#212529",

            # ========== Borders ==========
            "border": "#374151",
            "border_subtle": "#252b3b",
            "border_hover": "#4B5563",
            "border_focus": "#3D6DB3",
            "border_error": "#E74C3C",

            # ========== Shadows ==========
            "shadow": "rgba(0, 0, 0, 0.3)",
            "shadow_sm": "rgba(0, 0, 0, 0.2)",
            "shadow_md": "rgba(0, 0, 0, 0.3)",
            "shadow_lg": "rgba(0, 0, 0, 0.4)",
            "shadow_xl": "rgba(0, 0, 0, 0.5)",

            # ========== Special Effects ==========
            "glass_bg": "rgba(26, 31, 46, 0.8)",
            "glass_border": "rgba(255, 255, 255, 0.1)",
            "overlay": "rgba(0, 0, 0, 0.7)",

            # ========== Backgrounds (aliases) ==========
            "bg_primary": "#111827",
            "bg_secondary": "#1F2937",
            "bg_surface": "#1F2937",

            # ========== Accent System ==========
            "accent": "#3D6DB3",
            "accent_hover": "#5484C7",
            "accent_active": "#2C5AA0",
            "accent_soft": "rgba(61, 109, 179, 0.25)",

            # ========== Inputs ==========
            "input_bg": "#1e2430",
        }

    @classmethod
    def get(cls, theme_name: str):
        """Get semantic colors by theme name"""
        if theme_name.lower() == "dark":
            return cls.get_dark()
        return cls.get_light()