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

    /* ===== DASHBOARD HEADER ===== */

    QWidget#dashboard-header-bar {{
        background: transparent;
    }}

    QLabel#panel-title {{
        color: {c["text_primary"]};
        font-weight: 700;
        background: transparent;
    }}

    /* ===== ACTIVITIES ===== */

    QWidget#activities-container {{
        background: transparent;
    }}

    QFrame#activity-item {{
        background: {c["bg_hover"]};
        border-radius: 10px;
        border: none;
    }}

    QFrame#activity-item:hover {{
        background: {c["bg_active"]};
    }}

    QLabel#activity-msg {{
        color: {c["text_primary"]};
        background: transparent;
    }}

    QLabel#activity-ts {{
        color: {c["text_muted"]};
        background: transparent;
    }}

    /* ===== TRANSACTIONS TABLE ===== */

    QTableWidget#data-table {{
        background: {c["bg_card"]};
        border: none;
        gridline-color: transparent;
        alternate-background-color: {c["bg_hover"]};
        selection-background-color: {c["primary_light"]};
        selection-color: {c["primary"]};
        outline: none;
        font-size: 12px;
    }}

    QTableWidget#data-table::item {{
        padding: 6px 10px;
        border: none;
    }}

    QTableWidget#data-table QHeaderView::section {{
        background: {c["bg_hover"]};
        color: {c["text_secondary"]};
        font-weight: 700;
        font-size: 11px;
        padding: 8px 10px;
        border: none;
    }}

    """
