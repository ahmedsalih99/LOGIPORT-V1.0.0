from typing import Optional, Dict, Any, List

from database.models import get_session_local, Material  # تأكد أن Material مضاف في database.models
from database.crud.base_crud import BaseCRUD


class MaterialsCRUD(BaseCRUD):
    """
    Materials CRUD على نمط CountriesCRUD:
    - passing session factory (get_session_local) إلى BaseCRUD
    - stamping created_by/updated_by إذا كانت الحقول بدون *_id أو معها
    """

    def __init__(self):
        super().__init__(Material, get_session_local)

    # Create
    def add_material(
        self,
        *,
        code: str,
        name_ar: str,
        name_en: Optional[str] = None,
        name_tr: Optional[str] = None,
        material_type_id: int,
        estimated_price: Optional[float] = None,
        currency_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Material:
        obj = Material(
            code=code,
            name_ar=name_ar,
            name_en=name_en,
            name_tr=name_tr,
            material_type_id=material_type_id,
            estimated_price=estimated_price,
            currency_id=currency_id,
        )

        # stamp created_by/updated_by سواء كانت *_id أو بدونها
        cols = set(getattr(Material, "__table__").c.keys())
        if user_id is not None:
            if "created_by_id" in cols and getattr(obj, "created_by_id", None) in (None, 0, ""):
                obj.created_by_id = user_id
            elif "created_by" in cols and getattr(obj, "created_by", None) in (None, 0, ""):
                obj.created_by = user_id
            if "updated_by_id" in cols:
                obj.updated_by_id = user_id
            elif "updated_by" in cols:
                obj.updated_by = user_id

        # قاعدة العمل: إذا في سعر لازم عملة (نخلّي Base/DB تتحقق أيضًا لو عندك constraint)
        if obj.estimated_price is not None and obj.currency_id is None:
            raise ValueError("currency_id is required when estimated_price is provided")

        return self.add(obj, current_user={"id": user_id} if user_id is not None else None)

    # Read helpers
    def get_material(self, material_id: int) -> Optional[Material]:
        return self.get(material_id)

    def list_materials(self, *, order_by=None) -> List[Material]:
        return self.get_all(order_by=order_by)

    # Update
    def update_material(self, material_id: int, data: Dict[str, Any], user_id: Optional[int] = None) -> Optional[Material]:
        payload = dict(data or {})

        # قاعدة العمل
        if payload.get("estimated_price") is not None and payload.get("currency_id") is None:
            # إذا جاء سعر بدون عملة في الداتا المرسلة
            raise ValueError("currency_id is required when estimated_price is provided")

        # stamping updated_by (يدعم *_id أو بدونها)
        cols = set(getattr(Material, "__table__").c.keys())
        if user_id is not None:
            if "updated_by_id" in cols:
                payload["updated_by_id"] = user_id
            elif "updated_by" in cols:
                payload["updated_by"] = user_id

        return self.update(material_id, payload, current_user={"id": user_id} if user_id is not None else None)

    # Delete
    def delete_material(self, material_id: int, user_id: Optional[int] = None) -> bool:
        return self.delete(material_id, current_user={"id": user_id} if user_id is not None else None)
