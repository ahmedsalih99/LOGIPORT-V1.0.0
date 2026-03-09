"""
database/models/sync_models.py — LOGIPORT
===========================================
نماذج المزامنة مع الخادم المركزي.

الجداول:
  - sync_state : آخر إصدار مُزامَن لكل entity
  - op_log     : سجل العمليات المحلية المنتظرة للإرسال

تُنشأ تلقائياً عبر init_db() في Bootstrap.
مخصص لإصدارات مستقبلية — لا تُستخدم حالياً.
"""
from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text, DateTime, func

from database.models.base import Base


class SyncState(Base):
    """آخر إصدار مُزامَن لكل كيان (entity)."""
    __tablename__ = "sync_state"

    entity_name          = Column(String(64), primary_key=True)
    last_pulled_version  = Column(Integer, default=0)


class OpLog(Base):
    """سجل العمليات المحلية (create/update/delete) المنتظرة للإرسال."""
    __tablename__ = "op_log"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    entity_name  = Column(String(64), nullable=False, index=True)
    entity_id    = Column(Integer,    nullable=True)
    op           = Column(String(16), nullable=False)   # create | update | delete
    payload_json = Column(Text,       nullable=True)
    version      = Column(Integer,    nullable=True)
    status       = Column(String(16), default="pending", index=True)  # pending | sent | failed
    created_at   = Column(DateTime,   server_default=func.now())