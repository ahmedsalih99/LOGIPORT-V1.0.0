"""
Button Component Styles - NO SIZE CONSTRAINTS
============================================

Visual-only button styles.
No width / height / min / max enforced.
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    """Generate button styles without size constraints"""
    c = theme.colors
    s = theme.sizes

    return f"""
    /* ========== BUTTONS - VISUAL ONLY ========== */

    /* Base Button Style */
    QPushButton {{
        background: {c["bg_hover"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: {BorderRadius.MD};
        padding: {Spacing.SM} {Spacing.LG};
        font-size: {s["base"]}px;
        font-weight: 500;
    }}

    QPushButton:hover {{
        background: {c["bg_active"]};
        border-color: {c["border_hover"]};
    }}

    QPushButton:pressed {{
        background: {c["border"]};
    }}

    QPushButton:disabled {{
        background: {c["bg_disabled"]};
        color: {c["text_disabled"]};
        border-color: {c["border"]};
    }}

    /* ========== Primary Button ========== */
    QPushButton#primary-btn {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 {c["primary"]},
            stop: 1 {c["primary_active"]}
        );
        color: {c["text_white"]};
        border: none;
        font-weight: 600;
        border-radius: {BorderRadius.MD};
        padding: 6px 12px;
    }}

    QPushButton#primary-btn:hover {{
        background: qlineargradient(
            x1: 0, y1: 0, x2: 0, y2: 1,
            stop: 0 {c["primary_hover"]},
            stop: 1 {c["primary"]}
        );
    }}

    QPushButton#primary-btn:pressed {{
        background: {c["primary_active"]};
    }}

    /* ========== Secondary Button ========== */
    QPushButton#secondary-btn {{
        background: transparent;
        color: {c["text_secondary"]};
        border: 1px solid {c["border"]};
        padding: 6px 12px;
    }}

    QPushButton#secondary-btn:hover {{
        background: {c["bg_hover"]};
        color: {c["text_primary"]};
    }}

    /* ========== Danger Button ========== */
    QPushButton#danger-btn {{
        background: {c["danger"]};
        color: {c["text_white"]};
        border: none;
        font-weight: 600;
        padding: 6px 12px;
    }}

    QPushButton#danger-btn:hover {{
        background: {c["danger_hover"]};
    }}

    QPushButton#danger-btn:pressed {{
        background: {c["danger_active"]};
    }}

    /* ========== Success Button ========== */
    QPushButton#success-btn {{
        background: {c["success"]};
        color: {c["text_white"]};
        border: none;
        font-weight: 600;
        padding: 6px 12px;
    }}

    QPushButton#success-btn:hover {{
        background: {c["success_hover"]};
    }}

    /* ========== Warning Button ========== */
    QPushButton#warning-btn {{
        background: {c["warning"]};
        color: {c["text_white"]};
        border: none;
        font-weight: 600;
        padding: 6px 12px;
    }}

    QPushButton#warning-btn:hover {{
        background: {c["warning_hover"]};
    }}

    /* ========== Small Button (Visual only) ========== */
    QPushButton#small-btn {{
        padding: {Spacing.XS} {Spacing.SM};
        font-size: {s["sm"]}px;
    }}

    /* ========== Large Button (Visual only) ========== */
    QPushButton#large-btn {{
        padding: {Spacing.MD} {Spacing.XL};
        font-size: {s["lg"]}px;
    }}

    /* ========== Icon Button (no forced square) ========== */
    QPushButton#icon-btn {{
        background: transparent;
        border: none;
        padding: {Spacing.SM};
    }}

    QPushButton#icon-btn:hover {{
        background: {c["bg_hover"]};
        border-radius: {BorderRadius.SM};
    }}

    /* ========== TABLE BUTTONS - NO SIZE LOCK ========== */
    QTableWidget QPushButton,
    QTableView QPushButton {{
        padding: 2px 6px;
        font-size: {s["sm"]}px;
        border-radius: {BorderRadius.SM};
        font-weight: 500;
    }}

    /* Table Primary */
    QTableWidget QPushButton#primary-btn,
    QTableView QPushButton#primary-btn,
    QTableWidget QPushButton#table-edit,
    QTableView QPushButton#table-edit {{
        background: {c["primary"]};
        color: {c["text_white"]};
        border: none;
    }}

    QTableWidget QPushButton#primary-btn:hover,
    QTableView QPushButton#primary-btn:hover,
    QTableWidget QPushButton#table-edit:hover,
    QTableView QPushButton#table-edit:hover {{
        background: {c["primary_hover"]};
    }}

    /* Table Danger */
    QTableWidget QPushButton#danger-btn,
    QTableView QPushButton#danger-btn,
    QTableWidget QPushButton#table-delete,
    QTableView QPushButton#table-delete {{
        background: {c["danger"]};
        color: {c["text_white"]};
        border: none;
    }}

    QTableWidget QPushButton#danger-btn:hover,
    QTableView QPushButton#danger-btn:hover,
    QTableWidget QPushButton#table-delete:hover,
    QTableView QPushButton#table-delete:hover {{
        background: {c["danger_hover"]};
    }}

    /* Outline Table Button */
    QPushButton#table-btn-outline {{
        background: transparent;
        border: 1px solid {c["border"]};
        color: {c["text_primary"]};
        padding: 3px 6px;
    }}

    QPushButton#table-btn-outline:hover {{
        background: {c["bg_hover"]};
        border-color: {c["primary"]};
        color: {c["primary"]};
    }}

    /* ========== Toolbar Button ========== */
    QPushButton#toolbar-btn {{
        background: transparent;
        border: 1px solid transparent;
        padding: {Spacing.SM} {Spacing.MD};
    }}

    QPushButton#toolbar-btn:hover {{
        background: {c["bg_hover"]};
        border-color: {c["border"]};
    }}

    /* ========== Link Button ========== */
    QPushButton#link-btn {{
        background: transparent;
        color: {c["primary"]};
        border: none;
        text-decoration: underline;
        padding: 0;
        text-align: left;
    }}

    QPushButton#link-btn:hover {{
        color: {c["primary_hover"]};
    }}

    /* ========== Compact Button (visual density only) ========== */
    QPushButton#compact-btn {{
        padding: 4px 8px;
        font-size: {s["sm"]}px;
        border-radius: {BorderRadius.SM};
    }}
    """
