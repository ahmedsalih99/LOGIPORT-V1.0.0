"""TopBar Component Styles"""
from ..border_radius import BorderRadius


def get_styles(theme):
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ── CONTAINER ── */
    QWidget#TopBar {{
        background   : {c["bg_topbar"]};
        border-bottom: 1px solid {c["border_subtle"]};
    }}

    /* ── TOOL BUTTONS ── */
    QPushButton#topbar-tool-btn {{
        min-width    : 32px; max-width: 32px;
        min-height   : 32px; max-height: 32px;
        background   : transparent;
        border       : none;
        border-radius: 8px;
        padding      : 0;
    }}
    QPushButton#topbar-tool-btn:hover  {{ background: {c["bg_hover"]};    }}
    QPushButton#topbar-tool-btn:pressed{{ background: {c["primary_light"]}; }}

    /* ── LANGUAGE ── */
    QPushButton#topbar-lang-btn {{
        min-height  : 26px; max-height: 26px;
        min-width   : 30px;
        padding     : 0 8px;
        background  : transparent;
        border      : none;
        border-radius: 6px;
        color       : {c["topbar_text"]};
        font-size   : {s["sm"]}px;
        font-weight : 700;
    }}
    QPushButton#topbar-lang-btn:hover {{ background: {c["bg_hover"]}; color: {c["primary"]}; }}

    /* ── SEARCH BAR ── */
    QPushButton#topbar-search-bar {{
        min-height   : 34px; max-height: 34px;
        padding      : 0 14px;
        background   : {c["bg_hover"]};
        border       : 1px solid {c["border"]};
        border-radius: {BorderRadius.LG};
        color        : {c["text_muted"]};
        font-size    : {s["sm"]}px;
        text-align   : right;
    }}
    QPushButton#topbar-search-bar:hover {{
        background  : {c["bg_active"]};
        border-color: {c["primary"]};
    }}

    /* ── CLOCK ── */
    QLabel#topbar-clock {{
        background : transparent;
        border     : none;
        color      : {c["text_secondary"]};
        font-size  : {s["base"]}px;
        font-weight: 600;
        padding    : 0 6px;
        min-width  : 44px;
    }}

    /* ── SEPARATOR ── */
    QFrame#topbar-sep {{
        background : {c["border_subtle"]};
        border     : none;
        max-width  : 1px; min-width: 1px;
        min-height : 18px; max-height: 18px;
        margin     : 0 3px;
    }}

    /* ── USER CHIP (QFrame) ── */
    QFrame#topbar-user-chip {{
        background   : transparent;
        border       : none;
        border-radius: {BorderRadius.XL};
    }}
    QFrame#topbar-user-chip:hover {{
        background: {c["bg_hover"]};
    }}

    /* username inside chip */
    QLabel#topbar-username-lbl {{
        background : transparent;
        color      : {c["topbar_text"]};
        font-size  : {s["sm"]}px;
        font-weight: 600;
    }}

    /* ── backward compat ── */
    QPushButton#topbar-btn      {{ background: transparent; border: none; color: {c["topbar_text"]}; padding: 0 8px; min-height: 32px; }}
    QPushButton#topbar-btn-icon {{ background: transparent; border: none; min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px; }}
    QPushButton#topbar-user-widget {{ background: transparent; border: none; border-radius: {BorderRadius.XL}; min-height: 36px; }}
    QPushButton#topbar-user-widget:hover {{ background: {c["bg_hover"]}; }}
    """


def office_badge_style(c: dict, s: dict) -> str:
    """CSS badge المكتب في TopBar."""
    return f"""
    #topbar-office-badge {{
        background-color: {c["primary"]}18;
        border: 1px solid {c["primary"]}40;
        border-radius: 12px;
        padding: 0 6px;
    }}
    #topbar-office-lbl {{
        color: {c["primary"]};
        font-size: {s["sm"]}px;
        font-weight: 600;
    }}
    """