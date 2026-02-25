from typing import Any, Dict, List, Optional, Iterable, Tuple
import logging

logger = logging.getLogger(__name__)


from sqlalchemy import select, func, text as _sql_text
from sqlalchemy.orm import Session
from services.numbering_service import NumberingService

from database.models import get_session_local
from database.models.transport_details import TransportDetails
from database.crud.base_crud_v5 import BaseCRUD_V5 as BaseCRUD

# Models (import robustly for runtime)
try:
    from database.models.transaction import Transaction, TransactionItem, TransactionEntry  # type: ignore
    from database.models.entry_item import EntryItem
except Exception:
    # Real models are present at runtime
    pass

# PricingType import (support both aggregator and module path)
try:
    from database.models import PricingType  # type: ignore
except Exception:
    try:
        from database.models.pricing_type import PricingType  # type: ignore
    except Exception:
        PricingType = None  # type: ignore


_MANUAL_NO_ALIASES = (
    "transaction_no", "transactionNo", "trx_no", "trxNo",
    "no", "number", "doc_no", "docNo", "code",
)


def _norm_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    # treat placeholders as empty
    if s in {"", "-", "—", "None", "null", "AUTO", "auto"}:
        return ""
    return s


def _extract_manual_no(data: Dict[str, Any]) -> str:
    # direct keys
    for k in _MANUAL_NO_ALIASES:
        if k in data:
            s = _norm_str(data.get(k))
            if s:
                return s
    # nested dicts (e.g., {"transaction": {"number": "..."}})
    for nest_key in ("transaction", "trx", "header"):
        nested = data.get(nest_key)
        if isinstance(nested, dict):
            for k in _MANUAL_NO_ALIASES:
                if k in nested:
                    s = _norm_str(nested.get(k))
                    if s:
                        return s
    return ""


def _get_pricing_code_by_id(session: Session) -> Dict[int, str]:
    """Return map {pricing_type_id: CODE} (uppercased) from DB. No assumptions."""
    rows: List[Tuple[int, Optional[str]]] = []
    if PricingType is not None:
        try:
            rows = session.query(PricingType.id, PricingType.code).all()  # type: ignore
        except Exception:
            rows = []
    if not rows:
        # Fallback to raw SQL if ORM class import failed
        rows = [tuple(r) for r in session.execute(_sql_text("SELECT id, code FROM pricing_types")).fetchall()]  # type: ignore
    return {int(r[0]): (r[1] or "").upper() for r in rows}

def _get_pricing_formula_by_id(session) -> Dict[int, tuple]:
    """
    Map: {pricing_type_id: (compute_by, price_unit, divisor)}
    compute_by in {'QTY','NET','GROSS'}, price_unit in {'UNIT','KG','TON'}, divisor: float
    """
    rows = []
    try:
        # إن كان ORM متاح وفيه الأعمدة
        if PricingType is not None and hasattr(PricingType, 'compute_by'):
            rows = session.query(
                PricingType.id, PricingType.compute_by, PricingType.price_unit, PricingType.divisor
            ).all()
        else:
            rows = [tuple(r) for r in session.execute(
                _sql_text("SELECT id, compute_by, price_unit, divisor FROM pricing_types")
            ).fetchall()]
    except Exception:
        rows = []
    out = {}
    for rid, cb, pu, dv in rows:
        cb = (cb or "").upper()
        pu = (pu or "").upper()
        try:
            dv = float(dv) if dv is not None else 1.0
        except Exception:
            dv = 1.0
        out[int(rid)] = (cb, pu, dv)
    return out



class TransactionsCRUD(BaseCRUD):
    """CRUD for Transactions with strict, no-assumption semantics."""

    def __init__(self):
        super().__init__(Transaction, get_session_local)

    # -- Session helper ----------------------------------------------------
    def _SessionLocal(self):
        factory = self.session_factory

        # إذا كان دالة ترجع sessionmaker
        if callable(factory):
            factory = factory()

        # الآن factory هو sessionmaker
        return factory()  # ← هنا ننشئ Session حقيقية

    # -- Create (safe override) -------------------------------------------
    def create(self, data: Dict[str, Any], **kwargs) -> Transaction:
        """Ensure any generic create() route respects manual number too."""
        return self.create_transaction(
            data=data,
            items=kwargs.get("items"),
            entry_ids=kwargs.get("entry_ids"),
            user_id=kwargs.get("user_id"),
            number_prefix=kwargs.get("number_prefix", "T"),
        )


    # ─────────────────────────────────────────────────────────────────────
    # Transport Details helpers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _save_transport_details(session, transaction_id: int, transport: dict):
        """
        يحفظ أو يُحدِّث TransportDetails لمعاملة.
        إذا كانت كل القيم None → لا يفعل شيئاً.
        """
        if not transport or not any(transport.values()):
            return

        td = session.query(TransportDetails).filter_by(
            transaction_id=transaction_id
        ).first()

        if td is None:
            td = TransportDetails(transaction_id=transaction_id)
            session.add(td)

        for field, value in transport.items():
            if hasattr(td, field):
                setattr(td, field, value)

    def create_transaction(
            self,
            *,
            data: Dict[str, Any],
            items: List[Dict[str, Any]] | None = None,
            entry_ids: Iterable[int] | None = None,
            user_id: Optional[int] = None,
            number_prefix: str = "T",
    ) -> Transaction:

        with self._SessionLocal() as s:
            # 1) Determine transaction number (manual or auto)
            manual_no = _extract_manual_no(data)
            if manual_no:
                exists = s.execute(
                    select(func.count()).select_from(Transaction).where(Transaction.transaction_no == manual_no)
                ).scalar_one()
                if exists:
                    raise ValueError(f"Transaction number '{manual_no}' already exists")
                trx_no = manual_no
            else:
                trx_no = NumberingService.get_next_transaction_number(s)

            # 2) Create transaction head (status removed)
            trx = Transaction(
                transaction_no=trx_no,
                transaction_date=data.get("transaction_date"),
                transaction_type=data.get("transaction_type"),
                client_id=data.get("client_id"),
                exporter_company_id=data.get("exporter_company_id"),
                importer_company_id=data.get("importer_company_id"),
                relationship_type=data.get("relationship_type"),
                broker_company_id=data.get("broker_company_id"),
                origin_country_id=data.get("origin_country_id"),
                dest_country_id=data.get("dest_country_id"),
                currency_id=data.get("currency_id"),
                pricing_type_id=data.get("pricing_type_id"),
                delivery_method_id=data.get("delivery_method_id"),
                transport_type=data.get("transport_type"),
                transport_ref=data.get("transport_ref"),
                notes=data.get("notes"),
                created_by_id=user_id,
                updated_by_id=user_id,
            )
            s.add(trx)
            s.flush()  # ensure trx.id

            # 3) Link entries (explicit + from items)
            linked_ids: set[int] = set()
            if entry_ids:
                for eid in entry_ids:
                    try:
                        eid_i = int(eid) if eid is not None else None
                        if eid_i:
                            linked_ids.add(eid_i)
                    except Exception:
                        pass
            if items:
                for it in items:
                    try:
                        eid = it.get("entry_id")
                        eid_i = int(eid) if eid is not None else None
                        if eid_i:
                            linked_ids.add(eid_i)
                    except Exception:
                        pass
            for eid in sorted(linked_ids):
                s.add(TransactionEntry(transaction_id=trx.id, entry_id=eid))

            # 4) Items & totals
            total_qty = total_gross = total_net = total_val = 0.0

            def _f(x, default=0.0):
                try:
                    return float(x)
                except Exception:
                    return float(default)

            # Fallback by code (old behavior)
            pt_code_map = _get_pricing_code_by_id(s)

            # Formula map from DB (new behavior). If columns not present or NULL, will be empty -> fallback kicks in.
            form_map = _get_pricing_formula_by_id(s)

            def _pricing_code(item: Dict[str, Any]) -> str:
                pid = item.get("pricing_type_id")
                if pid is None:
                    raise ValueError("pricing_type_id is required for each item")
                code = (pt_code_map.get(int(pid)) or "").upper()
                if not code:
                    raise ValueError(f"Missing pricing_type code for id={pid}")
                return code

            def _calc_total_from_formula(item: Dict[str, Any], price: float) -> float:
                pid = item.get("pricing_type_id")  # ← كان ناقص
                if pid is not None and int(pid) in form_map:
                    cb, _pu, dv = form_map[int(pid)]
                    qty = _f(item.get("quantity"))
                    net = _f(item.get("net_weight_kg"))
                    gross = _f(item.get("gross_weight_kg"))
                    base = qty if cb == "QTY" else (net if cb == "NET" else gross if cb == "GROSS" else 0.0)
                    return (base / (dv or 1.0)) * price

                # === Fallback بالكود إذا ما توفرت الصيغة من الجدول ===
                code = _pricing_code(item)
                qty = _f(item.get("quantity"))
                net = _f(item.get("net_weight_kg"))
                gross = _f(item.get("gross_weight_kg"))
                if code in ("UNIT", "PCS", "PIECE"):
                    return qty * price
                if code in ("KG", "KILO", "KG_NET"):
                    return net * price
                if code in ("KG_GROSS", "GROSS", "BRUT"):
                    return gross * price
                if code in ("TON", "T", "MT", "TON_NET"):
                    return (net / 1000.0) * price
                if code in ("TON_GROSS",):
                    return (gross / 1000.0) * price
                return qty * price

            if items:
                for it in items:
                    # strict required fields (unit_label removed)
                    if it.get("currency_id") is None:
                        raise ValueError("currency_id is required for each item")
                    if it.get("pricing_type_id") is None:
                        raise ValueError("pricing_type_id is required for each item")
                    if it.get("packaging_type_id") is None:
                        raise ValueError("packaging_type_id is required for each item")
                    if it.get("unit_price") in (None, "", 0, 0.0):
                        raise ValueError("unit_price is required and must be > 0 for each item")

                    qty = _f(it.get("quantity"))
                    gross = _f(it.get("gross_weight_kg"))
                    net = _f(it.get("net_weight_kg"))
                    price = _f(it.get("unit_price"))

                    # respect provided total if present & numeric, else compute
                    lt = it.get("line_total", it.get("total_price"))
                    try:
                        line_total = float(lt) if lt is not None else None
                    except Exception:
                        line_total = None
                    if line_total is None:
                        line_total = _calc_total_from_formula(it, price)

                    row = TransactionItem(
                        transaction_id=trx.id,
                        entry_id=it.get("entry_id"),
                        entry_item_id=it.get("entry_item_id"),
                        material_id=it.get("material_id"),
                        packaging_type_id=it.get("packaging_type_id"),
                        quantity=qty,
                        gross_weight_kg=gross,
                        net_weight_kg=net,
                        pricing_type_id=it.get("pricing_type_id"),
                        unit_price=price,
                        currency_id=it.get("currency_id"),
                        line_total=_f(line_total),
                        origin_country_id=it.get("origin_country_id"),
                        source_type=it.get("source") or it.get("source_type") or (
                            "manual" if it.get("is_manual") else "entry"),
                        is_manual=bool(it.get("is_manual")),
                        notes=it.get("notes"),
                        # 👇 الجديد: خزّن رقم السيارة/الكونتينر
                        transport_ref=(it.get("transport_ref") or it.get("truck_or_container_no")),
                        created_by_id=user_id,
                        updated_by_id=user_id,
                    )
                    s.add(row)

                    total_qty += qty
                    total_gross += gross
                    total_net += net
                    total_val += _f(line_total)

            # 5) Cache totals on head
            trx.totals_count = total_qty
            trx.totals_gross_kg = total_gross
            trx.totals_net_kg = total_net
            trx.totals_value = total_val

            # 6) Transport details (CMR / Form A) — اختياري
            if data.get("transport"):
                self._save_transport_details(s, trx.id, data["transport"])

            s.commit()
            s.refresh(trx)
            return trx

    # -- Update (override) -------------------------------------------------
    def update(self, obj_id: int, data: Dict[str, Any], current_user: Dict[str, Any] | None = None):
        """Avoid writing blank numbers; enforce uniqueness if changing the number."""
        payload = dict(data or {})
        with self._SessionLocal() as s:
            t = s.get(Transaction, obj_id)
            if not t:
                return None

            if "transaction_no" in payload or any(a in payload for a in _MANUAL_NO_ALIASES if a != "transaction_no"):
                # unify to transaction_no
                raw_no = _extract_manual_no(payload)
                if not raw_no:
                    payload.pop("transaction_no", None)  # ignore
                    for a in _MANUAL_NO_ALIASES:
                        payload.pop(a, None)
                elif raw_no != (t.transaction_no or ""):
                    exists = s.execute(
                        select(func.count()).select_from(Transaction).where(
                            Transaction.transaction_no == raw_no, Transaction.id != obj_id
                        )
                    ).scalar_one()
                    if exists:
                        raise ValueError(f"Transaction number '{raw_no}' already exists")
                    t.transaction_no = raw_no
                # cleanup aliases
                for a in _MANUAL_NO_ALIASES:
                    payload.pop(a, None)

            for k, v in list(payload.items()):
                if k == "transaction_no":
                    continue
                setattr(t, k, v)

            if current_user and current_user.get("id"):
                t.updated_by_id = current_user.get("id")

            s.commit()
            s.refresh(t)
            return t

    def update_transaction_with_items(
            self,
            trx_id: int,
            *,
            data: Dict[str, Any],
            items: List[Dict[str, Any]] | None = None,
            entry_ids: Iterable[int] | None = None,
            user_id: Optional[int] = None,
    ):
        """يحدّث رأس المعاملة ويستبدل العناصر وروابط الإدخالات بالكامل ثم يعيد احتساب الإجماليات."""
        with self._SessionLocal() as s:
            t = s.get(Transaction, trx_id)
            if not t:
                return None

            # --- 1) تحديث الهيدر (نفس منطق update مع حماية رقم المعاملة) ---
            payload = dict(data or {})
            # توحيد رقم المعاملة إن أُرسل بأي مفتاح معروف
            raw_no = _extract_manual_no(payload)
            if raw_no:
                exists = s.execute(
                    select(func.count()).select_from(Transaction).where(
                        Transaction.transaction_no == raw_no, Transaction.id != trx_id
                    )
                ).scalar_one()
                if exists:
                    raise ValueError(f"Transaction number '{raw_no}' already exists")
                t.transaction_no = raw_no
            # نظّف أي مفاتيح بديلة للرقم
            for a in _MANUAL_NO_ALIASES:
                payload.pop(a, None)
            payload.pop("transaction_no", None)

            # طبّق بقية الحقول مباشرة على الرأس
            for k, v in payload.items():
                setattr(t, k, v)
            if user_id:
                t.updated_by_id = user_id

            # --- 2) استبدال روابط الإدخالات (transaction_entries) إن وُجدت ---
            s.query(TransactionEntry).filter(TransactionEntry.transaction_id == trx_id).delete(
                synchronize_session=False
            )
            if entry_ids:
                for eid in {int(e) for e in entry_ids if e is not None}:
                    s.add(TransactionEntry(transaction_id=trx_id, entry_id=eid))

            # --- 3) استبدال عناصر المعاملة بالكامل ---
            s.query(TransactionItem).filter(TransactionItem.transaction_id == trx_id).delete(
                synchronize_session=False
            )

            def _f(x, default=0.0):
                try:
                    return float(x)
                except Exception:
                    return float(default)

            # خريطة الأكواد القديمة + صيغ التسعير الجديدة من الجدول (إن وُجدت الأعمدة)
            pt_code_map = _get_pricing_code_by_id(s)

            form_map = _get_pricing_formula_by_id(s)

            def _calc_total(item: Dict[str, Any], price: float) -> float:
                pid = item.get("pricing_type_id")
                qty = _f(item.get("quantity"))
                net = _f(item.get("net_weight_kg"))
                gross = _f(item.get("gross_weight_kg"))
                if pid is not None and int(pid) in form_map:
                    cb, _pu, dv = form_map[int(pid)]
                    base = qty if cb == "QTY" else (net if cb == "NET" else gross if cb == "GROSS" else 0.0)
                    return (base / (dv or 1.0)) * price
                # fallback بالأكواد القديمة
                code = (pt_code_map.get(int(pid)) or "").upper() if pid is not None else ""
                if code in ("UNIT", "PCS", "PIECE"):
                    return qty * price
                if code in ("KG", "KILO", "KG_NET"):
                    return net * price
                if code in ("KG_GROSS", "GROSS", "BRUT"):
                    return gross * price
                if code in ("TON", "T", "MT", "TON_NET"):
                    return (net / 1000.0) * price
                if code in ("TON_GROSS",):
                    return (gross / 1000.0) * price
                return qty * price

            total_qty = total_gross = total_net = total_val = 0.0
            for it in (items or []):
                # تحقّقات أساسية (بدون unit_label)
                if it.get("currency_id") is None:
                    raise ValueError("currency_id is required for each item")
                if it.get("pricing_type_id") is None:
                    raise ValueError("pricing_type_id is required for each item")
                if it.get("packaging_type_id") is None:
                    raise ValueError("packaging_type_id is required for each item")
                if it.get("unit_price") in (None, "", 0, 0.0):
                    raise ValueError("unit_price is required and must be > 0 for each item")

                qty = _f(it.get("quantity"))
                gross = _f(it.get("gross_weight_kg"))
                net = _f(it.get("net_weight_kg"))
                price = _f(it.get("unit_price"))

                lt_in = it.get("line_total", it.get("total_price"))
                try:
                    line_total = float(lt_in) if lt_in is not None else None
                except Exception:
                    line_total = None
                if line_total is None:
                    line_total = _calc_total(it, price)

                row = TransactionItem(
                    transaction_id=trx_id,
                    entry_id=it.get("entry_id"),
                    entry_item_id=it.get("entry_item_id"),
                    material_id=it.get("material_id"),
                    packaging_type_id=it.get("packaging_type_id"),
                    quantity=qty,
                    gross_weight_kg=gross,
                    net_weight_kg=net,
                    pricing_type_id=it.get("pricing_type_id"),
                    unit_price=price,
                    currency_id=it.get("currency_id"),
                    line_total=_f(line_total),
                    origin_country_id=it.get("origin_country_id"),
                    source_type=it.get("source") or it.get("source_type") or (
                        "manual" if it.get("is_manual") else "entry"),
                    is_manual=bool(it.get("is_manual")),
                    notes=it.get("notes"),
                    # 👇 الجديد:
                    transport_ref=(it.get("transport_ref") or it.get("truck_or_container_no")),
                    created_by_id=user_id,
                    updated_by_id=user_id,
                )
                s.add(row)

                total_qty += qty
                total_gross += gross
                total_net += net
                total_val += _f(line_total)

            # --- 4) إجماليات الرأس ---
            t.totals_count = total_qty
            t.totals_gross_kg = total_gross
            t.totals_net_kg = total_net
            t.totals_value = total_val

            # --- 5) Transport details (CMR / Form A) ---
            if data.get("transport"):
                self._save_transport_details(s, trx_id, data["transport"])

            s.commit()
            s.refresh(t)
            return t

    # -- Facade helpers ----------------------------------------------------
    def update_transaction(self, trx_id: int, data: Dict[str, Any], user_id: Optional[int] = None) -> Optional[Transaction]:
        payload = dict(data or {})
        if user_id is not None:
            payload["updated_by_id"] = user_id
        return self.update(trx_id, payload, current_user={"id": user_id} if user_id is not None else None)

    def delete_transaction(self, trx_id: int) -> bool:
        result = self.delete(trx_id)
        if result:
            try:
                with self._SessionLocal() as s:
                    NumberingService.sync_last_number(s)
            except Exception as e:
                logger.warning(f"sync_last_number failed (non-critical): {e}")
        return result

    # -- Items helpers -----------------------------------------------------
    def add_items_from_entries(self, trx_id: int, entry_ids: Iterable[int], user_id: Optional[int] = None) -> int:
        ids = [int(e) for e in (entry_ids or []) if e is not None]
        if not ids:
            return 0
        with self._SessionLocal() as s:
            t = s.get(Transaction, trx_id)
            if not t:
                return 0

            # 👇 جديد: حمّل transport_ref لكل entry_id مرة واحدة (بدون الاعتماد على ORM Entry)
            entry_ref_map: dict[int, Optional[str]] = {}
            try:
                from database.models.entry import Entry
                rows_e = s.execute(
                    select(Entry.id, Entry.transport_ref).where(Entry.id.in_(ids))
                ).fetchall()
                entry_ref_map = {int(r[0]): (r[1] or None) for r in rows_e}
            except Exception:
                entry_ref_map = {}

            rows = s.execute(select(EntryItem).where(EntryItem.entry_id.in_(ids))).scalars().all()
            if not rows:
                return 0

            def _f(x, default=0.0):
                try:
                    return float(x)
                except Exception:
                    return float(default)

            # fallback by pricing code
            pt_code_map = _get_pricing_code_by_id(s)

            # formula map from DB (if added)
            form_map = _get_pricing_formula_by_id(s)

            def _pricing_code_by_id(pid: int) -> str:
                return (pt_code_map.get(int(pid)) or "").upper()

            def _calc_total(pid: int, qty: float, net: float, gross: float, price: float) -> float:
                f = form_map.get(int(pid))
                if f:
                    cb, _pu, dv = f
                    base = qty if cb == "QTY" else (net if cb == "NET" else gross if cb == "GROSS" else 0.0)
                    return (base / (dv or 1.0)) * price
                # Fallback بالكود
                code = _pricing_code_by_id(pid)
                if code in ("UNIT", "PCS", "PIECE"):
                    return qty * price
                if code in ("KG", "KILO", "KG_NET"):
                    return net * price
                if code in ("KG_GROSS", "GROSS", "BRUT"):
                    return gross * price
                if code in ("TON", "T", "MT", "TON_NET"):
                    return (net / 1000.0) * price
                if code in ("TON_GROSS",):
                    return (gross / 1000.0) * price
                return qty * price

            n = 0
            for r in rows:
                qty = _f(getattr(r, "count", None) or getattr(r, "quantity", None))
                price = _f(getattr(r, "unit_price", None))
                pid = getattr(r, "pricing_type_id", None)
                cid = getattr(r, "currency_id", None)
                if cid is None:
                    raise ValueError("currency_id is required on entry items when importing to a transaction")
                if pid is None:
                    raise ValueError("pricing_type_id is required on entry items when importing to a transaction")

                net = _f(getattr(r, "net_weight_kg", None))
                gross = _f(getattr(r, "gross_weight_kg", None))
                line_total = _calc_total(pid, qty, net, gross, price)

                it = TransactionItem(
                    transaction_id=trx_id,
                    entry_id=r.entry_id,
                    entry_item_id=r.id,
                    material_id=r.material_id,
                    packaging_type_id=getattr(r, "packaging_type_id", None),
                    quantity=qty,
                    gross_weight_kg=gross,
                    net_weight_kg=net,
                    pricing_type_id=pid,
                    unit_price=price,
                    currency_id=cid,
                    line_total=line_total,
                    origin_country_id=getattr(r, "origin_country_id", None),
                    source_type="entry",
                    is_manual=False,
                    notes=getattr(r, "notes", None),
                    created_by_id=user_id,
                    updated_by_id=user_id,
                )
                # 👇 جديد: خزّن مرجع النقل المأخوذ من الإدخال المرتبط
                try:
                    it.transport_ref = entry_ref_map.get(getattr(r, "entry_id", None))
                except Exception:
                    # لا توقف العملية إذا حصلت مشكلة غير متوقعة
                    pass

                s.add(it)
                n += 1

            totals = s.execute(
                select(
                    func.coalesce(func.sum(TransactionItem.quantity), 0.0),
                    func.coalesce(func.sum(TransactionItem.gross_weight_kg), 0.0),
                    func.coalesce(func.sum(TransactionItem.net_weight_kg), 0.0),
                    func.coalesce(func.sum(TransactionItem.line_total), 0.0),
                ).where(TransactionItem.transaction_id == trx_id)
            ).one()
            t.totals_count = float(totals[0] or 0.0)
            t.totals_gross_kg = float(totals[1] or 0.0)
            t.totals_net_kg = float(totals[2] or 0.0)
            t.totals_value = float(totals[3] or 0.0)
            s.commit()
            return n

    def add_manual_item(self, trx_id: int, item: Dict[str, Any], user_id: Optional[int] = None) -> TransactionItem:
        with self._SessionLocal() as s:
            def _f(x, default=0.0):
                try:
                    return float(x)
                except Exception:
                    return float(default)

            # fallback by pricing code
            pt_code_map = _get_pricing_code_by_id(s)

            # formula map from DB (if added)
            form_map = _get_pricing_formula_by_id(s)

            def _pricing_code_by_id(pid: int) -> str:
                return (pt_code_map.get(int(pid)) or "").upper()

            def _calc_total(pid: int, qty: float, net: float, gross: float, price: float) -> float:
                f = form_map.get(int(pid))
                if f:
                    cb, _pu, dv = f
                    base = qty if cb == "QTY" else (net if cb == "NET" else gross if cb == "GROSS" else 0.0)
                    return (base / (dv or 1.0)) * price
                code = _pricing_code_by_id(pid)
                if code in ("UNIT", "PCS", "PIECE"):
                    return qty * price
                if code in ("KG", "KILO", "KG_NET"):
                    return net * price
                if code in ("KG_GROSS", "GROSS", "BRUT"):
                    return gross * price
                if code in ("TON", "T", "MT", "TON_NET"):
                    return (net / 1000.0) * price
                if code in ("TON_GROSS",):
                    return (gross / 1000.0) * price
                return qty * price

            qty = _f(item.get("quantity"))
            price = _f(item.get("unit_price"))
            pid = item.get("pricing_type_id")
            cid = item.get("currency_id")
            if cid is None:
                raise ValueError("currency_id is required for manual items")
            if pid is None:
                raise ValueError("pricing_type_id is required for manual items")

            net = _f(item.get("net_weight_kg"))
            gross = _f(item.get("gross_weight_kg"))

            lt = item.get("line_total")
            try:
                line_total = float(lt) if lt is not None else None
            except Exception:
                line_total = None
            if line_total is None:
                line_total = _calc_total(pid, qty, net, gross, price)

            it = TransactionItem(
                transaction_id=trx_id,
                material_id=item.get("material_id"),
                packaging_type_id=item.get("packaging_type_id"),
                quantity=qty,
                gross_weight_kg=gross,
                net_weight_kg=net,
                pricing_type_id=pid,
                unit_price=price,
                currency_id=cid,
                line_total=float(line_total),
                origin_country_id=item.get("origin_country_id"),
                is_manual=True,
                source_type="manual",
                notes=item.get("notes"),
                created_by_id=user_id,
                updated_by_id=user_id,
            )
            s.add(it)

            totals = s.execute(
                select(
                    func.coalesce(func.sum(TransactionItem.quantity), 0.0),
                    func.coalesce(func.sum(TransactionItem.gross_weight_kg), 0.0),
                    func.coalesce(func.sum(TransactionItem.net_weight_kg), 0.0),
                    func.coalesce(func.sum(TransactionItem.line_total), 0.0),
                ).where(TransactionItem.transaction_id == trx_id)
            ).one()
            t = s.get(Transaction, trx_id)
            t.totals_count = float(totals[0] or 0.0)
            t.totals_gross_kg = float(totals[1] or 0.0)
            t.totals_net_kg = float(totals[2] or 0.0)
            t.totals_value = float(totals[3] or 0.0)
            s.commit()
            s.refresh(it)
            return it

    # -- Query helpers -----------------------------------------------------
    def list_transactions(
        self,
        *,
        client_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: Optional[str] = None,
        transaction_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Transaction]:
        """
        server-side filters:
          transaction_type : "export" | "import" | "transit"
          search           : يبحث في transaction_no (LIKE %search%)
        """
        with self._SessionLocal() as s:
            q = select(Transaction)
            if client_id:
                q = q.where(Transaction.client_id == client_id)
            if status:
                q = q.where(Transaction.status == status)
            if transaction_type:
                q = q.where(Transaction.transaction_type == transaction_type)
            if date_from:
                q = q.where(Transaction.transaction_date >= date_from)
            if date_to:
                q = q.where(Transaction.transaction_date <= date_to)
            if search:
                pattern = f"%{search}%"
                q = q.where(Transaction.transaction_no.ilike(pattern))
            q = q.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).limit(limit).offset(offset)
            return list(s.execute(q).scalars().all())

    def get_with_items(self, trx_id: int) -> Optional[Tuple[Transaction, List[TransactionItem]]]:
        with self._SessionLocal() as s:
            from sqlalchemy.orm import joinedload
            trx = s.execute(
                select(Transaction)
                .where(Transaction.id == trx_id)
                .options(joinedload(Transaction.items))
            ).unique().scalar_one_or_none()
            if not trx:
                return None
            items = list(trx.items)  # يُحمَّل داخل الـ session — آمن
            s.expunge_all()  # فصل الكائنات بأمان
            return trx, items

    # ─────────────────────────────────────────────────────────────────────
    # Workflow — Status Management
    # ─────────────────────────────────────────────────────────────────────

    # الحالات المسموح بها + الانتقالات القانونية
    VALID_STATUSES = {"draft", "active", "closed", "archived"}

    ALLOWED_TRANSITIONS = {
        "draft":    {"active"},                 # مسودة → نشطة
        "active":   {"closed", "draft"},        # نشطة → مغلقة أو إرجاع لمسودة
        "closed":   {"active", "archived"},     # مغلقة → إعادة فتح أو أرشفة
        "archived": set(),                      # مؤرشفة → نهائية (لا رجوع)
    }

    def change_status(
        self,
        trx_id: int,
        new_status: str,
        current_user=None,
    ) -> tuple[bool, str]:
        """
        يغيّر حالة المعاملة مع التحقق من الانتقال القانوني.
        يعيد (True, "") عند النجاح أو (False, error_message) عند الفشل.
        """
        if new_status not in self.VALID_STATUSES:
            return False, f"invalid_status: {new_status}"

        with self._SessionLocal() as s:
            t = s.get(Transaction, trx_id)
            if not t:
                return False, "transaction_not_found"

            current = t.status or "active"
            allowed = self.ALLOWED_TRANSITIONS.get(current, set())

            if new_status not in allowed:
                return False, f"transition_not_allowed:{current}→{new_status}"

            t.status = new_status
            if current_user:
                uid = (
                    current_user.get("id")
                    if isinstance(current_user, dict)
                    else getattr(current_user, "id", None)
                )
                if uid:
                    t.updated_by_id = uid

            s.commit()
            return True, ""

    def close_transaction(self, trx_id: int, current_user=None) -> tuple[bool, str]:
        return self.change_status(trx_id, "closed", current_user)

    def reopen_transaction(self, trx_id: int, current_user=None) -> tuple[bool, str]:
        return self.change_status(trx_id, "active", current_user)

    def archive_transaction(self, trx_id: int, current_user=None) -> tuple[bool, str]:
        return self.change_status(trx_id, "archived", current_user)

    def activate_draft(self, trx_id: int, current_user=None) -> tuple[bool, str]:
        """ترقية مسودة إلى نشطة."""
        return self.change_status(trx_id, "active", current_user)

    def recalc_totals(self, trx_id: int) -> bool:
        """Recompute and cache totals on the transaction head from its items."""
        with self._SessionLocal() as s:
            t = s.get(Transaction, trx_id)
            if not t:
                return False
            qty, gross, net, val = s.execute(
                select(
                    func.coalesce(func.sum(TransactionItem.quantity), 0.0),
                    func.coalesce(func.sum(TransactionItem.gross_weight_kg), 0.0),
                    func.coalesce(func.sum(TransactionItem.net_weight_kg), 0.0),
                    func.coalesce(func.sum(TransactionItem.line_total), 0.0),
                ).where(TransactionItem.transaction_id == trx_id)
            ).one()
            t.totals_count = float(qty or 0.0)
            t.totals_gross_kg = float(gross or 0.0)
            t.totals_net_kg = float(net or 0.0)
            t.totals_value = float(val or 0.0)
            s.commit()
            return True