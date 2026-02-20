"""
database/crud/base_crud.py
===========================
BaseCRUD — الصنف الأساسي لجميع عمليات CRUD.

قواعد الجلسة:
  1. get_session() context manager مبسَّط وصريح (بلا nested returns)
  2. كل عملية (add/update/delete) تنتهي بـ commit واحد فقط
  3. rollback تلقائي عند أي استثناء
  4. close() مضمون في finally
  5. يدعم: callable (get_session_local) أو Session مباشرة (للاختبارات)
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session
from contextlib import contextmanager
from typing import Any, Callable, List, Optional, Dict, Union
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

try:
    from database.models.audit_log import AuditLog
except Exception:
    AuditLog = None


class BaseCRUD:

    def __init__(
        self,
        model: Any,
        session_factory: Callable,
        *,
        sync_service=None,
        table_name: Optional[str] = None,
    ):
        self.model          = model
        self.session_factory = session_factory
        self.sync_service   = sync_service
        self.table_name     = table_name or getattr(model, "__tablename__", model.__name__.lower())

    # ─────────────────────────────────────────────────────────────────────────
    # Session Management
    # ─────────────────────────────────────────────────────────────────────────

    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager يُرجع Session جاهزة.

        حالة 1 — Session مباشرة (test injection):
            self.session_factory هو Session → نستخدمه مباشرة بدون إغلاق

        حالة 2 — callable (get_session_local):
            factory()       → sessionmaker → factory()()  → Session
            factory()       → Session مباشرة (نادر)

        السلوك:
            - rollback تلقائي عند أي استثناء
            - close() مضمون في finally (إلا في حالة 1)
        """
        # ── حالة 1: Session جاهزة (لا نغلقها — مُدارة خارجياً) ──────────
        if isinstance(self.session_factory, Session):
            yield self.session_factory
            return

        # ── حالة 2: callable ─────────────────────────────────────────────
        session = None
        try:
            result = self.session_factory()           # get_session_local → sessionmaker

            if callable(result):                      # sessionmaker → Session
                session = result()
            elif isinstance(result, Session):         # مباشرة Session (نادر)
                session = result
            else:
                raise TypeError(
                    f"session_factory returned unexpected type: {type(result).__name__}"
                )

            yield session

        except Exception:
            if session is not None:
                try:
                    session.rollback()
                except Exception:
                    pass
            raise

        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_user_id(self, user) -> Optional[int]:
        if user is None:
            return None
        try:
            return user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
        except Exception:
            return None

    def _has_column(self, obj: Any, col_name: str) -> bool:
        try:
            return col_name in getattr(obj, "__table__").c.keys()
        except Exception:
            return False

    def _stamp_create(self, obj: Any, user):
        now = datetime.utcnow()
        if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
            setattr(obj, "created_at", now)
        if hasattr(obj, "updated_at"):
            setattr(obj, "updated_at", now)
        uid = self._get_user_id(user)
        if uid is None:
            return
        if hasattr(obj, "created_by_id") and getattr(obj, "created_by_id", None) in (None, 0, ""):
            setattr(obj, "created_by_id", uid)
        elif self._has_column(obj, "created_by") and getattr(obj, "created_by", None) in (None, 0, ""):
            setattr(obj, "created_by", uid)
        if hasattr(obj, "updated_by_id"):
            setattr(obj, "updated_by_id", uid)
        elif self._has_column(obj, "updated_by"):
            setattr(obj, "updated_by", uid)

    def _stamp_update(self, obj: Any, user):
        if hasattr(obj, "updated_at"):
            setattr(obj, "updated_at", datetime.utcnow())
        uid = self._get_user_id(user)
        if uid is None:
            return
        if hasattr(obj, "updated_by_id"):
            setattr(obj, "updated_by_id", uid)
        elif self._has_column(obj, "updated_by"):
            setattr(obj, "updated_by", uid)

    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        try:
            return {c.name: getattr(obj, c.name) for c in getattr(obj, "__table__").columns}
        except Exception:
            return {}

    def _audit(self, session: Session, *, user_id, action: str, before, after):
        if AuditLog is None:
            return
        try:
            rec_id  = (after or {}).get("id") or (before or {}).get("id")
            details = {}
            if after:
                details["after"]  = after
            if before:
                details["before"] = before
            session.add(AuditLog(
                user_id    = user_id,
                action     = action,
                table_name = self.table_name,
                record_id  = rec_id,
                details    = json.dumps(details, ensure_ascii=False, default=str),
            ))
        except Exception as e:
            logger.warning(f"Audit error ({action}): {e}")

    def _sync_record(self, *, entity_id, op: str, payload: dict):
        if not self.sync_service:
            return
        try:
            self.sync_service.record_op(
                entity_name  = self.table_name,
                entity_id    = entity_id,
                op           = op,
                payload_json = json.dumps(payload, ensure_ascii=False),
                version      = None,
            )
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # CRUD — commit واحد لكل عملية بعد كل شيء (audit + بيانات معاً)
    # ─────────────────────────────────────────────────────────────────────────

    def add(self, obj: Any, *, current_user=None):
        with self.get_session() as session:
            self._stamp_create(obj, current_user)
            session.add(obj)
            self._audit(session,
                        user_id=self._get_user_id(current_user),
                        action="create", before=None, after=self._to_dict(obj))
            session.commit()
            session.refresh(obj)
            self._sync_record(entity_id=getattr(obj, "id", None),
                              op="create", payload=self._to_dict(obj))
            return obj

    def add_many(self, objs: List[Any], *, current_user=None) -> List[Any]:
        if not objs:
            return []
        with self.get_session() as session:
            for obj in objs:
                self._stamp_create(obj, current_user)
                session.add(obj)
            if AuditLog is not None:
                try:
                    session.add(AuditLog(
                        user_id=self._get_user_id(current_user),
                        action="bulk_create", table_name=self.table_name,
                        record_id=None,
                        details=json.dumps({"count": len(objs)}, ensure_ascii=False),
                    ))
                except Exception:
                    pass
            session.commit()
            for obj in objs:
                try:
                    session.refresh(obj)
                except Exception:
                    pass
            return objs

    def update(self, id: Any, data: Dict[str, Any], *, current_user=None):
        with self.get_session() as session:
            obj = id if hasattr(id, "__table__") else session.get(self.model, id)
            if not obj:
                return None
            before = self._to_dict(obj)
            for key, value in data.items():
                setattr(obj, key, value)
            self._stamp_update(obj, current_user)
            self._audit(session,
                        user_id=self._get_user_id(current_user),
                        action="update", before=before, after={**before, **data})
            session.commit()
            session.refresh(obj)
            self._sync_record(entity_id=getattr(obj, "id", None),
                              op="update", payload=self._to_dict(obj))
            return obj

    def delete(self, id: Any, *, current_user=None) -> bool:
        with self.get_session() as session:
            obj = id if hasattr(id, "__table__") else session.get(self.model, id)
            if not obj:
                return False
            before = self._to_dict(obj)
            self._audit(session,
                        user_id=self._get_user_id(current_user),
                        action="delete", before=before, after=None)
            session.delete(obj)
            session.commit()
            self._sync_record(entity_id=before.get("id"),
                              op="delete", payload=before)
            return True

    # ─────────────────────────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────────────────────────

    def get(self, id: Any):
        with self.get_session() as session:
            return session.get(self.model, id)

    def get_all(self, order_by=None) -> List[Any]:
        with self.get_session() as session:
            q = session.query(self.model)
            if order_by is not None:
                q = q.order_by(order_by)
            return q.all()

    def filter_by(self, **kwargs) -> List[Any]:
        with self.get_session() as session:
            return session.query(self.model).filter_by(**kwargs).all()

    def search(self, search_term: str, *columns, limit: int = 50) -> List[Any]:
        if not columns:
            return []
        with self.get_session() as session:
            conditions = [col.ilike(f"%{search_term}%") for col in columns]
            return session.query(self.model).filter(or_(*conditions)).limit(limit).all()

    def get_paginated(self, page: int = 1, per_page: int = 25, *,
                      order_by=None, filters: Optional[Dict] = None) -> Dict[str, Any]:
        with self.get_session() as session:
            q = session.query(self.model)
            if filters:
                q = q.filter_by(**filters)
            total = q.count()
            if order_by is not None:
                q = q.order_by(order_by)
            items = q.offset((page - 1) * per_page).limit(per_page).all()
            return {
                "items": items, "total": total, "page": page, "per_page": per_page,
                "pages": max(1, (total + per_page - 1) // per_page),
            }

    def delete_many(self, ids: List[Any], *, current_user=None) -> int:
        if not ids:
            return 0
        deleted = 0
        with self.get_session() as session:
            for _id in ids:
                obj = session.get(self.model, _id)
                if not obj:
                    continue
                self._audit(session,
                            user_id=self._get_user_id(current_user),
                            action="delete", before=self._to_dict(obj), after=None)
                session.delete(obj)
                deleted += 1
            if deleted and AuditLog is not None:
                try:
                    session.add(AuditLog(
                        user_id=self._get_user_id(current_user),
                        action="bulk_delete", table_name=self.table_name,
                        record_id=None,
                        details=json.dumps({"count": deleted}, ensure_ascii=False),
                    ))
                except Exception:
                    pass
            session.commit()
            return deleted

    def bulk_insert(self, objs: List[Any], *, current_user=None):
        with self.get_session() as session:
            for obj in objs:
                self._stamp_create(obj, current_user)
            session.bulk_save_objects(objs)
            if AuditLog is not None:
                try:
                    session.add(AuditLog(
                        user_id=self._get_user_id(current_user),
                        action="bulk_insert", table_name=self.table_name,
                        record_id=None,
                        details=json.dumps({"count": len(objs)}, ensure_ascii=False),
                    ))
                except Exception:
                    pass
            session.commit()

    def count(self, filters: Optional[Dict] = None) -> int:
        with self.get_session() as session:
            q = session.query(self.model)
            if filters:
                q = q.filter_by(**filters)
            return q.count()