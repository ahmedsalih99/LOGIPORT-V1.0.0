"""
container_tracking_crud.py — LOGIPORT v2
==========================================
CRUD لجدول container_tracking + shipment_containers.
"""
from __future__ import annotations

import logging
from typing import List, Optional
from sqlalchemy import or_, desc
from sqlalchemy.orm import joinedload

from database.crud.base_crud import BaseCRUD
from database.models import get_session_local
from database.models.container_tracking import ContainerTracking, ShipmentContainer

logger = logging.getLogger(__name__)


def _get_current_office_id() -> Optional[int]:
    try:
        from core.settings_manager import SettingsManager
        user = SettingsManager.get_instance().get("user")
        if isinstance(user, dict):
            return user.get("office_id")
        return getattr(user, "office_id", None)
    except Exception:
        return None


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
        """إرجاع كل البوليصات مع فلترة اختيارية."""
        with self.get_session() as session:
            q = session.query(ContainerTracking).options(
                joinedload(ContainerTracking.client),
                joinedload(ContainerTracking.transaction),
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
                    ContainerTracking.bl_number.ilike(like),
                    ContainerTracking.shipping_line.ilike(like),
                    ContainerTracking.cargo_type.ilike(like),
                    ContainerTracking.origin_country.ilike(like),
                    ContainerTracking.port_of_discharge.ilike(like),
                ))
            from sqlalchemy.orm import make_transient
            results = (
                q.order_by(desc(ContainerTracking.updated_at))
                 .limit(limit).offset(offset)
                 .all()
            )
            for obj in results:
                if obj.client:
                    obj._client_name_ar = getattr(obj.client, "name_ar", "") or ""
                    obj._client_name_en = getattr(obj.client, "name_en", "") or ""
                if obj.transaction:
                    obj._transaction_no = getattr(obj.transaction, "transaction_no", "") or ""
                session.expunge(obj)
                make_transient(obj)
            return results

    def get_by_id(self, record_id: int) -> Optional[ContainerTracking]:
        """يُرجع البوليصة مع كل علاقاتها بما فيها الكونتينرات."""
        from sqlalchemy.orm import make_transient
        with self.get_session() as session:
            obj = session.query(ContainerTracking).options(
                joinedload(ContainerTracking.client),
                joinedload(ContainerTracking.transaction),
                joinedload(ContainerTracking.containers),
            ).filter(ContainerTracking.id == record_id).first()
            if obj is None:
                return None
            _ = obj.client
            _ = obj.transaction
            _ = obj.containers
            if obj.client:
                obj._client_name_ar = getattr(obj.client, "name_ar", "") or ""
                obj._client_name_en = getattr(obj.client, "name_en", "") or ""
            if obj.transaction:
                obj._transaction_no = getattr(obj.transaction, "transaction_no", "") or ""
            # نسخ بيانات الكونتينرات كـ plain dicts قبل إغلاق الـ session
            obj._containers_data = [
                {
                    "id":           c.id,
                    "container_no": c.container_no or "",
                    "seal_no":      c.seal_no      or "",
                    "recipient":    c.recipient    or "",
                }
                for c in (obj.containers or [])
            ]
            session.expunge(obj)
            make_transient(obj)
            return obj

    def get_by_transaction(self, transaction_id: int) -> List[ContainerTracking]:
        with self.get_session() as session:
            return (
                session.query(ContainerTracking)
                .filter(ContainerTracking.transaction_id == transaction_id)
                .order_by(desc(ContainerTracking.updated_at))
                .all()
            )

    def count(
        self, search: str = "",
        status: Optional[str] = None,
        office_id: Optional[int] = None,
    ) -> int:
        with self.get_session() as session:
            q = session.query(ContainerTracking)
            if status:
                q = q.filter(ContainerTracking.status == status)
            if office_id:
                q = q.filter(ContainerTracking.office_id == office_id)
            if search:
                like = f"%{search}%"
                q = q.filter(or_(
                    ContainerTracking.bl_number.ilike(like),
                    ContainerTracking.shipping_line.ilike(like),
                ))
            return q.count()

    # ── إنشاء / تحديث / حذف ──────────────────────────────────────────────────

    def create(self, data: dict, current_user=None) -> ContainerTracking:
        """ينشئ بوليصة جديدة مع كونتينراتها اختيارياً."""
        containers_data = data.pop("containers", [])
        obj = ContainerTracking(
            bl_number          = data.get("bl_number"),
            shipping_line      = data.get("shipping_line"),
            cargo_type         = data.get("cargo_type"),
            quantity           = data.get("quantity"),
            origin_country     = data.get("origin_country"),
            port_of_discharge  = data.get("port_of_discharge"),
            containers_count   = data.get("containers_count"),
            docs_delivered     = bool(data.get("docs_delivered", False)),
            cargo_tracking     = data.get("cargo_tracking"),
            docs_received_date = data.get("docs_received_date"),
            bl_status          = data.get("bl_status"),
            eta                = data.get("eta"),
            status             = data.get("status", "booked"),
            notes              = data.get("notes"),
            client_id          = data.get("client_id"),
            transaction_id     = data.get("transaction_id"),
            office_id          = data.get("office_id") or _get_current_office_id(),
        )
        # إضافة الكونتينرات
        for c in containers_data:
            obj.containers.append(ShipmentContainer(
                container_no = c.get("container_no") or "",
                seal_no      = c.get("seal_no")      or None,
                recipient    = c.get("recipient")    or None,
            ))
        return self.add(obj, current_user=current_user)

    def update(self, record_id: int, data: dict, current_user=None) -> Optional[ContainerTracking]:
        """يُحدّث البوليصة — إذا أُرسلت containers تُستبدل بالكاملة."""
        containers_data = data.pop("containers", None)
        result = super().update(record_id, data, current_user=current_user)
        if result is not None and containers_data is not None:
            self._replace_containers(record_id, containers_data)
        return result

    def _replace_containers(self, shipment_id: int, containers_data: list):
        """يحذف الكونتينرات الموجودة ويُعيد إنشاءها من الـ list الجديدة."""
        with self.get_session() as session:
            session.query(ShipmentContainer).filter(
                ShipmentContainer.shipment_id == shipment_id
            ).delete()
            for c in containers_data:
                session.add(ShipmentContainer(
                    shipment_id  = shipment_id,
                    container_no = c.get("container_no") or "",
                    seal_no      = c.get("seal_no")      or None,
                    recipient    = c.get("recipient")    or None,
                ))
            session.commit()

    def delete(self, record_id: int, current_user=None) -> bool:
        return super().delete(record_id, current_user=current_user)

    def update_status(self, record_id: int, status: str, current_user=None) -> bool:
        result = super().update(record_id, {"status": status}, current_user=current_user)
        return result is not None