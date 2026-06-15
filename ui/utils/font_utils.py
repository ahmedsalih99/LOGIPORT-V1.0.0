"""
ui/utils/font_utils.py — LOGIPORT
===================================
دالة مركزية لإنشاء QFont بناءً على إعدادات ThemeManager الحالية.

بدل:
    QFont("Tajawal", 9)          # ❌ hard-coded
    QFont("Tajawal", 14, Bold)   # ❌ hard-coded

استخدم:
    app_font()                   # ✅ حجم base
    app_font(scale=1.17, bold=True)  # ✅ عنوان

الـ scale يُحسب من base=12px (الافتراضي):
    xs   = 0.67  → 8px
    sm   = 0.75  → 9px
    body = 0.83  → 10px
    md   = 0.92  → 11px
    base = 1.0   → 12px
    lg   = 1.08  → 13px
    xl   = 1.17  → 14px
    xl2  = 1.25  → 15px
    xl3  = 1.67  → 20px
    xl4  = 1.83  → 22px
    hero = 2.33  → 28px
    logo = 3.0   → 36px

ملاحظة: QFont("Segoe UI Emoji", X) للأيقونات — يبقى ثابتاً عمداً (لا يتأثر بتغيير الخط).
"""
from __future__ import annotations
from PySide6.QtGui import QFont

# ثوابت الـ scale الشائعة — استخدمها بالاسم للوضوح
XS   = 0.67   # تفاصيل صغيرة جداً (badge, timestamp صغير)
SM   = 0.75   # نص ثانوي عادي
BODY = 0.83   # نص متوسط
MD   = 0.92   # نص أكبر قليلاً
BASE = 1.0    # حجم الـ base كما هو
LG   = 1.08   # عنوان صغير
XL   = 1.17   # عنوان متوسط
XL2  = 1.25   # عنوان كبير
XL3  = 1.67   # عنوان قسم رئيسي
XL4  = 1.83   # عنوان داشبورد
HERO = 2.33   # رقم KPI
LOGO = 3.0    # شعار / عنوان ضخم


def app_font(scale: float = BASE, bold: bool = False, weight: QFont.Weight | None = None) -> QFont:
    """
    ينشئ QFont مبني على الحجم الحالي من ThemeManager.

    المعاملات:
        scale   : نسبة الحجم من الـ base (استخدم ثوابت SM/BODY/XL... أو رقم مباشر)
        bold    : True لخط Bold
        weight  : QFont.Weight مخصص (يتجاوز bold إذا أُعطي)

    مثال:
        app_font(HERO, bold=True)           # رقم KPI كبير
        app_font(SM)                        # نص ثانوي
        app_font(XL, weight=QFont.DemiBold) # عنوان DemiBold
    """
    try:
        from core.theme_manager import ThemeManager
        tm = ThemeManager.get_instance()
        family = tm.get_current_font_family()
        base_size = tm.get_current_font_size()
    except Exception:
        family = "Tajawal"
        base_size = 12

    size = max(7, round(base_size * scale))
    f = QFont(family, size)

    if weight is not None:
        f.setWeight(weight)
    else:
        f.setBold(bold)

    return f