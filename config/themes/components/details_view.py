"""
Details View Component Styles - LOGIPORT
==========================================

Object names targeted (defined in core/base_details_view.py):

  Container / Scroll
    details-scroll        QScrollArea wrapper
    details-container     inner QWidget
    details-card          QFrame main card

  Sections (collapsible)
    details-section       QWidget per section
    section-header        QFrame clickable header
    section-title         QLabel title text
    section-arrow         QLabel arrow (collapse indicator)
    section-count         QLabel row-count badge
    section-body          QWidget rows container

  Rows
    detail-row            QWidget normal row
    detail-row-alt        QWidget alternating row
    detail-icon           QLabel emoji icon
    detail-sep            QLabel colon separator
    detail-key            QLabel field label
    detail-key-financial  QLabel financial field label
    detail-value          QLabel field value
    detail-value-financial QLabel financial field value

  Interactive
    copy-btn              QToolButton copy icon
    copy-toast            QLabel success tick

  Badges  (badge-{value} pattern)
    badge-active
    badge-inactive
    badge-draft
    badge-import
    badge-export
    badge-transit
    badge-pending
    badge-cancelled
    badge-completed
"""

from ..border_radius import BorderRadius


def get_styles(theme) -> str:
    c = theme.colors
    s = theme.sizes

    return f"""
    /* =========================================================
       DETAILS VIEW — SCROLL & CONTAINER
       ========================================================= */

    QScrollArea#details-scroll {{
        background: transparent;
        border: none;
    }}

    QScrollArea#details-scroll > QWidget#qt_scrollarea_viewport {{
        background: transparent;
    }}

    QWidget#details-container {{
        background: transparent;
    }}


    /* =========================================================
       DETAILS VIEW — MAIN CARD
       ========================================================= */

    QFrame#details-card {{
        background: {c["bg_card"]};
        border: 1px solid {c["border_subtle"]};
        border-radius: {BorderRadius.LG};
    }}


    /* =========================================================
       SECTION — COLLAPSIBLE BLOCK
       ========================================================= */

    QWidget#details-section {{
        background: transparent;
    }}

    QFrame#section-header {{
        background: {c["primary_lighter"]};
        border: none;
        border-radius: {BorderRadius.SM};
    }}

    QFrame#section-header:hover {{
        background: {c["primary_light"]};
    }}

    QLabel#section-title {{
        color: {c["primary"]};
        font-size: {s["md"]}px;
        font-weight: 700;
        background: transparent;
    }}

    QLabel#section-arrow {{
        color: {c["primary"]};
        font-size: {s["base"]}px;
        font-weight: 700;
        background: transparent;
    }}

    QLabel#section-count {{
        color: {c["text_white"]};
        background: {c["primary"]};
        border-radius: {BorderRadius.FULL};
        font-size: {s["xs"]}px;
        font-weight: 700;
        padding: 1px 6px;
        min-width: 18px;
    }}

    QWidget#section-body {{
        background: transparent;
    }}


    /* =========================================================
       ROWS — NORMAL & ALTERNATING
       ========================================================= */

    QWidget#detail-row {{
        background: transparent;
        border-radius: {BorderRadius.SM};
    }}

    QWidget#detail-row:hover {{
        background: {c["bg_hover"]};
    }}

    QWidget#detail-row-alt {{
        background: {c["bg_main_gradient_end"]};
        border-radius: {BorderRadius.SM};
    }}

    QWidget#detail-row-alt:hover {{
        background: {c["bg_hover"]};
    }}


    /* =========================================================
       ROW ELEMENTS — ICON / SEP / KEY / VALUE
       ========================================================= */

    QLabel#detail-icon {{
        color: {c["text_secondary"]};
        background: transparent;
        font-size: {s["md"]}px;
    }}

    QLabel#detail-sep {{
        color: {c["text_muted"]};
        background: transparent;
        font-size: {s["base"]}px;
        font-weight: 400;
    }}

    QLabel#detail-key {{
        color: {c["text_secondary"]};
        background: transparent;
        font-size: {s["sm"]}px;
        font-weight: 600;
    }}

    QLabel#detail-key-financial {{
        color: {c["primary"]};
        background: transparent;
        font-size: {s["sm"]}px;
        font-weight: 700;
    }}

    QLabel#detail-value {{
        color: {c["text_primary"]};
        background: transparent;
        font-size: {s["base"]}px;
        font-weight: 400;
    }}

    QLabel#detail-value-financial {{
        color: {c["success"]};
        background: transparent;
        font-size: {s["base"]}px;
        font-weight: 700;
    }}


    /* =========================================================
       COPY BUTTON & TOAST
       ========================================================= */

    QToolButton#copy-btn {{
        background: {c["bg_hover"]};
        color: {c["text_muted"]};
        border: 1px solid {c["border_subtle"]};
        border-radius: {BorderRadius.SM};
        font-size: {s["sm"]}px;
    }}

    QToolButton#copy-btn:hover {{
        background: {c["primary_light"]};
        color: {c["primary"]};
        border-color: {c["primary"]};
    }}

    QToolButton#copy-btn:pressed {{
        background: {c["primary"]};
        color: {c["text_white"]};
    }}

    QLabel#copy-toast {{
        color: {c["success"]};
        background: {c["success_light"]};
        border: 1px solid {c["success"]};
        border-radius: {BorderRadius.SM};
        font-size: {s["sm"]}px;
        font-weight: 700;
        padding: 1px 4px;
    }}


    /* =========================================================
       BADGES — badge-{{value}} pattern
       ========================================================= */

    /* Active / Completed / Paid  →  green */
    QLabel[objectName="badge-active"],
    QLabel[objectName="badge-completed"],
    QLabel[objectName="badge-paid"] {{
        color: {c["success_active"]};
        background: {c["success_light"]};
        border: 1px solid {c["success"]};
        border-radius: {BorderRadius.FULL};
        font-size: {s["xs"]}px;
        font-weight: 700;
        padding: 2px 10px;
    }}

    /* Inactive / Cancelled / Rejected  →  red */
    QLabel[objectName="badge-inactive"],
    QLabel[objectName="badge-cancelled"],
    QLabel[objectName="badge-rejected"] {{
        color: {c["danger_active"]};
        background: {c["danger_light"]};
        border: 1px solid {c["danger"]};
        border-radius: {BorderRadius.FULL};
        font-size: {s["xs"]}px;
        font-weight: 700;
        padding: 2px 10px;
    }}

    /* Draft / Pending  →  orange */
    QLabel[objectName="badge-draft"],
    QLabel[objectName="badge-pending"] {{
        color: {c["warning_active"]};
        background: {c["warning_light"]};
        border: 1px solid {c["warning"]};
        border-radius: {BorderRadius.FULL};
        font-size: {s["xs"]}px;
        font-weight: 700;
        padding: 2px 10px;
    }}

    /* Import  →  blue */
    QLabel[objectName="badge-import"] {{
        color: {c["primary_active"]};
        background: {c["primary_lighter"]};
        border: 1px solid {c["primary"]};
        border-radius: {BorderRadius.FULL};
        font-size: {s["xs"]}px;
        font-weight: 700;
        padding: 2px 10px;
    }}

    /* Export  →  cyan / info */
    QLabel[objectName="badge-export"] {{
        color: {c["info_active"]};
        background: {c["info_light"]};
        border: 1px solid {c["info"]};
        border-radius: {BorderRadius.FULL};
        font-size: {s["xs"]}px;
        font-weight: 700;
        padding: 2px 10px;
    }}

    /* Transit  →  purple (fallback to primary-light) */
    QLabel[objectName="badge-transit"] {{
        color: #7B2D8B;
        background: rgba(123, 45, 139, 0.10);
        border: 1px solid rgba(123, 45, 139, 0.40);
        border-radius: {BorderRadius.FULL};
        font-size: {s["xs"]}px;
        font-weight: 700;
        padding: 2px 10px;
    }}
    """