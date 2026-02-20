"""
Countries CRUD - LOGIPORT
Enhanced with logging and better error handling
"""
import logging
from typing import Optional, Dict, Any, List

from database.models import get_session_local, Country
from database.crud.base_crud import BaseCRUD

logger = logging.getLogger(__name__)


class CountriesCRUD(BaseCRUD):
    """CRUD operations for countries with automatic uppercase conversion"""

    def __init__(self):
        super().__init__(Country, get_session_local)
        logger.debug("CountriesCRUD initialized")

    # -----------------------------
    # Helpers
    # -----------------------------
    @staticmethod
    def _uppercase(value: Any) -> Optional[str]:
        """Convert string to uppercase, strip whitespace"""
        if isinstance(value, str):
            value = value.strip()
            return value.upper() if value else None
        return value

    # -----------------------------
    # Create
    # -----------------------------
    def add_country(
            self,
            name_ar: str,
            name_en: str,
            name_tr: str,
            code: Optional[str] = None,
            user_id: Optional[int] = None,
    ) -> Optional[Country]:
        """
        Add new country with automatic uppercase conversion.

        Args:
            name_ar: Arabic name
            name_en: English name
            name_tr: Turkish name
            code: Country code (optional)
            user_id: Creator user ID

        Returns:
            Created Country object or None if failed
        """
        try:
            # Apply uppercase conversion
            name_ar = self._uppercase(name_ar)
            name_en = self._uppercase(name_en)
            name_tr = self._uppercase(name_tr)
            code = self._uppercase(code)

            logger.info(f"Creating country: {name_en} ({code})")

            obj = Country(
                name_ar=name_ar,
                name_en=name_en,
                name_tr=name_tr,
                code=code,
            )

            # Stamp creator/updater
            if user_id is not None:
                if hasattr(obj, "created_by") and getattr(obj, "created_by", None) in (None, 0, ""):
                    setattr(obj, "created_by", user_id)
                if hasattr(obj, "updated_by"):
                    setattr(obj, "updated_by", user_id)

            result = self.add(obj, current_user={"id": user_id} if user_id is not None else None)

            if result:
                logger.info(f"Country created successfully: id={result.id}, name={name_en}")

            return result

        except Exception as e:
            logger.error(f"Failed to create country: {e}")
            return None

    # -----------------------------
    # Read helpers
    # -----------------------------
    def get_country(self, country_id: int) -> Optional[Country]:
        """Get country by ID"""
        try:
            logger.debug(f"Getting country id={country_id}")
            return self.get(country_id)
        except Exception as e:
            logger.error(f"Failed to get country id={country_id}: {e}")
            return None

    def list_countries(self, *, order_by=None) -> List[Country]:
        """List all countries"""
        try:
            logger.debug("Listing all countries")
            return self.get_all(order_by=order_by)
        except Exception as e:
            logger.error(f"Failed to list countries: {e}")
            return []

    # -----------------------------
    # Update
    # -----------------------------
    def update_country(
            self,
            country_id: int,
            data: Dict[str, Any],
            user_id: Optional[int] = None
    ) -> Optional[Country]:
        """
        Update country with automatic uppercase conversion.

        Args:
            country_id: Country ID to update
            data: Dictionary of fields to update
            user_id: Updater user ID

        Returns:
            Updated Country object or None if failed
        """
        try:
            payload = dict(data or {})

            logger.info(f"Updating country id={country_id}")

            # Apply uppercase to text fields
            for k in ("name_ar", "name_en", "name_tr", "code"):
                if k in payload:
                    payload[k] = self._uppercase(payload[k])

            # Stamp updater
            if user_id is not None and "updated_by" in Country.__table__.c.keys():
                payload["updated_by"] = user_id

            result = self.update(
                country_id,
                payload,
                current_user={"id": user_id} if user_id is not None else None
            )

            if result:
                logger.info(f"Country updated successfully: id={country_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to update country id={country_id}: {e}")
            return None

    # -----------------------------
    # Delete
    # -----------------------------
    def delete_country(self, country_id: int, user_id: Optional[int] = None) -> bool:
        """
        Delete country by ID.

        Args:
            country_id: Country ID to delete
            user_id: Deleter user ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            logger.info(f"Deleting country id={country_id}")

            result = self.delete(
                country_id,
                current_user={"id": user_id} if user_id is not None else None
            )

            if result:
                logger.info(f"Country deleted successfully: id={country_id}")
            else:
                logger.warning(f"Failed to delete country id={country_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to delete country id={country_id}: {e}")
            return False