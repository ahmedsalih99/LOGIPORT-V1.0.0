"""Table Component Styles - Enhanced Modern Version"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    """Generate modern flat enhanced table styles"""
    c = theme.colors
    s = theme.sizes

    return f"""
    /* =======================================================
       TABLES - MODERN CLEAN ENHANCED
    ======================================================= */

    /* ---------- QTableWidget Base ---------- */

    QTableWidget {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: none;
        border-radius: {BorderRadius.MD};
        gridline-color: transparent;
        font-size: {s["base"]}px;

        alternate-background-color: {c["bg_hover"]};

        selection-background-color: {c["primary_light"]};
        selection-color: {c["primary"]};

        outline: none;
    }}

    QTableWidget:focus {{
        border: none;
        outline: none;
    }}

    /* ---------- Items ---------- */

    QTableWidget::item {{
        padding: {Spacing.SM} {Spacing.MD};
        border: none;
        font-weight: 600;
    }}

    QTableWidget::item:hover {{
        background: {c["bg_active"]};
    }}

    QTableWidget::item:selected {{
        background: {c["primary_light"]};
        color: {c["primary"]};
        border-radius: {BorderRadius.SM};
    }}

    /* ---------- Alternating Rows ---------- */

    QTableView {{
        alternate-background-color: {c["bg_hover"]};
    }}

    /* ---------- Header ---------- */

    QHeaderView {{
        background: {c["bg_hover"]};
        border: none;
    }}

    QHeaderView::section {{
        background: {c["bg_hover"]};
        color: {c["text_primary"]};
        padding: {Spacing.SM} {Spacing.MD};
        border: none;
        font-weight: 700;
        font-size: {s["sm"]}px;
    }}

    QHeaderView::section:hover {{
        background: {c["bg_active"]};
    }}

    QHeaderView::section:pressed {{
        background: {c["primary_light"]};
    }}

    /* ---------- Corner (top-left empty cell) ---------- */

    QTableCornerButton::section {{
        background: {c["bg_hover"]};
        border: none;
    }}

    /* ---------- Scrollbars ---------- */

    QTableWidget QScrollBar:vertical {{
        background: transparent;
        border: none;
        width: 10px;
        margin: 4px 0;
    }}

    QTableWidget QScrollBar::handle:vertical {{
        background: {c["bg_hover"]};
        border-radius: 6px;
        min-height: 30px;
    }}

    QTableWidget QScrollBar::handle:vertical:hover {{
        background: {c["bg_active"]};
    }}

    QTableWidget QScrollBar::add-line:vertical,
    QTableWidget QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QTableWidget QScrollBar:horizontal {{
        background: transparent;
        border: none;
        height: 10px;
        margin: 0 4px;
    }}

    QTableWidget QScrollBar::handle:horizontal {{
        background: {c["bg_hover"]};
        border-radius: 6px;
        min-width: 30px;
    }}

    QTableWidget QScrollBar::handle:horizontal:hover {{
        background: {c["bg_active"]};
    }}

    QTableWidget QScrollBar::add-line:horizontal,
    QTableWidget QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ── Base Tab: Status Bar ──────────────────────────────────────────── */

    QWidget#base-tab-status-bar {{
        background: {c["bg_secondary"]};
        border-top: 1px solid {c["border_subtle"]};
        min-height: 28px;
        max-height: 28px;
    }}

    QLabel#base-tab-count-label {{
        color: {c["text_secondary"]};
        font-size: 11px;
        font-weight: 500;
    }}

    QLabel#base-tab-sort-label {{
        color: {c["text_secondary"]};
        font-size: 11px;
    }}

    /* ── Base Tab: Empty State ─────────────────────────────────────────── */

    QWidget#empty-state-widget {{
        background: transparent;
    }}

    QLabel#empty-state-icon {{
        color: {c["text_secondary"]};
        margin-bottom: 8px;
    }}

    QLabel#empty-state-text {{
        color: {c["text_secondary"]};
        font-size: 14px;
        font-weight: 500;
    }}

    /* ── Sort Combo ────────────────────────────────────────────────────── */

    QComboBox#sort-combo {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        min-height: 30px;
    }}

    QComboBox#sort-combo:hover {{
        border-color: {c["primary"]};
    }}

    QComboBox#sort-combo::drop-down {{
        border: none;
        width: 20px;
    }}
    """