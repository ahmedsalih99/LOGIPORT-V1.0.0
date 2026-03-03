# documents/builders/_shared.py
# -*- coding: utf-8 -*-
"""
مكتبة مشتركة لجميع builders في LOGIPORT.
بدلاً من نسخ نفس الـ helpers في كل ملف، كل builder يستورد من هنا:

    from documents.builders._shared import (
        blankify, coalesce,
        country_name, company_obj, client_obj,
        tafqit_amount, num_words, unit_word, spell_non_monetary,
        dedup_preserve_order, label_from_pricing_code,
        compute_line_amount, get_bank_info,
        currency_info, delivery_method_name,
        pick_dest_col,
    )
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────
# 1. Utilities
# ─────────────────────────────────────────────

def blankify(v: Any) -> Any:
    """يحوّل None إلى '' ويُشذّب الـ strings ويُكرّر العملية على dict/list."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, Mapping):
        return {k: blankify(val) for k, val in v.items()}
    if isinstance(v, Sequence) and not isinstance(v, (str, bytes, bytearray)):
        return [blankify(x) for x in v]
    return v


def coalesce(*vals: Any) -> Any:
    """يُعيد أول قيمة ليست None أو ''."""
    for v in vals:
        if v not in (None, ""):
            return v
    return ""


def dedup_preserve_order(seq: List[str]) -> List[str]:
    """يُزيل المكررات مع الحفاظ على الترتيب."""
    seen: set = set()
    out: List[str] = []
    for v in seq:
        k = (v or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def join_with_and(names: List[str], lang: str) -> str:
    """يدمج قائمة بـ 'and / و / ve' حسب اللغة بدون تكرار."""
    lst = dedup_preserve_order([n for n in names if (n or "").strip()])
    if not lst:
        return ""
    if len(lst) == 1:
        return lst[0]
    sep  = "، " if lang.startswith("ar") else ", "
    conj = " و "  if lang.startswith("ar") else (" ve " if lang.startswith("tr") else " and ")
    return sep.join(lst[:-1]) + conj + lst[-1]


# ─────────────────────────────────────────────
# 2. Database helpers
# ─────────────────────────────────────────────

def country_name(s: Any, country_id: Optional[int], lang: str) -> str:
    """يُعيد اسم الدولة بالـ lang المطلوبة مع fallback."""
    if not country_id:
        return ""
    from sqlalchemy import text
    r = s.execute(
        text("SELECT name_ar, name_en, name_tr FROM countries WHERE id=:i"),
        {"i": country_id}
    ).mappings().first()
    if not r:
        return ""
    return r.get(f"name_{lang}") or r.get("name_en") or r.get("name_ar") or r.get("name_tr") or ""


def get_bank_info(s: Any, company_id: Optional[int]) -> str:
    """
    يجلب بيانات البنك الأساسي من company_banks.
    Fallback على companies.bank_info إن لم يوجد جدول company_banks.
    """
    if not company_id:
        return ""
    from sqlalchemy import text
    try:
        banks = s.execute(text("""
            SELECT bank_name, branch, beneficiary_name, iban, swift_bic, account_number
            FROM company_banks
            WHERE company_id = :cid
            ORDER BY is_primary DESC, id ASC
            LIMIT 1
        """), {"cid": int(company_id)}).mappings().all()
        if banks:
            b = banks[0]
            lines = []
            if b.get("beneficiary_name"): lines.append(b["beneficiary_name"])
            if b.get("bank_name"):
                line = b["bank_name"]
                if b.get("branch"): line += f" — {b['branch']}"
                lines.append(line)
            if b.get("iban"):           lines.append(f"IBAN: {b['iban']}")
            if b.get("swift_bic"):      lines.append(f"SWIFT/BIC: {b['swift_bic']}")
            if b.get("account_number"): lines.append(f"A/C: {b['account_number']}")
            if lines:
                return "\n".join(lines)
    except Exception:
        pass

    # fallback: عمود bank_info في جدول companies
    try:
        from sqlalchemy import text as _t
        r = s.execute(_t("SELECT bank_info FROM companies WHERE id=:id"),
                      {"id": company_id}).mappings().first()
        if r:
            return r.get("bank_info") or ""
    except Exception:
        pass
    return ""


def company_obj(s: Any, company_id: Optional[int], lang: str) -> Dict[str, Any]:
    """
    يُعيد dict كامل لشركة مع bank_info محسوبة من company_banks.
    يُستخدم في جميع builders (فواتير + CMR + Form A + ...).
    """
    if not company_id:
        return {"name": "", "address": ""}
    from sqlalchemy import text
    r = s.execute(text("""
        SELECT id,
               name_ar, name_en, name_tr,
               address_ar, address_en, address_tr,
               country_id, city, phone, email, website, tax_id, registration_number,
               bank_info
        FROM companies WHERE id=:id
    """), {"id": company_id}).mappings().first()
    if not r:
        return {"name": "", "address": ""}

    name    = r.get(f"name_{lang}")    or r.get("name_en")    or r.get("name_ar")    or r.get("name_tr")    or ""
    address = r.get(f"address_{lang}") or r.get("address_en") or r.get("address_ar") or r.get("address_tr") or ""
    if not address:
        try:
            r2 = s.execute(text("SELECT address FROM companies WHERE id=:id"),
                           {"id": company_id}).mappings().first()
            if r2 and r2.get("address"):
                address = r2["address"]
        except Exception:
            pass

    bank = get_bank_info(s, company_id)

    return {
        "id":                  r.get("id"),
        "name":                name,
        "name_ar":             r.get("name_ar", ""),
        "name_en":             r.get("name_en", ""),
        "name_tr":             r.get("name_tr", ""),
        "address":             address,
        "city":                r.get("city") or "",
        "country":             country_name(s, r.get("country_id"), lang),
        "country_id":          r.get("country_id"),
        "phone":               r.get("phone") or "",
        "email":               r.get("email") or "",
        "website":             r.get("website") or "",
        "tax_id":              r.get("tax_id") or "",
        "tax_no":              r.get("tax_id") or "",
        "vat_no":              r.get("tax_id") or "",
        "cr_no":               r.get("registration_number") or "",
        "registration_number": r.get("registration_number") or "",
        "bank_info":           bank,
    }


def client_obj(s: Any, client_id: Optional[int], lang: str) -> Dict[str, Any]:
    """يُعيد dict كامل للعميل (من جدول clients)."""
    if not client_id:
        return {"name": "", "address": ""}
    from sqlalchemy import text
    r = s.execute(text("""
        SELECT id,
               name_ar, name_en, name_tr,
               COALESCE(address_ar, address) AS address_ar,
               COALESCE(address_en, address) AS address_en,
               COALESCE(address_tr, address) AS address_tr,
               country_id, city, phone, email, website, tax_id
        FROM clients WHERE id=:id
    """), {"id": client_id}).mappings().first()
    if not r:
        return {"name": "", "address": ""}

    name    = r.get(f"name_{lang}")    or r.get("name_en")    or r.get("name_ar")    or r.get("name_tr")    or ""
    address = r.get(f"address_{lang}") or r.get("address_en") or r.get("address_ar") or r.get("address_tr") or ""
    return {
        "id":      r.get("id"),
        "name":    name,
        "name_ar": r.get("name_ar", ""),
        "name_en": r.get("name_en", ""),
        "name_tr": r.get("name_tr", ""),
        "address": address,
        "city":    r.get("city") or "",
        "country": country_name(s, r.get("country_id"), lang),
        "phone":   r.get("phone") or "",
        "email":   r.get("email") or "",
        "website": r.get("website") or "",
        "tax_id":  r.get("tax_id") or "",
    }


def currency_info(s: Any, currency_id: Optional[int], lang: str) -> Tuple[str, str, str]:
    """
    يُعيد (code, localized_name, symbol_or_code).
    """
    if not currency_id:
        return "", "", ""
    from sqlalchemy import text
    # اكتشف وجود عمود symbol
    cols = {r["name"] for r in s.execute(text("PRAGMA table_info(currencies)")).mappings().all()}
    q = text("SELECT code, name_ar, name_en, name_tr, symbol FROM currencies WHERE id=:id") \
        if "symbol" in cols else \
        text("SELECT code, name_ar, name_en, name_tr FROM currencies WHERE id=:id")
    r = s.execute(q, {"id": currency_id}).mappings().first()
    if not r:
        return "", "", ""
    code   = r["code"] or ""
    name   = r.get(f"name_{lang}") or r.get("name_en") or r.get("name_ar") or r.get("name_tr") or ""
    symbol = (r.get("symbol") if "symbol" in cols else None) or code
    return code, name, symbol


def delivery_method_name(s: Any, dm_id: Optional[int], lang: str) -> str:
    """يُعيد اسم طريقة التسليم بالـ lang المطلوبة."""
    if not dm_id:
        return ""
    from sqlalchemy import text
    r = s.execute(
        text("SELECT name_ar, name_en, name_tr FROM delivery_methods WHERE id=:id"),
        {"id": dm_id}
    ).mappings().first()
    if not r:
        return ""
    return r.get(f"name_{lang}") or r.get("name_en") or r.get("name_ar") or r.get("name_tr") or ""


def pick_dest_col(s: Any) -> str:
    """يُعيد اسم عمود بلد الوجهة الصحيح حسب الـ schema."""
    from sqlalchemy import text
    cols = {r["name"] for r in s.execute(text("PRAGMA table_info(transactions)")).mappings().all()}
    return "destination_country_id" if "destination_country_id" in cols else "dest_country_id"


# ─────────────────────────────────────────────
# 3. Pricing helpers
# ─────────────────────────────────────────────

def label_from_pricing_code(code: str) -> str:
    """يُعيد لابل وحدة التسعير (TON/KG/UNIT) بناءً على الكود."""
    c = (code or "").upper()
    if c in ("TON", "T", "MT", "TON_NET", "TON_GROSS"):
        return "TON"
    if c in ("KG", "KILO", "KG_NET", "KG_GROSS", "GROSS", "BRUT"):
        return "KG"
    return "UNIT"


def compute_line_amount(
    qty: float, net: float, gross: float,
    unit_price: float,
    pt_compute_by: str, pt_price_unit: str, pt_divisor: float,
    pricing_code: str,
) -> Tuple[float, str]:
    """
    يحسب مبلغ السطر ويُعيد (amount, unit_label).
    يأخذ compute_by/price_unit/divisor من pricing_type إن وُجدت،
    وإلا يعتمد على الكود (fallback).
    """
    cb = (pt_compute_by or "").upper()
    pu = (pt_price_unit or "").upper()
    dv = float(pt_divisor or 1.0)

    if not pu:
        pu = label_from_pricing_code(pricing_code)

    if cb in ("QTY", "NET", "GROSS"):
        base = qty if cb == "QTY" else (net if cb == "NET" else gross)
        return (base / (dv or 1.0)) * unit_price, pu

    # Fallback بالكود
    code = (pricing_code or "").upper()
    if code in ("KG", "KILO", "KG_NET"):
        return net * unit_price, "KG"
    if code in ("KG_GROSS", "GROSS", "BRUT"):
        return gross * unit_price, "KG"
    if code in ("TON", "T", "MT", "TON_NET"):
        return (net / 1000.0) * unit_price, "TON"
    if code in ("TON_GROSS",):
        return (gross / 1000.0) * unit_price, "TON"
    if code in ("UNIT", "PCS", "PIECE"):
        return qty * unit_price, "UNIT"
    return qty * unit_price, "UNIT"


# ─────────────────────────────────────────────
# 4. Tafqit (تفقيط)
# ─────────────────────────────────────────────

def tafqit_amount(total_value: float, currency_code: str, lang: str) -> str:
    """تفقيط مبلغ مالي."""
    try:
        from services.tafqit_service import tafqit
        return tafqit(float(total_value or 0), currency_code or "", (lang or "ar").lower())
    except Exception:
        pass
    try:
        from services.tafqit_service import TafqitService
        return TafqitService().amount_in_words(float(total_value or 0), currency_code or "", (lang or "ar").lower())
    except Exception:
        return ""


def num_words(n: float, lang: str) -> str:
    """يُحوّل رقم صحيح إلى نص."""
    n_int = int(round(float(n or 0)))
    try:
        l = (lang or "ar").lower()
        if l.startswith("ar"):
            from services.tafqit_service import number_to_words_ar
            return number_to_words_ar(n_int)
        if l.startswith("tr"):
            from services.tafqit_service import number_to_words_tr
            return number_to_words_tr(n_int)
        from services.tafqit_service import number_to_words_en
        return number_to_words_en(n_int)
    except Exception:
        return str(n_int)


def unit_word(unit_label: Optional[str], lang: str, *, kind: str = "qty") -> str:
    """يُعيد الكلمة المناسبة للوحدة (كيلوغرام/طن/وحدة) حسب اللغة."""
    u = (unit_label or "").strip().upper()
    l = (lang or "en").lower()
    if l.startswith("ar"):
        if kind == "weight":
            return "كيلوغرام" if u in ("", "KG", "KILOGRAM") else ("طن" if u in ("T", "TON", "TONS") else (unit_label or "كيلوغرام"))
        return "وحدة" if not u else (unit_label or "وحدة")
    if l.startswith("tr"):
        if kind == "weight":
            return "kilogram" if u in ("", "KG", "KILOGRAM") else ("ton" if u in ("T", "TON", "TONS") else (unit_label or "kilogram"))
        return "birim" if not u else (unit_label or "birim")
    # EN
    if kind == "weight":
        return "kilograms" if u in ("", "KG", "KILOGRAM") else ("tons" if u in ("T", "TON", "TONS") else (unit_label or "kilograms"))
    return "units" if not u else (unit_label or "units")


def spell_non_monetary(n: float, lang: str, unit_label: Optional[str], *, kind: str = "qty") -> str:
    """رقم + وحدة كنص (غير مالي)."""
    return f"{num_words(n, lang)} {unit_word(unit_label, lang, kind=kind)}".strip()
