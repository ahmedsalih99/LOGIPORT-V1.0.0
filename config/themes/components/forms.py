"""
Form Components - No Borders, Bold Text
========================================
Clean inputs: no internal borders, bold font everywhere.
Focus/hover shown via background change only.
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    """Generate borderless bold form input styles"""
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ========== QLineEdit — NO BORDER ========== */

    QLineEdit {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: none;
        border-radius: {BorderRadius.MD};
        padding: {Spacing.SM} {Spacing.MD};
        font-size: {s["base"]}px;
        font-weight: 600;
    }}

    QLineEdit:hover {{
        background: {c["bg_hover"]};
    }}

    QLineEdit:focus {{
        background: {c["bg_hover"]};
    }}

    QLineEdit:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
    }}

    QLineEdit[readOnly="true"] {{
        background: {c["bg_hover"]};
        color: {c["text_secondary"]};
    }}

    QLineEdit#search-field {{
        padding-left: {Spacing.XL};
        border-radius: {BorderRadius.LG};
    }}

    /* ========== QComboBox — NO BORDER ========== */

    QComboBox {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: none;
        border-radius: {BorderRadius.MD};
        padding: {Spacing.SM} {Spacing.MD};
        font-size: {s["base"]}px;
        font-weight: 600;
    }}

    QComboBox:hover {{
        background: {c["bg_hover"]};
    }}

    QComboBox:focus {{
        background: {c["bg_hover"]};
    }}

    QComboBox:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
    }}

    QComboBox::drop-down {{
        background: transparent;
        subcontrol-origin: padding;
        subcontrol-position: left center;
        border: none;
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

    QComboBox QAbstractItemView {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: none;
        border-radius: {BorderRadius.SM};
        selection-background-color: {c["primary_light"]};
        selection-color: {c["primary"]};
        padding: {Spacing.XS};
        font-weight: 600;
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

    QTableWidget QComboBox,
    QTableView QComboBox {{
        padding: 2px 4px;
        font-size: {s["sm"]}px;
        border-radius: {BorderRadius.SM};
        border: none;
    }}

    QTableWidget QComboBox::down-arrow,
    QTableView QComboBox::down-arrow {{
        border-left: 3px solid transparent;
        border-right: 3px solid transparent;
        border-top: 4px solid {c["text_secondary"]};
        margin-left: 2px;
    }}

    /* ========== QTextEdit — NO BORDER ========== */

    QTextEdit {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: none;
        border-radius: {BorderRadius.MD};
        padding: {Spacing.SM};
        font-size: {s["base"]}px;
        font-weight: 600;
    }}

    QTextEdit:hover {{
        background: {c["bg_hover"]};
    }}

    QTextEdit:focus {{
        background: {c["bg_hover"]};
    }}

    QTextEdit:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
    }}

    /* ========== QDateEdit — NO BORDER ========== */

    QDateEdit {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: none;
        border-radius: {BorderRadius.MD};
        padding: {Spacing.SM} {Spacing.MD};
        font-size: {s["base"]}px;
        font-weight: 600;
    }}

    QDateEdit:hover {{
        background: {c["bg_hover"]};
    }}

    QDateEdit:focus {{
        background: {c["bg_hover"]};
    }}

    QDateEdit:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
    }}

    QDateEdit::drop-down {{
        background: transparent;
        subcontrol-origin: padding;
        subcontrol-position: left center;
        border: none;
    }}

    QDateEdit::down-arrow {{
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {c["text_secondary"]};
    }}

    /* ========== QSpinBox & QDoubleSpinBox — NO BORDER ========== */

    QSpinBox, QDoubleSpinBox {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: none;
        border-radius: {BorderRadius.MD};
        padding: {Spacing.SM};
        font-size: {s["base"]}px;
        font-weight: 600;
    }}

    QSpinBox:hover, QDoubleSpinBox:hover {{
        background: {c["bg_hover"]};
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        background: {c["bg_hover"]};
    }}

    QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        background: transparent;
        border: none;
    }}

    /* ========== QCheckBox ========== */

    QCheckBox {{
        spacing: 6px;
        font-size: {s["base"]}px;
        font-weight: 600;
        color: {c["text_primary"]};
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: none;
        background: {c["bg_hover"]};
    }}

    QCheckBox::indicator:hover {{
        background: {c["bg_active"]};
    }}

    QCheckBox::indicator:checked {{
        background: {c["primary"]};
    }}

    QCheckBox::indicator:checked:hover {{
        background: {c["primary_hover"]};
    }}

    QCheckBox::indicator:disabled {{
        background: {c["bg_hover"]};
    }}

    /* ========== QRadioButton ========== */

    QRadioButton {{
        color: {c["text_primary"]};
        font-size: {s["base"]}px;
        font-weight: 600;
        spacing: {Spacing.SM};
    }}

    QRadioButton::indicator {{
        border: none;
        border-radius: 10px;
        background: {c["bg_hover"]};
    }}

    QRadioButton::indicator:checked {{
        background: {c["primary"]};
    }}

    /* ========== QProgressBar ========== */

    QProgressBar {{
        background: {c["bg_hover"]};
        border: none;
        border-radius: {BorderRadius.SM};
        text-align: center;
        color: {c["text_primary"]};
        font-weight: 600;
    }}

    QProgressBar::chunk {{
        background: {c["primary"]};
        border-radius: {BorderRadius.SM};
    }}

    """