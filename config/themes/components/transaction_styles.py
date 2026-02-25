"""
Unified Transaction Styles – Visual Only
========================================
✔ No geometry control
✔ Layout-driven sizing
✔ Safe for Dialogs & Tabs
"""

from ..border_radius import BorderRadius


def get_styles(theme):
    c = theme.colors

    return f"""
    /* ============================================================================
       TRANSACTION – UNIFIED STYLES (VISUAL ONLY)
       ============================================================================ */

    /* --------------------------------------------------------------------------
       Window / Page Root
    -------------------------------------------------------------------------- */
    #AddTransactionWindow,
    #TransactionPage {{
        background: {c["bg_primary"]};
        color: {c["text_primary"]};
    }}

    #transaction-dialog-root,
    #transaction-page-root {{
        background: transparent;
    }}

    /* --------------------------------------------------------------------------
       Top / Header Area
    -------------------------------------------------------------------------- */
    #top-section,
    #transaction-page-header {{
        background: transparent;
        border-bottom: 1px solid {c["border"]};
    }}

    QLabel#transaction-page-title {{
        font-weight: 700;
        color: {c["text_primary"]};
    }}

    QLabel#transaction-page-subtitle {{
        color: {c["text_secondary"]};
    }}

    /* --------------------------------------------------------------------------
       Status Bar
    -------------------------------------------------------------------------- */
    #status-bar {{
        background: {c["bg_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
    }}

    QLabel#status-label {{
        color: {c["text_secondary"]};
    }}

    QLabel#status-label[message_type="success"] {{
        color: {c["success"]};
    }}

    QLabel#status-label[message_type="error"] {{
        color: {c["danger"]};
    }}

    QLabel#status-label[message_type="info"] {{
        color: {c["text_secondary"]};
    }}

    /* --------------------------------------------------------------------------
       General Info Card
    -------------------------------------------------------------------------- */
    #general-info-card {{
        background: {c["bg_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
    }}

    /* --------------------------------------------------------------------------
       Form Fields
    -------------------------------------------------------------------------- */
    #transaction-number-input,
    #transaction-date-input,
    #transaction-type-combo,
    #transaction-notes-input {{
        background: {c["input_bg"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        color: {c["text_primary"]};
    }}

    #transaction-number-input:focus,
    #transaction-date-input:focus,
    #transaction-type-combo:focus,
    #transaction-notes-input:focus {{
        border-color: {c["accent"]};
        background: {c["input_bg"]};
    }}

    /* --------------------------------------------------------------------------
       Parties Combos
    -------------------------------------------------------------------------- */
    QComboBox#client-combo,
    QComboBox#exporter-combo,
    QComboBox#importer-combo,
    QComboBox#broker-combo {{
        background: {c["input_bg"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        color: {c["text_primary"]};
    }}

    QComboBox#broker-combo:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
    }}

    /* --------------------------------------------------------------------------
       Tabs
    -------------------------------------------------------------------------- */
    QTabWidget#transaction-tabs::pane {{
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        background: {c["bg_secondary"]};
    }}

    QTabWidget#transaction-tabs QTabBar::tab {{
        background: transparent;
        color: {c["text_secondary"]};
        border: none;
    }}

    QTabWidget#transaction-tabs QTabBar::tab:selected {{
        color: {c["accent"]};
        font-weight: 600;
        border-bottom: 2px solid {c["accent"]};
    }}

    /* --------------------------------------------------------------------------
       Items Table
    -------------------------------------------------------------------------- */
    QTableWidget#items-table {{
        background: {c["bg_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        gridline-color: {c["border_subtle"]};
    }}

    QTableWidget#items-table::item:selected {{
        background: {c["accent_soft"]};
        color: {c["text_primary"]};
    }}

    /* --------------------------------------------------------------------------
       Action Buttons
    -------------------------------------------------------------------------- */
    QPushButton#primary-btn {{
        background: {c["accent"]};
        color: {c["text_white"]};
        border-radius: {BorderRadius.MD};
        font-weight: 600;
        border: none;
    }}

    QPushButton#primary-btn:hover {{
        background: {c["accent_hover"]};
    }}

    QPushButton#secondary-btn {{
        background: transparent;
        border: 1px solid {c["border"]};
        color: {c["text_primary"]};
        border-radius: {BorderRadius.MD};
    }}

    QPushButton#secondary-btn:hover {{
        background: {c["bg_hover"]};
    }}

    /* --------------------------------------------------------------------------
       RTL Support
    -------------------------------------------------------------------------- */
    [direction="rtl"] QLabel {{
        text-align: right;
    }}

    /* ============================================================================
       Transactions Footer / Totals Bar
       ============================================================================ */

    QWidget#transactions-footer {{
        background: {c["bg_secondary"]};
        border-top: 1px solid {c["border"]};
    }}

    QLabel#footer-stat-title {{
        color: {c["text_secondary"]};
        font-size: 10px;
        font-weight: 500;
    }}

    QLabel#footer-stat-value {{
        color: {c["text_primary"]};
        font-size: 14px;
        font-weight: 700;
    }}

    QLabel#footer-stat-value-accent {{
        color: {c["accent"]};
        font-size: 14px;
        font-weight: 700;
    }}

    /* ============================================================================
       Documents Side Panel
       ============================================================================ */

    QWidget#documents-side-panel {{
        background: {c["bg_secondary"]};
        border-left: 1px solid {c["border"]};
        border-radius: 0;
    }}

    QLabel#docs-panel-title {{
        color: {c["text_primary"]};
        font-size: 12px;
        font-weight: 700;
    }}

    QLabel#docs-count-badge {{
        background: {c["accent"]};
        color: {c["text_white"]};
        border-radius: 10px;
        font-size: 10px;
        font-weight: 700;
        padding: 0 4px;
    }}

    QLabel#docs-count-badge[count_state="none"] {{
        background: {c["border"]};
        color: {c["text_secondary"]};
    }}

    QLabel#docs-count-badge[count_state="some"] {{
        background: {c["warning"] if "warning" in c else "#f59e0b"};
        color: white;
    }}

    QLabel#docs-count-badge[count_state="all"] {{
        background: {c["success"] if "success" in c else "#10b981"};
        color: white;
    }}

    QFrame#docs-separator {{
        background: {c["border"]};
        max-height: 1px;
    }}

    QCheckBox#doc-checkbox-card {{
        color: {c["text_primary"]};
        font-size: 11px;
        padding: 4px 6px;
        border-radius: 4px;
        spacing: 8px;
    }}

    QCheckBox#doc-checkbox-card:hover {{
        background: {c["bg_hover"]};
    }}

    QCheckBox#doc-checkbox-card:checked {{
        color: {c["accent"]};
        font-weight: 600;
    }}

    QCheckBox#doc-checkbox-card:disabled {{
        color: {c["text_secondary"]};
        opacity: 0.5;
    }}

    QLabel#doc-group-header {{
        color: {c["text_secondary"]};
        font-size: 10px;
        padding: 6px 4px 2px 4px;
        text-transform: uppercase;
    }}

    QLabel#docs-hint-label {{
        color: {c["text_secondary"]};
        font-size: 10px;
        padding: 6px;
        border: 1px dashed {c["border"]};
        border-radius: 4px;
        background: transparent;
    }}

    QScrollArea#docs-scroll-area {{
        background: transparent;
        border: none;
    }}

    QWidget#docs-scroll-content {{
        background: transparent;
    }}

    /* ============================================================================
       End of Unified Transaction Styles
       ============================================================================ */
    """