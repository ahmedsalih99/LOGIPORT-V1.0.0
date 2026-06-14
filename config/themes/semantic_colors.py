"""
Semantic Color System - LOGIPORT Brand Identity
================================================

Navy Midnight (#0D1B2A) + Champagne Gold (#C9A84C)
"""

from .palettes import ColorPalette


class SemanticColors:
    """
    LOGIPORT brand semantic color mapping.
    Primary  = Navy Midnight  #0D1B2A
    Accent   = Champagne Gold #C9A84C
    """

    @staticmethod
    def get_light():
        """Get semantic colors for LIGHT theme — Navy + Gold"""

        return {
            # ========== Primary (Navy) ==========
            "primary":          "#0D1B2A",              # Navy Midnight
            "primary_hover":    "#1B2F4A",              # Navy 700
            "primary_active":   "#122337",              # Navy 800
            "primary_light":    "rgba(13, 27, 42, 0.08)",
            "primary_lighter":  "rgba(13, 27, 42, 0.04)",

            # ========== Accent (Gold) ==========
            "accent":           "#C9A84C",              # Champagne Gold
            "accent_hover":     "#D4B86A",              # Gold 400
            "accent_active":    "#A8873A",              # Gold 600
            "accent_soft":      "rgba(201, 168, 76, 0.15)",

            # ========== Success (Green) ==========
            "success":          "#10B981",
            "success_hover":    "#34D399",
            "success_active":   "#059669",
            "success_light":    "rgba(16, 185, 129, 0.1)",

            # ========== Warning (Orange) ==========
            "warning":          "#F39C12",
            "warning_hover":    "#FFB836",
            "warning_active":   "#E67E00",
            "warning_light":    "rgba(243, 156, 18, 0.1)",

            # ========== Danger (Red) ==========
            "danger":           "#E74C3C",
            "danger_hover":     "#FF6B5C",
            "danger_active":    "#C0392B",
            "danger_light":     "rgba(231, 76, 60, 0.1)",

            # ========== Info (Blue — kept for status) ==========
            "info":             "#3498DB",
            "info_hover":       "#5DADE2",
            "info_active":      "#2874A6",
            "info_light":       "rgba(52, 152, 219, 0.1)",

            # ========== Backgrounds ==========
            "bg_main":                  "#FFFFFF",
            "bg_card":                  "#FFFFFF",
            "bg_hover":                 "#F5EDD6",      # Gold 50 warm tint
            "bg_active":                "#F0E4C0",      # Slightly deeper gold tint
            "bg_disabled":              "#F3F4F6",
            "bg_selected":              "#FBF7EE",      # Gold 50
            "bg_main_gradient_start":   "#FFFFFF",
            "bg_main_gradient_end":     "#F8F7F4",      # Warm off-white
            "bg_elevated":              "#FFFFFF",
            "bg_sidebar":               "#0D1B2A",      # Navy Midnight
            "bg_topbar":                "#FFFFFF",
            "bg_input":                 "#FFFFFF",

            # Surface levels
            "bg_surface_1":     "#FFFFFF",
            "bg_surface_2":     "#F8F7F4",
            "bg_surface_3":     "#FBF7EE",
            "bg_surface_focus": "#FBF7EE",

            # ========== Sidebar Colors ==========
            "sidebar_text":         "#FFFFFF",
            "sidebar_text_hover":   "#C9A84C",          # Gold on hover
            "sidebar_item_hover":   "rgba(201, 168, 76, 0.15)",
            "sidebar_item_active":  "rgba(201, 168, 76, 0.25)",

            # ========== Topbar Colors ==========
            "topbar_text":  "#0D1B2A",
            "topbar_icon":  "#0D1B2A",

            # ========== Text Colors ==========
            "text_primary":     "#0D1B2A",              # Navy as primary text
            "text_secondary":   "#374151",
            "text_muted":       "#6B7280",
            "text_disabled":    "#ADB5BD",
            "text_white":       "#FFFFFF",
            "text_inverse":     "#FFFFFF",

            # ========== Borders ==========
            "border":           "#E0E0E0",
            "border_subtle":    "#F0F0F0",
            "border_hover":     "#C9A84C",              # Gold on hover
            "border_focus":     "#C9A84C",              # Gold when focused
            "border_error":     "#E74C3C",

            # ========== Shadows ==========
            "shadow":       "rgba(13, 27, 42, 0.10)",
            "shadow_sm":    "rgba(13, 27, 42, 0.05)",
            "shadow_md":    "rgba(13, 27, 42, 0.10)",
            "shadow_lg":    "rgba(13, 27, 42, 0.15)",
            "shadow_xl":    "rgba(13, 27, 42, 0.20)",

            # ========== Special Effects ==========
            "glass_bg":     "rgba(255, 255, 255, 0.8)",
            "glass_border": "rgba(255, 255, 255, 0.2)",
            "overlay":      "rgba(13, 27, 42, 0.5)",

            # ========== Backgrounds (aliases) ==========
            "bg_primary":   "#FFFFFF",
            "bg_secondary": "#FFFFFF",
            "bg_surface":   "#FFFFFF",

            # ========== Inputs ==========
            "input_bg": "#FFFFFF",

            # ========== Extended Accent Colors ==========
            "accent_indigo":    "#6366F1",
            "accent_violet":    "#8B5CF6",
            "accent_purple":    "#7C3AED",
            "accent_cyan":      "#0891B2",

            # ========== Status Colors (container timeline) ==========
            "status_booked":        "#6366F1",
            "status_loaded":        "#0891B2",
            "status_in_transit":    "#0D1B2A",          # Navy
            "status_arrived":       "#7C3AED",
            "status_customs":       "#C9A84C",          # Gold
            "status_delivered":     "#059669",
            "status_hold":          "#DC2626",

            # ========== Progress / Chart Colors ==========
            "chart_red":        "#EF4444",
            "chart_orange":     "#F97316",
            "chart_yellow":     "#C9A84C",              # Gold replaces yellow
            "chart_lime":       "#84CC16",
            "chart_green":      "#10B981",
            "chart_green_light":"#6EE7B7",

            # ========== Background aliases (legacy support) ==========
            "background":   "#F8F7F4",
            "surface":      "#FFFFFF",
        }

    @staticmethod
    def get_dark():
        """Get semantic colors for DARK theme — Deep Navy + Gold"""

        return {
            # ========== Primary (Navy — lighter for dark bg) ==========
            "primary":          "#C9A84C",              # Gold as primary CTA in dark
            "primary_hover":    "#D4B86A",
            "primary_active":   "#A8873A",
            "primary_light":    "rgba(201, 168, 76, 0.15)",
            "primary_lighter":  "rgba(201, 168, 76, 0.08)",

            # ========== Accent (Navy tones) ==========
            "accent":           "#C9A84C",
            "accent_hover":     "#D4B86A",
            "accent_active":    "#A8873A",
            "accent_soft":      "rgba(201, 168, 76, 0.20)",

            # ========== Success (Green) ==========
            "success":          "#10B981",
            "success_hover":    "#34D399",
            "success_active":   "#059669",
            "success_light":    "rgba(16, 185, 129, 0.15)",

            # ========== Warning (Orange) ==========
            "warning":          "#F39C12",
            "warning_hover":    "#FFB836",
            "warning_active":   "#E67E00",
            "warning_light":    "rgba(243, 156, 18, 0.15)",

            # ========== Danger (Red) ==========
            "danger":           "#E74C3C",
            "danger_hover":     "#FF6B5C",
            "danger_active":    "#C0392B",
            "danger_light":     "rgba(231, 76, 60, 0.15)",

            # ========== Info (Blue) ==========
            "info":             "#3498DB",
            "info_hover":       "#5DADE2",
            "info_active":      "#2874A6",
            "info_light":       "rgba(52, 152, 219, 0.15)",

            # ========== Backgrounds ==========
            "bg_main":                  "#0D1B2A",      # Navy Midnight as base
            "bg_card":                  "#122337",      # Navy 800
            "bg_hover":                 "#1B2F4A",      # Navy 700
            "bg_active":                "#1E3A5F",      # Navy 600
            "bg_disabled":              "#1B2F4A",
            "bg_selected":              "#25496F",      # Navy 500

            "bg_main_gradient_start":   "#0D1B2A",
            "bg_main_gradient_end":     "#0A1520",
            "bg_elevated":              "#1B2F4A",
            "bg_sidebar":               "#080F18",      # Deeper than main
            "bg_topbar":                "#122337",      # Navy 800
            "bg_input":                 "#1B2F4A",

            # Surface levels
            "bg_surface_1":     "#122337",
            "bg_surface_2":     "#0D1B2A",
            "bg_surface_3":     "#1B2F4A",
            "bg_surface_focus": "#1E3A5F",

            # ========== Sidebar Colors ==========
            "sidebar_text":         "#FFFFFF",
            "sidebar_text_hover":   "#C9A84C",
            "sidebar_item_hover":   "rgba(201, 168, 76, 0.15)",
            "sidebar_item_active":  "rgba(201, 168, 76, 0.25)",

            # ========== Topbar Colors ==========
            "topbar_text":  "#F1F5F9",
            "topbar_icon":  "#C9A84C",                  # Gold icons in topbar

            # ========== Text Colors ==========
            "text_primary":     "#F1F5F9",
            "text_secondary":   "#CBD5E1",
            "text_muted":       "#94A3B8",
            "text_disabled":    "#64748B",
            "text_white":       "#FFFFFF",
            "text_inverse":     "#0D1B2A",

            # ========== Borders ==========
            "border":           "#1E3A5F",
            "border_subtle":    "#1B2F4A",
            "border_hover":     "#C9A84C",              # Gold border on hover
            "border_focus":     "#C9A84C",              # Gold border on focus
            "border_error":     "#E74C3C",

            # ========== Shadows ==========
            "shadow":       "rgba(0, 0, 0, 0.40)",
            "shadow_sm":    "rgba(0, 0, 0, 0.25)",
            "shadow_md":    "rgba(0, 0, 0, 0.40)",
            "shadow_lg":    "rgba(0, 0, 0, 0.55)",
            "shadow_xl":    "rgba(0, 0, 0, 0.70)",

            # ========== Special Effects ==========
            "glass_bg":     "rgba(13, 27, 42, 0.85)",
            "glass_border": "rgba(201, 168, 76, 0.15)",
            "overlay":      "rgba(0, 0, 0, 0.70)",

            # ========== Backgrounds (aliases) ==========
            "bg_primary":   "#0D1B2A",
            "bg_secondary": "#122337",
            "bg_surface":   "#122337",

            # ========== Inputs ==========
            "input_bg": "#1B2F4A",

            # ========== Extended Accent Colors ==========
            "accent_indigo":    "#818CF8",
            "accent_violet":    "#A78BFA",
            "accent_purple":    "#9061F9",
            "accent_cyan":      "#22D3EE",

            # ========== Status Colors ==========
            "status_booked":        "#818CF8",
            "status_loaded":        "#22D3EE",
            "status_in_transit":    "#C9A84C",          # Gold
            "status_arrived":       "#9061F9",
            "status_customs":       "#D4B86A",          # Light gold
            "status_delivered":     "#34D399",
            "status_hold":          "#F87171",

            # ========== Progress / Chart Colors ==========
            "chart_red":        "#F87171",
            "chart_orange":     "#FB923C",
            "chart_yellow":     "#C9A84C",              # Gold
            "chart_lime":       "#A3E635",
            "chart_green":      "#34D399",
            "chart_green_light":"#6EE7B7",

            # ========== Background aliases ==========
            "background":   "#0D1B2A",
            "surface":      "#122337",
        }

    @classmethod
    def get(cls, theme_name: str):
        """Get semantic colors by theme name"""
        if theme_name.lower() == "dark":
            return cls.get_dark()
        return cls.get_light()