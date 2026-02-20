"""
Audit Log CRUD - LOGIPORT
Enhanced with logging and comprehensive error handling
"""
import logging
from typing import Optional

from database.models import get_session_local
from database.models.audit_log import AuditLog
from database.crud.base_crud import BaseCRUD

logger = logging.getLogger(__name__)


class AuditLogCRUD(BaseCRUD):
    """CRUD operations for audit logs with logging and error handling"""

    def __init__(self):
        # Pass callable, not instance
        super().__init__(AuditLog, get_session_local)
        logger.debug("AuditLogCRUD initialized")

    def log_action(
            self,
            user_id: Optional[int],
            action: str,
            table_name: str,
            record_id: Optional[int] = None,
            details: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        Log an action to audit log.

        Args:
            user_id: User ID who performed the action
            action: Action performed (e.g., 'CREATE', 'UPDATE', 'DELETE')
            table_name: Table name where action occurred
            record_id: Record ID affected (optional)
            details: Additional details (optional)

        Returns:
            Created AuditLog object or None if failed
        """
        try:
            logger.debug(f"Logging action: {action} on {table_name} by user={user_id}")

            log = AuditLog(
                user_id=user_id,
                action=action,
                table_name=table_name,
                record_id=record_id,
                details=details
            )

            result = self.add(log, current_user={"id": user_id} if user_id else None)

            if result:
                logger.debug(f"Action logged: id={result.id}")

            return result

        except Exception as e:
            logger.error(f"Failed to log action: {e}")
            return None

    def get_logs_by_user(self, user_id: int, limit: int = 100):
        """Get audit logs for specific user"""
        try:
            logger.debug(f"Getting audit logs for user_id={user_id}")
            return self.filter_by(user_id=user_id)[:limit]
        except Exception as e:
            logger.error(f"Failed to get logs for user: {e}")
            return []

    def get_logs_by_table(self, table_name: str, limit: int = 100):
        """Get audit logs for specific table"""
        try:
            logger.debug(f"Getting audit logs for table={table_name}")
            return self.filter_by(table_name=table_name)[:limit]
        except Exception as e:
            logger.error(f"Failed to get logs for table: {e}")
            return []