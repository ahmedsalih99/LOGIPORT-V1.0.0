"""
services/sync_service.py — LOGIPORT
=====================================
خدمة المزامنة مع الخادم المركزي (مخصص لإصدارات مستقبلية).

الجداول المطلوبة (sync_state, op_log) مُعرَّفة في:
  database/models/sync_models.py
وتُنشأ تلقائياً عبر Bootstrap عند بدء التطبيق.

ملاحظة: هذه الخدمة غير مفعّلة حتى تكتمل البنية التحتية للـ API.
"""
from __future__ import annotations
from typing import Optional, List
import logging

from database.models.sync_models import OpLog

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, session_factory, settings, logger):
        self.session_factory = session_factory
        self.settings = settings
        self.logger = logger

    def is_online(self) -> bool:
        try:
            if self.settings.get("offline_mode", False):
                return False
            # TODO: Optionally ping API URL
            return bool(self.settings.get("api_url"))
        except Exception:
            return False

    def record_op(self, entity_name: str, entity_id: Optional[int], op: str, payload_json: str, version: Optional[int]):
        with self.session_factory() as session:
            session.add(OpLog(entity_name=entity_name, entity_id=entity_id, op=op,
                              payload_json=payload_json, version=version, status="pending"))
            session.commit()

    def push(self) -> None:
        if not self.is_online():
            return
        with self.session_factory() as session:
            pending: List[OpLog] = session.query(OpLog).filter_by(status="pending").all()
            for op in pending:
                try:
                    # TODO: call API /sync/ops with op data
                    op.status = "sent"
                    session.commit()
                except Exception as e:
                    self.logger.error(f"Sync push failed for op {op.id}: {e}")

    def pull(self) -> None:
        if not self.is_online():
            return
        with self.session_factory() as session:
            # TODO: call API /sync/changes?since=last_version per entity in sync_state
            # For now, this is a placeholder
            pass

    def sync_now(self) -> None:
        if not self.is_online():
            return
        self.push()
        self.pull()