"""
transactions_crud.py — LOGIPORT
================================
CRUD للمعاملات مع منطق صارم ولا افتراضات.

التغييرات عن النسخة السابقة:
  - حذف _SessionLocal() المخصص → استبدال بـ get_session() من BaseCRUD
  - استيراد مباشر من base_crud بدل base_crud_v5 (deprecated)
  - استخراج _f() و _calc_line_total() كدوال module-level مشتركة
    بدل تعريفهم 4 مرات داخل كل method
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Iterable, Tuple
import logging

logger = logging.getLogger(__name__)

from sqlalchemy import select, func, text as _sql_text
from sqlalchemy.orm import Session
from services.numbering_service import NumberingService

from database.models import get_session_local
from database.models.transport_details import TransportDetails
from database.crud.base_crud import BaseCRUD  # ← مباشر، بدون v5

# Models
try:
    from database.models.transaction import Transaction, TransactionItem, TransactionEntry  # type: ignore
    from database.models.entry_item import EntryItem
except Exception:
    pass

# PricingType
try:
    from database.models import PricingType  # type: ignore
except Exception:
    try:
        from database.models.pricing_type import PricingType  # type: ignore
    except Exception:
        PricingType = None  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers (مشتركة بين كل الـ methods)
# ─────────────────────────────────────────────────────────────────────────────

_MANUAL_NO_ALIASES = (
    "transaction_no", "transactionNo", "trx_no", "trxNo",
    "no", "number", "doc_no", "docNo", "code",
)


def _f(x: Any, default: float = 0.0) -> float:
    """تحويل آمن لـ float مع fallback."""
    try:
        return float(x)
    except Exception:
        return float(default)


def _norm_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s in {"", "-", "—", "None", "null", "AUTO", "auto"}:
        return ""
    return s


def _extract_manual_no(data: Dict[str, Any]) -> str:
    for k in _MANUAL_NO_ALIASES:
        if k in data:
            s = _norm_str(data.get(k))
            if s:
                return s
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
    """Map {pricing_type_id: CODE} من DB."""
    rows: List[Tuple[int, Optional[str]]] = []
    if PricingType is not None:
        try:
            rows = session.query(PricingType.id, PricingType.code).all()  # type: ignore
        except Exception:
            rows = []
    if not rows:
        rows = [tuple(r) for r in session.execute(  # type: ignore
            _sql_text("SELECT id, code FROM pricing_types")
        ).fetchall()]
    return {int(r[0]): (r[1] or "").upper() for r in rows}


def _get_pricing_formula_by_id(session: Session) -> Dict[int, tuple]:
    """
    Map {pricing_type_id: (compute_by, price_unit, divisor)}
    compute_by in {'QTY','NET','GROSS'}
    """
    rows = []
    try:
        if PricingType is not None and hasattr(PricingType, "compute_by"):
            rows = session.query(
                PricingType.id, PricingType.compute_by,
                PricingType.price_unit, PricingType.divisor,
            ).all()
        else:
            rows = [tuple(r) for r in session.execute(
                _sql_text("SELECT id, compute_by, price_unit, divisor FROM pricing_types")
            ).fetchall()]
    except Exception:
        rows = []

    out: Dict[int, tuple] = {}
    for rid, cb, pu, dv in rows:
        try:
            out[int(rid)] = (
                (cb or "").upper(),
                (pu or "").upper(),
                float(dv) if dv is not None else 1.0,
            )
        except Exception:
            pass
    return out


def _calc_line_total(
    pid: int,
    qty: float,
    net: float,
    gross: float,
    price: float,
    pt_code_map: Dict[int, str],
    form_map: Dict[int, tuple],
) -> float:
    """
    احسب إجمالي السطر.
    أولاً: صيغة الجدول (compute_by + divisor).
    ثانياً: fallback بالكود القديم.
    """
    # صيغة الجدول
    f = form_map.get(int(pid))
    if f:
        cb, _pu, dv = f
        base = qty if cb == "QTY" else (net if cb == "NET" else gross if cb == "GROSS" else 0.0)
        return (base / (dv or 1.0)) * price

    # fallback بالكود
    code = (pt_code_map.get(int(pid)) or "").upper()
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


def _validate_item(it: Dict[str, Any]) -> None:
    """تحقق من الحقول الإلزامية لكل سطر — يرمي ValueError عند الفشل."""
    if it.get("currency_id") is None:
        raise ValueError("currency_id is required for each item")
    if it.get("pricing_type_id") is None:
        raise ValueError("pricing_type_id is required for each item")
    if it.get("packaging_type_id") is None:
        raise ValueError("packaging_type_id is required for each item")
    if it.get("unit_price") in (None, "", 0, 0.0):
        raise ValueError("unit_price is required and must be > 0 for each item")


def _build_item_row(
    it: Dict[str, Any],
    transaction_id: int,
    user_id: Optional[int],
    pt_code_map: Dict[int, str],
    form_map: Dict[int, tuple],
) -> Tuple["TransactionItem", float, float, float, float]:
    """
    ينشئ TransactionItem من dict ويعيد (row, qty, gross, net, line_total).
    يُستخدم في create و update لتجنب التكرار.
    """
    _validate_item(it)

    qty   = _f(it.get("quantity"))
    gross = _f(it.get("gross_weight_kg"))
    net   = _f(it.get("net_weight_kg"))
    price = _f(it.get("unit_price"))
    pid   = it.get("pricing_type_id")

    # احترم الإجمالي المُرسَل إن كان موجوداً ورقمياً
    lt_in = it.get("line_total", it.get("total_price"))
    try:
        line_total: float = float(lt_in) if lt_in is not None else None  # type: ignore
    except Exception:
        line_total = None  # type: ignore
    if line_total is None:
        line_total = _calc_line_total(pid, qty, net, gross, price, pt_code_map, form_map)

    row = TransactionItem(
        transaction_id   = transaction_id,
        entry_id         = it.get("entry_id"),
        entry_item_id    = it.get("entry_item_id"),
        material_id      = it.get("material_id"),
        packaging_type_id= it.get("packaging_type_id"),
        quantity         = qty,
        gross_weight_kg  = gross,
        net_weight_kg    = net,
        pricing_type_id  = pid,
        unit_price       = price,
        currency_id      = it.get("currency_id"),
        line_total       = _f(line_total),
        origin_country_id= it.get("origin_country_id"),
        source_type      = it.get("source") or it.get("source_type") or (
                               "manual" if it.get("is_manual") else "entry"),
        is_manual        = bool(it.get("is_manual")),
        notes            = it.get("notes"),
        transport_ref    = it.get("transport_ref") or it.get("truck_or_container_no"),
        created_by_id    = user_id,
        updated_by_id    = user_id,
    )
    return row, qty, gross, net, _f(line_total)


def _recalc_totals_from_db(s: Session, trx_id: int) -> Tuple[float, float, float, float]:
    """يحسب الإجماليات مباشرة من DB ويعيدها كـ tuple."""
    row = s.execute(
        select(
            func.coalesce(func.sum(TransactionItem.quantity),        0.0),
            func.coalesce(func.sum(TransactionItem.gross_weight_kg), 0.0),
            func.coalesce(func.sum(TransactionItem.net_weight_kg),   0.0),
            func.coalesce(func.sum(TransactionItem.line_total),      0.0),
        ).where(TransactionItem.transaction_id == trx_id)
    ).one()
    return float(row[0]), float(row[1]), float(row[2]), float(row[3])


# ─────────────────────────────────────────────────────────────────────────────
# TransactionsCRUD
# ─────────────────────────────────────────────────────────────────────────────

class TransactionsCRUD(BaseCRUD):
    """CRUD للمعاملات — يستخدم get_session() من BaseCRUD مباشرة."""

    def __init__(self):
        super().__init__(Transaction, get_session_local)

    # -- Create (safe override) -------------------------------------------

    def create(self, data: Dict[str, Any], **kwargs) -> "Transaction":
        """يوجّه أي create() عام لـ create_transaction."""
        return self.create_transaction(
            data         = data,
            items        = kwargs.get("items"),
            entry_ids    = kwargs.get("entry_ids"),
            user_id      = kwargs.get("user_id"),
            number_prefix= kwargs.get("number_prefix", "T"),
        )

    # ── Transport Details ────────────────────────────────────────────────

    @staticmethod
    def _save_transport_details(session: Session, transaction_id: int, transport: dict) -> None:
        """يحفظ أو يحدّث TransportDetails. يتجاهل إذا كل القيم None."""
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

    # ── Create Transaction ───────────────────────────────────────────────

    def create_transaction(
        self,
        *,
        data      : Dict[str, Any],
        items     : List[Dict[str, Any]] | None = None,
        entry_ids : Iterable[int] | None = None,
        user_id   : Optional[int] = None,
        number_prefix: str = "T",
    ) -> "Transaction":

        with self.get_session() as s:
            # 1) رقم المعاملة
            manual_no = _extract_manual_no(data)
            if manual_no:
                exists = s.execute(
                    select(func.count()).select_from(Transaction)
                    .where(Transaction.transaction_no == manual_no)
                ).scalar_one()
                if exists:
                    raise ValueError(f"Transaction number '{manual_no}' already exists")
                trx_no = manual_no
            else:
                trx_no = NumberingService.get_next_transaction_number(s)

            # 2) رأس المعاملة
            trx = Transaction(
                transaction_no    = trx_no,
                transaction_date  = data.get("transaction_date"),
                transaction_type  = data.get("transaction_type"),
                client_id         = data.get("client_id"),
                exporter_company_id  = data.get("exporter_company_id"),
                importer_company_id  = data.get("importer_company_id"),
                relationship_type = data.get("relationship_type"),
                broker_company_id = data.get("broker_company_id"),
                origin_country_id = data.get("origin_country_id"),
                dest_country_id   = data.get("dest_country_id"),
                currency_id       = data.get("currency_id"),
                pricing_type_id   = data.get("pricing_type_id"),
                delivery_method_id= data.get("delivery_method_id"),
                transport_type    = data.get("transport_type"),
                transport_ref     = data.get("transport_ref"),
                notes             = data.get("notes"),
                created_by_id     = user_id,
                updated_by_id     = user_id,
            )
            s.add(trx)
            s.flush()  # نحتاج trx.id

            # 3) ربط الإدخالات
            linked_ids: set[int] = set()
            for eid in (entry_ids or []):
                try:
                    if (v := int(eid) if eid is not None else None):
                        linked_ids.add(v)
                except Exception:
                    pass
            for it in (items or []):
                try:
                    if (v := int(it["entry_id"]) if it.get("entry_id") is not None else None):
                        linked_ids.add(v)
                except Exception:
                    pass
            for eid in sorted(linked_ids):
                s.add(TransactionEntry(transaction_id=trx.id, entry_id=eid))

            # 4) السطور والإجماليات
            total_qty = total_gross = total_net = total_val = 0.0
            if items:
                pt_code_map = _get_pricing_code_by_id(s)
                form_map    = _get_pricing_formula_by_id(s)
                for it in items:
                    row, qty, gross, net, lt = _build_item_row(
                        it, trx.id, user_id, pt_code_map, form_map
                    )
                    s.add(row)
                    total_qty   += qty
                    total_gross += gross
                    total_net   += net
                    total_val   += lt

            trx.totals_count    = total_qty
            trx.totals_gross_kg = total_gross
            trx.totals_net_kg   = total_net
            trx.totals_value    = total_val

            # 5) تفاصيل الشحن (اختياري)
            if data.get("transport"):
                self._save_transport_details(s, trx.id, data["transport"])

            s.commit()
            s.refresh(trx)
            return trx

    # ── Update (override) ────────────────────────────────────────────────

    def update(
        self,
        obj_id      : int,
        data        : Dict[str, Any],
        current_user: Dict[str, Any] | None = None,
    ) -> Optional["Transaction"]:
        """تحديث رأس المعاملة مع حماية رقم المعاملة."""
        payload = dict(data or {})
        with self.get_session() as s:
            t = s.get(Transaction, obj_id)
            if not t:
                return None

            # توحيد رقم المعاملة
            if "transaction_no" in payload or any(
                a in payload for a in _MANUAL_NO_ALIASES if a != "transaction_no"
            ):
                raw_no = _extract_manual_no(payload)
                if not raw_no:
                    payload.pop("transaction_no", None)
                    for a in _MANUAL_NO_ALIASES:
                        payload.pop(a, None)
                elif raw_no != (t.transaction_no or ""):
                    exists = s.execute(
                        select(func.count()).select_from(Transaction).where(
                            Transaction.transaction_no == raw_no,
                            Transaction.id != obj_id,
                        )
                    ).scalar_one()
                    if exists:
                        raise ValueError(f"Transaction number '{raw_no}' already exists")
                    t.transaction_no = raw_no
                for a in _MANUAL_NO_ALIASES:
                    payload.pop(a, None)

            for k, v in list(payload.items()):
                if k == "transaction_no":
                    continue
                setattr(t, k, v)

            if current_user and current_user.get("id"):
                t.updated_by_id = current_user["id"]

            s.commit()
            s.refresh(t)
            return t

    # ── Update with Items ────────────────────────────────────────────────

    def update_transaction_with_items(
        self,
        trx_id   : int,
        *,
        data     : Dict[str, Any],
        items    : List[Dict[str, Any]] | None = None,
        entry_ids: Iterable[int] | None = None,
        user_id  : Optional[int] = None,
    ) -> Optional["Transaction"]:
        """يحدّث الرأس ويستبدل السطور وروابط الإدخالات بالكامل."""
        with self.get_session() as s:
            t = s.get(Transaction, trx_id)
            if not t:
                return None

            # 1) الهيدر
            payload = dict(data or {})
            raw_no = _extract_manual_no(payload)
            if raw_no:
                exists = s.execute(
                    select(func.count()).select_from(Transaction).where(
                        Transaction.transaction_no == raw_no,
                        Transaction.id != trx_id,
                    )
                ).scalar_one()
                if exists:
                    raise ValueError(f"Transaction number '{raw_no}' already exists")
                t.transaction_no = raw_no
            for a in _MANUAL_NO_ALIASES:
                payload.pop(a, None)
            payload.pop("transaction_no", None)
            for k, v in payload.items():
                setattr(t, k, v)
            if user_id:
                t.updated_by_id = user_id

            # 2) استبدال روابط الإدخالات
            s.query(TransactionEntry).filter(
                TransactionEntry.transaction_id == trx_id
            ).delete(synchronize_session=False)
            if entry_ids:
                for eid in {int(e) for e in entry_ids if e is not None}:
                    s.add(TransactionEntry(transaction_id=trx_id, entry_id=eid))

            # 3) استبدال السطور
            s.query(TransactionItem).filter(
                TransactionItem.transaction_id == trx_id
            ).delete(synchronize_session=False)

            total_qty = total_gross = total_net = total_val = 0.0
            if items:
                pt_code_map = _get_pricing_code_by_id(s)
                form_map    = _get_pricing_formula_by_id(s)
                for it in items:
                    row, qty, gross, net, lt = _build_item_row(
                        it, trx_id, user_id, pt_code_map, form_map
                    )
                    s.add(row)
                    total_qty   += qty
                    total_gross += gross
                    total_net   += net
                    total_val   += lt

            # 4) إجماليات الرأس
            t.totals_count    = total_qty
            t.totals_gross_kg = total_gross
            t.totals_net_kg   = total_net
            t.totals_value    = total_val

            # 5) تفاصيل الشحن
            if data.get("transport"):
                self._save_transport_details(s, trx_id, data["transport"])

            s.commit()
            s.refresh(t)
            return t

    # ── Facade helpers ───────────────────────────────────────────────────

    def update_transaction(
        self,
        trx_id : int,
        data   : Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> Optional["Transaction"]:
        payload = dict(data or {})
        if user_id is not None:
            payload["updated_by_id"] = user_id
        return self.update(
            trx_id, payload,
            current_user={"id": user_id} if user_id is not None else None,
        )

    def delete_transaction(self, trx_id: int) -> bool:
        result = self.delete(trx_id)
        if result:
            try:
                with self.get_session() as s:
                    NumberingService.sync_last_number(s)
            except Exception as e:
                logger.warning(f"sync_last_number failed (non-critical): {e}")
        return result

    # ── Items helpers ────────────────────────────────────────────────────

    def add_items_from_entries(
        self,
        trx_id   : int,
        entry_ids: Iterable[int],
        user_id  : Optional[int] = None,
    ) -> int:
        ids = [int(e) for e in (entry_ids or []) if e is not None]
        if not ids:
            return 0

        with self.get_session() as s:
            t = s.get(Transaction, trx_id)
            if not t:
                return 0

            # حمّل transport_ref من الإدخالات مرة واحدة
            entry_ref_map: Dict[int, Optional[str]] = {}
            try:
                from database.models.entry import Entry
                rows_e = s.execute(
                    select(Entry.id, Entry.transport_ref).where(Entry.id.in_(ids))
                ).fetchall()
                entry_ref_map = {int(r[0]): (r[1] or None) for r in rows_e}
            except Exception:
                pass

            rows = s.execute(
                select(EntryItem).where(EntryItem.entry_id.in_(ids))
            ).scalars().all()
            if not rows:
                return 0

            pt_code_map = _get_pricing_code_by_id(s)
            form_map    = _get_pricing_formula_by_id(s)

            n = 0
            for r in rows:
                qty   = _f(getattr(r, "count", None) or getattr(r, "quantity", None))
                price = _f(getattr(r, "unit_price", None))
                pid   = getattr(r, "pricing_type_id", None)
                cid   = getattr(r, "currency_id", None)

                if cid is None:
                    raise ValueError("currency_id is required on entry items")
                if pid is None:
                    raise ValueError("pricing_type_id is required on entry items")

                net   = _f(getattr(r, "net_weight_kg", None))
                gross = _f(getattr(r, "gross_weight_kg", None))
                lt    = _calc_line_total(pid, qty, net, gross, price, pt_code_map, form_map)

                item = TransactionItem(
                    transaction_id   = trx_id,
                    entry_id         = r.entry_id,
                    entry_item_id    = r.id,
                    material_id      = r.material_id,
                    packaging_type_id= getattr(r, "packaging_type_id", None),
                    quantity         = qty,
                    gross_weight_kg  = gross,
                    net_weight_kg    = net,
                    pricing_type_id  = pid,
                    unit_price       = price,
                    currency_id      = cid,
                    line_total       = lt,
                    origin_country_id= getattr(r, "origin_country_id", None),
                    source_type      = "entry",
                    is_manual        = False,
                    notes            = getattr(r, "notes", None),
                    transport_ref    = entry_ref_map.get(getattr(r, "entry_id", None)),
                    created_by_id    = user_id,
                    updated_by_id    = user_id,
                )
                s.add(item)
                n += 1

            # إجماليات من DB (أدق من الجمع اليدوي)
            qty_t, gross_t, net_t, val_t = _recalc_totals_from_db(s, trx_id)
            t.totals_count    = qty_t
            t.totals_gross_kg = gross_t
            t.totals_net_kg   = net_t
            t.totals_value    = val_t
            s.commit()
            return n

    def add_manual_item(
        self,
        trx_id : int,
        item   : Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> "TransactionItem":
        with self.get_session() as s:
            pt_code_map = _get_pricing_code_by_id(s)
            form_map    = _get_pricing_formula_by_id(s)

            row, *_ = _build_item_row(item, trx_id, user_id, pt_code_map, form_map)
            s.add(row)

            # إجماليات من DB
            t = s.get(Transaction, trx_id)
            qty_t, gross_t, net_t, val_t = _recalc_totals_from_db(s, trx_id)
            t.totals_count    = qty_t
            t.totals_gross_kg = gross_t
            t.totals_net_kg   = net_t
            t.totals_value    = val_t

            s.commit()
            s.refresh(row)
            return row

    # ── Query helpers ────────────────────────────────────────────────────

    def list_transactions(
        self,
        *,
        client_id       : Optional[int] = None,
        date_from       : Optional[str] = None,
        date_to         : Optional[str] = None,
        status          : Optional[str] = None,
        transaction_type: Optional[str] = None,
        search          : Optional[str] = None,
        limit           : int = 100,
        offset          : int = 0,
    ) -> List["Transaction"]:
        with self.get_session() as s:
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
                q = q.where(Transaction.transaction_no.ilike(f"%{search}%"))
            q = q.order_by(
                Transaction.transaction_date.desc(),
                Transaction.id.desc(),
            ).limit(limit).offset(offset)
            return list(s.execute(q).scalars().all())

    def get_with_items(
        self, trx_id: int
    ) -> Optional[Tuple["Transaction", List["TransactionItem"]]]:
        with self.get_session() as s:
            from sqlalchemy.orm import joinedload
            trx = s.execute(
                select(Transaction)
                .where(Transaction.id == trx_id)
                .options(joinedload(Transaction.items))
            ).unique().scalar_one_or_none()
            if not trx:
                return None
            items = list(trx.items)
            s.expunge_all()
            return trx, items

    # ── Status Management ─────────────────────────────────────────────────

    VALID_STATUSES = {"draft", "active", "closed", "archived"}

    ALLOWED_TRANSITIONS: Dict[str, set] = {
        "draft":    {"active"},
        "active":   {"closed", "draft"},
        "closed":   {"active", "archived"},
        "archived": set(),
    }

    def change_status(
        self,
        trx_id      : int,
        new_status  : str,
        current_user: Any = None,
    ) -> Tuple[bool, str]:
        if new_status not in self.VALID_STATUSES:
            return False, f"invalid_status: {new_status}"

        with self.get_session() as s:
            t = s.get(Transaction, trx_id)
            if not t:
                return False, "transaction_not_found"

            current = t.status or "active"
            if new_status not in self.ALLOWED_TRANSITIONS.get(current, set()):
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

    def close_transaction(self, trx_id: int, current_user=None) -> Tuple[bool, str]:
        return self.change_status(trx_id, "closed", current_user)

    def reopen_transaction(self, trx_id: int, current_user=None) -> Tuple[bool, str]:
        return self.change_status(trx_id, "active", current_user)

    def archive_transaction(self, trx_id: int, current_user=None) -> Tuple[bool, str]:
        return self.change_status(trx_id, "archived", current_user)

    def activate_draft(self, trx_id: int, current_user=None) -> Tuple[bool, str]:
        return self.change_status(trx_id, "active", current_user)

    def recalc_totals(self, trx_id: int) -> bool:
        with self.get_session() as s:
            t = s.get(Transaction, trx_id)
            if not t:
                return False
            qty_t, gross_t, net_t, val_t = _recalc_totals_from_db(s, trx_id)
            t.totals_count    = qty_t
            t.totals_gross_kg = gross_t
            t.totals_net_kg   = net_t
            t.totals_value    = val_t
            s.commit()
            return True