from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


from database.models import get_session_local, User, Role
from database.models.permission import Permission
from database.models.role_permission import RolePermission
from database.crud.base_crud import BaseCRUD


# ==== أضِف تحت الاستيرادات مباشرة ====
# Helpers to support both ORM objects and dict users
def _get_role_id(user):
    if not user:
        return None
    try:
        if isinstance(user, dict):
            rid = user.get("role_id")
            if rid is not None:
                return int(rid)
            role = user.get("role")
            if isinstance(role, dict):
                rid = role.get("id")
                return int(rid) if rid is not None else None
            rid = getattr(role, "id", None)
            return int(rid) if rid is not None else None
        # ORM object
        rid = getattr(user, "role_id", None)
        return int(rid) if rid is not None else None
    except Exception:
        return None

def _is_super_admin(user):
    if not user:
        return False
    role = user.get("role") if isinstance(user, dict) else getattr(user, "role", None)
    name = ""
    if isinstance(role, dict):
        name = role.get("name") or ""
    elif isinstance(role, str):
        name = role
    else:
        name = getattr(role, "name", "") or ""
    return str(name).strip().lower() == "admin"

# -----------------------------
# Permissions CRUD
# -----------------------------
class PermissionsCRUD(BaseCRUD):
    """
    Permissions CRUD adapted to the new BaseCRUD (stamping + audit ready).
    - Passes the *callable* get_session_local (not an opened session)
    - Provides a get_all(...) that returns dictionaries with a language-aware label
    - Optional helpers for create/update/delete that forward current_user
    """

    def __init__(self) -> None:
        # IMPORTANT: pass the session factory (callable), not get_session_local()
        super().__init__(Permission, get_session_local)
        logger.debug("PermissionsCRUD initialized")

    def get_all(self, language: str = "ar") -> List[Dict[str, Any]]:
        label_field = f"label_{language}"
        with self.get_session() as session:
            perms = session.query(Permission).all()
            return [self._to_dict(p, label_field) for p in perms]

    # Optional audited helpers (use if you need to add/update/delete via UI)
    def add_permission(
        self,
        code: str,
        label_ar: Optional[str] = None,
        label_en: Optional[str] = None,
        label_tr: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Permission:
        obj = Permission(
            code=code,
            label_ar=label_ar,
            label_en=label_en,
            label_tr=label_tr,
            description=description,
        )
        return self.add(obj, current_user={"id": user_id} if user_id is not None else None)

    def update_permission(self, permission_id: int, data: Dict[str, Any], user_id: Optional[int] = None):
        payload = dict(data or {})
        return self.update(
            permission_id,
            payload,
            current_user={"id": user_id} if user_id is not None else None
        )

    def delete_permission(self, permission_id: int, user_id: Optional[int] = None) -> bool:
        return self.delete(permission_id, current_user={"id": user_id} if user_id is not None else None)

    @staticmethod
    def _to_dict(p: Optional[Permission], label_field: str = "label_ar") -> Dict[str, Any]:
        if not p:
            return {}
        return {
            "id": p.id,
            "code": p.code,
            "label_ar": p.label_ar,
            "label_en": p.label_en,
            "label_tr": p.label_tr,
            "label": getattr(p, label_field, None) or p.code,
            "description": p.description,
        }


# -----------------------------
# Roles CRUD
# -----------------------------
class RolesCRUD(BaseCRUD):
    """
    Roles CRUD adapted to the new BaseCRUD (stamping + audit ready).
    """

    def __init__(self) -> None:
        super().__init__(Role, get_session_local)

    def get_all(self, language: str = "ar") -> List[Dict[str, Any]]:
        label_field = f"label_{language}"
        with self.get_session() as session:
            roles = session.query(Role).all()
            return [self._to_dict(r, label_field) for r in roles]

    # Optional audited helpers
    def add_role(
        self,
        name: str,
        label_ar: Optional[str] = None,
        label_en: Optional[str] = None,
        label_tr: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Role:
        obj = Role(
            name=name,
            label_ar=label_ar,
            label_en=label_en,
            label_tr=label_tr,
            description=description,
        )
        return self.add(obj, current_user={"id": user_id} if user_id is not None else None)

    def update_role(self, role_id: int, data: Dict[str, Any], user_id: Optional[int] = None) -> Optional[Role]:
        payload = dict(data or {})
        return self.update(role_id, payload, current_user={"id": user_id} if user_id is not None else None)

    def delete_role(self, role_id: int, user_id: Optional[int] = None) -> bool:
        return self.delete(role_id, current_user={"id": user_id} if user_id is not None else None)

    @staticmethod
    def _to_dict(r: Optional[Role], label_field: str = "label_ar") -> Dict[str, Any]:
        if not r:
            return {}
        return {
            "id": r.id,
            "name": r.name,
            "label_ar": r.label_ar,
            "label_en": r.label_en,
            "label_tr": r.label_tr,
            "label": getattr(r, label_field, None) or r.name,
            "description": r.description,
        }


# -----------------------------
# RolePermission CRUD (for audited assign/remove)
# -----------------------------
class RolePermissionsCRUD(BaseCRUD):
    """A tiny CRUD wrapper for RolePermission to leverage BaseCRUD auditing."""

    def __init__(self) -> None:
        super().__init__(RolePermission, get_session_local)

    def assign(self, role_id: int, permission_id: int, user_id: Optional[int] = None) -> bool:
        with self.get_session() as session:
            existing = (
                session.query(RolePermission)
                .filter_by(role_id=role_id, permission_id=permission_id)
                .first()
            )
        if existing:
            return True
        obj = RolePermission(role_id=role_id, permission_id=permission_id)
        self.add(obj, current_user={"id": user_id} if user_id is not None else None)
        return True

    def remove(self, role_id: int, permission_id: int, user_id: Optional[int] = None) -> bool:
        with self.get_session() as session:
            rp = session.query(RolePermission).filter_by(
                role_id=role_id, permission_id=permission_id
            ).first()
            if not rp:
                return False
            session.delete(rp)
            session.commit()
        return True


# -----------------------------
# Facade helpers (backwards compatible)
# -----------------------------

def assign_permission_to_role(role_id: int, permission_id: int, user_id: Optional[int] = None) -> bool:
    """Assign with audit trail (user_id optional)."""
    return RolePermissionsCRUD().assign(role_id, permission_id, user_id=user_id)


def remove_permission_from_role(role_id: int, permission_id: int, user_id: Optional[int] = None) -> bool:
    """Remove with audit trail (user_id optional)."""
    return RolePermissionsCRUD().remove(role_id, permission_id, user_id=user_id)


# -----------------------------
# Permission queries
# -----------------------------

def get_role_permissions(role_id: int, language: str = "ar") -> List[Dict[str, Any]]:
    label_field = f"label_{language}"
    SessionLocal = get_session_local()
    with SessionLocal() as session:
        perms = (
            session.query(Permission)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .filter(RolePermission.role_id == role_id)
            .all()
        )
        return [PermissionsCRUD._to_dict(p, label_field) for p in perms]


def get_user_permissions(user: Optional[User], language: str = "ar") -> List[Dict[str, Any]]:
    rid = _get_role_id(user)
    if not rid:
        return []
    return get_role_permissions(rid, language=language)

def has_permission(user: Optional[User], permission_code: str) -> bool:
    if _is_super_admin(user):
        return True
    rid = _get_role_id(user)
    if not rid:
        return False
    perms = get_role_permissions(rid)
    codes = [p["code"] for p in perms]
    return permission_code in codes


def allowed_tabs(user: Optional[User]) -> List[str]:
    TAB_PERMISSIONS = {
        "dashboard": "view_dashboard",
        "materials": "view_materials",
        "clients": "view_clients",
        "companies": "view_companies",
        "countries": "view_countries",
        "pricing": "view_pricing",
        "entries": "view_entries",
        "transactions": "view_transactions",
        "documents": "view_documents",
        "values": "view_values",
        "users_permissions": "view_users_roles",
        "audit_trail": "view_audit_trail",
        "control_panel": "view_control_panel",
    }
    return [tab for tab, perm in TAB_PERMISSIONS.items() if has_permission(user, perm)]


# -----------------------------
# Bulk fetchers (language-aware)
# -----------------------------

def all_roles(language: str = "ar") -> List[Dict[str, Any]]:
    label_field = f"label_{language}"
    SessionLocal = get_session_local()
    with SessionLocal() as session:
        roles = session.query(Role).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "label": getattr(r, label_field) or r.name,
                "label_ar": r.label_ar,
                "label_en": r.label_en,
                "label_tr": r.label_tr,
                "description": r.description,
            }
            for r in roles
        ]


def all_permissions(language: str = "ar") -> List[Dict[str, Any]]:
    label_field = f"label_{language}"
    SessionLocal = get_session_local()
    with SessionLocal() as session:
        perms = session.query(Permission).all()
        return [
            {
                "id": p.id,
                "code": p.code,
                "label": getattr(p, label_field) or p.code,
                "label_ar": p.label_ar,
                "label_en": p.label_en,
                "label_tr": p.label_tr,
                "description": p.description,
            }
            for p in perms
        ]


# Backwards-compatible alias
get_all_permissions = all_permissions