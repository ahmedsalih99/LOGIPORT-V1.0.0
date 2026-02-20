# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Document Mapper - LOGIPORT
Mapping logic for document generation and processing

document_mapper.py
يوحّد قراءة بيانات المعاملة (الهيدر + العناصر + الأطراف + الإجماليات)
ويطبّق منطق التسعير القابل للتهيئة من جدول pricing_types:
  - compute_by: 'QTY' | 'NET' | 'GROSS'
  - price_unit: 'UNIT' | 'KG' | 'TON'  (مستخدمة كـ label للعرض في المستندات)
  - divisor: عامل تحويل (مثلاً 1000 للتحويل من كغ إلى طن)

Fallback ذكي في حال الأعمدة غير موجودة بعد:
  KG/KILO  -> NET * price
  TON/T/MT -> (NET/1000) * price
  GROSS    -> GROSS * price
  else     -> QTY * price
"""

import logging

logger = logging.getLogger(__name__)


from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import date

# SQLAlchemy
try:
    from sqlalchemy import select, func, text as _sql_text
except Exception:  # pragma: no cover
    # حد أدنى للبيئات التي لا تملك SQLAlchemy أثناء التصميم
    def select(*_a, **_kw):  # type: ignore
        raise RuntimeError("SQLAlchemy not available")
    def func(*_a, **_kw):  # type: ignore
        raise RuntimeError("SQLAlchemy not available")
    def _sql_text(*_a, **_kw):  # type: ignore
        raise RuntimeError("SQLAlchemy not available")

# ORM models (مرن لو بعض الجداول غير متاحة)
try:
    from database.models import (
        get_session_local,
        Transaction, TransactionItem,
        Company, Country, Material, PricingType, Currency, PackagingType,
        DeliveryMethod,
    )
except Exception:
    # Fallbacks لتجنّب الانهيار وقت التصميم
    get_session_local = None  # type: ignore
    Transaction = object  # type: ignore
    TransactionItem = object  # type: ignore
    Company = object  # type: ignore
    Country = object  # type: ignore
    Material = object  # type: ignore
    PricingType = object  # type: ignore
    Currency = object  # type: ignore
    PackagingType = object  # type: ignore
    DeliveryMethod = object  # type: ignore


# --------------------------- helpers ---------------------------

def _get(o: Any, k: str, d: Any = None) -> Any:
    """Safe getattr/[] access for dict or ORM object."""
    try:
        if isinstance(o, dict):
            return o.get(k, d)
        return getattr(o, k, d)
    except Exception:
        return d


def _as_date(x: Any) -> Optional[date]:
    if not x:
        return None
    try:
        if hasattr(x, "year") and hasattr(x, "month") and hasattr(x, "day"):
            return date(x.year, x.month, x.day)  # type: ignore
        # "YYYY-MM-DD"
        parts = str(x).split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return None


def _company_dict(s, company_id: Optional[int], lang: str) -> Dict[str, Any]:
    d: Dict[str, Any] = {}
    if not company_id:
        return d
    try:
        c = s.get(Company, int(company_id))
    except Exception:
        c = None
    if not c:
        return d
    # أسماء متعددة اللغات
    name = (
        _get(c, "name_ar", "") if lang == "ar" else
        _get(c, "name_tr", "") if lang == "tr" else
        _get(c, "name_en", "")
    )
    d = {
        "id": _get(c, "id"),
        "name": name or (_get(c, "name_en") or _get(c, "name_ar") or _get(c, "name_tr") or ""),
        "name_ar": _get(c, "name_ar", ""),
        "name_en": _get(c, "name_en", ""),
        "name_tr": _get(c, "name_tr", ""),
        "address": _get(c, "address", "") or _get(c, "address_text", ""),
        "phone": _get(c, "phone", ""),
        "email": _get(c, "email", ""),
        "vat_no": _get(c, "vat_no", "") or _get(c, "tax_no", ""),
        "customs_no": _get(c, "customs_no", ""),
        "country_id": _get(c, "country_id"),
        "city": _get(c, "city", ""),
    }
    return d


def _country_name(s, country_id: Optional[int], lang: str) -> str:
    if not country_id:
        return ""
    try:
        c = s.get(Country, int(country_id))
    except Exception:
        c = None
    if not c:
        return ""
    if lang == "ar":
        return _get(c, "name_ar", "") or _get(c, "name_en", "") or _get(c, "name_tr", "")
    if lang == "tr":
        return _get(c, "name_tr", "") or _get(c, "name_en", "") or _get(c, "name_ar", "")
    return _get(c, "name_en", "") or _get(c, "name_ar", "") or _get(c, "name_tr", "")


def _currency_code(s, currency_id: Optional[int]) -> str:
    if not currency_id:
        return ""
    try:
        c = s.get(Currency, int(currency_id))
    except Exception:
        c = None
    return (_get(c, "code", "") or _get(c, "iso_code", "") or "").upper() if c else ""


def _pricing_code_map(s) -> Dict[int, str]:
    """Map pricing_type.id -> UPPER(code)"""
    out: Dict[int, str] = {}
    try:
        rows = s.execute(_sql_text("SELECT id, code FROM pricing_types")).fetchall()
        for r in rows:
            out[int(r[0])] = (str(r[1]) or "").upper()
    except Exception:
        pass
    return out


def _pricing_formula_for(s, pt_id: Optional[int]) -> Optional[tuple[str, str, float]]:
    """
    Return (compute_by, price_unit, divisor) for a given pricing_type_id.
    compute_by ∈ {'QTY','NET','GROSS'}
    price_unit is a display label like 'UNIT'/'KG'/'TON' (used as unit label in docs).
    divisor is a float (e.g., 1000 for TON if base is in kg).
    Falls back from `code` if columns are missing.
    """
    if not pt_id:
        return None
    try:
        pt = s.get(PricingType, int(pt_id))
    except Exception:
        pt = None
    if not pt:
        return None

    code = (_get(pt, "code", "") or "").upper()

    # prefer DB columns if they exist
    cb = (_get(pt, "compute_by", "") or "").upper() if hasattr(pt, "compute_by") else ""
    pu = (_get(pt, "price_unit", "") or "").upper() if hasattr(pt, "price_unit") else ""
    dv = _get(pt, "divisor", None) if hasattr(pt, "divisor") else None
    try:
        dv = float(dv) if dv not in (None, "") else 1.0
    except Exception:
        dv = 1.0

    if cb in {"QTY", "NET", "GROSS"}:
        if not pu:
            pu = code or "UNIT"
        return (cb, pu, dv or 1.0)

    # Fallbacks based on code only
    # داخل _pricing_formula_for ... بعد قسم الـ Fallbacks based on code only:
    if code in {"KG_NET"}:
        return ("NET", "KG", 1.0)
    if code in {"KG_GROSS"}:
        return ("GROSS", "KG", 1.0)
    if code in {"TON_NET"}:
        return ("NET", "TON", 1000.0)
    if code in {"TON_GROSS"}:
        return ("GROSS", "TON", 1000.0)
    # الموجودين أصلاً:
    if code in {"KG", "KILO"}:
        return ("NET", "KG", 1.0)
    if code in {"TON", "T", "MT"}:
        return ("NET", "TON", 1000.0)
    if code in {"GROSS", "BRUT"}:
        return ("GROSS", "KG", 1.0)


def _pack_name(s, pack_id: Optional[int], lang: str) -> str:
    if not pack_id:
        return ""
    try:
        p = s.get(PackagingType, int(pack_id))
    except Exception:
        p = None
    if not p:
        return ""
    if lang == "ar":
        return _get(p, "name_ar", "") or _get(p, "name_en", "") or _get(p, "name_tr", "")
    if lang == "tr":
        return _get(p, "name_tr", "") or _get(p, "name_en", "") or _get(p, "name_ar", "")
    return _get(p, "name_en", "") or _get(p, "name_ar", "") or _get(p, "name_tr", "")


# --------------------------- items mapping ---------------------------

def _item_dict(s, it, lang: str) -> Dict[str, Any]:
    """Normalize a transaction item to a template-friendly dict (no assumptions)."""
    mat: Optional[Material] = _get(it, "material", None)
    desc_ar = _get(mat, "name_ar", "") if mat else ""
    desc_en = _get(mat, "name_en", "") if mat else ""
    desc_tr = _get(mat, "name_tr", "") if mat else ""

    qty = float(_get(it, "quantity", 0) or 0)
    gross = float(_get(it, "gross_weight_kg", 0) or 0)
    net = float(_get(it, "net_weight_kg", 0) or 0)
    unit_price = float(_get(it, "unit_price", 0) or 0)

    pt_id = _get(it, "pricing_type_id", None)
    pt_code = ""
    try:
        if pt_id:
            pt = s.get(PricingType, int(pt_id))
            pt_code = (_get(pt, "code", "") or "").upper()
    except Exception:
        pass

    # line total: use stored value if present; else compute from pricing formula
    line_total = _get(it, "line_total", None)
    try:
        line_total = float(line_total) if line_total is not None else None
    except Exception:
        line_total = None

    unit_label = ""

    # prefer DB formula (compute_by/price_unit/divisor), fallback to legacy by code
    formula = _pricing_formula_for(s, pt_id)
    if line_total is None:
        if formula:
            compute_by, price_unit, divisor = formula
            base = qty if compute_by == "QTY" else (net if compute_by == "NET" else gross if compute_by == "GROSS" else 0.0)
            eff = base / (divisor or 1.0)
            line_total = unit_price * eff
            unit_label = price_unit  # shown on docs (unit column)
        else:
            # legacy fallback by pricing code
            if pt_code in ("KG", "KILO"):
                line_total = net * unit_price
                unit_label = "KG"
            elif pt_code in ("TON", "T", "MT"):
                line_total = (net / 1000.0) * unit_price
                unit_label = "TON"
            elif pt_code in ("GROSS", "BRUT"):
                line_total = gross * unit_price
                unit_label = "KG"
            else:
                line_total = qty * unit_price
                unit_label = "UNIT"
    else:
        # even if pre-computed, still try to pick a nice unit label to display
        if formula:
            _cb, price_unit, _dv = formula
            unit_label = price_unit
        else:
            # fallback label by code
            # داخل else:  # legacy fallback by pricing code
            if pt_code in ("UNIT", "PCS", "PIECE"):
                line_total = qty * unit_price;
                unit_label = "UNIT"
            elif pt_code in ("KG", "KILO", "KG_NET"):
                line_total = net * unit_price;
                unit_label = "KG"
            elif pt_code in ("KG_GROSS", "GROSS", "BRUT"):
                line_total = gross * unit_price;
                unit_label = "KG"
            elif pt_code in ("TON", "T", "MT", "TON_NET"):
                line_total = (net / 1000.0) * unit_price;
                unit_label = "TON"
            elif pt_code in ("TON_GROSS",):
                line_total = (gross / 1000.0) * unit_price;
                unit_label = "TON"
            else:
                line_total = qty * unit_price;
                unit_label = "UNIT"

    pack_id = _get(it, "packaging_type_id", None)

    # اختر الوصف حسب اللغة
    description = desc_ar if lang == "ar" else desc_tr if lang == "tr" else desc_en or desc_ar or desc_tr

    return {
        "id": _get(it, "id", None),
        "material_code": _get(mat, "code", "") if mat else "",
        "description": description,
        "description_ar": desc_ar,
        "description_en": desc_en,
        "description_tr": desc_tr,
        "packaging": _pack_name(s, pack_id, lang),
        "quantity": qty,
        "gross_weight_kg": gross,
        "net_weight_kg": net,
        "unit": unit_label,          # label from pricing formula (display only)
        "unit_price": unit_price,
        "line_total": float(line_total or 0.0),
        "currency_id": _get(it, "currency_id", None),
        "pricing_type_id": pt_id,
        "packaging_type_id": pack_id,
        "origin_country_id": _get(it, "origin_country_id", None),
        "notes": _get(it, "notes", "") or "",
        "source": _get(it, "source_type", None) or _get(it, "source", None) or ("manual" if _get(it, "is_manual", False) else "entry"),
        "is_manual": bool(_get(it, "is_manual", False)),
    }


# --------------------------- main mapper ---------------------------

def fetch_transaction_dict(transaction_id: int, lang: str = "ar") -> Dict[str, Any]:
    """
    يرجع قاموس شامل لحقن القوالب (HTML/PDF):
      {
        "header": {...},
        "parties": {"exporter":..., "importer":..., "broker":..., "client":...},
        "countries": {"origin": "...", "destination": "..."},
        "items": [ ... ],
        "totals": {"quantity":..., "gross_kg":..., "net_kg":..., "value":..., "currency":"USD"},
        "meta": {"lang":"ar"}
      }
    """
    if get_session_local is None:
        raise RuntimeError("get_session_local is not available")

    with get_session_local()() as s:
        t = s.get(Transaction, int(transaction_id))
        if not t:
            raise ValueError(f"Transaction id={transaction_id} not found")

        trx_no = _get(t, "transaction_no") or str(_get(t, "id", "") or "")
        trx_date = _as_date(_get(t, "transaction_date"))
        trx_type = _get(t, "transaction_type", "") or "export"

        # currency & pricing type info
        currency_id = _get(t, "currency_id", None)
        currency_code = _currency_code(s, currency_id)

        pt_id_head = _get(t, "pricing_type_id", None)
        pricing_type_code = ""
        try:
            if pt_id_head:
                pth = s.get(PricingType, int(pt_id_head))
                pricing_type_code = (_get(pth, "code", "") or "").upper()
        except Exception:
            pass

        # optional: expose head pricing formula to templates (لو بدك تبيّنها في الهيدر)
        pricing_info: Dict[str, Any] = {}
        try:
            ff = _pricing_formula_for(s, pt_id_head) if pt_id_head else None
            if ff:
                cb, pu, dv = ff
                pricing_info = {"compute_by": cb, "price_unit": pu, "divisor": float(dv)}
        except Exception:
            pricing_info = {}

        # delivery method (display name only if exists)
        delivery_name = ""
        try:
            dm_id = _get(t, "delivery_method_id", None)
            if dm_id:
                dm = s.get(DeliveryMethod, int(dm_id))
                if lang == "ar":
                    delivery_name = _get(dm, "name_ar", "") or _get(dm, "name_en", "") or _get(dm, "name_tr", "")
                elif lang == "tr":
                    delivery_name = _get(dm, "name_tr", "") or _get(dm, "name_en", "") or _get(dm, "name_ar", "")
                else:
                    delivery_name = _get(dm, "name_en", "") or _get(dm, "name_ar", "") or _get(dm, "name_tr", "")
        except Exception:
            delivery_name = ""

        # parties
        exporter = _company_dict(s, _get(t, "exporter_company_id", None), lang)
        importer = _company_dict(s, _get(t, "importer_company_id", None), lang)
        broker   = _company_dict(s, _get(t, "broker_company_id",   None), lang)
        client   = _company_dict(s, _get(t, "client_id",           None), lang)

        # countries
        origin_name = _country_name(s, _get(t, "origin_country_id", None), lang)
        dest_name   = _country_name(s, _get(t, "dest_country_id",   None), lang)

        # items
        try:
            rows = s.execute(
                select(TransactionItem).where(TransactionItem.transaction_id == int(transaction_id))
            ).scalars().all()
        except Exception:
            # fallback: حاول الوصول عبر علاقة items إن وُجدت
            rows = list(_get(t, "items", []) or [])

        items: List[Dict[str, Any]] = []
        total_qty = total_gross = total_net = total_value = 0.0
        for it in rows:
            d = _item_dict(s, it, lang)
            items.append(d)
            try:
                total_qty   += float(d.get("quantity") or 0.0)
                total_gross += float(d.get("gross_weight_kg") or 0.0)
                total_net   += float(d.get("net_weight_kg") or 0.0)
                total_value += float(d.get("line_total") or 0.0)
            except Exception:
                pass

        # header dictionary
        header = {
            "id": _get(t, "id", None),
            "transaction_no": trx_no,
            "transaction_date": trx_date.isoformat() if trx_date else "",
            "transaction_type": trx_type,
            "transport_type": _get(t, "transport_type", ""),
            "transport_ref": _get(t, "transport_ref", ""),
            "notes": _get(t, "notes", "") or "",
            "currency_id": currency_id,
            "currency_code": currency_code,
            "pricing_type_id": pt_id_head,
            "pricing_type_code": pricing_type_code,
            "delivery_method": delivery_name,
        }

        # totals dictionary (لو عندك كولمنز cached على الرأس تقدر تستخدمها، لكن هنا نحسب لضمان الدقة)
        totals = {
            "quantity": round(total_qty, 3),
            "gross_kg": round(total_gross, 3),
            "net_kg":   round(total_net, 3),
            "value":    round(total_value, 3),
            "currency": currency_code,
        }

        result = {
            "header": header,
            "parties": {
                "exporter": exporter,
                "importer": importer,
                "broker":   broker,
                "client":   client,
            },
            "countries": {
                "origin":      origin_name,
                "destination": dest_name,
            },
            "items": items,
            "totals": totals,
            "pricing": pricing_info,   # optional section for templates
            "meta": {
                "lang": lang,
            }
        }
        return result