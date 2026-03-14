"""
database/crud/tasks_crud.py — LOGIPORT
=========================================
CRUD للمهام — المرحلة 5.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import or_, and_, func
from sqlalchemy.orm import joinedload

from database.models.base import get_session_local
from database.models.task import Task

logger = logging.getLogger(__name__)


class TasksCRUD:

    def __init__(self):
        self._factory = get_session_local()  # sessionmaker instance — call once to get Session

    # ─── Read ─────────────────────────────────────────────────────────────────

    def get_all(
        self,
        *,
        status:      Optional[str] = None,
        priority:    Optional[str] = None,
        assigned_to: Optional[int] = None,
        search:      Optional[str] = None,
        only_overdue: bool = False,
    ) -> List[Task]:
        """
        إرجاع قائمة المهام مع eager-load للمستخدمين لتجنب DetachedInstanceError.
        """
        s = self._factory()
        try:
            q = s.query(Task).options(
                joinedload(Task.assigned_to),
                joinedload(Task.created_by),
            )
            if status:
                q = q.filter(Task.status == status)
            if priority:
                q = q.filter(Task.priority == priority)
            if assigned_to:
                q = q.filter(Task.assigned_to_id == assigned_to)
            if only_overdue:
                q = q.filter(
                    Task.due_date < date.today(),
                    Task.status.notin_(["done", "cancelled"])
                )
            if search:
                term = f"%{search.strip()}%"
                q = q.filter(or_(
                    Task.title.ilike(term),
                    Task.description.ilike(term),
                ))
            tasks = q.order_by(
                # الأولوية أولاً، ثم تاريخ الاستحقاق
                Task.status.notin_(["done", "cancelled"]).desc(),
                Task.due_date.asc().nullslast(),
                Task.priority.asc(),
            ).all()
            s.expunge_all()
            return tasks
        finally:
            s.close()

    def get_by_id(self, task_id: int) -> Optional[Task]:
        s = self._factory()
        try:
            task = s.query(Task).options(
                joinedload(Task.assigned_to),
                joinedload(Task.created_by),
                joinedload(Task.transaction),
                joinedload(Task.client),
            ).filter(Task.id == task_id).first()
            if task:
                s.expunge(task)
            return task
        finally:
            s.close()

    def count_pending(self, *, assigned_to: Optional[int] = None) -> int:
        """عدد المهام غير المكتملة (pending + in_progress)."""
        s = self._factory()
        try:
            q = s.query(func.count(Task.id)).filter(
                Task.status.in_(["pending", "in_progress"])
            )
            if assigned_to:
                q = q.filter(Task.assigned_to_id == assigned_to)
            return q.scalar() or 0
        finally:
            s.close()

    def count_overdue(self, *, assigned_to: Optional[int] = None) -> int:
        """عدد المهام المتأخرة (due_date < today + غير مكتملة)."""
        s = self._factory()
        try:
            q = s.query(func.count(Task.id)).filter(
                Task.due_date < date.today(),
                Task.status.notin_(["done", "cancelled"])
            )
            if assigned_to:
                q = q.filter(Task.assigned_to_id == assigned_to)
            return q.scalar() or 0
        finally:
            s.close()

    # ─── Write ────────────────────────────────────────────────────────────────

    def create(
        self,
        *,
        title:          str,
        priority:       str = "medium",
        status:         str = "pending",
        description:    Optional[str] = None,
        due_date:       Optional[date] = None,
        assigned_to_id: Optional[int] = None,
        created_by_id:  Optional[int] = None,
        transaction_id: Optional[int] = None,
        container_id:   Optional[int] = None,
        client_id:      Optional[int] = None,
    ) -> Task:
        s = self._factory()
        try:
            task = Task(
                title=title, priority=priority, status=status,
                description=description, due_date=due_date,
                assigned_to_id=assigned_to_id, created_by_id=created_by_id,
                transaction_id=transaction_id, container_id=container_id,
                client_id=client_id,
                created_at=datetime.utcnow(),
            )
            s.add(task)
            s.commit()
            s.refresh(task)
            s.expunge(task)
            return task
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def update(self, task_id: int, **fields) -> bool:
        s = self._factory()
        try:
            task = s.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False
            for k, v in fields.items():
                if hasattr(task, k):
                    setattr(task, k, v)
            task.updated_at = datetime.utcnow()
            if fields.get("status") == "done" and not task.completed_at:
                task.completed_at = datetime.utcnow()
            s.commit()
            return True
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def delete(self, task_id: int) -> bool:
        s = self._factory()
        try:
            task = s.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False
            s.delete(task)
            s.commit()
            return True
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def mark_done(self, task_id: int) -> bool:
        return self.update(task_id, status="done", completed_at=datetime.utcnow())

    def mark_cancelled(self, task_id: int) -> bool:
        return self.update(task_id, status="cancelled")
