"""
Form Components - Clear Borders & Professional Focus States
===========================================================
كل حقل عنده حد واضح (1px border) بلون رمادي خفيف.
عند الـ hover → يتحول الحد للـ primary.
عند الـ focus → حد أزرق 2px + خلفية خفيفة.
الـ font-weight بقي 600 لكن خُفِّف على الـ disabled/readOnly.
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    """Generate form input styles with clear borders and focus states"""
    c = theme.colors
    s = theme.sizes

    # ── حد خفيف مشترك لكل الحقول (رمادي محايد) ──────────────────────────────
    BORDER_BASE   = f"1px solid {c['border']}"
    BORDER_HOVER  = f"1px solid {c['border_hover']}"
    BORDER_FOCUS  = f"2px solid {c['border_focus']}"
    BORDER_ERROR  = f"2px solid {c['border_error']}"

    # ── padding يعوّض الفرق بين 1px و 2px حتى لا يتحرك النص عند الفوكس ──────
    PAD_NORMAL = f"{Spacing.SM} {Spacing.MD}"          # 8px 12px
    PAD_FOCUS  = f"7px 11px"                           # 8-1  12-1  (يعوّض الـ 2px)

    return f"""
    /* =======================================================================
       QLineEdit
    ======================================================================= */

    QLineEdit {{
        background : {c["bg_card"]};
        color      : {c["text_primary"]};
        border     : {BORDER_BASE};
        border-radius : {BorderRadius.MD};
        padding    : {PAD_NORMAL};
        font-size  : {s["base"]}px;
        font-weight: 600;
    }}

    QLineEdit:hover {{
        background : {c["bg_hover"]};
        border     : {BORDER_HOVER};
    }}

    QLineEdit:focus {{
        background : {c["bg_hover"]};
        border     : {BORDER_FOCUS};
        padding    : {PAD_FOCUS};
    }}

    QLineEdit:disabled {{
        background : {c["bg_disabled"]};
        color      : {c["text_disabled"]};
        border     : 1px solid {c["border_subtle"]};
    }}

    QLineEdit[readOnly="true"] {{
        background : {c["bg_hover"]};
        color      : {c["text_secondary"]};
        border     : 1px solid {c["border_subtle"]};
    }}

    /* حقل البحث — حواف مدوّرة أكثر */
    QLineEdit#search-field {{
        padding-right: {Spacing.XL};
        border-radius : {BorderRadius.LG};
    }}

    /* حقل خطأ */
    QLineEdit[error="true"] {{
        border: {BORDER_ERROR};
        background: {c["danger_light"]};
    }}

    /* =======================================================================
       QComboBox
    ======================================================================= */

    QComboBox {{
        background : {c["bg_card"]};
        color      : {c["text_primary"]};
        border     : {BORDER_BASE};
        border-radius : {BorderRadius.MD};
        padding    : {PAD_NORMAL};
        font-size  : {s["base"]}px;
        font-weight: 600;
    }}

    QComboBox:hover {{
        background : {c["bg_hover"]};
        border     : {BORDER_HOVER};
    }}

    QComboBox:focus, QComboBox:on {{
        background : {c["bg_hover"]};
        border     : {BORDER_FOCUS};
        padding    : {PAD_FOCUS};
    }}

    QComboBox:disabled {{
        background : {c["bg_disabled"]};
        color      : {c["text_disabled"]};
        border     : 1px solid {c["border_subtle"]};
    }}

    QComboBox::drop-down {{
        background : transparent;
        subcontrol-origin   : padding;
        subcontrol-position : left center;
        border: none;
        width: 24px;
    }}

    QComboBox::down-arrow {{
        border-left  : 4px solid transparent;
        border-right : 4px solid transparent;
        border-top   : 5px solid {c["text_secondary"]};
        margin-left  : 4px;
    }}

    QComboBox::down-arrow:hover {{
        border-top-color: {c["primary"]};
    }}

    QComboBox QAbstractItemView {{
        background  : {c["bg_card"]};
        color       : {c["text_primary"]};
        border      : 1px solid {c["border"]};
        border-radius: {BorderRadius.SM};
        selection-background-color: {c["primary_light"]};
        selection-color: {c["primary"]};
        padding     : {Spacing.XS};
        font-weight : 600;
        outline     : none;
    }}

    QComboBox QAbstractItemView::item {{
        padding      : {Spacing.XS} {Spacing.SM};
        border-radius: {BorderRadius.SM};
        min-height   : 28px;
    }}

    QComboBox QAbstractItemView::item:hover {{
        background: {c["bg_hover"]};
    }}

    QComboBox QAbstractItemView::item:selected {{
        background: {c["primary_light"]};
        color     : {c["primary"]};
    }}

    /* ComboBox داخل الجداول — padding مضغوط */
    QTableWidget QComboBox,
    QTableView  QComboBox {{
        padding      : 2px 4px;
        font-size    : {s["sm"]}px;
        border-radius: {BorderRadius.SM};
        border       : 1px solid {c["border"]};
    }}

    QTableWidget QComboBox::down-arrow,
    QTableView  QComboBox::down-arrow {{
        border-left  : 3px solid transparent;
        border-right : 3px solid transparent;
        border-top   : 4px solid {c["text_secondary"]};
        margin-left  : 2px;
    }}

    /* =======================================================================
       QTextEdit
    ======================================================================= */

    QTextEdit {{
        background : {c["bg_card"]};
        color      : {c["text_primary"]};
        border     : {BORDER_BASE};
        border-radius : {BorderRadius.MD};
        padding    : {Spacing.SM};
        font-size  : {s["base"]}px;
        font-weight: 600;
    }}

    QTextEdit:hover {{
        background : {c["bg_hover"]};
        border     : {BORDER_HOVER};
    }}

    QTextEdit:focus {{
        background : {c["bg_hover"]};
        border     : {BORDER_FOCUS};
        padding    : 7px;
    }}

    QTextEdit:disabled {{
        background : {c["bg_disabled"]};
        color      : {c["text_disabled"]};
        border     : 1px solid {c["border_subtle"]};
    }}

    /* =======================================================================
       QDateEdit
    ======================================================================= */

    QDateEdit {{
        background : {c["bg_card"]};
        color      : {c["text_primary"]};
        border     : {BORDER_BASE};
        border-radius : {BorderRadius.MD};
        padding    : {PAD_NORMAL};
        font-size  : {s["base"]}px;
        font-weight: 600;
    }}

    QDateEdit:hover {{
        background : {c["bg_hover"]};
        border     : {BORDER_HOVER};
    }}

    QDateEdit:focus {{
        background : {c["bg_hover"]};
        border     : {BORDER_FOCUS};
        padding    : {PAD_FOCUS};
    }}

    QDateEdit:disabled {{
        background : {c["bg_disabled"]};
        color      : {c["text_disabled"]};
        border     : 1px solid {c["border_subtle"]};
    }}

    QDateEdit::drop-down {{
        background          : transparent;
        subcontrol-origin   : padding;
        subcontrol-position : left center;
        border: none;
        width: 24px;
    }}

    QDateEdit::down-arrow {{
        border-left  : 4px solid transparent;
        border-right : 4px solid transparent;
        border-top   : 5px solid {c["text_secondary"]};
    }}

    /* =======================================================================
       QSpinBox & QDoubleSpinBox
    ======================================================================= */

    QSpinBox, QDoubleSpinBox {{
        background : {c["bg_card"]};
        color      : {c["text_primary"]};
        border     : {BORDER_BASE};
        border-radius : {BorderRadius.MD};
        padding    : {PAD_NORMAL};
        font-size  : {s["base"]}px;
        font-weight: 600;
    }}

    QSpinBox:hover, QDoubleSpinBox:hover {{
        background : {c["bg_hover"]};
        border     : {BORDER_HOVER};
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        background : {c["bg_hover"]};
        border     : {BORDER_FOCUS};
        padding    : {PAD_FOCUS};
    }}

    QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background : {c["bg_disabled"]};
        color      : {c["text_disabled"]};
        border     : 1px solid {c["border_subtle"]};
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        background : transparent;
        border     : none;
        width      : 16px;
    }}

    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        border-left  : 3px solid transparent;
        border-right : 3px solid transparent;
        border-bottom: 4px solid {c["text_secondary"]};
    }}

    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        border-left  : 3px solid transparent;
        border-right : 3px solid transparent;
        border-top   : 4px solid {c["text_secondary"]};
    }}

    /* =======================================================================
       QCheckBox
    ======================================================================= */

    QCheckBox {{
        spacing    : 6px;
        font-size  : {s["base"]}px;
        font-weight: 600;
        color      : {c["text_primary"]};
    }}

    QCheckBox::indicator {{
        width        : 16px;
        height       : 16px;
        border-radius: 4px;
        border       : 1px solid {c["border"]};
        background   : {c["bg_card"]};
    }}

    QCheckBox::indicator:hover {{
        border    : 1px solid {c["border_hover"]};
        background: {c["bg_hover"]};
    }}

    QCheckBox::indicator:checked {{
        background: {c["primary"]};
        border    : 1px solid {c["primary"]};
    }}

    QCheckBox::indicator:checked:hover {{
        background: {c["primary_hover"]};
        border    : 1px solid {c["primary_hover"]};
    }}

    QCheckBox::indicator:disabled {{
        background: {c["bg_disabled"]};
        border    : 1px solid {c["border_subtle"]};
    }}

    /* =======================================================================
       QRadioButton
    ======================================================================= */

    QRadioButton {{
        color      : {c["text_primary"]};
        font-size  : {s["base"]}px;
        font-weight: 600;
        spacing    : {Spacing.SM};
    }}

    QRadioButton::indicator {{
        width        : 16px;
        height       : 16px;
        border-radius: 8px;
        border       : 1px solid {c["border"]};
        background   : {c["bg_card"]};
    }}

    QRadioButton::indicator:hover {{
        border: 1px solid {c["border_hover"]};
    }}

    QRadioButton::indicator:checked {{
        background: {c["primary"]};
        border    : 1px solid {c["primary"]};
    }}

    /* =======================================================================
       QProgressBar
    ======================================================================= */

    QProgressBar {{
        background   : {c["bg_hover"]};
        border       : 1px solid {c["border_subtle"]};
        border-radius: {BorderRadius.SM};
        text-align   : center;
        color        : {c["text_primary"]};
        font-weight  : 600;
    }}

    QProgressBar::chunk {{
        background   : {c["primary"]};
        border-radius: {BorderRadius.SM};
    }}

    """
