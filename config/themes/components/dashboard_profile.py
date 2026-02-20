"""
Dashboard, Profile, and Notification Styles - LOGIPORT v3.1
=============================================================

Styles for:
- DashboardTab (stat cards, panels, header)
- UserProfileTab (hero, info rows, stat mini)
- NotificationPopup / bell
"""

from ..border_radius import BorderRadius


def get_styles(theme):
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ===== DASHBOARD ===== */

    QWidget#dashboard-container {{
        background: {c["bg_main"]};
    }}

    QLabel#dashboard-title {{
        color: {c["text_primary"]};
        background: transparent;
    }}

    QLabel#text-muted {{
        color: {c["text_muted"]};
        background: transparent;
    }}

    /* ===== PROFILE ===== */

    QWidget#user-profile-tab {{
        background: {c["bg_main"]};
    }}

    QWidget#profile-container {{
        background: {c["bg_main"]};
    }}

    QLabel#section-title-lbl {{
        color: {c["text_primary"]};
        background: transparent;
    }}

    QFrame#separator {{
        background: {c["border_subtle"]};
        max-height: 1px;
        border: none;
    }}

    QLabel#info-label {{
        color: {c["text_secondary"]};
        background: transparent;
    }}

    QLabel#info-value {{
        color: {c["text_primary"]};
        background: transparent;
    }}

    /* ===== NOTIFICATION POPUP ===== */

    QFrame#notif-popup {{
        background: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.XL};
    }}

    QFrame#notif-header {{
        background: transparent;
        border-bottom: 1px solid {c["border_subtle"]};
    }}

    /* ===== WARNING & DANGER BUTTONS ===== */

    QPushButton#btn-warning {{
        background: {c["warning"]};
        color: white;
        border: none;
        border-radius: {BorderRadius.MD};
        padding: 8px 20px;
        font-weight: bold;
    }}
    QPushButton#btn-warning:hover {{
        background: {c["warning_hover"]};
    }}
    QPushButton#btn-warning:pressed {{
        background: {c["warning_active"]};
    }}

    QPushButton#btn-danger {{
        background: {c["danger"]};
        color: white;
        border: none;
        border-radius: {BorderRadius.MD};
        padding: 8px 20px;
        font-weight: bold;
    }}
    QPushButton#btn-danger:hover {{
        background: {c["danger_hover"]};
    }}
    QPushButton#btn-danger:pressed {{
        background: {c["danger_active"]};
    }}
    """
