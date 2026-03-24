"""
sidebar.py (theme) — Floating Pill Navigation Styles
======================================================
Styles للـ FloatingPillNav — شريط التنقل الأفقي العائم.
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ── Floating Pill container ─────────────────────────────────── */

    QFrame#FloatingPill {{
        background   : transparent;
        border       : none;
    }}

    QFrame#pill-inner {{
        background   : {c["bg_card"]};
        border       : 1px solid {c["border"]};
        border-radius: 40px;
    }}

    /* ── Tab buttons ─────────────────────────────────────────────── */

    QToolButton#pill-tab-btn {{
        background   : transparent;
        border       : none;
        border-radius: 12px;
        padding      : 4px 8px 6px 8px;
        color        : {c["text_secondary"]};
        font-size    : {s["sm"]}px;
        font-weight  : 500;
        min-width    : 60px;
        max-width    : 100px;
        /* Qt needs explicit text position for ToolButtonTextUnderIcon */
        qproperty-toolButtonStyle: ToolButtonTextUnderIcon;
    }}

    QToolButton#pill-tab-btn:hover {{
        background : {c["bg_hover"]};
        color      : {c["text_primary"]};
    }}

    QToolButton#pill-tab-btn:checked {{
        background : {c["primary"]};
        color      : #FFFFFF;
        font-weight: 700;
        border-radius: 12px;
    }}

    QToolButton#pill-tab-btn:checked:hover {{
        background : {c["primary_hover"]};
    }}

    /* ── backward compat — لو في مكان يستخدم sidebar-btn ────────── */

    QToolButton#sidebar-btn {{
        background   : transparent;
        border       : none;
        border-radius: {BorderRadius.LG};
        padding      : {Spacing.SM} {Spacing.MD};
        color        : {c["text_secondary"]};
        font-size    : {s["base"]}px;
        font-weight  : 500;
    }}

    QToolButton#sidebar-btn:hover {{
        background: {c["bg_hover"]};
        color     : {c["text_primary"]};
    }}

    QToolButton#sidebar-btn:checked {{
        background: {c["bg_sidebar"]};
        color     : {c["text_white"]};
        font-weight: 700;
    }}
    """