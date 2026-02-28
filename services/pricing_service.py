from typing import Optional
from database.crud.pricing_crud import PricingCRUD

class PricingService:
    """
    Selection logic to retrieve the appropriate price (no validity dates).
    Exact-key match; fallback: ignore delivery_method if provided and no match.
    """
    def __init__(self):
        self.crud = PricingCRUD()

    def find_best_price(self, *, seller_company_id: int, buyer_company_id: int, material_id: int,
                        pricing_type_id: int, currency_id: int, delivery_method_id: Optional[int] = None):
        """
        أولوية البحث:
        1. مطابقة كاملة: seller+buyer+material+ptype+currency+dm
        2. نفس الشيء لكن بدون dm (dm=NULL في DB)
        3. أي سعر بدون قيد على seller أو buyer (فقط material+ptype+currency)
        """
        base = {
            "seller_company_id": seller_company_id,
            "buyer_company_id":  buyer_company_id,
            "material_id":       material_id,
            "pricing_type_id":   pricing_type_id,
            "currency_id":       currency_id,
            "is_active":         True,
        }

        # 1. مطابقة تامة مع delivery_method
        if delivery_method_id is not None:
            lst = self.crud.list({**base, "delivery_method_id": delivery_method_id})
            if lst:
                return lst[0]

        # 2. نفس seller+buyer+material+ptype+currency بدون قيد dm
        lst = self.crud.list(base)   # بدون "delivery_method_id" → يجيب الكل ثم نفلتر يدوياً
        # فلتر: نفضل dm=None أولاً ثم أي dm
        no_dm = [p for p in lst if getattr(p, "delivery_method_id", None) is None]
        if no_dm:
            return no_dm[0]
        if lst:
            return lst[0]   # أي سعر متطابق حتى لو dm مختلف

        return None