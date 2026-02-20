from typing import Optional, Dict, Any, List

from database.models import get_session_local
from database.models.packaging_type import PackagingType
from database.crud.base_crud import BaseCRUD


class PackagingTypesCRUD(BaseCRUD):
    """
    Packaging Types CRUD adapted to the new BaseCRUD (stamping + audit).

    Changes vs your previous file:
    - Pass the *callable* get_session_local to BaseCRUD (not get_session_local()).
    - Forward the acting user to BaseCRUD via current_user so timestamps are
      stamped and audit rows are written.
    - Your schema uses created_by / updated_by (without *_id), so we also set
      those explicitly when user_id is provided.
    """

    def __init__(self):
        # IMPORTANT: pass the session factory, not an already-open session
        super().__init__(PackagingType, get_session_local)

    # -----------------------------
    # Create
    # -----------------------------
    def add_packaging_type(
        self,
        name_ar: str,
        name_en: str,
        name_tr: str,
        user_id: Optional[int] = None,
    ) -> PackagingType:
        obj = PackagingType(
            name_ar=name_ar,
            name_en=name_en,
            name_tr=name_tr,
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
    def get_packaging_type(self, pt_id: int) -> Optional[PackagingType]:
        return self.get(pt_id)

    def list_packaging_types(self, *, order_by=None) -> List[PackagingType]:
        return self.get_all(order_by=order_by)

    # -----------------------------
    # Update
    # -----------------------------
    def update_packaging_type(self, packaging_type_id: int, data: Dict[str, Any], user_id: Optional[int] = None) -> Optional[PackagingType]:
        payload = dict(data or {})
        if user_id is not None:
            # stamp updated_by for schemas without *_id
            if "updated_by" in PackagingType.__table__.c.keys():
                payload["updated_by"] = user_id
        return self.update(packaging_type_id, payload, current_user={"id": user_id} if user_id is not None else None)

    # -----------------------------
    # Delete
    # -----------------------------
    def delete_packaging_type(self, packaging_type_id: int, user_id: Optional[int] = None) -> bool:
        return self.delete(packaging_type_id, current_user={"id": user_id} if user_id is not None else None)
