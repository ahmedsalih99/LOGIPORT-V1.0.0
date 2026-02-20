"""
Card Component Styles - FIXED
=====================

Modern card designs compatible with Qt.
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    """Generate card styles"""
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ========== CARDS ========== */

    /* Base Card */
    QFrame#card {{
        background: {c["bg_card"]};
        border: 1px solid {c["border_subtle"]};
        border-radius: 12px;
        padding: 20px;
    }}
    
    QFrame#card:hover {{
        border: 1px solid {c["primary"]};
        background: {c["bg_hover"]};
    }}

    /* Login Card - Special Gradient */
    QFrame#login-card {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 {c["bg_card"]},
            stop: 1 {c["bg_elevated"]}
        );
        border: 1px solid {c["border_subtle"]};
        border-radius: {BorderRadius.XXL};
    }}

    /* Settings Card */
    QFrame#settings-card {{
        background: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.XL};
    }}

    /* Settings Card Color Bar - Rainbow Gradient */
    QFrame#settings-card-bar {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 0,
            stop: 0 {c["primary"]},
            stop: 0.5 {c["info"]},
            stop: 1 {c["success"]}
        );
        border-radius: {BorderRadius.SM};
    }}
    """
