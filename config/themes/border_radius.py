"""
Border Radius System — Unified 4-value scale
=============================================
القاعدة: 4 قيم فقط في كل التطبيق.
  SM  = 6px   → أزرار صغيرة، badges، chips
  MD  = 8px   → حقول إدخال، buttons، cards داخلية
  LG  = 12px  → cards رئيسية، dialogs داخلية، panels
  XL  = 18px  → dialogs خارجية، modals كبيرة
  FULL = 9999px → دائري (avatar, pill)
"""

class BorderRadius:
    NONE = "0"
    SM   = "6px"
    MD   = "8px"
    LG   = "12px"
    XL   = "18px"
    XXL  = "18px"   # alias — لا نستخدم 22px بعد الآن
    FULL = "9999px"

    @classmethod
    def get(cls, size: str) -> str:
        size_upper = size.upper()
        if hasattr(cls, size_upper):
            return getattr(cls, size_upper)
        return cls.MD


BORDER_RADIUS = BorderRadius
