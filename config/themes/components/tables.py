"""Table Component Styles - Professional Clean v2"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    c = theme.colors
    s = theme.sizes

    return f"""
    /* =======================================================
       TABLES - PROFESSIONAL CLEAN v2
    ======================================================= */

    QTableWidget {{
        background               : {c["bg_card"]};
        color                    : {c["text_primary"]};
        border                   : 1px solid {c["border_subtle"]};
        border-radius            : {BorderRadius.MD};
        gridline-color           : {c["border_subtle"]};
        font-size                : {s["base"]}px;
        alternate-background-color: {c["bg_disabled"]};
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
        padding    : 5px {Spacing.MD};
        border     : none;
        font-weight: 500;
        font-size  : {s["base"]}px;
        color      : {c["text_primary"]};
    }}

    QTableWidget::item:hover {{
        background: {c["bg_hover"]};
    }}

    QTableWidget::item:selected {{
        background   : {c["primary_light"]};
        color        : {c["primary"]};
    }}

    QTableWidget::item:alternate {{
        background: {c["bg_disabled"]};
    }}

    /* ── Header - clear and readable ── */

    QHeaderView {{
        background: transparent;
        border    : none;
    }}

    /* Sort indicator arrows */
    QHeaderView::down-arrow {{
        width : 10px;
        height: 10px;
    }}
    QHeaderView::up-arrow {{
        width : 10px;
        height: 10px;
    }}



    /* ── Corner Button ── */

    QTableCornerButton::section {{
        background   : {c["bg_disabled"]};
        border-bottom: 2px solid {c["border"]};
        border       : none;
    }}

    /* ── Scrollbars ── */

    QTableWidget QScrollBar:vertical {{
        background   : transparent;
        border       : none;
        width        : 6px;
        margin       : 2px 0;
    }}

    QTableWidget QScrollBar::handle:vertical {{
        background   : {c["border"]};
        border-radius: 3px;
        min-height   : 24px;
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
        height       : 6px;
        margin       : 0 2px;
    }}

    QTableWidget QScrollBar::handle:horizontal {{
        background   : {c["border"]};
        border-radius: 3px;
        min-width    : 24px;
    }}

    QTableWidget QScrollBar::handle:horizontal:hover {{
        background: {c["primary"]};
    }}

    QTableWidget QScrollBar::add-line:horizontal,
    QTableWidget QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ── Selection Action Bar ── */

    QFrame#selection-action-bar {{
        background   : {c["primary"]};
        border       : none;
        border-radius: 8px;
        min-height   : 38px;
        max-height   : 38px;
        margin       : 0 2px;
    }}

    /* Force white on all children — higher specificity */
    QFrame#selection-action-bar QLabel {{
        color      : #FFFFFF;
        background : transparent;
        font-size  : {s["base"]}px;
        font-weight: 600;
    }}

    QFrame#selection-action-bar QLabel#sel-count-label {{
        color      : #FFFFFF;
        background : transparent;
        font-size  : {s["base"]}px;
        font-weight: 600;
    }}

    /* Override global QPushButton inside sel bar */
    QFrame#selection-action-bar QPushButton,
    QFrame#selection-action-bar QPushButton:!hover,
    QFrame#selection-action-bar QPushButton:!pressed {{
        background   : rgba(255,255,255,0.15);
        color        : #FFFFFF;
        border       : 1px solid rgba(255,255,255,0.35);
        border-radius: 6px;
        padding      : 3px 12px;
        font-size    : {s["sm"]}px;
        font-weight  : 600;
    }}

    QFrame#selection-action-bar QPushButton:hover {{
        background  : rgba(255,255,255,0.28);
        border-color: rgba(255,255,255,0.55);
        color       : #FFFFFF;
    }}

    QFrame#selection-action-bar QPushButton:pressed {{
        background: rgba(255,255,255,0.38);
        color     : #FFFFFF;
    }}

    QFrame#selection-action-bar QPushButton#danger-btn,
    QFrame#selection-action-bar QPushButton#danger-btn:!hover {{
        background  : rgba(220,38,38,0.75);
        border-color: rgba(220,38,38,0.9);
        color       : #FFFFFF;
    }}

    QFrame#selection-action-bar QPushButton#danger-btn:hover {{
        background: rgba(220,38,38,0.95);
        color     : #FFFFFF;
    }}

    /* ── Status Bar ── */

    QLabel#status-count-lbl,
    QLabel#status-sort-lbl {{
        color    : {c["text_muted"]};
        font-size: {s["xs"]}px;
        font-weight: 500;
    }}

    QLabel#status-count-lbl {{
        font-weight: 600;
        color: {c["text_secondary"]};
    }}

    QLabel#status-sort-lbl {{
        color: {c["primary"]};
    }}

    /* ── Empty State ── */

    QWidget#empty-state {{
        background: transparent;
    }}

    QLabel#empty-state-text {{
        color      : {c["text_muted"]};
        font-size  : {s["lg"]}px;
        font-weight: 500;
    }}

    /* ── Aliases (documents-table, custom-table) ── */

    QTableWidget#documents-table,
    QTableWidget#custom-table {{
        background               : {c["bg_card"]};
        color                    : {c["text_primary"]};
        border                   : 1px solid {c["border_subtle"]};
        border-radius            : {BorderRadius.MD};
        gridline-color           : {c["border_subtle"]};
        font-size                : {s["base"]}px;
        alternate-background-color: {c["bg_disabled"]};
        selection-background-color: {c["primary_light"]};
        selection-color          : {c["primary"]};
        outline                  : none;
    }}

    QTableWidget#documents-table::item,
    QTableWidget#custom-table::item {{
        padding    : 5px {Spacing.MD};
        border     : none;
        font-weight: 500;
        font-size  : {s["base"]}px;
    }}

    /* ── Horizontal Header — Navy + Gold هوية LOGIPORT ─────────────── */

    QHeaderView::section:horizontal {{
        background   : #0D1B2A;
        color        : #C9A84C;
        padding      : 8px {Spacing.MD};
        border       : none;
        border-bottom: 2px solid #C9A84C;
        border-right : 1px solid rgba(201,168,76,0.15);
        font-weight  : 700;
        font-size    : {s["sm"]}px;
        letter-spacing: 0.4px;
        border-radius: 0;
    }}

    QHeaderView::section:horizontal:hover {{
        background: #1B2F4A;
        color     : #E8C96A;
    }}

    QHeaderView::section:horizontal:pressed {{
        background: #1B2F4A;
    }}

    QHeaderView::section:horizontal:last {{
        border-right: none;
    }}

    /* ── Vertical Header (ترقيم الصفوف) — فاتح ومتناسق مع الجدول ─── */

    QHeaderView::section:vertical {{
        background   : {c["bg_card"]};
        color        : {c["text_muted"]};
        border       : none;
        border-bottom: 1px solid {c["border_subtle"]};
        border-left  : 2px solid #C9A84C;
        font-weight  : 600;
        font-size    : {s["xs"]}px;
        padding      : 0 6px;
        min-width    : 28px;
        max-width    : 36px;
    }}

    QHeaderView::section:vertical:alternate {{
        background: {c["bg_disabled"]};
    }}

    /* ── Corner button (تقاطع الـ headers) ──────────────────────────── */

    QTableCornerButton::section {{
        background   : #0D1B2A;
        border-bottom: 2px solid #C9A84C;
        border-left  : 2px solid #C9A84C;
        border-top   : none;
        border-right : none;
    }}

    /* ── Row selection — خط جانبي Gold عند التحديد ──────────────────── */

    QTableWidget::item:selected {{
        background  : rgba(201,168,76,0.12);
        color       : {c["text_primary"]};
        border-left : 3px solid #C9A84C;
    }}

    QTableWidget::item:hover:!selected {{
        background: {c["bg_hover"]};
    }}

    /* ── Toolbar Frame ───────────────────────────────────────────────── */

    QFrame#tab-toolbar {{
        background   : {c["bg_card"]};
        border       : none;
        border-bottom: 1px solid {c["border_subtle"]};
        border-radius: 0;
    }}

    /* ── Search Wrap ─────────────────────────────────────────────────── */

    QFrame#search-wrap {{
        background   : {c["bg_main"]};
        border       : 1.5px solid {c["border"]};
        border-radius: {BorderRadius.LG};
    }}

    QFrame#search-wrap:focus-within {{
        border-color: {c["primary"]};
        background  : {c["bg_card"]};
    }}

    QFrame#search-wrap QLineEdit#search-field {{
        background   : transparent;
        border       : none;
        border-radius: 0;
        padding      : 0;
        font-size    : {s["base"]}px;
    }}

    QLabel#search-icon-lbl {{
        color     : {c["text_muted"]};
        background: transparent;
        font-size : 13px;
    }}

    /* ── Pagination Frame ────────────────────────────────────────────── */

    QFrame#pagination-bar-frame {{
        background   : {c["bg_card"]};
        border       : none;
        border-top   : 1px solid {c["border_subtle"]};
        border-radius: 0;
        max-height   : 42px;
    }}

    QPushButton#pagination-btn {{
        background   : {c["bg_main"]};
        color        : {c["text_secondary"]};
        border       : 1px solid {c["border"]};
        border-radius: {BorderRadius.SM};
        font-weight  : 700;
        font-size    : {s["sm"]}px;
        padding      : 0;
    }}

    QPushButton#pagination-btn:hover {{
        background  : {c["primary_light"]};
        color       : {c["primary"]};
        border-color: {c["primary"]};
    }}

    QPushButton#pagination-btn:pressed {{
        background: {c["primary"]};
        color     : white;
    }}

    QPushButton#pagination-btn:disabled {{
        background  : {c["bg_disabled"]};
        color       : {c["text_disabled"]};
        border-color: {c["border_subtle"]};
    }}

    QLabel#pagination-lbl {{
        color      : {c["text_primary"]};
        font-weight: 600;
        font-size  : {s["sm"]}px;
        background : transparent;
        padding    : 0 8px;
    }}

    QLabel#rows-per-page-lbl {{
        color      : {c["text_muted"]};
        font-size  : {s["sm"]}px;
        background : transparent;
    }}
    """