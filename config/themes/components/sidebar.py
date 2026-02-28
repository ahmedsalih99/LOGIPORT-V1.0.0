"""
Sidebar Component Styles - RTL-Aware Blue Modern
=================================================
إصلاحات:
  - active border على الجانب الأيمن (RTL) بدل الأيسر
  - hover gradient صحيح الاتجاه
  - active state أوضح مع خلفية solid خفيفة
  - logo box gradient محسّن
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    """Generate RTL-correct Sidebar styles"""
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ========== SIDEBAR CONTAINER ========== */

    QFrame#Sidebar {{
        background  : {c["bg_sidebar"]};
        border-left : 1px solid rgba(255, 255, 255, 0.08);
    }}

    /* ========== SIDEBAR BUTTONS ========== */

    QToolButton#sidebar-btn {{
        background   : transparent;
        border       : none;
        border-radius: {BorderRadius.LG};
        padding      : {Spacing.SM} {Spacing.MD};
        color        : {c["sidebar_text"]};
        text-align   : right;
        font-size    : {s["base"]}px;
        font-weight  : 500;
    }}

    /* Hover — gradient من اليمين للأيسر (RTL-friendly) */
    QToolButton#sidebar-btn:hover {{
        background: rgba(255, 255, 255, 0.12);
        color     : {c["sidebar_text_hover"]};
        border-radius: {BorderRadius.MD};
    }}

    /* Active/Checked — خلفية صلبة واضحة + خط على اليمين (RTL) */
    QToolButton#sidebar-btn:checked {{
        background  : rgba(255, 255, 255, 0.22);
        color       : {c["sidebar_text"]};
        font-weight : 700;
        border-right: 3px solid {c["text_white"]};
        border-top-right-radius   : 0px;
        border-bottom-right-radius: 0px;
    }}

    /* ========== TOGGLE BUTTON ========== */

    QPushButton#sidebar-toggle-btn {{
        background   : rgba(255, 255, 255, 0.15);
        border       : 1.5px solid rgba(255, 255, 255, 0.4);
        border-radius: 50%;
    }}

    QPushButton#sidebar-toggle-btn:hover {{
        background: rgba(255, 255, 255, 0.25);
        border    : 1.5px solid rgba(255, 255, 255, 0.7);
    }}

    QPushButton#sidebar-toggle-btn:pressed {{
        background: rgba(255, 255, 255, 0.35);
    }}

    /* ========== LOGO BOX ========== */

    QFrame#SidebarLogoBox {{
        background   : transparent;
        border-bottom: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 0px;
    }}

    QLabel#sidebar-app-name {{
        color      : {c["sidebar_text"]};
        font-size  : {s["lg"]}px;
        font-weight: 800;
        letter-spacing: 1px;
    }}

    /* ========== SEPARATOR ========== */

    QFrame#sidebar-separator {{
        background: rgba(255, 255, 255, 0.12);
        border    : none;
        max-height: 1px;
    }}
    """
