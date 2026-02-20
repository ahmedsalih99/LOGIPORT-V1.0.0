from typing import Optional, Dict, List, Any

from sqlalchemy.orm import joinedload
from passlib.hash import bcrypt

from database.models import get_session_local, User, Role
from database.crud.base_crud import BaseCRUD
from core.translator import TranslationManager


class UsersCRUD(BaseCRUD):
    """
    Users CRUD compatible with the new BaseCRUD (stamping + unified audit).

    NOTE:
    - **FIX**: use self.get_session() (context manager provided by BaseCRUD)
      instead of calling self.session_factory() directly. This avoids the
      "sessionmaker object does not support the context manager protocol"
      error.
    - Forward the acting user to BaseCRUD via current_user so timestamps and
      audit rows are written automatically.
    - Hash passwords on create/update (only if a plain password is provided).
    - Your schema uses created_by / updated_by (without *_id), so we also set
      those explicitly when user_id/admin_user_id is provided.
    """

    def __init__(self):
        super().__init__(User, get_session_local)

    # -----------------------------
    # Reads
    # -----------------------------
    def get_all(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        lang = language or TranslationManager.get_instance().get_current_language()
        with self.get_session() as session:
            users = session.query(User).options(joinedload(User.role)).all()
            return [self.as_dict(u, lang) for u in users]

    def get_by_id(self, user_id: int) -> Optional[User]:
        with self.get_session() as session:
            return (
                session.query(User)
                .options(joinedload(User.role))
                .filter(User.id == user_id)
                .first()
            )

    def get_by_username(self, username: str) -> Optional[User]:
        with self.get_session() as session:
            return (
                session.query(User)
                .options(joinedload(User.role))
                .filter(User.username == username)
                .first()
            )

    def authenticate(self, username: str, password: str) -> Optional[User]:
        with self.get_session() as session:
            user = (
                session.query(User)
                .options(joinedload(User.role))
                .filter(User.username == username)
                .first()
            )

            if user and self._check_password(password, user.password) and user.is_active:
                return user

            return None

    # -----------------------------
    # Creates / Updates / Deletes
    # -----------------------------
    def add_user(
        self,
        username: str,
        password: str,
        full_name: str,
        role_id: Optional[int] = None,
        is_active: bool = True,
        user_id: Optional[int] = None,
    ) -> User:
        password_hashed = self._hash_password(password)
        obj = User(
            username=username,
            password=password_hashed,
            full_name=full_name,
            role_id=role_id,
            is_active=is_active,
        )
        # Stamp created_by/updated_by for schemas without *_id
        if user_id is not None:
            if hasattr(obj, "created_by") and getattr(obj, "created_by", None) in (None, 0, ""):
                setattr(obj, "created_by", user_id)
            if hasattr(obj, "updated_by"):
                setattr(obj, "updated_by", user_id)
        return self.add(obj, current_user={"id": user_id} if user_id is not None else None)

    def update_user(
        self,
        user_id: int,
        data: Optional[Dict[str, Any]] = None,
        admin_user_id: Optional[int] = None,
    ) -> Optional[User]:
        if not data:
            return self.get_by_id(user_id)
        payload = dict(data)
        # Hash password if a plain password was provided
        if "password" in payload and payload["password"]:
            if not self._is_password_hashed(payload["password"]):
                payload["password"] = self._hash_password(payload["password"])
        # Stamp updated_by for schemas without *_id
        if admin_user_id is not None and "updated_by" in User.__table__.c.keys():
            payload["updated_by"] = admin_user_id
        return self.update(user_id, payload, current_user={"id": admin_user_id} if admin_user_id is not None else None)

    def delete_user(self, user_id: int, admin_user_id: Optional[int] = None) -> bool:
        return self.delete(user_id, current_user={"id": admin_user_id} if admin_user_id is not None else None)

    def toggle_active(self, user_id: int, admin_user_id: Optional[int] = None) -> Optional[User]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        new_state = not bool(user.is_active)
        payload = {"is_active": new_state}
        if admin_user_id is not None and "updated_by" in User.__table__.c.keys():
            payload["updated_by"] = admin_user_id
        return self.update(user_id, payload, current_user={"id": admin_user_id} if admin_user_id is not None else None)

    # -----------------------------
    # Utilities
    # -----------------------------
    @staticmethod
    def get_role_label(role_id: Optional[int], language: str = "ar") -> str:
        if not role_id:
            return ""
        label_field = f"label_{language}"
        with get_session_local()() as session:
            role = session.query(Role).filter_by(id=role_id).first()
            return getattr(role, label_field) if role else ""

    @staticmethod
    def get_role_name_by_id(role_id: int):
        """
        يرجّع اسم/كود الدور بناءً على الـ id.
        إصلاح لاستخدام Session حقيقي وليس sessionmaker كـ context manager.
        """
        if not role_id:
            return None

        SessionLocal = get_session_local()  # هذا هو الـ factory
        with SessionLocal() as session:  # أنشئ Session من الـ factory
            if Role is None:
                return None
            role = session.query(Role).filter(Role.id == role_id).first()
            if not role:
                return None
            # جرّب حقول شائعة للاسم
            return (
                    getattr(role, "name", None) or
                    getattr(role, "code", None) or
                    getattr(role, "title", None)
            )

    @staticmethod
    def as_dict(user: Optional[User], language: str = "ar") -> Dict[str, Any]:
        if not user:
            return {}
        lang = language or "ar"
        role_label = ""
        if getattr(user, "role", None):
            label_field = f"label_{lang}"
            role_label = getattr(user.role, label_field, getattr(user.role, "name", ""))
        return {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role_id": user.role_id,
            "role": getattr(user.role, "name", "") if getattr(user, "role", None) else "",
            "role_label": role_label,
            "is_active": user.is_active,
        }

    # -----------------------------
    # Password helpers
    # -----------------------------
    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hash(password)

    @staticmethod
    def _is_password_hashed(password: str) -> bool:
        # bcrypt hashes usually start with $2
        return isinstance(password, str) and password.startswith("$2")

    @staticmethod
    def _check_password(plain: str, hashed: str) -> bool:
        try:
            return bcrypt.verify(plain, hashed)
        except Exception:
            return False