"""
Form Components - Clean & Auto Size
==================================
No fixed width / height.
Layouts control sizing 100%.
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    """Generate form input styles - auto size safe"""
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ========== FORMS - AUTO SIZE ========== */

    /* QLineEdit */
    QLineEdit {{
        background: {c["bg_card"]};
    color: {c["text_primary"]};
    border: none;
    border-radius: {BorderRadius.MD};
    padding: {Spacing.SM} {Spacing.MD};
    font-size: {s["base"]}px;
    }}

    QLineEdit:hover {{
        background: {c["bg_hover"]};
    }}

    QLineEdit:focus {{
        background: {c["bg_card"]};
    }}

    QLineEdit:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
    }}

    QLineEdit[readOnly="true"] {{
        background: {c["bg_hover"]};
        color: {c["text_secondary"]};
    }}

    /* Search Field */
    QLineEdit#search-field {{
        padding-left: {Spacing.XL};
        border-radius: {BorderRadius.LG};
    }}

    /* ========== QComboBox ========== */

    QComboBox {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        padding: {Spacing.SM} {Spacing.MD};
        font-size: {s["base"]}px;
    }}

    QComboBox:hover {{
        border-color: {c["border_hover"]};
        background: {c["bg_hover"]};
    }}

    QComboBox:focus {{
        border-color: {c["border_focus"]};
        background: {c["bg_card"]};
    }}

    QComboBox:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
        border-color: {c["border"]};
    }}

    QComboBox::drop-down {{
        background: transparent;
        subcontrol-origin: padding;
        subcontrol-position: left center;
    }}

    QComboBox::down-arrow {{
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {c["text_secondary"]};
        margin-left: 4px;
    }}

    QComboBox::down-arrow:hover {{
        border-top-color: {c["primary"]};
    }}

    /* Dropdown List */
    QComboBox QAbstractItemView {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.SM};
        selection-background-color: {c["primary_light"]};
        selection-color: {c["primary"]};
        padding: {Spacing.XS};
    }}

    QComboBox QAbstractItemView::item {{
        padding: {Spacing.XS} {Spacing.SM};
        border-radius: {BorderRadius.SM};
    }}

    QComboBox QAbstractItemView::item:hover {{
        background: {c["bg_hover"]};
    }}

    QComboBox QAbstractItemView::item:selected {{
        background: {c["primary_light"]};
        color: {c["primary"]};
    }}

    /* ComboBox in Tables */
    QTableWidget QComboBox,
    QTableView QComboBox {{
        padding: 2px 4px;
        font-size: {s["sm"]}px;
        border-radius: {BorderRadius.SM};
    }}

    QTableWidget QComboBox::down-arrow,
    QTableView QComboBox::down-arrow {{
        border-left: 3px solid transparent;
        border-right: 3px solid transparent;
        border-top: 4px solid {c["text_secondary"]};
        margin-left: 2px;
    }}

    /* ========== QTextEdit ========== */

    QTextEdit {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        padding: {Spacing.SM};
        font-size: {s["base"]}px;
    }}

    QTextEdit:focus {{
        border-color: {c["border_focus"]};
    }}

    QTextEdit:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
    }}

    /* ========== QDateEdit ========== */

    QDateEdit {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        padding: {Spacing.SM} {Spacing.MD};
        font-size: {s["base"]}px;
    }}

    QDateEdit:hover {{
        border-color: {c["border_hover"]};
        background: {c["bg_hover"]};
    }}

    QDateEdit:focus {{
        border-color: {c["border_focus"]};
    }}

    QDateEdit:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
    }}

    QDateEdit::drop-down {{
        background: transparent;
        subcontrol-origin: padding;
        subcontrol-position: left center;
    }}

    QDateEdit::down-arrow {{
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {c["text_secondary"]};
    }}

    /* ========== QSpinBox & QDoubleSpinBox ========== */

    QSpinBox, QDoubleSpinBox {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        padding: {Spacing.SM};
        font-size: {s["base"]}px;
    }}

    QSpinBox:hover, QDoubleSpinBox:hover {{
        border-color: {c["border_hover"]};
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {c["border_focus"]};
    }}

    QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        background: transparent;
    }}

    /* ========== QCheckBox ========== */

    QCheckBox {{
        color: {c["text_primary"]};
        font-size: {s["base"]}px;
        spacing: {Spacing.SM};
    }}

    QCheckBox::indicator {{
        border: 2px solid {c["border"]};
        border-radius: {BorderRadius.SM};
        background: {c["bg_card"]};
    }}

    QCheckBox::indicator:hover {{
        border-color: {c["primary"]};
        background: {c["bg_hover"]};
    }}

    QCheckBox::indicator:checked {{
        background: {c["primary"]};
        border-color: {c["primary"]};
    }}

    /* ========== QRadioButton ========== */

    QRadioButton {{
        color: {c["text_primary"]};
        font-size: {s["base"]}px;
        spacing: {Spacing.SM};
    }}

    QRadioButton::indicator {{
        border: 2px solid {c["border"]};
        border-radius: 10px;
        background: {c["bg_card"]};
    }}

    QRadioButton::indicator:checked {{
        background: {c["primary"]};
        border-color: {c["primary"]};
    }}

    /* ========== QProgressBar ========== */

    QProgressBar {{
        background: {c["bg_hover"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.SM};
        text-align: center;
        color: {c["text_primary"]};
    }}

    QProgressBar::chunk {{
        background: {c["primary"]};
        border-radius: {BorderRadius.SM};
    }}
    
    
        /* ========== CHECKBOX ========== */
    QCheckBox {{
        spacing: 6px;
        font-size: 14px;
        color: {c["text_primary"]};
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {c["border"]};
        background: {c["bg_card"]};
    }}

    QCheckBox::indicator:hover {{
        border: 1px solid {c["primary"]};
    }}

    QCheckBox::indicator:checked {{
        background: {c["primary"]};
        border: 1px solid {c["primary"]};
    }}

    QCheckBox::indicator:checked:hover {{
        background: {c["primary_hover"]};
    }}

    QCheckBox::indicator:disabled {{
        background: {c["bg_hover"]};
        border: 1px solid {c["border"]};
    }}
    
    
    """
