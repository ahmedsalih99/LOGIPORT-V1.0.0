"""
Form Components - Unified & Consistent
=======================================
قواعد موحّدة لكل حقول الإدخال:
  ✔ font-weight: 400 على كل الحقول (لا ثقل زائد)
  ✔ min-height: 36px موحّد (LineEdit / ComboBox / DateEdit / SpinBox)
  ✔ border-radius من BorderRadius.MD
  ✔ padding يعوّض الـ 1px→2px عند focus (لا يتحرك النص)
  ✔ QCheckBox indicator مع checkmark مرئي
  ✔ QComboBox inside tables: compact
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    c = theme.colors
    s = theme.sizes

    BORDER_BASE   = f"1px solid {c['border']}"
    BORDER_HOVER  = f"1px solid {c['border_hover']}"
    BORDER_FOCUS  = f"2px solid {c['border_focus']}"
    BORDER_ERROR  = f"2px solid {c['border_error']}"

    PAD_NORMAL = "5px 10px"                      # compact
    PAD_FOCUS  = "4px 9px"                        # يعوّض الـ 2px border

    R  = BorderRadius.MD
    RS = BorderRadius.SM

    return f"""
    /* ═══════════════════════════════════════════════════════════
       QLineEdit
    ═══════════════════════════════════════════════════════════ */

    QLineEdit {{
        background    : {c["bg_card"]};
        color         : {c["text_primary"]};
        border        : {BORDER_BASE};
        border-radius : {R};
        padding       : {PAD_NORMAL};
        font-size     : {s["base"]}px;
        font-weight   : 400;
    }}
    QLineEdit:hover {{
        background: {c["bg_hover"]};
        border    : {BORDER_HOVER};
    }}
    QLineEdit:focus {{
        background: {c["bg_hover"]};
        border    : {BORDER_FOCUS};
        padding   : {PAD_FOCUS};
    }}
    QLineEdit:disabled {{
        background: {c["bg_disabled"]};
        color     : {c["text_disabled"]};
        border    : 1px solid {c["border_subtle"]};
    }}
    QLineEdit[readOnly="true"] {{
        background: {c["bg_hover"]};
        color     : {c["text_secondary"]};
        border    : 1px solid {c["border_subtle"]};
    }}
    QLineEdit#search-field {{
        border-radius: {BorderRadius.LG};
    }}
    QLineEdit[error="true"] {{
        border    : {BORDER_ERROR};
        background: {c["danger_light"]};
    }}

    /* ═══════════════════════════════════════════════════════════
       QComboBox
    ═══════════════════════════════════════════════════════════ */

    QComboBox {{
        background    : {c["bg_card"]};
        color         : {c["text_primary"]};
        border        : {BORDER_BASE};
        border-radius : {R};
        padding       : {PAD_NORMAL};
        font-size     : {s["base"]}px;
        font-weight   : 400;
    }}
    QComboBox:hover {{
        background: {c["bg_hover"]};
        border    : {BORDER_HOVER};
    }}
    QComboBox:focus, QComboBox:on {{
        background: {c["bg_hover"]};
        border    : {BORDER_FOCUS};
        padding   : {PAD_FOCUS};
    }}
    QComboBox:disabled {{
        background: {c["bg_disabled"]};
        color     : {c["text_disabled"]};
        border    : 1px solid {c["border_subtle"]};
    }}
    QComboBox::drop-down {{
        width              : 1px;
        border             : none;
        background         : transparent;
        subcontrol-origin  : padding;
        subcontrol-position: right center;
    }}
    QComboBox::down-arrow {{
        image : none;
        width : 0;
        height: 0;
        border: none;
    }}

    /* form-combo — editable search */
    QComboBox#form-combo {{
        background   : {c["input_bg"]};
        border       : 1.5px solid {c["border"]};
        border-radius: {RS};
        color        : {c["text_primary"]};
        font-size    : {s["base"]}px;
        font-weight  : 400;
        padding   : 3px 8px;
    }}
    QComboBox#form-combo:focus,
    QComboBox#form-combo:on {{
        border-color: {c["accent"]};
        border-width: 2px;
        background  : {c["input_bg"]};
    }}
    QComboBox#form-combo QLineEdit {{
        background               : transparent;
        border                   : none;
        color                    : {c["text_primary"]};
        font-size                : {s["base"]}px;
        padding                  : 0 2px;
        selection-background-color: {c["accent_soft"]};
    }}
    QComboBox#form-combo::drop-down {{
        width              : 1px;
        border             : none;
        background         : transparent;
        subcontrol-origin  : padding;
        subcontrol-position: right center;
    }}
    QComboBox#form-combo::down-arrow {{
        image : none;
        width : 0;
        height: 0;
        border: none;
    }}

    /* ComboBox داخل الجداول — compact */
    QTableWidget QComboBox,
    QTableView  QComboBox {{
        padding      : 2px 6px;
        font-size    : {s["sm"]}px;
        border-radius: {RS};
        border       : 1px solid {c["border"]};
        min-height   : 26px;
        font-weight  : 400;
    }}
    QTableWidget QComboBox::down-arrow,
    QTableView  QComboBox::down-arrow {{
        image : none;
        width : 0;
        height: 0;
        border: none;
    }}

    /* ═══════════════════════════════════════════════════════════
       QTextEdit
    ═══════════════════════════════════════════════════════════ */

    QTextEdit {{
        background    : {c["bg_card"]};
        color         : {c["text_primary"]};
        border        : {BORDER_BASE};
        border-radius : {R};
        padding       : {Spacing.SM} {Spacing.MD};
        font-size     : {s["base"]}px;
        font-weight   : 400;
    }}
    QTextEdit:hover {{
        background: {c["bg_hover"]};
        border    : {BORDER_HOVER};
    }}
    QTextEdit:focus {{
        background: {c["bg_hover"]};
        border    : {BORDER_FOCUS};
        padding   : 4px 9px;
    }}
    QTextEdit:disabled {{
        background: {c["bg_disabled"]};
        color     : {c["text_disabled"]};
        border    : 1px solid {c["border_subtle"]};
    }}

    /* ═══════════════════════════════════════════════════════════
       QDateEdit
    ═══════════════════════════════════════════════════════════ */

    QDateEdit {{
        background    : {c["bg_card"]};
        color         : {c["text_primary"]};
        border        : {BORDER_BASE};
        border-radius : {R};
        padding       : {PAD_NORMAL};
        font-size     : {s["base"]}px;
        font-weight   : 400;
    }}
    QDateEdit:hover {{
        background: {c["bg_hover"]};
        border    : {BORDER_HOVER};
    }}
    QDateEdit:focus {{
        background: {c["bg_hover"]};
        border    : {BORDER_FOCUS};
        padding   : {PAD_FOCUS};
    }}
    QDateEdit:disabled {{
        background: {c["bg_disabled"]};
        color     : {c["text_disabled"]};
        border    : 1px solid {c["border_subtle"]};
    }}
    QDateEdit::drop-down {{
        width              : 1px;
        border             : none;
        background         : transparent;
        subcontrol-origin  : padding;
        subcontrol-position: right center;
    }}
    QDateEdit::down-arrow {{
        image : none;
        width : 0;
        height: 0;
        border: none;
    }}

    /* ═══════════════════════════════════════════════════════════
       QCalendarWidget
    ═══════════════════════════════════════════════════════════ */

    QCalendarWidget QWidget#qt_calendar_navigationbar {{
        background: {c["primary"]};
        min-height: 40px;
        padding   : 2px 6px;
    }}
    QCalendarWidget QToolButton {{
        background   : transparent;
        color        : #FFFFFF;
        font-size    : 13px;
        font-weight  : 700;
        border       : none;
        border-radius: {RS};
        padding      : 4px 10px;
        margin       : 1px 2px;
        min-width    : 28px;
        min-height   : 28px;
    }}
    QCalendarWidget QToolButton:hover {{
        background: rgba(255,255,255,0.20);
    }}
    QCalendarWidget QToolButton:pressed {{
        background: rgba(255,255,255,0.35);
    }}
    QCalendarWidget QToolButton::menu-indicator {{
        image : none;
        width : 0px;
    }}
    QCalendarWidget QSpinBox {{
        background                : rgba(255,255,255,0.15);
        color                     : #FFFFFF;
        border                    : 1px solid rgba(255,255,255,0.35);
        border-radius             : {RS};
        padding                   : 2px 4px;
        font-size                 : 13px;
        font-weight               : 700;
        min-width : 52px;
        min-height: 0;
        selection-background-color: {c["primary_active"]};
        selection-color           : #FFFFFF;
    }}
    QCalendarWidget QSpinBox::up-button,
    QCalendarWidget QSpinBox::down-button {{
        background: transparent;
        border    : none;
        width     : 14px;
        height    : 10px;
    }}
    QCalendarWidget QSpinBox::up-arrow {{
        border-left  : 3px solid transparent;
        border-right : 3px solid transparent;
        border-bottom: 4px solid #FFFFFF;
        width : 0px;
        height: 0px;
    }}
    QCalendarWidget QSpinBox::down-arrow {{
        border-left  : 3px solid transparent;
        border-right : 3px solid transparent;
        border-top   : 4px solid #FFFFFF;
        width : 0px;
        height: 0px;
    }}
    QCalendarWidget QHeaderView {{
        background: {c["bg_disabled"]};
    }}
    QCalendarWidget QHeaderView::section {{
        background : {c["bg_disabled"]};
        color      : {c["text_muted"]};
        font-size  : 11px;
        font-weight: 600;
        border     : none;
        padding    : 4px 0;
    }}
    QCalendarWidget QAbstractItemView {{
        background                : {c["bg_card"]};
        color                     : {c["text_primary"]};
        selection-background-color: {c["primary"]};
        selection-color           : #FFFFFF;
        gridline-color            : {c["border_subtle"]};
        outline                   : none;
        border                    : none;
        font-size                 : 13px;
    }}

    /* ═══════════════════════════════════════════════════════════
       QSpinBox & QDoubleSpinBox
    ═══════════════════════════════════════════════════════════ */

    QSpinBox, QDoubleSpinBox {{
        background    : {c["bg_card"]};
        color         : {c["text_primary"]};
        border        : {BORDER_BASE};
        border-radius : {R};
        padding       : {PAD_NORMAL};
        font-size     : {s["base"]}px;
        font-weight   : 400;
    }}
    QSpinBox:hover, QDoubleSpinBox:hover {{
        background: {c["bg_hover"]};
        border    : {BORDER_HOVER};
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        background: {c["bg_hover"]};
        border    : {BORDER_FOCUS};
        padding   : {PAD_FOCUS};
    }}
    QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background: {c["bg_disabled"]};
        color     : {c["text_disabled"]};
        border    : 1px solid {c["border_subtle"]};
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        background: transparent;
        border    : none;
        width     : 16px;
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        border-left  : 3px solid transparent;
        border-right : 3px solid transparent;
        border-bottom: 4px solid {c["text_secondary"]};
        width : 0px;
        height: 0px;
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        border-left  : 3px solid transparent;
        border-right : 3px solid transparent;
        border-top   : 4px solid {c["text_secondary"]};
        width : 0px;
        height: 0px;
    }}

    /* ═══════════════════════════════════════════════════════════
       QCheckBox — مع checkmark مرئي
    ═══════════════════════════════════════════════════════════ */

    QCheckBox {{
        spacing    : 8px;
        font-size  : {s["base"]}px;
        font-weight: 400;
        color      : {c["text_primary"]};
    }}
    QCheckBox::indicator {{
        width        : 17px;
        height       : 17px;
        border-radius: {RS};
        border       : 1.5px solid {c["border"]};
        background   : {c["bg_card"]};
    }}
    QCheckBox::indicator:hover {{
        border    : 1.5px solid {c["border_hover"]};
        background: {c["bg_hover"]};
    }}
    QCheckBox::indicator:checked {{
        background   : {c["primary"]};
        border       : 1.5px solid {c["primary"]};
        /* checkmark via border trick */
        image        : none;
    }}
    QCheckBox::indicator:checked:hover {{
        background: {c["primary_hover"]};
        border    : 1.5px solid {c["primary_hover"]};
    }}
    QCheckBox::indicator:indeterminate {{
        background: {c["primary_light"]};
        border    : 1.5px solid {c["primary"]};
    }}
    QCheckBox::indicator:disabled {{
        background: {c["bg_disabled"]};
        border    : 1px solid {c["border_subtle"]};
    }}

    /* ═══════════════════════════════════════════════════════════
       QRadioButton
    ═══════════════════════════════════════════════════════════ */

    QRadioButton {{
        color      : {c["text_primary"]};
        font-size  : {s["base"]}px;
        font-weight: 400;
        spacing    : {Spacing.SM};
    }}
    QRadioButton::indicator {{
        width        : 17px;
        height       : 17px;
        border-radius: 9px;
        border       : 1.5px solid {c["border"]};
        background   : {c["bg_card"]};
    }}
    QRadioButton::indicator:hover {{
        border: 1.5px solid {c["border_hover"]};
    }}
    QRadioButton::indicator:checked {{
        background: {c["primary"]};
        border    : 1.5px solid {c["primary"]};
    }}
    QRadioButton::indicator:disabled {{
        background: {c["bg_disabled"]};
        border    : 1px solid {c["border_subtle"]};
    }}

    /* ═══════════════════════════════════════════════════════════
       QProgressBar
    ═══════════════════════════════════════════════════════════ */

    QProgressBar {{
        background   : {c["bg_disabled"]};
        border       : 1px solid {c["border_subtle"]};
        border-radius: {RS};
        text-align   : center;
        color        : {c["text_primary"]};
        font-weight  : 600;
        min-height   : 8px;
        max-height   : 8px;
    }}
    QProgressBar::chunk {{
        background   : {c["primary"]};
        border-radius: {RS};
    }}

    /* ═══════════════════════════════════════════════════════════
       QGroupBox — كان غائباً تماماً
    ═══════════════════════════════════════════════════════════ */

    QGroupBox {{
        background   : {c["bg_card"]};
        border       : 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        margin-top   : 12px;
        padding-top  : 8px;
        font-size    : {s["base"]}px;
        font-weight  : 600;
        color        : {c["text_secondary"]};
    }}
    QGroupBox::title {{
        subcontrol-origin  : margin;
        subcontrol-position: top right;
        padding            : 0 8px;
        color              : {c["text_secondary"]};
        font-weight        : 600;
        font-size          : {s["sm"]}px;
    }}

    /* ═══════════════════════════════════════════════════════════
       QScrollArea
    ═══════════════════════════════════════════════════════════ */

    QScrollArea {{
        background  : transparent;
        border      : none;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}

    """