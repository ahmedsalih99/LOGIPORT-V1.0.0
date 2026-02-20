"""
Company Roles CRUD - LOGIPORT
Enhanced with logging and comprehensive error handling
"""
import logging
from typing import List, Optional

from database.models import get_session_local
from database.models.company_role import CompanyRole
from database.crud.base_crud import BaseCRUD

logger = logging.getLogger(__name__)


class CompanyRolesCRUD(BaseCRUD):
    """CRUD operations for company roles with logging and error handling"""

    def __init__(self):
        super().__init__(CompanyRole, get_session_local)
        logger.debug("CompanyRolesCRUD initialized")

    # -------- Reads --------
    def get_all_roles(self, *, order_by=None) -> List[CompanyRole]:
        """Get all company roles"""
        try:
            logger.debug("Getting all company roles")
            if order_by is None:
                order_by = CompanyRole.sort_order
            return self.get_all(order_by=order_by)
        except Exception as e:
            logger.error(f"Failed to get all roles: {e}")
            return []

    def get_all_active(self, *, order_by=None) -> List[CompanyRole]:
        """Get all active company roles"""
        try:
            logger.debug("Getting active company roles")
            with self.get_session() as session:
                query = session.query(CompanyRole).filter(CompanyRole.is_active == True)
                if order_by is not None:
                    query = query.order_by(order_by.asc())
                else:
                    query = query.order_by(CompanyRole.sort_order.asc())
                return query.all()
        except Exception as e:
            logger.error(f"Failed to get active roles: {e}")
            return []

    # -------- Lookups --------
    def get_by_code(self, code: str) -> Optional[CompanyRole]:
        """Get company role by code"""
        try:
            logger.debug(f"Getting company role by code: {code}")
            with self.get_session() as session:
                return session.query(CompanyRole).filter(CompanyRole.code == code).first()
        except Exception as e:
            logger.error(f"Failed to get role by code {code}: {e}")
            return None

    def get_by_id(self, role_id: int) -> Optional[CompanyRole]:
        """Get company role by ID"""
        try:
            logger.debug(f"Getting company role id={role_id}")
            return self.get(role_id)
        except Exception as e:
            logger.error(f"Failed to get role id={role_id}: {e}")
            return None