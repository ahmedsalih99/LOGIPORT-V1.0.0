"""
Unified Transaction Styles – LOGIPORT Professional
===================================================
✔ No geometry control
✔ Layout-driven sizing
✔ Safe for Dialogs & Tabs
✔ Light + Dark theme aware
"""

from ..border_radius import BorderRadius


def get_styles(theme):
    c = theme.colors
    is_dark = getattr(theme, "name", "").lower() == "dark"

    # قيم مشتقة حسب الثيم
    if is_dark:
        header_bg      = "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1a2035, stop:1 #111827)"
        card_bg        = "#1e2535"
        card_shadow    = "rgba(0,0,0,0.4)"
        tab_active_bg  = "#1e2535"
        tab_idle_bg    = "#161d2d"
        field_focus_bg = "#1a2235"
        badge_export   = "#1e3a2e"
        badge_export_t = "#34d399"
        badge_import   = "#1e2d4a"
        badge_import_t = "#60a5fa"
        badge_transit  = "#2d2418"
        badge_transit_t = "#fbbf24"
        divider        = "rgba(255,255,255,0.06)"
    else:
        header_bg      = "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f8faff, stop:1 #f0f4fc)"
        card_bg        = "#ffffff"
        card_shadow    = "rgba(37,99,235,0.08)"
        tab_active_bg  = "#ffffff"
        tab_idle_bg    = "#f3f6fb"
        field_focus_bg = "#f8faff"
        badge_export   = "#dcfce7"
        badge_export_t = "#16a34a"
        badge_import   = "#dbeafe"
        badge_import_t = "#1d4ed8"
        badge_transit  = "#fef3c7"
        badge_transit_t = "#b45309"
        divider        = "rgba(0,0,0,0.06)"

    return f"""
    /* ============================================================================
       TRANSACTION – UNIFIED STYLES
       ============================================================================ */

    /* --------------------------------------------------------------------------
       Window Root
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
       Top Section — Gradient Header
    -------------------------------------------------------------------------- */
    #top-section {{
        background: {header_bg};
        border-bottom: 1px solid {c["border"]};
    }}

    /* --------------------------------------------------------------------------
       Actions Bar — شريط الأزرار
    -------------------------------------------------------------------------- */

    QPushButton#primary-btn:hover {{
        background: {c["accent_hover"]};
    }}

    QPushButton#primary-btn:pressed {{
        background: {c["accent_active"]};
    }}

    QPushButton#primary-btn:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
    }}


    QPushButton#secondary-btn:hover {{
        border-color: {c["accent"]};
        color: {c["accent"]};
        background: {c["accent_soft"]};
    }}

    QPushButton#secondary-btn:pressed {{
        background: {c["accent_soft"]};
        border-color: {c["accent_active"]};
    }}

    /* --------------------------------------------------------------------------
       Status Bar
    -------------------------------------------------------------------------- */
    #status-bar {{
        background: {c["bg_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.SM};
    }}

    QLabel#status-label {{
        color: {c["text_secondary"]};
        font-size: 12px;
    }}

    QLabel#status-label[message_type="success"] {{ color: {c["success"]}; }}
    QLabel#status-label[message_type="error"]   {{ color: {c["danger"]}; }}
    QLabel#status-label[message_type="info"]    {{ color: {c["text_secondary"]}; }}

    /* --------------------------------------------------------------------------
       General Info Card
    -------------------------------------------------------------------------- */
    #general-info-card {{
        background: {card_bg};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.LG};
    }}

    /* card divider */
    #card-row-divider {{
        background: {divider};
        max-height: 1px;
        min-height: 1px;
    }}

    /* field labels */
    QLabel#field-label {{
        font-size: 10px;
        font-weight: 700;
        color: {c["text_secondary"]};
        letter-spacing: 0.6px;
    }}

    /* --------------------------------------------------------------------------
       Form Fields
    -------------------------------------------------------------------------- */
    #transaction-number-input,
    #transaction-date-input,
    #transaction-type-combo,
    #transaction-notes-input {{
        background: {c["input_bg"]};
        border: 1.5px solid {c["border"]};
        border-radius: {BorderRadius.SM};
        color: {c["text_primary"]};
        font-size: 13px;
        padding: 2px 10px;
        selection-background-color: {c["accent_soft"]};
    }}

    #transaction-number-input:focus,
    #transaction-date-input:focus,
    #transaction-notes-input:focus {{
        border-color: {c["accent"]};
        background: {field_focus_bg};
        border-width: 2px;
    }}

    #transaction-type-combo:focus {{
        border-color: {c["accent"]};
        border-width: 2px;
    }}

    /* --------------------------------------------------------------------------
       Transaction Type — Colored Badges في الـ Combo
    -------------------------------------------------------------------------- */
    QComboBox#transaction-type-combo[current_type="export"] {{
        color: {badge_export_t};
        background: {badge_export};
        border-color: {badge_export_t};
        font-weight: 700;
    }}

    QComboBox#transaction-type-combo[current_type="import"] {{
        color: {badge_import_t};
        background: {badge_import};
        border-color: {badge_import_t};
        font-weight: 700;
    }}

    QComboBox#transaction-type-combo[current_type="transit"] {{
        color: {badge_transit_t};
        background: {badge_transit};
        border-color: {badge_transit_t};
        font-weight: 700;
    }}

    /* --------------------------------------------------------------------------
       Parties Combos
    -------------------------------------------------------------------------- */
    QComboBox#client-combo,
    QComboBox#exporter-combo,
    QComboBox#importer-combo,
    QComboBox#broker-combo {{
        background: {c["input_bg"]};
        border: 1.5px solid {c["border"]};
        border-radius: {BorderRadius.SM};
        color: {c["text_primary"]};
        font-size: 13px;
        padding: 2px 10px;
    }}

    QComboBox#client-combo::drop-down,
    QComboBox#exporter-combo::drop-down,
    QComboBox#importer-combo::drop-down,
    QComboBox#broker-combo::drop-down,
    QComboBox#transaction-type-combo::drop-down {{
        width             : 1px;
        border            : none;
        background        : transparent;
        subcontrol-origin : padding;
        subcontrol-position: right center;
    }}

    QComboBox#client-combo::down-arrow,
    QComboBox#exporter-combo::down-arrow,
    QComboBox#importer-combo::down-arrow,
    QComboBox#broker-combo::down-arrow,
    QComboBox#transaction-type-combo::down-arrow {{
        image: none;
        width: 0;
        height: 0;
        border: none;
    }}

    QComboBox#client-combo:focus,
    QComboBox#exporter-combo:focus,
    QComboBox#importer-combo:focus {{
        border-color: {c["accent"]};
        border-width: 2px;
        background: {field_focus_bg};
    }}

    QComboBox#broker-combo:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
        border-color: {c["border"]};
    }}

    /* --------------------------------------------------------------------------
       Tabs — Content Area
    -------------------------------------------------------------------------- */
    QTabWidget#transaction-tabs::pane {{
        border: 1px solid {c["border"]};
        border-top: none;
        border-bottom-left-radius: {BorderRadius.MD};
        border-bottom-right-radius: {BorderRadius.MD};
        background: {tab_active_bg};
    }}

    QTabWidget#transaction-tabs QTabBar {{
        background: transparent;
    }}

    QTabWidget#transaction-tabs QTabBar::tab {{
        background: {tab_idle_bg};
        color: {c["text_secondary"]};
        border: 1px solid {c["border"]};
        border-bottom: none;
        border-top-left-radius: {BorderRadius.SM};
        border-top-right-radius: {BorderRadius.SM};
        padding: 7px 20px;
        margin-right: 3px;
        font-size: 12px;
        font-weight: 500;
        min-width: 80px;
    }}

    QTabWidget#transaction-tabs QTabBar::tab:selected {{
        background: {tab_active_bg};
        color: {c["accent"]};
        font-weight: 700;
        border-bottom: 2px solid {c["accent"]};
    }}

    QTabWidget#transaction-tabs QTabBar::tab:hover:!selected {{
        background: {c["bg_hover"]};
        color: {c["text_primary"]};
    }}

    /* --------------------------------------------------------------------------
       Items Table
    -------------------------------------------------------------------------- */
    QTableWidget#items-table {{
        background: {c["bg_primary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.SM};
        gridline-color: {c["border_subtle"]};
        alternate-background-color: {c["bg_secondary"]};
    }}

    QTableWidget#items-table QHeaderView::section {{
        background: {tab_idle_bg};
        color: {c["text_secondary"]};
        border: none;
        border-bottom: 1px solid {c["border"]};
        border-right: 1px solid {c["border_subtle"]};
        padding: 6px 10px;
        font-weight: 600;
        font-size: 11px;
        letter-spacing: 0.3px;
    }}

    QTableWidget#items-table QHeaderView::section:first {{
        border-top-left-radius: {BorderRadius.SM};
    }}

    QTableWidget#items-table::item {{
        padding: 4px 8px;
    }}

    QTableWidget#items-table::item:selected {{
        background: {c["accent_soft"]};
        color: {c["text_primary"]};
    }}

    QTableWidget#items-table::item:hover {{
        background: {c["bg_hover"]};
    }}

    /* --------------------------------------------------------------------------
       Splitter Handle
    -------------------------------------------------------------------------- */
    QSplitter#main-splitter::handle {{
        background: {c["border_subtle"]};
        height: 4px;
        margin: 0 8px;
        border-radius: 2px;
    }}

    QSplitter#main-splitter::handle:hover {{
        background: {c["accent"]};
    }}

    QSplitter#content-splitter::handle {{
        background: {c["border_subtle"]};
        width: 4px;
        margin: 8px 0;
        border-radius: 2px;
    }}

    QSplitter#content-splitter::handle:hover {{
        background: {c["accent"]};
    }}

    /* ============================================================================
       Transactions Tab Footer / Totals Bar
       ============================================================================ */

    QWidget#transactions-footer {{
        background: {c["bg_secondary"]};
        border-top: 1px solid {c["border"]};
    }}

    QLabel#footer-stat-title {{
        color: {c["text_secondary"]};
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.4px;
    }}

    QLabel#footer-stat-value {{
        color: {c["text_primary"]};
        font-size: 15px;
        font-weight: 700;
    }}

    QLabel#footer-stat-value-accent {{
        color: {c["accent"]};
        font-size: 15px;
        font-weight: 700;
    }}

    /* ============================================================================
       Documents Side Panel
       ============================================================================ */

    QWidget#documents-side-panel {{
        background: {c["bg_secondary"]};
        border-left: 1px solid {c["border"]};
    }}

    QLabel#docs-panel-title {{
        color: {c["text_primary"]};
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.3px;
    }}

    QLabel#docs-count-badge {{
        background: {c["accent"]};
        color: {c["text_white"]};
        border-radius: 10px;
        font-size: 10px;
        font-weight: 700;
        padding: 0 5px;
    }}

    QLabel#docs-count-badge[count_state="none"] {{
        background: {c["border"]};
        color: {c["text_secondary"]};
    }}

    QLabel#docs-count-badge[count_state="some"] {{
        background: {c.get("warning", "#f59e0b")};
        color: white;
    }}

    QLabel#docs-count-badge[count_state="all"] {{
        background: {c.get("success", "#10b981")};
        color: white;
    }}

    QFrame#docs-separator {{
        background: {c["border"]};
        max-height: 1px;
        min-height: 1px;
    }}

    QCheckBox#doc-checkbox-card {{
        color: {c["text_primary"]};
        font-size: 11px;
        padding: 5px 8px;
        border-radius: {BorderRadius.SM};
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
        color: {c["text_disabled"]};
    }}

    QLabel#doc-group-header {{
        color: {c["text_secondary"]};
        font-size: 10px;
        font-weight: 600;
        padding: 8px 4px 2px 4px;
        letter-spacing: 0.5px;
    }}

    QLabel#docs-hint-label {{
        color: {c["text_secondary"]};
        font-size: 10px;
        padding: 8px;
        border: 1px dashed {c["border"]};
        border-radius: {BorderRadius.SM};
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
       End of Transaction Styles
       ============================================================================ */
    """