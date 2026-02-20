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
        lst = self.crud.list({
            "seller_company_id": seller_company_id,
            "buyer_company_id": buyer_company_id,
            "material_id": material_id,
            "pricing_type_id": pricing_type_id,
            "currency_id": currency_id,
            "delivery_method_id": delivery_method_id,
            "is_active": True
        })
        if lst:
            return lst[0]
        if delivery_method_id is not None:
            lst = self.crud.list({
                "seller_company_id": seller_company_id,
                "buyer_company_id": buyer_company_id,
                "material_id": material_id,
                "pricing_type_id": pricing_type_id,
                "currency_id": currency_id,
                "delivery_method_id": None,
                "is_active": True
            })
            if lst:
                return lst[0]
        return None