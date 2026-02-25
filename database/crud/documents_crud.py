"""
Documents CRUD - LOGIPORT
Simplified and enhanced with logging and comprehensive error handling
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from database.db_utils import utc_now

from database.models import get_session_local
from database.models.document import Document
from database.models.document_group import DocumentGroup
from database.models.document_type import DocumentType
from database.crud.base_crud import BaseCRUD
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class DocumentsCRUD(BaseCRUD):
    """CRUD operations for documents with logging and error handling"""

    def __init__(self):
        super().__init__(Document, get_session_local)
        logger.debug("DocumentsCRUD initialized")

    # -------- Document Groups --------
    def list_document_groups(self, *, active_only: bool = False) -> List[DocumentGroup]:
        """List document groups"""
        try:
            logger.debug(f"Listing document groups (active_only={active_only})")

            with self.get_session() as session:
                query = session.query(DocumentGroup)
                if active_only:
                    query = query.filter(DocumentGroup.is_active == True)
                query = query.order_by(DocumentGroup.sort_order.asc())
                return query.all()

        except Exception as e:
            logger.error(f"Failed to list document groups: {e}")
            return []

    def get_document_group(self, group_id: int) -> Optional[DocumentGroup]:
        """Get document group by ID"""
        try:
            logger.debug(f"Getting document group id={group_id}")

            with self.get_session() as session:
                return session.query(DocumentGroup).get(group_id)

        except Exception as e:
            logger.error(f"Failed to get document group: {e}")
            return None

    def get_group_by_code(self, code: str) -> Optional[DocumentGroup]:
        """Get document group by code"""
        try:
            logger.debug(f"Getting document group by code: {code}")

            with self.get_session() as session:
                return session.query(DocumentGroup).filter(
                    DocumentGroup.code == code
                ).first()

        except Exception as e:
            logger.error(f"Failed to get group by code: {e}")
            return None

    # -------- Document Types --------
    def list_document_types(self) -> List[DocumentType]:
        """List all document types"""
        try:
            logger.debug("Listing document types")

            with self.get_session() as session:
                return session.query(DocumentType).order_by(DocumentType.id.asc()).all()

        except Exception as e:
            logger.error(f"Failed to list document types: {e}")
            return []

    def get_document_type(self, type_id: int) -> Optional[DocumentType]:
        """Get document type by ID"""
        try:
            logger.debug(f"Getting document type id={type_id}")

            with self.get_session() as session:
                return session.query(DocumentType).get(type_id)

        except Exception as e:
            logger.error(f"Failed to get document type: {e}")
            return None

    # -------- Documents --------
    def create_document(
            self,
            document_number: str,
            document_type_id: int,
            document_group_id: int,
            transaction_id: Optional[int] = None,
            issue_date: Optional[datetime] = None,
            notes: Optional[str] = None,
            user_id: Optional[int] = None,
    ) -> Optional[Document]:
        """
        Create new document.

        Args:
            document_number: Document number
            document_type_id: Document type ID
            document_group_id: Document group ID
            transaction_id: Related transaction ID
            issue_date: Document issue date
            notes: Additional notes
            user_id: Creator user ID

        Returns:
            Created Document object or None if failed
        """
        try:
            logger.info(f"Creating document: {document_number}")

            doc = Document(
                document_number=document_number,
                document_type_id=document_type_id,
                document_group_id=document_group_id,
                transaction_id=transaction_id,
                issue_date=issue_date or utc_now(),
                notes=notes,
            )

            result = self.add(doc, current_user={"id": user_id} if user_id else None)

            if result:
                logger.info(f"Document created successfully: id={result.id}, number={document_number}")

            return result

        except IntegrityError as e:
            logger.error(f"Document number already exists or constraint violation: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            return None

    def get_document(self, document_id: int) -> Optional[Document]:
        """Get document by ID"""
        try:
            logger.debug(f"Getting document id={document_id}")
            return self.get(document_id)
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None

    def get_by_number(self, document_number: str) -> Optional[Document]:
        """Get document by number"""
        try:
            logger.debug(f"Getting document by number: {document_number}")

            with self.get_session() as session:
                return session.query(Document).filter(
                    Document.document_number == document_number
                ).first()

        except Exception as e:
            logger.error(f"Failed to get document by number: {e}")
            return None

    def list_documents(
            self,
            *,
            transaction_id: Optional[int] = None,
            document_type_id: Optional[int] = None,
            document_group_id: Optional[int] = None,
            limit: int = 100
    ) -> List[Document]:
        """
        List documents with optional filters.

        Args:
            transaction_id: Filter by transaction
            document_type_id: Filter by type
            document_group_id: Filter by group
            limit: Maximum results

        Returns:
            List of documents
        """
        try:
            logger.debug(
                f"Listing documents (filters: trans={transaction_id}, type={document_type_id}, group={document_group_id})")

            with self.get_session() as session:
                query = session.query(Document)

                if transaction_id:
                    query = query.filter(Document.transaction_id == transaction_id)
                if document_type_id:
                    query = query.filter(Document.document_type_id == document_type_id)
                if document_group_id:
                    query = query.filter(Document.document_group_id == document_group_id)

                query = query.order_by(Document.issue_date.desc())
                query = query.limit(limit)

                return query.all()

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []

    def update_document(
            self,
            document_id: int,
            data: Dict[str, Any],
            user_id: Optional[int] = None
    ) -> Optional[Document]:
        """
        Update document.

        Args:
            document_id: Document ID to update
            data: Dictionary of fields to update
            user_id: Updater user ID

        Returns:
            Updated Document object or None if failed
        """
        try:
            logger.info(f"Updating document id={document_id}")

            result = self.update(
                document_id,
                data,
                current_user={"id": user_id} if user_id else None
            )

            if result:
                logger.info(f"Document updated successfully: id={document_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            return None

    def delete_document(self, document_id: int, user_id: Optional[int] = None) -> bool:
        """
        Delete document by ID.

        Args:
            document_id: Document ID to delete
            user_id: Deleter user ID

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            logger.info(f"Deleting document id={document_id}")

            result = self.delete(
                document_id,
                current_user={"id": user_id} if user_id else None
            )

            if result:
                logger.info(f"Document deleted successfully: id={document_id}")
            else:
                logger.warning(f"Failed to delete document id={document_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False