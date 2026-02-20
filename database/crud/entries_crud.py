from typing import List, Optional, Dict, Any, Iterable, Tuple
import logging

logger = logging.getLogger(__name__)

from datetime import date, datetime
from sqlalchemy import func, select, desc, asc
from sqlalchemy.orm import joinedload, selectinload
from database.models import get_session_local
from database.models.entry import Entry
from database.models.entry_item import EntryItem
from database.models.client import Client
from typing import List, Optional, Dict, Any, Iterable, Tuple


class EntriesCRUD:
    @staticmethod
    def _to_date(val) -> Optional[date]:
        if val in (None, "", 0):
            return None
        if isinstance(val, date) and not isinstance(val, datetime):
            return val
        try:
            from PySide6.QtCore import QDate  # import lazy
            if isinstance(val, QDate):
                if val.isValid():
                    return date(val.year(), val.month(), val.day())
                return None
        except Exception:
            pass
        # datetime
        if isinstance(val, datetime):
            return val.date()
        # string
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(s, fmt).date()
                except Exception:
                    continue
            # ISO 8601
            try:
                return date.fromisoformat(s)
            except Exception:
                return None
        return None

    # ---------- قراءة قائمة مع تجميع الإجماليات ----------
    @staticmethod
    def list(limit: int = 200, offset: int = 0, date_from=None, date_to=None, client_id=None) -> List[Entry]:
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            q = (
                select(Entry)
                .options(
                    selectinload(Entry.items).selectinload(EntryItem.material),
                    selectinload(Entry.items).selectinload(EntryItem.packaging_type),
                    selectinload(Entry.items).selectinload(EntryItem.origin_country),
                )
            )
            if date_from:
                try:
                    from datetime import date as _d
                    q = q.where(Entry.entry_date >= _d.fromisoformat(str(date_from)))
                except Exception:
                    pass
            if date_to:
                try:
                    from datetime import date as _d
                    q = q.where(Entry.entry_date <= _d.fromisoformat(str(date_to)))
                except Exception:
                    pass
            if client_id:
                q = q.where(Entry.owner_client_id == int(client_id))
            q = q.order_by(desc(Entry.entry_date), desc(Entry.id)).limit(limit).offset(offset)
            return list(s.scalars(q))

    # ---------- قراءة واحدة ----------
    def get(self, entry_id: int) -> Optional[Entry]:
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            return (
                s.query(Entry)
                .options(
                    joinedload(Entry.owner_client),
                    joinedload(Entry.created_by),
                    joinedload(Entry.updated_by),
                    selectinload(Entry.items)
                    .joinedload(EntryItem.material),
                )
                .filter(Entry.id == entry_id)
                .first()
            )

    @staticmethod
    def get_by_id(entry_id: int) -> Optional[Entry]:
        if not entry_id:
            return None
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            q = (
                select(Entry)
                .where(Entry.id == entry_id)
                .options(
                    selectinload(Entry.items).selectinload(EntryItem.material),
                    selectinload(Entry.items).selectinload(EntryItem.packaging_type),
                    selectinload(Entry.items).selectinload(EntryItem.origin_country),
                )
            )
            return s.scalars(q).first()
    # ---------- إنشاء ----------
    def create(
            self,
            header: Dict[str, Any],
            items: List[Dict[str, Any]],
            user_id: Optional[int] = None,
    ):
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            e = Entry(
                entry_no=header.get("entry_no"),
                entry_date=self._to_date(header.get("entry_date")),
                transport_unit_type=header.get("transport_unit_type"),
                transport_ref=header.get("transport_ref"),
                seal_no=header.get("seal_no"),
                owner_client_id=header.get("owner_client_id"),
                notes=header.get("notes"),
                created_by_id=user_id,
                updated_by_id=user_id,
            )
            s.add(e)
            s.flush()  # للحصول على e.id

            for it in (items or []):
                item = EntryItem(
                    entry_id=e.id,
                    material_id=it.get("material_id"),
                    packaging_type_id=it.get("packaging_type_id"),
                    count=it.get("count") or 0,
                    net_weight_kg=it.get("net_weight_kg") or 0.0,
                    gross_weight_kg=it.get("gross_weight_kg") or 0.0,
                    mfg_date=self._to_date(it.get("mfg_date")),
                    exp_date=self._to_date(it.get("exp_date")),
                    origin_country_id=it.get("origin_country_id"),
                    batch_no=it.get("batch_no"),
                    notes=it.get("notes"),
                    created_by_id=user_id,
                    updated_by_id=user_id,
                )
                s.add(item)

            s.commit()
            return e.id

    def update(
            self,
            entry_id: int,
            header: Dict[str, Any],
            items: List[Dict[str, Any]],
            user_id: Optional[int] = None,
    ):
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            e: Entry | None = s.query(Entry).filter(Entry.id == entry_id).first()
            if not e:
                return False

            e.entry_no = header.get("entry_no")
            e.entry_date = self._to_date(header.get("entry_date"))
            e.transport_unit_type = header.get("transport_unit_type")
            e.transport_ref = header.get("transport_ref")
            e.seal_no = header.get("seal_no")
            #e.warehouse = header.get("warehouse")
            #e.location_note = header.get("location_note")
            e.owner_client_id = header.get("owner_client_id")
            e.notes = header.get("notes")
            e.updated_by_id = user_id

            # سياسة بسيطة: احذف البنود القديمة ثم أضف الجديدة
            s.query(EntryItem).filter(EntryItem.entry_id == e.id).delete()

            for it in (items or []):
                s.add(EntryItem(
                    entry_id=e.id,
                    material_id=it.get("material_id"),
                    packaging_type_id=it.get("packaging_type_id"),
                    count=it.get("count") or 0,
                    net_weight_kg=it.get("net_weight_kg") or 0.0,
                    gross_weight_kg=it.get("gross_weight_kg") or 0.0,
                    mfg_date=self._to_date(it.get("mfg_date")),
                    exp_date=self._to_date(it.get("exp_date")),
                    origin_country_id=it.get("origin_country_id"),
                    batch_no=it.get("batch_no"),
                    notes=it.get("notes"),
                    created_by_id=user_id,
                    updated_by_id=user_id,
                ))

            s.commit()
            return True

    # ---------- حذف ----------
    def delete(self, entry_id: int) -> bool:
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            # حذف العناصر أوتوماتيك عبر cascade
            cnt = s.query(Entry).filter(Entry.id == entry_id).delete(synchronize_session=False)
            s.commit()
            return cnt > 0

    # ---------- تجميع سريع للإجماليات (لعرض الجدول) ----------
    def totals_for(self, entry_id: int) -> Dict[str, Any]:
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            row = (
                s.query(
                    func.count(EntryItem.id),
                    func.coalesce(func.sum(EntryItem.count), 0),
                    func.coalesce(func.sum(EntryItem.net_weight_kg), 0),
                    func.coalesce(func.sum(EntryItem.gross_weight_kg), 0),
                )
                .filter(EntryItem.entry_id == entry_id)
                .first()
            )
            return {
                "items_count": int(row[0] or 0),
                "total_pcs": float(row[1] or 0),
                "total_net": float(row[2] or 0),
                "total_gross": float(row[3] or 0),
            }

    def get_with_details(self, entry_id: int):
        """
        يرجّع Entry مُحمّلًا بكل التفاصيل اللازمة للعرض، بدون Lazy Loads لاحقة.
        """
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            e = (
                s.query(Entry)
                .options(
                    # حمّل البنود
                    selectinload(Entry.items)
                    .selectinload(EntryItem.material),
                    selectinload(Entry.items)
                    .selectinload(EntryItem.packaging_type),
                    selectinload(Entry.items)
                    .selectinload(EntryItem.origin_country),
                    # علاقات الترويسة المفيدة للعرض
                    joinedload(Entry.owner_client),
                    joinedload(Entry.created_by),
                    joinedload(Entry.updated_by),
                )
                .filter(Entry.id == entry_id)
                .first()
            )
            # فك ارتباطهم عن الجلسة – بس بعد ما صار كلشي محمّل
            if e is not None:
                s.expunge_all()
            return e

    # ---------- إرجاع عناصر مجموعة إدخالات (ORM objects) ----------
    def get_items_for_entries(self, entry_ids: List[int]):
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            q = s.query(EntryItem).filter(EntryItem.entry_id.in_(entry_ids or [-1]))
            return q.all()

    # ---------- واجهات مخصّصة لعارض الانتقاء ----------
    def list_for_picker(self, limit: int = 500) -> List[Dict[str, Any]]:

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            # إجمالي الوزن الصافي لكل إدخال
            totals_subq = (
                s.query(
                    EntryItem.entry_id.label("eid"),
                    func.coalesce(func.sum(EntryItem.net_weight_kg), 0.0).label("total_net_kg"),
                )
                .group_by(EntryItem.entry_id)
                .subquery()
            )

            q = (
                s.query(
                    Entry.id,  # 0 -> eid
                    Entry.entry_no,  # 1 -> eno (قديم/رقمي)
                    Entry.transport_ref,  # 2 -> tref (رقم الحاوية/اللوحة)
                    Client.name_ar,  # 3 -> cn_ar
                    Client.name_en,  # 4 -> cn_en
                    Client.name_tr,  # 5 -> cn_tr
                    func.coalesce(totals_subq.c.total_net_kg, 0.0),  # 6 -> tnet
                )
                .outerjoin(Client, Client.id == Entry.owner_client_id)
                .outerjoin(totals_subq, totals_subq.c.eid == Entry.id)
                .order_by(desc(Entry.id))
                .limit(limit)
            )

            out: List[Dict[str, Any]] = []
            for (eid, eno, tref, cn_ar, cn_en, cn_tr, tnet) in q.all():
                client_name = cn_ar or cn_en or cn_tr
                # نفضّل transport_ref كرقم الإدخال المعروض
                display_no = tref or eno
                out.append({
                    "id": eid,
                    "entry_no": eno,  # للإبقاء على الحقل القديم إن احتاجته واجهات أخرى
                    "transport_ref": tref,  # الرقم الحقيقي (حاوية/لوحة)
                    "truck_or_container_no": tref,  # للتوافق الخلفي إن أردت
                    "client_name": client_name,
                    "total_net_kg": float(tnet or 0.0),
                    # بإمكانك إضافة أي حقول إضافية هنا عند الحاجة
                })
            return out

    @staticmethod
    def get_items_for_entry(entry_id: int) -> List[EntryItem]:
        SessionLocal = get_session_local()  # ← خُذ الـ factory
        with SessionLocal() as s:  # ← افتح Session فعلي
            q = (
                select(EntryItem)
                .where(EntryItem.entry_id == entry_id)
                .options(
                    selectinload(EntryItem.material),
                    selectinload(EntryItem.packaging_type),
                    selectinload(EntryItem.origin_country),
                )
            )
            return list(s.scalars(q))

    @staticmethod
    def compute_totals(items: Iterable[EntryItem]) -> Dict[str, float]:
        items = items or []
        total_pcs = sum(float(getattr(it, "count", 0) or 0) for it in items)
        total_gross = sum(float(getattr(it, "gross_weight_kg", 0) or 0) for it in items)
        total_net = sum(float(getattr(it, "net_weight_kg", 0) or 0) for it in items)
        return {"total_pcs": total_pcs, "total_gross": total_gross, "total_net": total_net}

    def list_with_totals(
            self,
            limit: int = 1000,
            offset: int = 0,
            date_from=None,
            date_to=None
    ) -> List[Dict[str, Any]]:
        """
        إرجاع قائمة الإدخالات مع إجمالياتها وبيانات العميل كـ object.
        ✅ owner_client_obj يحتوي على id واسم العميل بعدة لغات.
        """
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            # Subquery لإجماليات البنود لكل إدخال
            totals_sq = (
                select(
                    EntryItem.entry_id.label("eid"),
                    func.count(EntryItem.id).label("items_count"),
                    func.coalesce(func.sum(EntryItem.count), 0).label("total_pcs"),
                    func.coalesce(func.sum(EntryItem.net_weight_kg), 0.0).label("total_net"),
                    func.coalesce(func.sum(EntryItem.gross_weight_kg), 0.0).label("total_gross"),
                )
                .group_by(EntryItem.entry_id)
                .subquery()
            )

            # Query رئيسية
            q = (
                select(
                    Entry.id,
                    Entry.entry_no,
                    Entry.entry_date,
                    Entry.transport_unit_type,
                    Entry.transport_ref,
                    Entry.created_by_id, Entry.created_at,
                    Entry.updated_by_id, Entry.updated_at,
                    Client.id, Client.name_ar, Client.name_en, Client.name_tr,
                    totals_sq.c.items_count,
                    totals_sq.c.total_pcs,
                    totals_sq.c.total_net,
                    totals_sq.c.total_gross,
                )
                .outerjoin(Client, Client.id == Entry.owner_client_id)
                .outerjoin(totals_sq, totals_sq.c.eid == Entry.id)
            )

            # تطبيق الفلاتر حسب التاريخ
            if date_from:
                try:
                    from datetime import date as _d
                    q = q.where(Entry.entry_date >= _d.fromisoformat(str(date_from)))
                except Exception:
                    pass
            if date_to:
                try:
                    from datetime import date as _d
                    q = q.where(Entry.entry_date <= _d.fromisoformat(str(date_to)))
                except Exception:
                    pass

            # ترتيب وحدود النتائج
            q = q.order_by(desc(Entry.entry_date), desc(Entry.id)).limit(limit).offset(offset)
            rows = s.execute(q).all()

            # بناء القائمة النهائية
            out = []
            for (
                    eid, entry_no, entry_date, tut, tref,
                    cby, cat, uby, uat,
                    cid, cn_ar, cn_en, cn_tr,
                    items_count, total_pcs, total_net, total_gross
            ) in rows:
                client_obj = {
                    "id": cid,
                    "name_ar": cn_ar,
                    "name_en": cn_en,
                    "name_tr": cn_tr
                } if cid else None

                out.append({
                    "id": eid,
                    "entry_no": entry_no,
                    "entry_date": entry_date,
                    "transport_unit_type": tut,
                    "transport_ref": tref,
                    "owner_client_obj": client_obj,  # ✅ object العميل
                    "items_count": int(items_count or 0),
                    "total_pcs": float(total_pcs or 0),
                    "total_net": float(total_net or 0.0),
                    "total_gross": float(total_gross or 0.0),
                    "created_by_id": cby,
                    "created_at": cat,
                    "updated_by_id": uby,
                    "updated_at": uat,
                })
            return out

    @staticmethod
    def get_all(limit: int = 500) -> List[Entry]:
        """جلب جميع الإدخالات"""
        return EntriesCRUD.list(limit=limit, offset=0)

    @staticmethod
    def get_with_items(entry_id: int):
        """
        جلب إدخال مع موادّه — يُعيد dicts بدل ORM objects
        لتجنب DetachedInstanceError بعد إغلاق الـ session.
        """
        if not entry_id:
            return None

        SessionLocal = get_session_local()
        with SessionLocal() as s:
            # جلب الإدخال
            entry_q = (
                select(Entry)
                .where(Entry.id == entry_id)
                .options(selectinload(Entry.owner_client))
            )
            entry = s.scalars(entry_q).first()
            if not entry:
                return None

            # نسخ بيانات الـ entry كـ dict داخل الـ session
            entry_dict = {c.name: getattr(entry, c.name, None)
                         for c in entry.__table__.columns}
            entry_dict["entry_no"]      = getattr(entry, "entry_no", None)
            entry_dict["transport_ref"] = getattr(entry, "transport_ref", None)
            entry_dict["id"]            = entry.id

            # جلب المواد
            items_q = (
                select(EntryItem)
                .where(EntryItem.entry_id == entry_id)
                .options(
                    selectinload(EntryItem.material),
                    selectinload(EntryItem.packaging_type),
                    selectinload(EntryItem.origin_country),
                )
            )
            orm_items = list(s.scalars(items_q))

            # نسخ بيانات كل item كـ dict داخل الـ session
            items_dicts = []
            for it in orm_items:
                d = {c.name: getattr(it, c.name, None)
                     for c in it.__table__.columns}
                # أضف حقول العلاقات الضرورية
                d["material_id"]       = getattr(it, "material_id", None)
                d["packaging_type_id"] = getattr(it, "packaging_type_id", None)
                d["currency_id"]       = getattr(it, "currency_id", None)
                d["pricing_type_id"]   = getattr(it, "pricing_type_id", None)
                d["unit_price"]        = getattr(it, "unit_price", None)
                d["count"]             = getattr(it, "count", None)
                d["gross_weight_kg"]   = getattr(it, "gross_weight_kg", None)
                d["net_weight_kg"]     = getattr(it, "net_weight_kg", None)
                d["production_date"]   = getattr(it, "production_date", None)
                d["expiry_date"]       = getattr(it, "expiry_date", None)
                d["id"]                = it.id
                items_dicts.append(d)

            return (entry_dict, items_dicts)