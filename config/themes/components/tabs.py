"""Tab Widget Component Styles"""

from ..spacing import Spacing
from ..border_radius import BorderRadius

def get_styles(theme):
    """Generate tab widget styles"""
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ========== TABS ========== */
    
    /* QTabWidget */
    QTabWidget::pane {{
        background: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        top: -1px;
    }}
    
    QTabBar::tab {{
        background: {c["bg_hover"]};
        color: {c["text_secondary"]};
        border: 1px solid {c["border"]};
        border-bottom: none;
        border-top-left-radius: {BorderRadius.MD};
        border-top-right-radius: {BorderRadius.MD};
        padding: {Spacing.SM} {Spacing.LG};
        margin-right: 2px;
        font-size: {s["base"]}px;
    }}
    
    QTabBar::tab:hover {{
        background: {c["bg_active"]};
        color: {c["text_primary"]};
    }}
    
    QTabBar::tab:selected {{
        background: {c["bg_card"]};
        color: {c["primary"]};
        font-weight: 600;
        border-bottom: 2px solid {c["primary"]};
    }}
    
    QTabBar::tab:!selected {{
        margin-top: 2px;
    }}
    """