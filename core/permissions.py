"""
Core Permissions Module - LOGIPORT
100% Database-Driven (No Hardcoded Values)

All permissions are read from the database dynamically.
This makes the system fully extensible without code changes.
"""
import logging
from typing import Any, Dict, List, Optional, Callable
from functools import wraps, lru_cache


logger = logging.getLogger(__name__)

# Database path - will be updated from config


class PermissionManager:
    """
    Permission manager that reads everything from database.
    No hardcoded permission codes - fully dynamic and extensible.
    """

    @staticmethod
    @lru_cache(maxsize=1)
    def get_all_permissions() -> List[Dict[str, Any]]:
        """
        Get all permissions from database (cached).

        Returns:
            List of permission dicts with all fields:
            [
                {
                    'id': 1,
                    'code': 'view_users',
                    'description': 'عرض جميع المستخدمين',
                    'label_ar': 'عرض المستخدمين',
                    'label_en': 'View Users',
                    'label_tr': 'Kullanıcıları Görüntüle'
                },
                ...
            ]

        Example:
            >>> perms = PermissionManager.get_all_permissions()
            >>> len(perms)
            49
            >>> perms[0]['code']
            'view_dashboard'
        """
        try:
            from database.db_utils import get_session_local
            from sqlalchemy import text
            session_factory = get_session_local()
            session = session_factory()
            try:
                rows = session.execute(text(
                    "SELECT id, code, description, label_ar, label_en, label_tr "
                    "FROM permissions ORDER BY id"
                )).fetchall()
                permissions = [
                    {
                        'id': r[0], 'code': r[1],
                        'description': r[2] or '',
                        'label_ar': r[3] or '',
                        'label_en': r[4] or '',
                        'label_tr': r[5] or '',
                    }
                    for r in rows
                ]
            finally:
                session.close()
            logger.info(f"Loaded {len(permissions)} permissions from database")
            return permissions

        except Exception as e:
            logger.error(f"Error loading permissions from database: {e}")
            return []

    @staticmethod
    @lru_cache(maxsize=128)
    def get_role_permissions(role_id: int) -> List[str]:
        """
        Get all permission codes for a specific role (cached).

        Args:
            role_id: Role ID

        Returns:
            List of permission codes that this role has

        Example:
            >>> perms = PermissionManager.get_role_permissions(1)  # Admin
            >>> 'view_users' in perms
            True
            >>> 'add_user' in perms
            True
        """
        if not role_id:
            return []

        try:
            from database.db_utils import get_session_local
            from sqlalchemy import text
            session_factory = get_session_local()
            session = session_factory()
            try:
                rows = session.execute(text(
                    "SELECT p.code FROM role_permissions rp "
                    "JOIN permissions p ON rp.permission_id = p.id "
                    "WHERE rp.role_id = :rid"
                ), {"rid": role_id}).fetchall()
                permissions = [r[0] for r in rows]
            finally:
                session.close()
            logger.debug(f"Role {role_id} has {len(permissions)} permissions")
            return permissions

        except Exception as e:
            logger.error(f"Error loading permissions for role {role_id}: {e}")
            return []

    @staticmethod
    @lru_cache(maxsize=32)
    def get_all_roles() -> List[Dict[str, Any]]:
        """
        Get all roles from database (cached).

        Returns:
            List of role dicts

        Example:
            >>> roles = PermissionManager.get_all_roles()
            >>> roles[0]['name']
            'Admin'
        """
        try:
            from database.db_utils import get_session_local
            from sqlalchemy import text
            session_factory = get_session_local()
            session = session_factory()
            try:
                rows = session.execute(text(
                    "SELECT id, name, description, label_ar, label_en, label_tr "
                    "FROM roles ORDER BY id"
                )).fetchall()
                roles = [
                    {
                        'id': r[0], 'name': r[1],
                        'description': r[2] or '',
                        'label_ar': r[3] or '',
                        'label_en': r[4] or '',
                        'label_tr': r[5] or '',
                    }
                    for r in rows
                ]
            finally:
                session.close()
            return roles

        except Exception as e:
            logger.error(f"Error loading roles from database: {e}")
            return []

    @staticmethod
    def get_permission_by_code(code: str) -> Optional[Dict[str, Any]]:
        """
        Get permission details by code.

        Args:
            code: Permission code (e.g., 'view_users')

        Returns:
            Permission dict or None if not found

        Example:
            >>> perm = PermissionManager.get_permission_by_code('view_users')
            >>> perm['label_en']
            'View Users'
        """
        all_perms = PermissionManager.get_all_permissions()
        for perm in all_perms:
            if perm['code'] == code:
                return perm
        return None

    @staticmethod
    def get_permission_by_id(permission_id: int) -> Optional[Dict[str, Any]]:
        """
        Get permission details by ID.

        Args:
            permission_id: Permission ID

        Returns:
            Permission dict or None if not found
        """
        all_perms = PermissionManager.get_all_permissions()
        for perm in all_perms:
            if perm['id'] == permission_id:
                return perm
        return None

    @staticmethod
    def get_role_by_id(role_id: int) -> Optional[Dict[str, Any]]:
        """
        Get role details by ID.

        Args:
            role_id: Role ID

        Returns:
            Role dict or None if not found
        """
        all_roles = PermissionManager.get_all_roles()
        for role in all_roles:
            if role['id'] == role_id:
                return role
        return None

    @staticmethod
    def get_role_by_name(name: str) -> Optional[Dict[str, Any]]:
        """
        Get role details by name.

        Args:
            name: Role name (e.g., 'Admin', 'Manager')

        Returns:
            Role dict or None if not found
        """
        all_roles = PermissionManager.get_all_roles()
        for role in all_roles:
            if role['name'].lower() == name.lower():
                return role
        return None

    @staticmethod
    def has_permission(user: Any, permission_code: str) -> bool:
        """
        Check if user has specific permission (reads from database).

        Args:
            user: User object with role_id attribute
            permission_code: Permission code (e.g., 'view_users')

        Returns:
            True if user has permission, False otherwise

        Example:
            >>> has_permission(admin_user, 'view_users')
            True
            >>> has_permission(viewer_user, 'delete_user')
            False
        """
        if not user or not permission_code:
            return False

        try:
            # Get user's role_id
            role_id = getattr(user, 'role_id', None)
            if role_id is None and isinstance(user, dict):
                role_id = user.get('role_id')

            if not role_id:
                logger.warning("User has no role_id")
                return False

            # Admin (role_id=1) has all permissions
            if role_id == 1:
                return True

            # Get role permissions from database
            role_perms = PermissionManager.get_role_permissions(role_id)
            has_perm = permission_code in role_perms

            logger.debug(f"User role {role_id} {'HAS' if has_perm else 'DOES NOT HAVE'} permission '{permission_code}'")
            return has_perm

        except Exception as e:
            logger.error(f"Error checking permission '{permission_code}': {e}")
            return False

    @staticmethod
    def clear_cache():
        """Clear all permission caches. Call this after updating permissions in DB."""
        PermissionManager.get_all_permissions.cache_clear()
        PermissionManager.get_role_permissions.cache_clear()
        PermissionManager.get_all_roles.cache_clear()
        logger.info("Permission caches cleared")


# --------- Core Permission Functions (Backward Compatible) ---------

def is_admin(user: Any) -> bool:
    """
    Check if user is admin.
    Admin = role_id == 1 or role.name == 'admin' (case-insensitive).

    Args:
        user: User object

    Returns:
        True if user is admin

    Example:
        >>> is_admin(admin_user)
        True
    """
    if not user:
        return False

    try:
        # Check role_id
        role_id = getattr(user, 'role_id', None)
        if role_id is None and isinstance(user, dict):
            role_id = user.get('role_id')

        if role_id == 1:
            return True

        # Check role name
        role = getattr(user, 'role', None)
        if role is None and isinstance(user, dict):
            role = user.get('role') or user.get('role_name')

        if isinstance(role, str) and role.strip().lower() == 'admin':
            return True

        if hasattr(role, 'name'):
            if str(getattr(role, 'name', '')).strip().lower() == 'admin':
                return True

        return False

    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False


def has_perm(user: Any, code: str) -> bool:
    """
    Check if user has permission (reads from database).

    Args:
        user: User object
        code: Permission code (e.g., 'view_users', 'add_material')

    Returns:
        True if user has permission

    Example:
        >>> has_perm(user, 'view_users')
        True
    """
    if is_admin(user):
        return True

    return PermissionManager.has_permission(user, code)


def has_any_perm(user: Any, codes: List[str]) -> bool:
    """
    Check if user has ANY of the specified permissions.

    Args:
        user: User object
        codes: List of permission codes

    Returns:
        True if user has at least one permission

    Example:
        >>> has_any_perm(user, ['view_users', 'edit_user'])
        True
    """
    if not user or not codes:
        return False

    if is_admin(user):
        return True

    return any(has_perm(user, code) for code in codes)


def has_all_perms(user: Any, codes: List[str]) -> bool:
    """
    Check if user has ALL of the specified permissions.

    Args:
        user: User object
        codes: List of permission codes

    Returns:
        True if user has all permissions

    Example:
        >>> has_all_perms(user, ['view_users', 'edit_user'])
        False
    """
    if not user or not codes:
        return False

    if is_admin(user):
        return True

    return all(has_perm(user, code) for code in codes)


def allowed_tabs(user: Any) -> Dict[str, bool]:
    """
    Get allowed tabs for user (compatibility with existing code).

    This now reads from database through permissions_crud.

    Args:
        user: User object

    Returns:
        Dictionary of tab names and visibility
    """
    try:
        from database.crud.permissions_crud import allowed_tabs as _allowed_tabs_db
        return _allowed_tabs_db(user)
    except Exception as e:
        logger.error(f"Error getting allowed tabs: {e}")
        return {}


def can_access_tab(user: Any, tab_name: str) -> bool:
    """
    Check if user can access specific tab.

    Args:
        user: User object
        tab_name: Tab name

    Returns:
        True if user can access tab
    """
    if not user or not tab_name:
        return False

    tabs = allowed_tabs(user)
    return tabs.get(tab_name, False)


# --------- Permission Decorators ---------

def require_permission(permission_code: str):
    """
    Decorator to require specific permission for a function.
    Permission is checked from database at runtime.

    Args:
        permission_code: Permission code from database (e.g., 'view_users')

    Raises:
        PermissionError: If user doesn't have permission

    Example:
        @require_permission('view_users')
        def show_users(current_user):
            # Only users with 'view_users' permission can execute
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to find user in args or kwargs
            user = kwargs.get('current_user') or kwargs.get('user')
            if not user and args:
                user = args[0] if hasattr(args[0], 'role_id') else None

            if not user:
                raise PermissionError(
                    f"Function '{func.__name__}' requires authentication"
                )

            if not has_perm(user, permission_code):
                raise PermissionError(
                    f"User does not have permission: {permission_code}"
                )

            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin role for a function.

    Example:
        @require_admin
        def delete_all_users(current_user):
            # Only admins can execute
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = kwargs.get('current_user') or kwargs.get('user')
        if not user and args:
            user = args[0] if hasattr(args[0], 'role_id') else None

        if not user:
            raise PermissionError(
                f"Function '{func.__name__}' requires authentication"
            )

        if not is_admin(user):
            raise PermissionError(
                f"Function '{func.__name__}' requires admin role"
            )

        return func(*args, **kwargs)
    return wrapper


# --------- Utility Functions ---------

def get_all_permissions() -> List[Dict[str, Any]]:
    """Get all permissions from database"""
    return PermissionManager.get_all_permissions()


def get_all_roles() -> List[Dict[str, Any]]:
    """Get all roles from database"""
    return PermissionManager.get_all_roles()


def get_permission_label(code: str, language: str = 'en') -> str:
    """
    Get permission label in specified language.

    Args:
        code: Permission code
        language: Language code ('ar', 'en', 'tr')

    Returns:
        Label in specified language or code if not found
    """
    perm = PermissionManager.get_permission_by_code(code)
    if not perm:
        return code

    label_key = f'label_{language}'
    return perm.get(label_key) or perm.get('label_en') or code


def clear_permission_cache():
    """Clear all permission caches. Call after updating permissions."""
    PermissionManager.clear_cache()


# --------- Dynamic Permission Constants (Auto-Generated) ---------

class Permissions:
    """
    Dynamic permission constants loaded from database.

    This class auto-generates attributes from database.
    No hardcoded values!

    Usage:
        # Instead of hardcoding:
        # USERS_VIEW = "users.view"

        # Use database code directly:
        if has_perm(user, 'view_users'):
            pass

        # Or get label:
        label = get_permission_label('view_users', 'ar')
    """

    @staticmethod
    def get_code(module: str, action: str) -> Optional[str]:
        """
        Try to find permission code by module and action.

        Args:
            module: Module name (e.g., 'users', 'materials')
            action: Action (e.g., 'view', 'add', 'edit', 'delete')

        Returns:
            Permission code if found, None otherwise

        Example:
            >>> Permissions.get_code('users', 'view')
            'view_users'
            >>> Permissions.get_code('materials', 'add')
            'add_material'
        """
        # Try different patterns
        patterns = [
            f"{action}_{module}",      # view_users
            f"{action}_{module}s",     # view_clients (plural)
            f"{module}_{action}",      # users_view
            f"{module}s_{action}",     # clients_view
        ]

        all_perms = get_all_permissions()
        for pattern in patterns:
            for perm in all_perms:
                if perm['code'] == pattern:
                    return pattern

        return None

    @staticmethod
    def list_by_module(module: str) -> List[str]:
        """
        Get all permission codes for a module.

        Args:
            module: Module name (e.g., 'users', 'materials')

        Returns:
            List of permission codes

        Example:
            >>> Permissions.list_by_module('users')
            ['view_users', 'add_user', 'edit_user', 'delete_user']
        """
        all_perms = get_all_permissions()
        return [
            perm['code']
            for perm in all_perms
            if module in perm['code']
        ]