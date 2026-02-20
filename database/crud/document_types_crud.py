"""
Document Types CRUD - LOGIPORT
Enhanced with logging and comprehensive error handling
"""
import logging
from typing import List, Optional, Dict, Any

from database.models import get_session_local
from database.models.document_type import DocumentType
from database.crud.base_crud import BaseCRUD

logger = logging.getLogger(__name__)


class DocumentTypesCRUD(BaseCRUD):
    """CRUD operations for document types with logging and error handling"""

    def __init__(self):
        super().__init__(DocumentType, get_session_local)
        logger.debug("DocumentTypesCRUD initialized")

    # -------- Reads --------
    def get_all_types(self, *, order_by=None) -> List[DocumentType]:
        """Get all document types"""
        try:
            logger.debug("Getting all document types")
            if order_by is None:
                order_by = DocumentType.id
            return self.get_all(order_by=order_by)
        except Exception as e:
            logger.error(f"Failed to get all document types: {e}")
            return []

    def get_by_id(self, type_id: int) -> Optional[DocumentType]:
        """Get document type by ID"""
        try:
            logger.debug(f"Getting document type id={type_id}")
            return self.get(type_id)
        except Exception as e:
            logger.error(f"Failed to get document type id={type_id}: {e}")
            return None

    def get_by_name(self, name_en: str) -> Optional[DocumentType]:
        """Get document type by English name"""
        try:
            logger.debug(f"Getting document type by name: {name_en}")
            results = self.filter_by(name_en=name_en)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Failed to get document type by name: {e}")
            return None

    # -------- Writes --------
    def add_document_type(
            self,
            name_ar: str,
            name_en: str,
            name_tr: str,
            user_id: Optional[int] = None,
    ) -> Optional[DocumentType]:
        """
        Add new document type.

        Args:
            name_ar: Arabic name
            name_en: English name
            name_tr: Turkish name
            user_id: Creator user ID

        Returns:
            Created DocumentType object or None if failed
        """
        try:
            logger.info(f"Creating document type: {name_en}")

            obj = DocumentType(
                name_ar=name_ar,
                name_en=name_en,
                name_tr=name_tr,
            )

            # Stamp creator/updater
            if user_id is not None:
                if hasattr(obj, "created_by"):
                    setattr(obj, "created_by", user_id)
                if hasattr(obj, "updated_by"):
                    setattr(obj, "updated_by", user_id)

            result = self.add(obj, current_user={"id": user_id} if user_id else None)

            if result:
                logger.info(f"Document type created successfully: id={result.id}, name={name_en}")

            return result

        except Exception as e:
            logger.error(f"Failed to create document type: {e}")
            return None

    def update_document_type(
            self,
            type_id: int,
            data: Dict[str, Any],
            user_id: Optional[int] = None
    ) -> Optional[DocumentType]:
        """
        Update document type.

        Args:
            type_id: Document type ID to update
            data: Dictionary of fields to update
            user_id: Updater user ID

        Returns:
            Updated DocumentType object or None if failed
        """
        try:
            payload = dict(data or {})

            logger.info(f"Updating document type id={type_id}")

            # Stamp updater
            if user_id is not None and "updated_by" in DocumentType.__table__.c.keys():
                payload["updated_by"] = user_id

            result = self.update(
                type_id,
                payload,
                current_user={"id": user_id} if user_id else None
            )

            if result:
                logger.info(f"Document type updated successfully: id={type_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to update document type id={type_id}: {e}")
            return None

    def delete_document_type(self, type_id: int, user_id: Optional[int] = None) -> bool:
        """
        Delete document type by ID.

        Args:
            type_id: Document type ID to delete
            user_id: Deleter user ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            logger.info(f"Deleting document type id={type_id}")

            result = self.delete(
                type_id,
                current_user={"id": user_id} if user_id else None
            )

            if result:
                logger.info(f"Document type deleted successfully: id={type_id}")
            else:
                logger.warning(f"Failed to delete document type id={type_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to delete document type id={type_id}: {e}")
            return False