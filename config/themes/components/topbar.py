"""
TopBar Component Styles - Modern Glass Effect
==============================================

Professional TopBar with glass effects and smooth interactions.
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ========== TOPBAR ========== */

    QWidget#TopBar {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 {c["glass_bg"]},
            stop: 1 rgba(255, 255, 255, 0.7)
        );
        border-bottom: 1px solid {c["border_subtle"]};
    }}

    /* ========== TOPBAR BUTTONS ========== */
    QPushButton#topbar-btn {{
        min-height: 36px;
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 rgba(255, 255, 255, 0.15),
            stop: 1 rgba(255, 255, 255, 0.05)
        );
        border: 1px solid {c["glass_border"]};
        border-radius: {BorderRadius.MD};
        padding: 6px 14px;
        color: {c["text_primary"]};
        font-weight: 500;
        font-size: {s["sm"]}px;
    }}

    /* ========== CLOCK ========== */
    QLabel#topbar-clock {{
        min-height: 36px;
        padding: 6px 16px;
        background: {c["primary_lighter"]};
        border-radius: {BorderRadius.MD};
        color: {c["text_primary"]};
        font-size: {s["md"]}px;
        font-weight: 600;
    }}

    /* ========== USER BOX ========== */
    QWidget#topbar-user-box {{
        min-height: 36px;
        background: {c["bg_elevated"]};
        border: 1px solid {c["border_subtle"]};
        border-radius: {BorderRadius.LG};
        padding: 6px 14px;
    }}

    QLabel#topbar-username {{
        font-size: {s["sm"]}px;
        padding: 0 6px;
    }}

    QLabel#topbar-user-pic {{
        min-width: 22px;
        min-height: 22px;
        font-size: {s["lg"]}px;
        text-align: center;
    }}
    """
