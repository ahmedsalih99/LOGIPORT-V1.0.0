# documents/builders/packing_list.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List
from sqlalchemy import text
from database.models import get_session_local
from documents.builders._shared import (
    blankify, coalesce, dedup_preserve_order, join_with_and,
    country_name   as _country_name,
    company_obj    as _company_obj,
    client_obj     as _client_obj,
    get_bank_info,
    tafqit_amount  as _tafqit_amount,
    num_words      as _num_words,
    unit_word      as _unit_word,
    spell_non_monetary as _spell_non_monetary,
    label_from_pricing_code,
    compute_line_amount,
    currency_info  as _currency_info,
    delivery_method_name,
    pick_dest_col  as _pick_dest_col,
)
_blankify  = blankify
_coalesce  = coalesce
_dedup_preserve_order = dedup_preserve_order

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