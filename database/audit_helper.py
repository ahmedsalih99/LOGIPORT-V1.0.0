"""
Audit Helper - LOGIPORT
Helper functions for audit logging with enhanced error handling
"""
import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
from database.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def log_audit(
        session: Session,
        *,
        user_id: Optional[int],
        action: str,
        table_name: str,
        record_id: Optional[int] = None,
        before: Optional[dict] = None,
        after: Optional[dict] = None,
        details: Optional[str] = None
) -> bool:
    """
    Log an audit entry to the database.

    Args:
        session: Database session
        user_id: User ID who performed the action
        action: Action performed (e.g., 'CREATE', 'UPDATE', 'DELETE')
        table_name: Table name where action occurred
        record_id: Record ID affected (optional)
        before: Data before the change (optional)
        after: Data after the change (optional)
        details: Additional details (optional)

    Returns:
        True if logged successfully, False otherwise

    Example:
        >>> log_audit(session, user_id=1, action='CREATE', table_name='users', record_id=5)
        True
    """
    try:
        logger.debug(f"Logging audit: {action} on {table_name} by user={user_id}")

        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            details=details,
            before_data=json.dumps(before, ensure_ascii=False) if before is not None else None,
            after_data=json.dumps(after, ensure_ascii=False) if after is not None else None,
        )

        session.add(audit_log)
        logger.debug(f"Audit log added successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to log audit: {e}")
        return False