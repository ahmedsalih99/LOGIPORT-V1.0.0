"""
Sidebar Component Styles - Blue Modern with Smooth Hover
=======================================================

Professional blue Sidebar with semantic colors and smooth animations.
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    """Generate Sidebar styles (Blue Variant)"""
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ========== SIDEBAR ========== */

    /* Sidebar Container */
    QFrame#Sidebar {{
        background: {c["bg_sidebar"]};
        border-left: 1px solid {c["border_subtle"]};
    }}

    /* Sidebar Buttons */
    QToolButton#sidebar-btn {{
        background: transparent;
        border: none;
        border-radius: {BorderRadius.LG};
        padding: {Spacing.SM};
        color: {c["sidebar_text"]};
        text-align: right;
        font-size: {s["base"]}px;
    }}

    /* Hover */
    QToolButton#sidebar-btn:hover {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 0,
            stop: 0 {c["primary_light"]},
            stop: 1 {c["primary_lighter"]}
        );
        color: {c["sidebar_text_hover"]};
    }}

    /* Active / Checked */
    QToolButton#sidebar-btn:checked {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 0,
            stop: 0 {c["accent_soft"]},
            stop: 1 {c["primary_lighter"]}
        );
        color: {c["sidebar_text"]};
        border-right: 3px solid {c["primary"]};
        font-weight: 600;
    }}

    /* Toggle Button */
    QPushButton#sidebar-toggle-btn {{
        background: {c["primary_light"]};
        border: 2px solid {c["border_focus"]};
        border-radius: 50%;
    }}

    QPushButton#sidebar-toggle-btn:hover {{
        background: {c["accent_soft"]};
        border: 2px solid {c["primary"]};
    }}

    QPushButton#sidebar-toggle-btn:pressed {{
        background: {c["primary_hover"]};
    }}

    /* Logo Box */
    QFrame#SidebarLogoBox {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 {c["bg_elevated"]},
            stop: 1 {c["bg_sidebar"]}
        );
        border-bottom: 1px solid {c["border_subtle"]};
    }}

    QLabel#sidebar-app-name {{
        color: {c["sidebar_text"]};
        font-size: {s["lg"]}px;
        font-weight: 700;
        letter-spacing: 1px;
    }}

    /* Separator */
    QFrame#sidebar-separator {{
        background: {c["border_subtle"]};
    }}
    """
