"""
container_tracking_crud.py — LOGIPORT
=======================================
CRUD لجدول container_tracking — يرث من BaseCRUD.
"""
from __future__ import annotations

import logging
from typing import List, Optional
from sqlalchemy import or_, desc
from sqlalchemy.orm import joinedload

from database.crud.base_crud import BaseCRUD
from database.models import get_session_local
from database.models.container_tracking import ContainerTracking

logger = logging.getLogger(__name__)


class ContainerTrackingCRUD(BaseCRUD):

    def __init__(self):
        super().__init__(
            model=ContainerTracking,
            session_factory=get_session_local,
            table_name="container_tracking",
        )

    # ── قراءة ─────────────────────────────────────────────────────────────────

    def get_all(
        self,
        search: str = "",
        status: Optional[str] = None,
        transaction_id: Optional[int] = None,
        office_id: Optional[int] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[ContainerTracking]:
        """إرجاع كل الكونتينرات مع فلترة اختيارية."""
        with self.get_session() as session:
            q = session.query(ContainerTracking).options(
                joinedload(ContainerTracking.transaction),
                joinedload(ContainerTracking.client),
                joinedload(ContainerTracking.entries),
            )
            if status:
                q = q.filter(ContainerTracking.status == status)
            if transaction_id:
                q = q.filter(ContainerTracking.transaction_id == transaction_id)
            if office_id:
                q = q.filter(ContainerTracking.office_id == office_id)
            if search:
                like = f"%{search}%"
                q = q.filter(or_(
                    ContainerTracking.container_no.ilike(like),
                    ContainerTracking.bl_number.ilike(like),
                    ContainerTracking.booking_no.ilike(like),
                    ContainerTracking.vessel_name.ilike(like),
                    ContainerTracking.shipping_line.ilike(like),
                ))
            return (
                q.order_by(desc(ContainerTracking.updated_at))
                 .limit(limit).offset(offset)
                 .all()
            )

    def count(self, search: str = "", status: Optional[str] = None, office_id: Optional[int] = None) -> int:
        with self.get_session() as session:
            q = session.query(ContainerTracking)
            if status:
                q = q.filter(ContainerTracking.status == status)
            if office_id:
                q = q.filter(ContainerTracking.office_id == office_id)
            if search:
                like = f"%{search}%"
                q = q.filter(or_(
                    ContainerTracking.container_no.ilike(like),
                    ContainerTracking.bl_number.ilike(like),
                    ContainerTracking.booking_no.ilike(like),
                ))
            return q.count()

    def get_by_id(self, record_id: int) -> Optional[ContainerTracking]:
        with self.get_session() as session:
            return session.query(ContainerTracking).options(
                joinedload(ContainerTracking.transaction),
                joinedload(ContainerTracking.client),
                joinedload(ContainerTracking.entries),
            ).filter(ContainerTracking.id == record_id).first()

    def get_by_transaction(self, transaction_id: int) -> List[ContainerTracking]:
        with self.get_session() as session:
            return (
                session.query(ContainerTracking)
                .filter(ContainerTracking.transaction_id == transaction_id)
                .order_by(desc(ContainerTracking.updated_at))
                .all()
            )

    # ── إنشاء / تحديث / حذف ──────────────────────────────────────────────────

    def create(self, data: dict, current_user=None) -> ContainerTracking:
        """ينشئ كونتينر جديد من dict — يبني الـ instance أولاً ثم يحفظه."""
        obj = ContainerTracking(
            container_no      = data.get("container_no"),
            bl_number         = data.get("bl_number"),
            booking_no        = data.get("booking_no"),
            shipping_line     = data.get("shipping_line"),
            vessel_name       = data.get("vessel_name"),
            voyage_no         = data.get("voyage_no"),
            port_of_loading   = data.get("port_of_loading"),
            port_of_discharge = data.get("port_of_discharge"),
            final_destination = data.get("final_destination"),
            etd               = data.get("etd"),
            eta               = data.get("eta"),
            atd               = data.get("atd"),
            ata               = data.get("ata"),
            customs_date      = data.get("customs_date"),
            delivery_date     = data.get("delivery_date"),
            status            = data.get("status", "booked"),
            notes             = data.get("notes"),
            client_id         = data.get("client_id"),
            transaction_id    = data.get("transaction_id"),
            office_id         = data.get("office_id") or _get_current_office_id(),
        )
        return self.add(obj, current_user=current_user)

    def update(self, record_id: int, data: dict, current_user=None) -> Optional[ContainerTracking]:
        return super().update(record_id, data, current_user=current_user)

    def delete(self, record_id: int, current_user=None) -> bool:
        return super().delete(record_id, current_user=current_user)

    def update_status(self, record_id: int, status: str, current_user=None) -> bool:
        """تحديث الحالة فقط — shortcut."""
        result = super().update(record_id, {"status": status}, current_user=current_user)
        return result is not None

    # ── ربط الإدخالات ─────────────────────────────────────────────────────────

    def link_entries(self, container_id: int, entry_ids: list[int], current_user=None) -> bool:
        """إضافة إدخالات للكونتينر (يُضيف بدون تكرار)."""
        try:
            from database.models.entry import Entry
            with self.get_session() as session:
                container = session.query(ContainerTracking).filter(
                    ContainerTracking.id == container_id
                ).first()
                if not container:
                    return False
                existing_ids = {e.id for e in container.entries}
                new_entries = session.query(Entry).filter(
                    Entry.id.in_([eid for eid in entry_ids if eid not in existing_ids])
                ).all()
                container.entries.extend(new_entries)
                session.commit()
                return True
        except Exception as e:
            logger.error("link_entries error: %s", e)
            return False

    def unlink_entry(self, container_id: int, entry_id: int) -> bool:
        """إزالة إدخال واحد من الكونتينر."""
        try:
            from database.models.entry import Entry
            with self.get_session() as session:
                container = session.query(ContainerTracking).filter(
                    ContainerTracking.id == container_id
                ).first()
                if not container:
                    return False
                container.entries = [e for e in container.entries if e.id != entry_id]
                session.commit()
                return True
        except Exception as e:
            logger.error("unlink_entry error: %s", e)
            return False

    def get_entries(self, container_id: int) -> list:
        """إرجاع كل الإدخالات المرتبطة بكونتينر."""
        with self.get_session() as session:
            container = session.query(ContainerTracking).filter(
                ContainerTracking.id == container_id
            ).first()
            return list(container.entries) if container else []

    def get_containers_for_entries(self, entry_ids: list) -> dict:
        """
        Batch: يرجع dict {entry_id: [ContainerTracking, ...]}
        استدعاء واحد بدل N استدعاء — يحل مشكلة N+1 في EntriesTab.
        """
        if not entry_ids:
            return {}
        with self.get_session() as session:
            from database.models.container_tracking import container_entry_links
            rows = (
                session.query(ContainerTracking, container_entry_links.c.entry_id)
                .join(container_entry_links,
                      ContainerTracking.id == container_entry_links.c.container_id)
                .filter(container_entry_links.c.entry_id.in_(entry_ids))
                .all()
            )
            result: dict = {eid: [] for eid in entry_ids}
            for ct, eid in rows:
                result.setdefault(eid, []).append(ct)
            return result

    def get_containers_for_entry(self, entry_id: int) -> list[ContainerTracking]:
        """إرجاع كل الكونتينرات المرتبطة بإدخال معين."""
        with self.get_session() as session:
            from database.models.container_tracking import container_entry_links
            return (
                session.query(ContainerTracking)
                .join(container_entry_links,
                      ContainerTracking.id == container_entry_links.c.container_id)
                .filter(container_entry_links.c.entry_id == entry_id)
                .all()
            )