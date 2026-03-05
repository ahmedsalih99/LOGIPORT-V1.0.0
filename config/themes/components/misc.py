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

    /* ========== QMENU - CONTEXT MENU & DROPDOWNS ========== */

    QMenu {{
        background-color : {c["bg_card"]};
        color            : {c["text_primary"]};
        border           : 1px solid {c["border"]};
        border-radius    : 10px;
        padding          : 6px 4px;
        font-size        : {s["base"]}px;
        font-weight      : 500;
    }}

    QMenu::item {{
        padding          : 9px 20px 9px 16px;
        border-radius    : 7px;
        margin           : 2px 4px;
        min-width        : 160px;
        color            : {c["text_primary"]};
    }}

    QMenu::item:selected {{
        background-color : {c["bg_hover"]};
        color            : {c["primary"]};
    }}

    QMenu::item:pressed {{
        background-color : {c["bg_active"]};
        color            : {c["primary_active"]};
    }}

    QMenu::item:disabled {{
        color            : {c["text_disabled"]};
        background-color : transparent;
    }}

    QMenu::separator {{
        height           : 1px;
        background       : {c["border_subtle"]};
        margin           : 4px 12px;
    }}

    QMenu::indicator {{
        width            : 16px;
        height           : 16px;
    }}

    /* ========== QCOMBOBOX DROPDOWN - أوسع وأكثر راحة ========== */

    QAbstractItemView {{
        background-color : {c["bg_card"]};
        color            : {c["text_primary"]};
        border           : 1px solid {c["border"]};
        border-radius    : 8px;
        padding          : 4px;
        outline          : none;
        selection-background-color: {c["primary_light"]};
        selection-color  : {c["primary"]};
    }}

    QAbstractItemView::item {{
        padding          : 8px 12px;
        border-radius    : 6px;
        min-height       : 34px;
        color            : {c["text_primary"]};
    }}

    QAbstractItemView::item:hover {{
        background-color : {c["bg_hover"]};
        color            : {c["primary"]};
    }}

    QAbstractItemView::item:selected {{
        background-color : {c["primary_light"]};
        color            : {c["primary"]};
        font-weight      : 600;
    }}
    """