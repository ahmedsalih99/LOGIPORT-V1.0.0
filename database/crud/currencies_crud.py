from typing import Optional, Dict, Any, List

from database.models import get_session_local
from database.models.currency import Currency
from database.crud.base_crud import BaseCRUD


class CurrenciesCRUD(BaseCRUD):
    """
    Currencies CRUD adapted to the new BaseCRUD (stamping + audit).

    Changes vs your previous file:
    - Passes the *callable* get_session_local to BaseCRUD (not get_session_local()).
    - add/update/delete forward the acting user to BaseCRUD via current_user so
      timestamps are stamped and audit rows are written.
    - For your schema (created_by / updated_by without *_id), we also set those
      fields explicitly when user_id is provided.
    """

    def __init__(self):
        # IMPORTANT: pass the session factory, not an already-open session
        super().__init__(Currency, get_session_local)

    # -----------------------------
    # Create
    # -----------------------------
    def add_currency(
        self,
        name_ar: str,
        name_en: str,
        name_tr: str,
        symbol: Optional[str] = None,
        code: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Currency:
        obj = Currency(
            name_ar=name_ar,
            name_en=name_en,
            name_tr=name_tr,
            symbol=symbol,
            code=code,
        )
        # Stamp created_by/updated_by for schemas without *_id
        if user_id is not None:
            if hasattr(obj, "created_by") and getattr(obj, "created_by", None) in (None, 0, ""):
                setattr(obj, "created_by", user_id)
            if hasattr(obj, "updated_by"):
                setattr(obj, "updated_by", user_id)
        return self.add(obj, current_user={"id": user_id} if user_id is not None else None)

    # -----------------------------
    # Read helpers (optional)
    # -----------------------------
    def get_currency(self, currency_id: int) -> Optional[Currency]:
        return self.get(currency_id)

    def list_currencies(self, *, order_by=None) -> List[Currency]:
        return self.get_all(order_by=order_by)

    def get_by_code(self, code: str) -> Optional[Currency]:
        with self.session_factory() as s:
            return s.query(Currency).filter(Currency.code == code).one_or_none()

    # -----------------------------
    # Update
    # -----------------------------
    def update_currency(self, currency_id: int, data: Dict[str, Any], user_id: Optional[int] = None) -> Optional[Currency]:
        payload = dict(data or {})
        if user_id is not None:
            # stamp updated_by for schemas without *_id
            if "updated_by" in Currency.__table__.c.keys():
                payload["updated_by"] = user_id
        return self.update(currency_id, payload, current_user={"id": user_id} if user_id is not None else None)

    # -----------------------------
    # Delete
    # -----------------------------
    def delete_currency(self, currency_id: int, user_id: Optional[int] = None) -> bool:
        return self.delete(currency_id, current_user={"id": user_id} if user_id is not None else None)
