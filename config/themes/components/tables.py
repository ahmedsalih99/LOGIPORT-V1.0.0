"""Table Component Styles - Professional Clean"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    c = theme.colors
    s = theme.sizes

    return f"""
    /* =======================================================
       TABLES - PROFESSIONAL CLEAN
    ======================================================= */

    QTableWidget {{
        background               : {c["bg_card"]};
        color                    : {c["text_primary"]};
        border                   : 1px solid {c["border_subtle"]};
        border-radius            : {BorderRadius.MD};
        gridline-color           : {c["border_subtle"]};
        font-size                : {s["base"]}px;
        alternate-background-color: {c["bg_hover"]};
        selection-background-color: {c["primary_light"]};
        selection-color          : {c["primary"]};
        outline                  : none;
    }}

    QTableWidget:focus {{
        border : 1px solid {c["border_hover"]};
        outline: none;
    }}

    /* ── Items ── */

    QTableWidget::item {{
        padding    : {Spacing.SM} {Spacing.MD};
        border     : none;
        font-weight: 700;
        font-size  : {s["base"]}px;
    }}

    QTableWidget::item:hover {{
        background: {c["bg_hover"]};
    }}

    QTableWidget::item:selected {{
        background   : {c["primary_light"]};
        color        : {c["primary"]};
        border-radius: {BorderRadius.SM};
    }}

    /* ── Alternating Rows ── */

    QTableView {{
        alternate-background-color: {c["bg_hover"]};
    }}

    /* ── Header — أخف وأنظف ── */

    QHeaderView {{
        background: transparent;
        border    : none;
    }}

    QHeaderView::section {{
        background   : {c["bg_card"]};
        color        : {c["text_secondary"]};
        padding      : {Spacing.SM} {Spacing.MD};
        border       : none;
        border-bottom: 2px solid {c["border"]};
        font-weight  : 700;
        font-size    : {s["sm"]}px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }}

    QHeaderView::section:hover {{
        background: {c["bg_hover"]};
        color     : {c["primary"]};
    }}

    QHeaderView::section:pressed {{
        background: {c["primary_light"]};
        color     : {c["primary"]};
    }}

    QHeaderView::section:first {{
        border-top-right-radius: {BorderRadius.MD};
    }}

    QHeaderView::section:last {{
        border-top-left-radius: {BorderRadius.MD};
    }}

    /* ── Corner Button ── */

    QTableCornerButton::section {{
        background   : {c["bg_card"]};
        border-bottom: 2px solid {c["border"]};
        border       : none;
    }}

    /* ── Scrollbars ── */

    QTableWidget QScrollBar:vertical {{
        background   : transparent;
        border       : none;
        width        : 8px;
        margin       : 4px 0;
    }}

    QTableWidget QScrollBar::handle:vertical {{
        background   : {c["border"]};
        border-radius: 4px;
        min-height   : 30px;
    }}

    QTableWidget QScrollBar::handle:vertical:hover {{
        background: {c["primary"]};
    }}

    QTableWidget QScrollBar::add-line:vertical,
    QTableWidget QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QTableWidget QScrollBar:horizontal {{
        background   : transparent;
        border       : none;
        height       : 8px;
        margin       : 0 4px;
    }}

    QTableWidget QScrollBar::handle:horizontal {{
        background   : {c["border"]};
        border-radius: 4px;
        min-width    : 30px;
    }}

    QTableWidget QScrollBar::handle:horizontal:hover {{
        background: {c["primary"]};
    }}

    QTableWidget QScrollBar::add-line:horizontal,
    QTableWidget QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ── Status Bar ── */

    QWidget#base-tab-status-bar {{
        background : {c["bg_card"]};
        border-top : 1px solid {c["border_subtle"]};
        min-height : 28px;
        max-height : 28px;
    }}

    QLabel#base-tab-count-label,
    QLabel#base-tab-sort-label {{
        color    : {c["text_secondary"]};
        font-size: 11px;
    }}

    QLabel#base-tab-count-label {{
        font-weight: 600;
    }}

    /* ── Empty State ── */

    QWidget#empty-state-widget {{
        background: transparent;
    }}

    QLabel#empty-state-icon {{
        color      : {c["text_secondary"]};
        margin-bottom: 8px;
    }}

    QLabel#empty-state-text {{
        color      : {c["text_secondary"]};
        font-size  : 14px;
        font-weight: 500;
    }}

    /* ── Sort Combo ── */

    QComboBox#sort-combo {{
        background   : {c["bg_card"]};
        color        : {c["text_primary"]};
        border       : 1px solid {c["border"]};
        border-radius: 6px;
        padding      : 4px 10px;
        font-size    : 12px;
        min-height   : 30px;
    }}

    QComboBox#sort-combo:hover {{
        border-color: {c["primary"]};
    }}

    QComboBox#sort-combo::drop-down {{
        border: none;
        width : 20px;
    }}

    /* ── Aliases for named tables (documents-table, custom-table) ── */

    QTableWidget#documents-table,
    QTableWidget#custom-table {{
        background               : {c["bg_card"]};
        color                    : {c["text_primary"]};
        border                   : 1px solid {c["border_subtle"]};
        border-radius            : {BorderRadius.MD};
        gridline-color           : {c["border_subtle"]};
        font-size                : {s["base"]}px;
        alternate-background-color: {c["bg_hover"]};
        selection-background-color: {c["primary_light"]};
        selection-color          : {c["primary"]};
        outline                  : none;
    }}

    QTableWidget#documents-table::item,
    QTableWidget#custom-table::item {{
        padding    : {Spacing.SM} {Spacing.MD};
        border     : none;
        font-weight: 700;
        font-size  : {s["base"]}px;
    }}

    QTableWidget#documents-table::item:selected,
    QTableWidget#custom-table::item:selected {{
        background   : {c["primary_light"]};
        color        : {c["primary"]};
        border-radius: {BorderRadius.SM};
    }}

    QTableWidget#documents-table QHeaderView::section,
    QTableWidget#custom-table QHeaderView::section {{
        background   : {c["bg_card"]};
        color        : {c["text_secondary"]};
        padding      : {Spacing.SM} {Spacing.MD};
        border       : none;
        border-bottom: 2px solid {c["border"]};
        font-weight  : 700;
        font-size    : {s["sm"]}px;
    }}
    """