# documents/builders/packing_list.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from datetime import date
from sqlalchemy import text
from database.models import get_session_local

# ------------------------- helpers -------------------------

def _blankify(v):
    from collections.abc import Mapping, Sequence
    if v is None: return ""
    if isinstance(v, str): return v.strip()
    if isinstance(v, Mapping): return {k: _blankify(val) for k, val in v.items()}
    if isinstance(v, Sequence) and not isinstance(v, (str, bytes, bytearray)): return [_blankify(x) for x in v]
    return v

def _coalesce(*vals):
    for v in vals:
        if v not in (None, "", 0):
            return v
    return None

def _lang_cols(lang: str, base: str) -> str:
    l = (lang or "en").lower()
    if l.startswith("ar"): return f"{base}_ar"
    if l.startswith("tr"): return f"{base}_tr"
    return f"{base}_en"

def _fmt_date(d: Optional[Any]) -> str:
    if not d: return ""
    if hasattr(d, "isoformat"): return d.isoformat()  # date/datetime
    return str(d)

def _num(v) -> float:
    try:
        if v in (None, ""): return 0.0
        return float(v)
    except Exception:
        return 0.0

def _table_cols(s, table: str) -> set[str]:
    rows = s.execute(text(f"PRAGMA table_info({table})")).mappings().all()
    return {str(r["name"]) for r in rows}

# ===== tafqit (نفس أسلوب الفواتير) =====
def _num_words(n: float, lang: str) -> str:
    n_int = int(round(float(n or 0)))
    try:
        if (lang or "en").lower().startswith("ar"):
            from services.tafqit_service import number_to_words_ar
            return number_to_words_ar(n_int)
        if (lang or "en").lower().startswith("tr"):
            from services.tafqit_service import number_to_words_tr
            return number_to_words_tr(n_int)
        from services.tafqit_service import number_to_words_en
        return number_to_words_en(n_int)
    except Exception:
        return str(n_int)

def _unit_word(unit_label: str | None, lang: str, *, kind: str = "qty") -> str:
    u = (unit_label or "").strip().upper()
    if (lang or "en").lower().startswith("ar"):
        if kind == "weight":
            return "كيلوغرام" if u in ("", "KG", "KILOGRAM") else ("طن" if u in ("T","TON","TONS") else unit_label or "كيلوغرام")
        return "وحدة" if not u else unit_label or "وحدة"
    if (lang or "en").lower().startswith("tr"):
        if kind == "weight":
            return "kilogram" if u in ("", "KG", "KILOGRAM") else ("ton" if u in ("T","TON","TONS") else unit_label or "kilogram")
        return "birim" if not u else unit_label or "birim"
    if kind == "weight":
        return "kilograms" if u in ("", "KG", "KILOGRAM") else ("tons" if u in ("T","TON","TONS") else (unit_label or "kilograms"))
    return "units" if not u else (unit_label or "units")

def _spell_non_monetary(n: float, lang: str, unit_label: str | None, *, kind: str = "qty") -> str:
    return f"{_num_words(n, lang)} {_unit_word(unit_label, lang, kind=kind)}".strip()

# ------------------------- parties (مطابقة للفواتير) -------------------------

def _country_name(s, country_id, lang: str) -> str:
    if not country_id: return ""
    r = s.execute(text("SELECT name_ar, name_en, name_tr FROM countries WHERE id=:i"),
                  {"i": country_id}).mappings().first()
    if not r: return ""
    fld = _lang_cols(lang, "name")
    return r.get(fld) or r.get("name_en") or r.get("name_ar") or r.get("name_tr") or ""

def _company_obj(s, company_id, lang: str) -> Dict[str, Any]:
    if not company_id: return {"name": "", "address": ""}
    r = s.execute(text("""
        SELECT id,
               name_ar, name_en, name_tr,
               address_ar, address_en, address_tr,
               country_id, city, phone, email, website, tax_id, registration_number,
               bank_info
        FROM companies WHERE id=:id
    """), {"id": company_id}).mappings().first()
    if not r: return {"name": "", "address": ""}
    name = r.get(_lang_cols(lang, "name")) or r.get("name_en") or r.get("name_ar") or r.get("name_tr") or ""
    addr = (r.get(_lang_cols(lang, "address")) or r.get("address_en") or r.get("address_ar") or r.get("address_tr") or "")
    if not addr:
        try:
            r2 = s.execute(text("SELECT address FROM companies WHERE id=:id"), {"id": company_id}).mappings().first()
            if r2 and r2.get("address"): addr = r2.get("address")
        except Exception:
            pass
    return {
        "name": name,
        "address": addr,
        "city": r.get("city"),
        "country": _country_name(s, r.get("country_id"), lang),
        "phone": r.get("phone"),
        "email": r.get("email"),
        "website": r.get("website"),
        "tax_id": r.get("tax_id"),
        "registration_number": r.get("registration_number"),
        "bank_info": r.get("bank_info") or "",
        "vat_no": r.get("tax_id"),
        "cr_no": r.get("registration_number"),
    }

def _client_obj(s, client_id, lang: str) -> Dict[str, Any]:
    if not client_id: return {"name": "", "address": ""}
    r = s.execute(text("""
        SELECT id,
               name_ar, name_en, name_tr,
               COALESCE(address_ar, address) AS address_ar,
               COALESCE(address_en, address) AS address_en,
               COALESCE(address_tr, address) AS address_tr,
               country_id, city, phone, email, website, tax_id
        FROM clients WHERE id=:id
    """), {"id": client_id}).mappings().first()
    if not r: return {"name": "", "address": ""}
    name = r.get(_lang_cols(lang, "name")) or r.get("name_en") or r.get("name_ar") or r.get("name_tr") or ""
    addr = r.get(_lang_cols(lang, "address")) or r.get("address_en") or r.get("address_ar") or r.get("address_tr") or ""
    return {"name": name, "address": addr, "city": r.get("city"),
            "country": _country_name(s, r.get("country_id"), lang),
            "phone": r.get("phone"), "email": r.get("email"),
            "website": r.get("website"), "tax_id": r.get("tax_id")}

# ------------------------- rows query -------------------------

def _fetch_items(trx_id: int, lang: str) -> List[Dict]:
    name_col_mat = _lang_cols(lang, "name")
    name_col_pkg = _lang_cols(lang, "name")

    SessionLocal = get_session_local()
    s = SessionLocal()

    ti_cols = _table_cols(s, "transaction_items")
    e_cols  = _table_cols(s, "entries")
    ei_cols = _table_cols(s, "entry_items")

    gw_alt_sel = "ti.gross_weight AS gw_alt" if "gross_weight" in ti_cols else "NULL AS gw_alt"
    nw_alt_sel = "ti.net_weight   AS nw_alt" if "net_weight"   in ti_cols else "NULL AS nw_alt"

    transp_type_sel = "e.transport_unit_type AS transport_unit_type" if "transport_unit_type" in e_cols else "NULL AS transport_unit_type"
    unit_label_sel  = "ei.unit_label AS unit_label" if "unit_label" in ei_cols else "NULL AS unit_label"
    batch_no_sel    = "ei.batch_no AS batch_no"     if "batch_no" in ei_cols else "NULL AS batch_no"
    mfg_sel         = "ei.mfg_date AS mfg_date"     if "mfg_date" in ei_cols else "NULL AS mfg_date"
    exp_sel         = "ei.exp_date AS exp_date"     if "exp_date" in ei_cols else "NULL AS exp_date"

    sql = f"""
        SELECT
            ti.id                 AS ti_id,
            ti.entry_id           AS entry_id,
            ti.entry_item_id      AS entry_item_id,
            ti.quantity           AS qty,
            ti.gross_weight_kg    AS gw_kg,
            ti.net_weight_kg      AS nw_kg,
            {gw_alt_sel},
            {nw_alt_sel},
            ti.packaging_type_id  AS packaging_type_id,
            ti.material_id        AS material_id,
            COALESCE(ti.transport_ref, e.transport_ref) AS transport_ref,
            {transp_type_sel},
            {mfg_sel}, {exp_sel}, {unit_label_sel}, {batch_no_sel},
            m.{name_col_mat}      AS material_name,
            pt.{name_col_pkg}     AS packaging_name
        FROM transaction_items ti
            LEFT JOIN entries e           ON e.id = ti.entry_id
            LEFT JOIN entry_items ei      ON ei.id = ti.entry_item_id
            LEFT JOIN materials m         ON m.id = ti.material_id
            LEFT JOIN packaging_types pt  ON pt.id = ti.packaging_type_id
        WHERE ti.transaction_id = :tid
        ORDER BY ti.id ASC
    """
    rows = s.execute(text(sql), {"tid": int(trx_id)}).mappings().all()
    s.close()

    items: List[Dict] = []
    for i, r in enumerate(rows, 1):
        g = _coalesce(r.get("gw_kg"), r.get("gw_alt"), 0) or 0
        n = _coalesce(r.get("nw_kg"), r.get("nw_alt"), 0) or 0
        items.append({
            "line_no": i,
            "container_no": _blankify(r.get("transport_ref")),
            "container_type": _blankify(r.get("transport_unit_type")),
            "description": _blankify(r.get("material_name")),
            "quantity": _num(r.get("qty")),
            "unit": _blankify(r.get("unit_label")),
            "gross_kg": _num(g),
            "net_kg": _num(n),
            "packaging_type": _blankify(r.get("packaging_name")),
            "batch_no": _blankify(r.get("batch_no")),
            "mfg_date": _fmt_date(r.get("mfg_date")),
            "exp_date": _fmt_date(r.get("exp_date")),
            "entry_item_id": r.get("entry_item_id"),   # للقوالب التي تعرض رقم السطر
            "line_id": r.get("entry_item_id"),          # alias مريح للقوالب
        })
    return items

def _compute_totals(items: List[Dict]) -> Dict[str, float]:
    tq = sum(_num(x.get("quantity")) for x in items)
    tg = sum(_num(x.get("gross_kg")) for x in items)
    tn = sum(_num(x.get("net_kg")) for x in items)
    return {"quantity": round(tq, 6), "gross_kg": round(tg, 6), "net_kg": round(tn, 6)}

# ------------------------- header/meta -------------------------

def _pick_dest_col(s) -> str:
    cols = _table_cols(s, "transactions")
    return "destination_country_id" if "destination_country_id" in cols else ("dest_country_id" if "dest_country_id" in cols else None)

def _fetch_header(trx_id: int, lang: str) -> Dict[str, Any]:
    SessionLocal = get_session_local()
    s = SessionLocal()

    tcols = _table_cols(s, "transactions")

    def sel(col: str, alias: Optional[str] = None) -> str:
        """اختيار عمود إذا موجود، وإلا NULL مع نفس الـ alias."""
        a = alias or col
        return f"{col} AS {a}" if col in tcols else f"NULL AS {a}"

    # تاريخ المستند: نختار أول الموجودين
    if "transaction_date" in tcols:
        issue_date_expr = "transaction_date"
    elif "issue_date" in tcols:
        issue_date_expr = "issue_date"
    elif "created_at" in tcols:
        issue_date_expr = "created_at"
    else:
        issue_date_expr = "NULL"

    # وجهة/بلد الوصول: اختلاف أسماء شائع
    if "destination_country_id" in tcols:
        dest_sel = sel("destination_country_id")
    elif "dest_country_id" in tcols:
        dest_sel = sel("dest_country_id", "destination_country_id")
    else:
        dest_sel = "NULL AS destination_country_id"

    # كوّن الاستعلام بأعمدة آمنة
    sql = f"""
        SELECT
            id,
            COALESCE(transaction_no, CAST(id AS TEXT)) AS transaction_no,
            {issue_date_expr} AS issue_date,
            {sel("client_id")},
            {sel("exporter_company_id")},
            {sel("importer_company_id")},
            {sel("delivery_method_id")},
            {sel("origin_country_id")},
            {dest_sel},
            {sel("transport_type")},
            {sel("transport_ref")},
            {sel("incoterms")},
            {sel("port_of_loading")},
            {sel("port_of_discharge")},
            {sel("notes")}
        FROM transactions
        WHERE id = :i
    """
    t = s.execute(text(sql), {"i": int(trx_id)}).mappings().first()
    if not t:
        s.close()
        raise ValueError(f"Transaction #{trx_id} not found")

    # اسم طريقة التسليم (إن وجِد)
    delivery = ""
    if t.get("delivery_method_id"):
        dm = s.execute(text("SELECT name_ar, name_en, name_tr FROM delivery_methods WHERE id=:id"),
                       {"id": t["delivery_method_id"]}).mappings().first()
        if dm:
            delivery = dm.get(_lang_cols(lang, "name")) or dm.get("name_en") or dm.get("name_ar") or dm.get("name_tr") or ""

    exporter = _company_obj(s, t.get("exporter_company_id"), lang)
    importer = _company_obj(s, t.get("importer_company_id"), lang)
    consignee = _client_obj(s, t.get("client_id"), lang)

    header = {
        "id": int(t["id"]),
        "no": _blankify(t["transaction_no"]),
        "issue_date": _fmt_date(t.get("issue_date")) or _fmt_date(date.today()),
        "exporter": exporter,
        "importer": importer,
        "consignee": consignee,
        "incoterms": _blankify(t.get("incoterms")),
        "delivery_method": delivery,
        "country_of_origin": _country_name(s, t.get("origin_country_id"), lang),
        "destination_country": _country_name(s, t.get("destination_country_id"), lang),
        "port_of_loading": _blankify(t.get("port_of_loading")),
        "port_of_discharge": _blankify(t.get("port_of_discharge")),
        "transport": {"type": t.get("transport_type"), "ref": t.get("transport_ref")},
        "notes": _blankify(t.get("notes")),
    }
    s.close()
    return header


# ------------------------- public API -------------------------

def build_ctx(*args, **kwargs) -> Dict:
    """
    build_ctx(doc_code, transaction_id, lang)  أو  build_ctx(doc_code=..., transaction_id=..., lang=...)
    يدعم ثلاثة أنواع:
      - packing_list.export.simple
      - packing_list.export.with_dates
      - packing_list.export.with_line_id
    """
    # تطبيع الاستدعاء
    doc_code = kwargs.get("doc_code") or (args[0] if len(args) >= 1 else None)
    transaction_id = kwargs.get("transaction_id") or kwargs.get("trx_id") or (args[1] if len(args) >= 2 else None)
    lang = kwargs.get("lang") or (args[2] if len(args) >= 3 else "en")
    if doc_code is None or transaction_id is None or lang is None:
        raise ValueError("build_ctx requires doc_code, transaction_id, and lang")

    code = str(doc_code).strip()
    with_dates   = (code == "packing_list.export.with_dates")
    with_line_id = (code == "packing_list.export.with_line_id")
    if code not in ("packing_list.export.simple", "packing_list.export.with_dates", "packing_list.export.with_line_id"):
        raise ValueError(f"Unsupported packing list code: {doc_code}")

    header = _fetch_header(int(transaction_id), str(lang))
    items  = _fetch_items(int(transaction_id), str(lang))
    totals = _compute_totals(items)

    # ===== تفقيط غير نقدي (كميّات/أوزان) =====
    # وحدة الوزن للعرض (KG دائماً بقائمة التعبئة؛ لو أردتها TON استنتجها من البيانات)
    weight_unit = "KG"
    qty_in_words   = _spell_non_monetary(totals["quantity"], lang, "", kind="qty")
    gross_in_words = _spell_non_monetary(totals["gross_kg"], lang, weight_unit, kind="weight")
    net_in_words   = _spell_non_monetary(totals["net_kg"],   lang, weight_unit, kind="weight")

    ctx: Dict[str, Any] = {
        "doc": {"code": code, "lang": str(lang), "with_dates": with_dates, "with_line_id": with_line_id},
        "transaction": {"id": header["id"], "no": header["no"], "issue_date": header["issue_date"]},
        "exporter": header["exporter"],
        "importer": header["importer"],
        "consignee": header["consignee"],
        "incoterms": header["incoterms"],
        "delivery_method": header["delivery_method"],
        "country_of_origin": header["country_of_origin"],
        "destination_country": header["destination_country"],
        "port_of_loading": header["port_of_loading"],
        "port_of_discharge": header["port_of_discharge"],
        "transport": header["transport"],
        "notes": header["notes"],
        "rows": items,
        "totals": totals,
        # tafqit (للاستخدام في القوالب)
        "tafqit_qty": qty_in_words,
        "tafqit_gross": gross_in_words,
        "tafqit_net": net_in_words,
    }

    if with_dates and (header.get("notes") or "").strip():
        ctx["brands_note"] = header["notes"].strip()

    return _blankify(ctx)