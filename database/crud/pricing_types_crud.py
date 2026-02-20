"""
Pricing Types CRUD - LOGIPORT
Enhanced with logging and comprehensive error handling
"""
import logging
from typing import List, Optional

from database.models import get_session_local
from database.models.pricing_type import PricingType
from database.crud.base_crud import BaseCRUD

logger = logging.getLogger(__name__)


class PricingTypesCRUD(BaseCRUD):
    """CRUD operations for pricing types with logging and error handling"""

    def __init__(self):
        super().__init__(PricingType, get_session_local)
        logger.debug("PricingTypesCRUD initialized")

    # -------- Reads --------
    def get_all_types(self, *, active_only: bool = False) -> List[PricingType]:
        """Get all pricing types, optionally filtered by active status"""
        try:
            logger.debug(f"Getting pricing types (active_only={active_only})")

            with self.get_session() as session:
                query = session.query(PricingType)
                if active_only:
                    query = query.filter(PricingType.is_active == True)
                query = query.order_by(PricingType.sort_order.asc(), PricingType.id.asc())
                return query.all()

        except Exception as e:
            logger.error(f"Failed to get pricing types: {e}")
            return []

    def get_by_code(self, code: str) -> Optional[PricingType]:
        """Get pricing type by code"""
        try:
            logger.debug(f"Getting pricing type by code: {code}")

            with self.get_session() as session:
                return session.query(PricingType).filter(PricingType.code == code).first()

        except Exception as e:
            logger.error(f"Failed to get pricing type by code {code}: {e}")
            return None

    def get_by_id(self, type_id: int) -> Optional[PricingType]:
        """Get pricing type by ID"""
        try:
            logger.debug(f"Getting pricing type id={type_id}")
            return self.get(type_id)
        except Exception as e:
            logger.error(f"Failed to get pricing type id={type_id}: {e}")
            return None

    # -------- Writes --------
    def add_pricing_type(
            self,
            code: str,
            name_ar: str,
            name_en: Optional[str] = None,
            name_tr: Optional[str] = None,
            is_active: bool = True,
            sort_order: int = 100,
            user_id: Optional[int] = None
    ) -> Optional[PricingType]:
        """
        Add new pricing type.

        Args:
            code: Unique code for pricing type
            name_ar: Arabic name
            name_en: English name
            name_tr: Turkish name
            is_active: Whether the type is active
            sort_order: Display order
            user_id: Creator user ID

        Returns:
            Created PricingType object or None if failed
        """
        try:
            logger.info(f"Creating pricing type: {code} ({name_en or name_ar})")

            obj = PricingType(
                code=code,
                name_ar=name_ar,
                name_en=name_en,
                name_tr=name_tr,
                is_active=is_active,
                sort_order=sort_order
            )

            result = self.add(obj, current_user={"id": user_id} if user_id else None)

            if result:
                logger.info(f"Pricing type created successfully: id={result.id}, code={code}")

            return result

        except Exception as e:
            logger.error(f"Failed to create pricing type: {e}")
            return None

    def update_pricing_type(
            self,
            type_id: int,
            user_id: Optional[int] = None,
            **fields
    ) -> Optional[PricingType]:
        """
        Update pricing type.

        Args:
            type_id: Pricing type ID to update
            user_id: Updater user ID
            **fields: Fields to update

        Returns:
            Updated PricingType object or None if failed
        """
        try:
            logger.info(f"Updating pricing type id={type_id}")

            result = self.update(
                type_id,
                fields,
                current_user={"id": user_id} if user_id else None
            )

            if result:
                logger.info(f"Pricing type updated successfully: id={type_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to update pricing type id={type_id}: {e}")
            return None