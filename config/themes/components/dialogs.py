"""Dialog Component Styles - Visual Only"""

from ..border_radius import BorderRadius


def get_styles(theme):
    """
    Generate dialog styles - visual only (no geometry control)
    """
    c = theme.colors

    return f"""
    /* ========== DIALOGS ========== */
    
    /* QDialog Base */
    QDialog {{
        background: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.XXL};
    }}
    
    /* Dialog Title */
    QDialog QLabel#title {{
        color: {c["primary"]};
        font-weight: 800;
    }}
    
    QDialog QLabel#subtitle {{
        color: {c["text_secondary"]};
        font-weight: 600;
    }}
    
    QDialog QLabel#muted {{
        color: {c["text_muted"]};
    }}
    
    /* Dialog Buttons */
    QDialog QPushButton {{
        border-radius: {BorderRadius.MD};
    }}
    
    /* QMessageBox */
    QMessageBox {{
        background: {c["bg_card"]};
        border-radius: {BorderRadius.XL};
    }}
    
    QMessageBox QLabel {{
        color: {c["text_primary"]};
    }}
    
    /* ========== LOGIN DIALOG SPECIFIC ========== */
    
    /* Login Dialog Container */
    QDialog#LoginDialog {{
        background: {c["bg_main"]};
        border: none;
    }}
    
    /* Login Card */
    QFrame#login-card {{
        background: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.XXL};
    }}
    
    /* Login Dialog Title */
    QDialog#LoginDialog QLabel#title {{
        color: {c["primary"]};
        font-weight: 800;
        letter-spacing: 2px;
    }}
    
    /* Login Dialog Labels */
    QDialog#LoginDialog QLabel#subtitle {{
        color: {c["text_secondary"]};
        font-weight: 600;
    }}
    
    /* Login Dialog Input Fields */
    QDialog#LoginDialog QLineEdit {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 2px solid {c["border"]};
        border-radius: {BorderRadius.MD};
    }}
    
    QDialog#LoginDialog QLineEdit:hover {{
        border-color: {c["border_hover"]};
    }}
    
    QDialog#LoginDialog QLineEdit:focus {{
        border-color: {c["border_focus"]};
        background: {c["bg_card"]};
    }}
    
    /* Login Dialog ComboBox */
    QDialog#LoginDialog QComboBox {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
    }}
    
    QDialog#LoginDialog QComboBox:hover {{
        border-color: {c["border_hover"]};
        background: {c["bg_hover"]};
    }}
    
    QDialog#LoginDialog QComboBox::drop-down {{
        border: none;
        background: transparent;
    }}
    
    QDialog#LoginDialog QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {c["text_secondary"]};
    }}
    
    /* Dropdown Items */
    QDialog#LoginDialog QComboBox QAbstractItemView {{
        background: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.SM};
        selection-background-color: {c["primary_light"]};
    }}
    
    /* Login Button (Primary) */
    QDialog#LoginDialog QPushButton#primary-btn {{
        background: {c["primary"]};
        color: {c["text_white"]};
        border: none;
        border-radius: {BorderRadius.MD};
        font-weight: 700;
        letter-spacing: 1px;
    }}
    
    QDialog#LoginDialog QPushButton#primary-btn:hover {{
        background: {c["primary_hover"]};
    }}
    
    QDialog#LoginDialog QPushButton#primary-btn:pressed {{
        background: {c["primary_active"]};
    }}
    
    /* Eye Button */
    QDialog#LoginDialog QPushButton#icon-btn {{
        background: transparent;
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
    }}
    
    QDialog#LoginDialog QPushButton#icon-btn:hover {{
        background: {c["bg_hover"]};
        border-color: {c["border_hover"]};
    }}
    
    QDialog#LoginDialog QPushButton#icon-btn:pressed {{
        background: {c["bg_active"]};
    }}
    
    QDialog#LoginDialog QPushButton#icon-btn:checked {{
        background: {c["primary_light"]};
        border-color: {c["primary"]};
    }}
    
    /* Copyright Label */
    QDialog#LoginDialog QLabel#muted {{
        color: {c["text_muted"]};
    }}
    
    /* ========== SETTINGS DIALOG SPECIFIC ========== */
    
    /* Settings Dialog Container */
    QDialog#SettingsDialog {{
        background: {c["bg_main"]};
        border: none;
    }}
    
    /* Settings Card */
    QFrame#settings-card {{
        background: {c["bg_card"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.XXL};
    }}
    
    /* Settings Titles */
    QFrame#settings-card QLabel#settings-title {{
        color: {c["primary"]};
        font-weight: 800;
    }}
    
    QFrame#settings-card QLabel#settings-section-title {{
        color: {c["text_primary"]};
        font-weight: 700;
    }}
    
    /* Settings Color Bar */
    QFrame#settings-card-bar {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 0,
            stop: 0 {c["primary"]},
            stop: 0.5 {c["success"]},
            stop: 1 {c["warning"]}
        );
        border-radius: {BorderRadius.SM};
    }}
    
    /* Settings ComboBox */
    QDialog#SettingsDialog QComboBox#settings-combo {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
    }}
    
    QDialog#SettingsDialog QComboBox#settings-combo:hover {{
        border-color: {c["border_hover"]};
        background: {c["bg_hover"]};
    }}
    
    QDialog#SettingsDialog QComboBox#settings-combo:focus {{
        border-color: {c["border_focus"]};
    }}
    
    /* Settings Input Fields */
    QDialog#SettingsDialog QLineEdit#settings-input {{
        background: {c["bg_card"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
    }}
    
    /* Settings CheckBox */
    QDialog#SettingsDialog QCheckBox#settings-checkbox {{
        color: {c["text_primary"]};
    }}
    
    /* Settings Separator */
    QFrame#settings-separator {{
        background: {c["border_subtle"]};
    }}
    
    /* Dialog Input Fields - General */
QDialog QLineEdit {{
    background: {c["bg_card"]};
    color: {c["text_primary"]};
    border: 1px solid {c["border"]};
    border-radius: {BorderRadius.MD};
    padding: 6px 8px;
}}

QDialog QLineEdit:hover {{
    border-color: {c["border_hover"]};
}}

QDialog QLineEdit:focus {{
    border: 2px solid {c["border_focus"]};
    background: {c["bg_card"]};
}}


    /* ========== FORM DIALOG ========== */

    QWidget#form-dialog-header {{
        background: {c["bg_card"]};
    }}

    QLabel#form-dialog-title {{
        color: {c["text_primary"]};
        font-weight: 700;
    }}

    QLabel#form-dialog-subtitle {{
        color: {c["text_secondary"]};
        font-weight: 500;
    }}

    QLabel#form-dialog-label {{
        color: {c["text_primary"]};
        font-weight: 600;
    }}

    QLabel#form-section-title {{
        color: {c["primary"]};
        font-weight: 700;
    }}

    QFrame#form-dialog-sep {{
        background: {c["border_subtle"]};
        border: none;
    }}

    QWidget#form-dialog-body {{
        background: {c["bg_main"]};
    }}

    QWidget#form-dialog-footer {{
        background: {c["bg_card"]};
    }}

    QScrollArea#form-dialog-scroll {{
        background: {c["bg_main"]};
        border: none;
    }}

    QScrollArea#form-dialog-scroll > QWidget > QWidget {{
        background: {c["bg_main"]};
    }}

    
    
    
    """
