from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import Session
from database.models.base import Base

class SyncState(Base):
    __tablename__ = "sync_state"
    entity_name = Column(String(64), primary_key=True)
    last_pulled_version = Column(Integer, default=0)

class OpLog(Base):
    __tablename__ = "op_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_name = Column(String(64), nullable=False)
    entity_id = Column(Integer, nullable=True)
    op = Column(String(16), nullable=False)  # create | update | delete
    payload_json = Column(Text, nullable=True)
    version = Column(Integer, nullable=True)
    status = Column(String(16), default="pending")  # pending | sent | failed
    created_at = Column(DateTime, server_default=func.now())

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