# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Tuple, List
from contextlib import closing
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

try:
    from documents.builders.invoice_syrian_entry import build_ctx as _entry_build_ctx2
except Exception:
    _entry_build_ctx2 = None  # type: ignore

try:
    from database.models import get_session_local
except Exception:
    def get_session_local():  # type: ignore
        raise RuntimeError("database.models.get_session_local is not available")


# ------------------------- utils -------------------------

def _blankify(v):
    from collections.abc import Mapping, Sequence
    if v is None: return ""
    if isinstance(v, str): return v.strip()
    if isinstance(v, Mapping): return {k: _blankify(val) for k, val in v.items()}
    if isinstance(v, Sequence) and not isinstance(v, (str, bytes, bytearray)): return [_blankify(x) for x in v]
    return v


def _normalize_call(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Accept positional or keyword style and ALWAYS capture the lang correctly.

    Supported calls:
      build_ctx("invoice.syrian.intermediary", 123, "en")
      build_ctx(doc_code="invoice.syrian.intermediary", transaction_id=123, lang="en")
      build_ctx("invoice.syrian.intermediary", lang="tr", transaction_id=123)
    """
    out = dict(kwargs)

    # doc_code
    if "doc_code" not in out and len(args) >= 1 and isinstance(args[0], str):
        out["doc_code"] = args[0]

    # transaction_id
    if "transaction_id" not in out:
        for a in args:
            if isinstance(a, int):
                out["transaction_id"] = a
                break

    # lang — IMPORTANT: handle both index 2 and 1 (some routers pass lang at pos=2)
    if "lang" not in out and len(args) >= 3 and isinstance(args[2], str):
        out["lang"] = args[2]
    if "lang" not in out and len(args) >= 2 and isinstance(args[1], str):
        out["lang"] = args[1]

    # sane default (system often expects English if not specified explicitly)
    out["lang"] = (out.get("lang") or "en").lower()

    if "transaction_id" not in out:
        raise TypeError("build_ctx missing required 'transaction_id'")

    return out


def _lang_order(lang: str) -> tuple[str, str, str]:
    l = (lang or "en").lower()
    if l.startswith("en"): return ("en", "tr", "ar")
    if l.startswith("tr"): return ("tr", "en", "ar")
    return ("ar", "en", "tr")


def _pick(values: Dict[str, Any], base: str, lang: str) -> str:
    """Pick value by language WITHOUT injecting cross-language fallbacks into *_en/*_tr keys."""
    l1, l2, l3 = _lang_order(lang)
    for code in (l1, l2, l3):
        v = values.get(f"{base}_{code}")
        if v not in (None, ""):
            return str(v).strip()
    v = values.get(base)
    return str(v).strip() if v not in (None, "") else ""


# ------------------------- shared normalize -------------------------

def _normalize_shared_blocks(base: Dict[str, Any]) -> None:
    consignee = base.get("consignee") or base.get("importer") or {}
    transport = base.get("transport", {}) or {}
    delivery  = base.get("delivery", {}) or {}
    currency  = base.get("currency", {}) or base.get("currency_code") or ""

    base["shipment"] = {
        "delivery_method": delivery.get("method") or transport.get("delivery_method") or "",
        "transport_ref": transport.get("container_no") or transport.get("truck_no") or transport.get("ref") or "",
        "destination_country": (consignee or {}).get("country") or "",
        "currency_code": (currency.get("code") if isinstance(currency, dict) else currency) or "",
    }

    t = base.get("totals", {}) or {}
    base["totals"] = {
        "qty":   t.get("qty")   or t.get("quantity")     or t.get("total_qty")   or 0,
        "gross": t.get("gross") or t.get("gross_weight") or t.get("total_gross") or 0,
        "net":   t.get("net")   or t.get("net_weight")   or t.get("total_net")   or 0,
        "value": t.get("value") or t.get("total_value")  or 0,
    }

    base["amount_in_words"] = (base.get("totals_text", {}) or {}).get("value", "")

    base.setdefault("transit", {})
    base["transit"].update({
        "has_intermediary": True,
        "border_point_in":  base.get("transit", {}).get("border_point_in")  or transport.get("entry_border", ""),
        "border_point_out": base.get("transit", {}).get("border_point_out") or transport.get("exit_border",  ""),
    })


# ------------------------- DB: intermediary (localized) -------------------------

def _fetch_company_localized(s, company_id: int, lang: str) -> Dict[str, Any]:
    try:
        row = s.execute(text("""
            SELECT
                cmp.name_ar     AS name_ar,
                cmp.name_en     AS name_en,
                cmp.name_tr     AS name_tr,
                cmp.address_ar  AS address_ar,
                cmp.address_en  AS address_en,
                cmp.address_tr  AS address_tr,
                (SELECT c.name_ar FROM countries c WHERE c.id = cmp.country_id) AS country_ar,
                (SELECT c.name_en FROM countries c WHERE c.id = cmp.country_id) AS country_en,
                (SELECT c.name_tr FROM countries c WHERE c.id = cmp.country_id) AS country_tr,
                cmp.city        AS city_raw
            FROM companies cmp
            WHERE cmp.id = :cid
        """), {"cid": int(company_id)}).mappings().first()
        if row:
            return {
                "intermediary_supplier_name": _pick(row, "name", lang),
                "intermediary_supplier_address": _pick(row, "address", lang),
                "intermediary_supplier_country": _pick(row, "country", lang),
                "intermediary_supplier_city": str(row.get("city_raw") or "").strip(),
            }
    except OperationalError:
        pass
    return {
        "intermediary_supplier_name": "",
        "intermediary_supplier_address": "",
        "intermediary_supplier_country": "",
        "intermediary_supplier_city": "",
    }


def _try_fetch_intermediary_fields(transaction_id: int, lang: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "intermediary_invoice_no": "",
        "intermediary_invoice_date": "",
        "intermediary_supplier_name": "",
        "intermediary_supplier_address": "",
        "intermediary_supplier_country": "",
        "intermediary_supplier_city": "",
        "_source": "not_found",
    }
    SessionLocal = get_session_local()
    with closing(SessionLocal()) as s:
        try:
            row = s.execute(text("""
                SELECT intermediary_invoice_no,
                       intermediary_invoice_date,
                       intermediary_supplier_id,
                       broker_company_id
                FROM transactions
                WHERE id = :i
            """), {"i": int(transaction_id)}).first()
        except OperationalError:
            return result

        if not row:
            return result

        ino, idate, supplier_id, broker_id = row
        result["intermediary_invoice_no"] = (ino or "")
        result["intermediary_invoice_date"] = (idate or "")
        company_id = supplier_id or broker_id
        result["_source"] = "transactions.intermediary_supplier_id" if supplier_id else (
                             "transactions.broker_company_id" if broker_id else "not_found")
        if company_id:
            result.update(_fetch_company_localized(s, int(company_id), lang))
    return result


# ------------------------- i18n labels -------------------------

def _labels(lang: str) -> Dict[str, str]:
    l = (lang or "en").lower()
    if l.startswith("en"): return {"TRANSIT": "TRANSIT", "TRANSIT_TO": "Transit to"}
    if l.startswith("tr"): return {"TRANSIT": "TRANSİT", "TRANSIT_TO": "Transit - Varış Ülkesi:"}
    return {"TRANSIT": "ترانزيت", "TRANSIT_TO": "ترانزيت إلى"}


# ------------------------- post-localize parties & items -------------------------

def _localize_party(p: Dict[str, Any], lang: str) -> Dict[str, Any]:
    if not isinstance(p, dict): return {}
    out = dict(p)
    out["name"]    = _pick(p, "name", lang)    or p.get("name")    or ""
    out["address"] = _pick(p, "address", lang) or p.get("address") or ""
    out["country"] = _pick(p, "country", lang) or p.get("country") or ""
    out["city"] = p.get("city") or ""
    return out


def _localize_items(items: List[Dict[str, Any]], lang: str) -> List[Dict[str, Any]]:
    out = []
    for it in (items or []):
        it2 = dict(it or {})
        it2["description"] = _pick(it2, "description", lang) or it.get("description") or ""
        it2["gross_unit_label"] = _pick(it2, "gross_unit_label", lang) or it.get("gross_unit_label") or it.get("gross_unit") or ""
        it2["net_unit_label"]   = _pick(it2, "net_unit_label",   lang) or it.get("net_unit_label")   or it.get("net_unit")   or ""
        it2["pricing_type_label"] = _pick(it2, "pricing_type_label", lang) or it.get("pricing_type_label") or ""
        out.append(it2)
    return out


def _compute_transit_to_text(transaction_id: int, base: Dict[str, Any], lang: str) -> Dict[str, str]:
    importer = base.get("importer") or base.get("consignee") or {}
    country_ar = importer.get("country_ar") or importer.get("country") or ""
    country_en = importer.get("country_en") or importer.get("country") or ""
    country_tr = importer.get("country_tr") or importer.get("country") or ""
    names = {"ar": country_ar, "en": country_en, "tr": country_tr}

    if not any(names.values()):
        SessionLocal = get_session_local()
        with closing(SessionLocal()) as s:
            try:
                row = s.execute(text("""
                    SELECT
                       (SELECT cn.name_ar FROM countries cn WHERE cn.id = t.dest_country_id) AS dest_ar,
                       (SELECT cn.name_en FROM countries cn WHERE cn.id = t.dest_country_id) AS dest_en,
                       (SELECT cn.name_tr FROM countries cn WHERE cn.id = t.dest_country_id) AS dest_tr,
                       t.importer_company_id
                    FROM transactions t
                    WHERE t.id = :i
                """), {"i": int(transaction_id)}).mappings().first()
            except OperationalError:
                row = None

            if row:
                names = {
                    "ar": row.get("dest_ar") or "",
                    "en": row.get("dest_en") or "",
                    "tr": row.get("dest_tr") or "",
                }
                if not any(names.values()) and row.get("importer_company_id"):
                    try:
                        r2 = s.execute(text("""
                            SELECT
                               (SELECT cn.name_ar FROM countries cn WHERE cn.id = cmp.country_id) AS c_ar,
                               (SELECT cn.name_en FROM countries cn WHERE cn.id = cmp.country_id) AS c_en,
                               (SELECT cn.name_tr FROM countries cn WHERE cn.id = cmp.country_id) AS c_tr
                            FROM companies cmp WHERE cmp.id = :cid
                        """), {"cid": int(row["importer_company_id"])}).mappings().first()
                        if r2:
                            names = {"ar": r2.get("c_ar") or "", "en": r2.get("c_en") or "", "tr": r2.get("c_tr") or ""}
                    except OperationalError:
                        pass

    txt = {
        "ar": (f"ترانزيت إلى {names['ar']}".strip() if names["ar"] else "ترانزيت"),
        "en": (f"Transit to {names['en']}".strip() if names["en"] else "TRANSIT"),
        "tr": (f"Transit - Varış Ülkesi: {names['tr']}".strip() if names["tr"] else "TRANSİT"),
    }
    sel = "ar" if lang.startswith("ar") else ("en" if lang.startswith("en") else "tr")
    return {"ar": txt["ar"], "en": txt["en"], "tr": txt["tr"], "selected": txt[sel]}


# ------------------------- public API -------------------------

def build_ctx(*args, **kwargs) -> Dict[str, Any]:
    if _entry_build_ctx2 is None:
        raise RuntimeError("invoice_syrian_entry.build_ctx is not importable")

    call = _normalize_call(args, kwargs)
    lang = (call["lang"] or "en").lower()

    base = _entry_build_ctx2(
        doc_code=call.get("doc_code", "invoice.syrian.intermediary"),
        transaction_id=int(call["transaction_id"]),
        lang=lang,
    )

    base.setdefault("doc", {})
    base["doc"]["type"] = "syrian_transit_intermediary"

    _normalize_shared_blocks(base)

    # Localize parties & items *without* cross-language injection
    for key in ("exporter", "importer", "consignee"):
        if key in base:
            base[key] = _localize_party(dict(base[key] or {}), lang)

    base["items"] = _localize_items(base.get("items") or [], lang)

    base["transit_label"] = _labels(lang)["TRANSIT"]
    interm = _try_fetch_intermediary_fields(int(call["transaction_id"]), lang)
    base.setdefault("transit", {})
    base["transit"]["intermediary"] = {k: v for k, v in interm.items() if not k.startswith("_")}
    base.setdefault("debug", {})
    base["debug"]["intermediary_source"] = interm.get("_source", "not_found")

    tt = _compute_transit_to_text(int(call["transaction_id"]), base, lang)
    base["transit_to_text"]    = tt["selected"]
    base["transit_to_text_en"] = tt["en"]
    base["transit_to_text_tr"] = tt["tr"]

    # Choose the correct template for the requested language
    if lang.startswith("en"):
        base["template_rel"] = "documents/templates/invoices/syrian/intermediary/en.html"
    elif lang.startswith("tr"):
        base["template_rel"] = "documents/templates/invoices/syrian/intermediary/tr.html"
    else:
        base["template_rel"] = "documents/templates/invoices/syrian/intermediary/ar.html"

    return _blankify(base)
