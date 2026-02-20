"""
Miscellaneous Component Styles
===============================

Scrollbar and other misc UI elements with modern gradients.
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    """Generate miscellaneous styles"""
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ========== SCROLLBAR - MODERN WITH GRADIENT ========== */

    /* Vertical Scrollbar */
    QScrollBar:vertical {{
        background: {c["bg_main"]};
        width: 12px;
        border-radius: 6px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 0,
            stop: 0 {c["primary"]},
            stop: 1 {c["primary_hover"]}
        );
        border-radius: 6px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {c["primary_hover"]};
    }}

    QScrollBar::add-line:vertical, 
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar::add-page:vertical, 
    QScrollBar::sub-page:vertical {{
        background: none;
    }}

    /* Horizontal Scrollbar */
    QScrollBar:horizontal {{
        background: {c["bg_main"]};
        height: 12px;
        border-radius: 6px;
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 {c["primary"]},
            stop: 1 {c["primary_hover"]}
        );
        border-radius: 6px;
        min-width: 30px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {c["primary_hover"]};
    }}

    QScrollBar::add-line:horizontal, 
    QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    """