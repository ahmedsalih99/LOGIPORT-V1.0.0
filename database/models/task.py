"""
database/models/task.py — LOGIPORT
=====================================
موديل المهام (Tasks) — المرحلة 5.

الحالات: pending | in_progress | done | cancelled
الأولويات: low | medium | high | urgent
"""
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, ForeignKey, func, Index
)
from sqlalchemy.orm import relationship
from database.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id          = Column(Integer, primary_key=True, autoincrement=True)

    # المحتوى
    title       = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # التصنيف
    priority    = Column(String(16), nullable=False, default="medium",  index=True)
    # pending | in_progress | done | cancelled
    status      = Column(String(16), nullable=False, default="pending", index=True)

    # التواريخ
    due_date    = Column(Date, nullable=True, index=True)
    created_at  = Column(DateTime, nullable=False, server_default=func.now())
    updated_at  = Column(DateTime, nullable=True, onupdate=func.now())
    completed_at= Column(DateTime, nullable=True)

    # الربط بالكيانات
    assigned_to_id   = Column(Integer, ForeignKey("users.id",         ondelete="SET NULL"), nullable=True, index=True)
    created_by_id    = Column(Integer, ForeignKey("users.id",         ondelete="SET NULL"), nullable=True)
    updated_by_id    = Column(Integer, ForeignKey("users.id",         ondelete="SET NULL"), nullable=True)
    transaction_id   = Column(Integer, ForeignKey("transactions.id",  ondelete="SET NULL"), nullable=True, index=True)
    container_id     = Column(Integer, ForeignKey("container_tracking.id", ondelete="SET NULL"), nullable=True, index=True)
    client_id        = Column(Integer, ForeignKey("clients.id",       ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    assigned_to  = relationship("User", foreign_keys=[assigned_to_id], lazy="joined")
    created_by   = relationship("User", foreign_keys=[created_by_id],  lazy="joined")
    updated_by   = relationship("User", foreign_keys="[Task.updated_by_id]", lazy="select")
    transaction  = relationship("Transaction", foreign_keys=[transaction_id], lazy="select")
    client       = relationship("Client",      foreign_keys=[client_id],      lazy="select")

    __table_args__ = (
        Index("ix_tasks_status_due", "status", "due_date"),
    )

    # ─── helpers ─────────────────────────────────────────────────────────────

    @property
    def is_overdue(self) -> bool:
        from datetime import date
        return (
            self.due_date is not None
            and self.status not in ("done", "cancelled")
            and self.due_date < date.today()
        )

    @property
    def priority_order(self) -> int:
        return {"urgent": 0, "high": 1, "medium": 2, "low": 3}.get(self.priority, 2)

    def __repr__(self):
        return f"<Task id={self.id} title={self.title!r} status={self.status}>"
