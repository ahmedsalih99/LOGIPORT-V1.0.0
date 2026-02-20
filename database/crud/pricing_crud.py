from typing import Optional, Dict, Any, List
from decimal import Decimal

from database.models import get_session_local
from database.crud.base_crud_v5 import BaseCRUD_V5 as BaseCRUD
from database.models.pricing import Pricing

class PricingCRUD(BaseCRUD):
    """
    CRUD for Pricing with duplicate-prevention on the exact key:
    (seller_company_id, buyer_company_id, material_id, pricing_type_id, currency_id, delivery_method_id)
    """
    def __init__(self):
        super().__init__(Pricing, get_session_local)

    def _SessionLocal(self):
        factory = self.session_factory
        return factory() if callable(factory) else factory

    # Validation helpers
    def _validate_payload(self, data: Dict[str, Any]):
        req = ["seller_company_id", "buyer_company_id", "material_id", "pricing_type_id", "currency_id", "price"]
        missing = [k for k in req if not data.get(k)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        try:
            price = Decimal(str(data.get("price")))
            if price <= 0:
                raise ValueError
        except Exception:
            raise ValueError("Price must be a positive number")

    def _exists_duplicate(self, s, *, seller_company_id: int, buyer_company_id: int, material_id: int,
                          pricing_type_id: int, currency_id: int, delivery_method_id: Optional[int],
                          exclude_id: Optional[int] = None) -> bool:
        q = s.query(Pricing).filter(
            Pricing.seller_company_id == seller_company_id,
            Pricing.buyer_company_id == buyer_company_id,
            Pricing.material_id == material_id,
            Pricing.pricing_type_id == pricing_type_id,
            Pricing.currency_id == currency_id,
            (Pricing.delivery_method_id == delivery_method_id) if delivery_method_id is not None else (Pricing.delivery_method_id.is_(None))
        )
        if exclude_id:
            q = q.filter(Pricing.id != exclude_id)
        return s.query(q.exists()).scalar()

    # Create
    def add_pricing(self, data: Dict[str, Any], user_id: Optional[int] = None) -> Pricing:
        self._validate_payload(data or {})
        payload = dict(data)

        with self.get_session() as s:
            if self._exists_duplicate(
                s,
                seller_company_id=payload["seller_company_id"],
                buyer_company_id=payload["buyer_company_id"],
                material_id=payload["material_id"],
                pricing_type_id=payload["pricing_type_id"],
                currency_id=payload["currency_id"],
                delivery_method_id=payload.get("delivery_method_id"),
            ):
                raise ValueError("Duplicate pricing record for the same key")

            obj = Pricing(**payload)
            if user_id:
                if getattr(obj, "created_by_id", None) in (None, 0, ""):
                    obj.created_by_id = user_id
                obj.updated_by_id = user_id
            s.add(obj)
            s.commit()
            s.refresh(obj)
            return obj

    # Read
    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Pricing]:
        with self.get_session() as s:
            q = s.query(Pricing)
            f = filters or {}
            if f.get("seller_company_id"):
                q = q.filter(Pricing.seller_company_id == f["seller_company_id"])
            if f.get("buyer_company_id"):
                q = q.filter(Pricing.buyer_company_id == f["buyer_company_id"])
            if f.get("material_id"):
                q = q.filter(Pricing.material_id == f["material_id"])
            if f.get("pricing_type_id"):
                q = q.filter(Pricing.pricing_type_id == f["pricing_type_id"])
            if f.get("currency_id"):
                q = q.filter(Pricing.currency_id == f["currency_id"])
            if "is_active" in f and f["is_active"] is not None:
                q = q.filter(Pricing.is_active == bool(f["is_active"]))
            if f.get("delivery_method_id") is not None:
                q = q.filter(Pricing.delivery_method_id == f["delivery_method_id"])
            q = q.order_by(Pricing.id.desc())
            return q.all()

    # Update
    def update_pricing(self, pricing_id: int, data: Dict[str, Any], user_id: Optional[int] = None):
        payload = dict(data or {})
        if "price" in payload:
            try:
                if Decimal(str(payload["price"])) <= 0:
                    raise ValueError
            except Exception:
                raise ValueError("Price must be a positive number")

        with self.get_session() as s:
            obj = s.get(Pricing, pricing_id)
            if not obj:
                return None

            candidate = {
                "seller_company_id": payload.get("seller_company_id", obj.seller_company_id),
                "buyer_company_id":  payload.get("buyer_company_id",  obj.buyer_company_id),
                "material_id":       payload.get("material_id",       obj.material_id),
                "pricing_type_id":   payload.get("pricing_type_id",   obj.pricing_type_id),
                "currency_id":       payload.get("currency_id",       obj.currency_id),
                "delivery_method_id":payload.get("delivery_method_id",obj.delivery_method_id),
            }
            if self._exists_duplicate(s, **candidate, exclude_id=obj.id):
                raise ValueError("Duplicate pricing record for the same key")

            for k, v in payload.items():
                if hasattr(obj, k):
                    setattr(obj, k, v)
            if user_id:
                obj.updated_by_id = user_id
            s.commit()
            s.refresh(obj)
            return obj

    # Delete
    def delete_pricing(self, pricing_id: int) -> bool:
        return self.delete(pricing_id)