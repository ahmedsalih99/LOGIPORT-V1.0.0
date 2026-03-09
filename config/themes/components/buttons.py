"""
Button Component Styles - Unified
==================================
مرجع موحّد لكل أنواع الأزرار في التطبيق.
قواعد:
  ✔ لا geometry (لا width/height/min/max) إلا ما يلزم للـ icon-btn
  ✔ كل اسم مُستخدَم في الكود موجود هنا
  ✔ لا تعريفات مكررة

أسماء الأزرار المعرّفة:
  primary-btn / btn-primary   → أزرار الإجراء الرئيسي (حفظ، تأكيد)
  secondary-btn               → أزرار ثانوية (إلغاء، رجوع)
  secondary-btn-small         → secondary بحجم صغير
  danger-btn  / btn-danger    → حذف، خطر
  success-btn                 → تفعيل، موافقة
  warning-btn / btn-warning   → تحذير، إغلاق
  muted-btn                   → أرشفة، إجراءات خافتة
  action-btn                  → زر رئيسي في شريط أدوات التابات
  table-edit                  → تعديل داخل الجدول
  table-delete                → حذف داخل الجدول
  icon-btn                    → زر أيقونة بدون نص
  toolbar-btn                 → أزرار الـ topbar
  filter-preset-btn           → أزرار الفلتر السريع (checkable)
  filter-clear-btn            → مسح الفلتر
  link-btn                    → رابط نصي
"""

from ..spacing import Spacing
from ..border_radius import BorderRadius


def get_styles(theme):
    c = theme.colors
    s = theme.sizes

    # padding موحّد
    PAD_MD   = "5px 14px"
    PAD_SM   = "3px 10px"
    PAD_XS   = "2px 7px"
    R        = BorderRadius.MD
    R_SM     = BorderRadius.SM

    return f"""
    /* ═══════════════════════════════════════════════════════════════════
       BASE — كل زر غير معرّف يأخذ هذا
    ═══════════════════════════════════════════════════════════════════ */
    QPushButton {{
        background   : {c["bg_secondary"]};
        color        : {c["text_primary"]};
        border       : 1px solid {c["border"]};
        border-radius: {R};
        padding      : {PAD_MD};
        font-size    : {s["base"]}px;
        font-weight  : 500;
    }}
    QPushButton:hover {{
        background  : {c["bg_hover"]};
        border-color: {c["border_hover"]};
    }}
    QPushButton:pressed {{
        background  : {c["bg_active"]};
    }}
    QPushButton:disabled {{
        background  : {c["bg_disabled"]};
        color       : {c["text_disabled"]};
        border-color: {c["border"]};
    }}

    /* ═══════════════════════════════════════════════════════════════════
       PRIMARY — الإجراء الرئيسي (حفظ، إنشاء، تأكيد)
       مستخدَم كـ: primary-btn  |  btn-primary  |  action-btn
    ═══════════════════════════════════════════════════════════════════ */
    QPushButton#primary-btn,
    QPushButton#btn-primary,
    QPushButton#action-btn {{
        background   : {c["primary"]};
        color        : {c["text_white"]};
        border       : none;
        border-radius: {R};
        font-weight  : 600;
        padding      : {PAD_MD};
    }}
    QPushButton#primary-btn:hover,
    QPushButton#btn-primary:hover,
    QPushButton#action-btn:hover {{
        background: {c["primary_hover"]};
    }}
    QPushButton#primary-btn:pressed,
    QPushButton#btn-primary:pressed,
    QPushButton#action-btn:pressed {{
        background: {c["primary_active"]};
    }}
    QPushButton#primary-btn:disabled,
    QPushButton#btn-primary:disabled,
    QPushButton#action-btn:disabled {{
        background: {c["bg_disabled"]};
        color     : {c["text_disabled"]};
    }}

    /* ═══════════════════════════════════════════════════════════════════
       SECONDARY — الإجراءات الثانوية (إلغاء، رجوع)
    ═══════════════════════════════════════════════════════════════════ */
    QPushButton#secondary-btn {{
        background   : transparent;
        color        : {c["text_secondary"]};
        border       : 1px solid {c["border"]};
        border-radius: {R};
        padding      : {PAD_MD};
    }}
    QPushButton#secondary-btn:hover {{
        background  : {c["bg_hover"]};
        color       : {c["text_primary"]};
        border-color: {c["border_hover"]};
    }}
    QPushButton#secondary-btn:pressed {{
        background: {c["bg_active"]};
    }}

    QPushButton#secondary-btn-small {{
        background   : transparent;
        color        : {c["text_secondary"]};
        border       : 1px solid {c["border"]};
        border-radius: {R_SM};
        padding      : {PAD_XS};
        font-size    : {s["sm"]}px;
    }}
    QPushButton#secondary-btn-small:hover {{
        background  : {c["bg_hover"]};
        color       : {c["text_primary"]};
        border-color: {c["border_hover"]};
    }}

    /* ═══════════════════════════════════════════════════════════════════
       DANGER — حذف، إجراءات لا رجعة فيها
       مستخدَم كـ: danger-btn  |  btn-danger
    ═══════════════════════════════════════════════════════════════════ */
    QPushButton#danger-btn,
    QPushButton#btn-danger {{
        background   : {c["danger"]};
        color        : {c["text_white"]};
        border       : none;
        border-radius: {R};
        font-weight  : 600;
        padding      : {PAD_MD};
    }}
    QPushButton#danger-btn:hover,
    QPushButton#btn-danger:hover {{
        background: {c["danger_hover"]};
    }}
    QPushButton#danger-btn:pressed,
    QPushButton#btn-danger:pressed {{
        background: {c["danger_active"]};
    }}

    /* ═══════════════════════════════════════════════════════════════════
       SUCCESS — تفعيل، موافقة
    ═══════════════════════════════════════════════════════════════════ */
    QPushButton#success-btn {{
        background   : {c["success"]};
        color        : {c["text_white"]};
        border       : none;
        border-radius: {R};
        font-weight  : 600;
        padding      : {PAD_MD};
    }}
    QPushButton#success-btn:hover  {{ background: {c["success_hover"]}; }}
    QPushButton#success-btn:pressed {{ background: {c["success_active"]}; }}

    /* ═══════════════════════════════════════════════════════════════════
       WARNING — تحذير، إغلاق
       مستخدَم كـ: warning-btn  |  btn-warning
    ═══════════════════════════════════════════════════════════════════ */
    QPushButton#warning-btn,
    QPushButton#btn-warning {{
        background   : {c["warning"]};
        color        : {c["text_white"]};
        border       : none;
        border-radius: {R};
        font-weight  : 600;
        padding      : {PAD_MD};
    }}
    QPushButton#warning-btn:hover,
    QPushButton#btn-warning:hover  {{ background: {c["warning_hover"]}; }}
    QPushButton#warning-btn:pressed,
    QPushButton#btn-warning:pressed {{ background: {c["warning_active"]}; }}

    /* ═══════════════════════════════════════════════════════════════════
       MUTED — أرشفة، إجراءات غير أساسية
    ═══════════════════════════════════════════════════════════════════ */
    QPushButton#muted-btn {{
        background   : {c["bg_secondary"]};
        color        : {c["text_secondary"]};
        border       : 1px solid {c["border"]};
        border-radius: {R};
        padding      : {PAD_MD};
        font-weight  : 500;
    }}
    QPushButton#muted-btn:hover {{
        background  : {c["bg_hover"]};
        color       : {c["text_primary"]};
    }}

    /* ═══════════════════════════════════════════════════════════════════
       TABLE BUTTONS — أزرار داخل صفوف الجدول
    ═══════════════════════════════════════════════════════════════════ */
    QTableWidget QPushButton,
    QTableView  QPushButton {{
        padding      : {PAD_XS};
        font-size    : {s["sm"]}px;
        border-radius: {R_SM};
        font-weight  : 500;
    }}

    /* edit */
    QPushButton#table-edit,
    QTableWidget QPushButton#table-edit,
    QTableView  QPushButton#table-edit {{
        background   : transparent;
        color        : {c["primary"]};
        border       : 1px solid {c["primary"]};
        border-radius: {R_SM};
        font-weight  : 600;
        font-size    : {s["sm"]}px;
        padding      : {PAD_XS};
    }}
    QPushButton#table-edit:hover,
    QTableWidget QPushButton#table-edit:hover,
    QTableView  QPushButton#table-edit:hover {{
        background: {c["primary_light"]};
    }}
    QPushButton#table-edit:pressed,
    QTableWidget QPushButton#table-edit:pressed,
    QTableView  QPushButton#table-edit:pressed {{
        background: {c["primary_lighter"]};
    }}

    /* delete */
    QPushButton#table-delete,
    QTableWidget QPushButton#table-delete,
    QTableView  QPushButton#table-delete {{
        background   : transparent;
        color        : {c["danger"]};
        border       : 1px solid {c["danger"]};
        border-radius: {R_SM};
        font-weight  : 600;
        font-size    : {s["sm"]}px;
        padding      : {PAD_XS};
    }}
    QPushButton#table-delete:hover,
    QTableWidget QPushButton#table-delete:hover,
    QTableView  QPushButton#table-delete:hover {{
        background: {c["danger_light"]};
    }}
    QPushButton#table-delete:pressed,
    QTableWidget QPushButton#table-delete:pressed,
    QTableView  QPushButton#table-delete:pressed {{
        background: {c["danger_light"]};
    }}

    /* ═══════════════════════════════════════════════════════════════════
       ICON BUTTON — زر أيقونة بدون نص
    ═══════════════════════════════════════════════════════════════════ */
    QPushButton#icon-btn {{
        background   : transparent;
        border       : none;
        padding      : {Spacing.SM};
        border-radius: {R_SM};
    }}
    QPushButton#icon-btn:hover {{
        background: {c["bg_hover"]};
    }}

    /* ═══════════════════════════════════════════════════════════════════
       TOPBAR — أزرار شريط العنوان
    ═══════════════════════════════════════════════════════════════════ */
    QPushButton#toolbar-btn {{
        background: transparent;
        border    : 1px solid transparent;
        padding   : {Spacing.SM} {Spacing.MD};
    }}
    QPushButton#toolbar-btn:hover {{
        background  : {c["bg_hover"]};
        border-color: {c["border"]};
    }}

    /* ═══════════════════════════════════════════════════════════════════
       LINK BUTTON
    ═══════════════════════════════════════════════════════════════════ */
    QPushButton#link-btn {{
        background     : transparent;
        color          : {c["primary"]};
        border         : none;
        text-decoration: underline;
        padding        : 0;
        font-weight    : 500;
    }}
    QPushButton#link-btn:hover {{
        color: {c["primary_hover"]};
    }}
    """