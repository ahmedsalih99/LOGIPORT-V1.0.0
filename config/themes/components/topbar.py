"""
TopBar Component Styles - Clean Modern
=======================================
إصلاح: على الـ light theme كانت الخلفية glass على أبيض = مش مرئي
الحل: خلفية صلبة واضحة مع shadow خفيف تحت
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    c = theme.colors
    s = theme.sizes

    # نحدد إذا dark أو light للتعامل مع الـ topbar بشكل مختلف
    is_dark = c.get("bg_main", "#fff").startswith("#1") or c.get("bg_main", "#fff").startswith("#0")

    return f"""
    /* ========== TOPBAR ========== */

    QWidget#TopBar {{
        background  : {c["bg_topbar"]};
        border-bottom: 1px solid {c["border_subtle"]};
    }}

    /* ========== TOPBAR BUTTONS ========== */

    QPushButton#topbar-btn {{
        min-height  : 34px;
        background  : {c["bg_hover"]};
        border      : 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        padding     : 5px 14px;
        color       : {c["topbar_text"]};
        font-weight : 500;
        font-size   : {s["sm"]}px;
    }}

    QPushButton#topbar-btn:hover {{
        background  : {c["bg_active"]};
        border-color: {c["border_hover"]};
        color       : {c["primary"]};
    }}

    QPushButton#topbar-btn:pressed {{
        background  : {c["primary_light"]};
        border-color: {c["primary"]};
    }}

    /* ========== CLOCK ========== */

    QLabel#topbar-clock {{
        min-height  : 34px;
        padding     : 5px 14px;
        background  : {c["primary_light"]};
        border      : 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        color       : {c["primary"]};
        font-size   : {s["md"]}px;
        font-weight : 700;
    }}

    /* ========== USER BOX ========== */

    QWidget#topbar-user-box {{
        min-height  : 34px;
        background  : {c["bg_hover"]};
        border      : 1px solid {c["border"]};
        border-radius: {BorderRadius.LG};
        padding     : 4px 12px;
    }}

    QLabel#topbar-username {{
        font-size   : {s["sm"]}px;
        font-weight : 600;
        color       : {c["topbar_text"]};
        padding     : 0 6px;
    }}

    QLabel#topbar-user-pic {{
        min-width   : 22px;
        min-height  : 22px;
        font-size   : {s["lg"]}px;
        text-align  : center;
    }}

    /* ── Icon-only topbar buttons ── */

    QPushButton#topbar-btn-icon {{
        min-width   : 34px;
        min-height  : 34px;
        max-width   : 34px;
        max-height  : 34px;
        background  : {c["bg_hover"]};
        border      : 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        padding     : 0;
        color       : {c["topbar_icon"]};
    }}

    QPushButton#topbar-btn-icon:hover {{
        background  : {c["bg_active"]};
        border-color: {c["border_hover"]};
        color       : {c["primary"]};
    }}

    QPushButton#topbar-btn-icon:pressed {{
        background  : {c["primary_light"]};
        border-color: {c["primary"]};
    }}
    """
