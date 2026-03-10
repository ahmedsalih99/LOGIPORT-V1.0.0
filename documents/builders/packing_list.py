"""
packing_list.py
================
Packing List builder for LOGIPORT

Context contract (matches all 3 template variants):
  exporter         : dict  (name, address, city, country, tax_id, ...)
  importer         : dict  (same)
  transaction      : dict  (no, issue_date)
  rows             : list of dicts per item:
      line_no          int
      line_id          str   (entry_item_id label — with_line_id variant)
      container_no     str   (from transport_ref)
      description      str
      quantity         float
      gross_kg         float
      net_kg           float
      packaging_type   str
      mfg_date         str   (with_dates variant)
      exp_date         str   (with_dates variant)
      entry_item_id    int   (with_line_id variant)
  totals           : dict  (quantity, gross_kg, net_kg)
  tafqit_qty       : str
  tafqit_gross     : str
  tafqit_net       : str
  incoterms        : str
  delivery_method  : str
  country_of_origin: str
  port_of_loading  : str
  port_of_discharge: str
  notes            : str
  weight_unit      : str
"""

from __future__ import annotations
from contextlib import closing
from typing import Dict, List, Any
from sqlalchemy import text
from database.models import get_session_local

from documents.builders._shared import (
    blankify,
    country_name,
    company_obj,
    client_obj,
    spell_non_monetary,
    pick_dest_col,
    delivery_method_name,
    join_with_and,
)

DEFAULT_WEIGHT_UNIT = "kg"


# ─────────────────────────────────────────────────────────────────────────────
# HEADER  →  transaction + exporter + importer
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_header(transaction_id: int, lang: str) -> Dict[str, Any]:
    SessionLocal = get_session_local()
    with closing(SessionLocal()) as s:
        dest_col = pick_dest_col(s)

        row = s.execute(text(f"""
            SELECT
                t.transaction_no,
                t.transaction_date      AS issue_date,
                t.exporter_company_id,
                t.importer_company_id,
                t.client_id,
                t.delivery_method_id,
                t.origin_country_id,
                t.{dest_col}            AS destination_country_id,
                t.transport_type,
                t.notes
            FROM transactions t
            WHERE t.id = :id
        """), {"id": transaction_id}).mappings().first()

        if not row:
            raise ValueError(f"Transaction #{transaction_id} not found")

        exporter = company_obj(s, row["exporter_company_id"], lang)
        importer = company_obj(s, row["importer_company_id"], lang)
        client   = client_obj(s,  row["client_id"],           lang)
        delivery = delivery_method_name(s, row.get("delivery_method_id"), lang)

        origin_country = country_name(s, row.get("origin_country_id"),      lang)
        dest_country   = country_name(s, row.get("destination_country_id"), lang)

        # incoterms — جلبه من pricing_type إذا وجد
        incoterms = ""

    return {
        # للـ template: trx.no / trx.issue_date
        "transaction": {
            "no":         row["transaction_no"] or "",
            "issue_date": str(row["issue_date"] or ""),
        },
        "exporter":           exporter,
        "importer":           importer,
        "client":             client,
        "delivery_method":    delivery,
        "country_of_origin":  origin_country,
        "destination_country": dest_country,
        "incoterms":          incoterms,
        "port_of_loading":    "",
        "port_of_discharge":  "",
        "transport_type":     row.get("transport_type") or "",
        "notes":              row.get("notes") or "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# ITEMS  →  rows list
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_rows(transaction_id: int, lang: str) -> List[Dict[str, Any]]:
    SessionLocal = get_session_local()
    with closing(SessionLocal()) as s:
        rows = s.execute(text("""
            SELECT
                ti.id               AS ti_id,
                ti.quantity,
                ti.gross_weight_kg,
                ti.net_weight_kg,
                ti.packaging_type_id,
                ti.transport_ref,
                ti.entry_item_id,
                m.code              AS mat_code,
                m.name_ar           AS mat_ar,
                m.name_en           AS mat_en,
                m.name_tr           AS mat_tr,
                ei.mfg_date,
                ei.exp_date
            FROM transaction_items ti
            LEFT JOIN materials    m  ON m.id  = ti.material_id
            LEFT JOIN entry_items  ei ON ei.id = ti.entry_item_id
            WHERE ti.transaction_id = :id
            ORDER BY ti.id
        """), {"id": transaction_id}).mappings().all()

        # جلب أسماء أنواع التغليف دفعة واحدة
        pkg_ids = {r["packaging_type_id"] for r in rows if r["packaging_type_id"]}
        pkg_names: Dict[int, str] = {}
        if pkg_ids:
            ph = ",".join(str(i) for i in pkg_ids)
            for p in s.execute(text(f"""
                SELECT id, name_ar, name_en, name_tr
                FROM packaging_types WHERE id IN ({ph})
            """)).mappings().all():
                pkg_names[p["id"]] = (
                    p.get(f"name_{lang}") or p.get("name_en")
                    or p.get("name_ar") or p.get("name_tr") or ""
                )

    result: List[Dict[str, Any]] = []
    for i, r in enumerate(rows, 1):
        mat = (r.get(f"mat_{lang}") or r.get("mat_en")
               or r.get("mat_ar")   or r.get("mat_tr") or "")
        pkg_id = r.get("packaging_type_id")

        result.append({
            "line_no":        i,
            "line_id":        str(r.get("entry_item_id") or ""),
            "material_code":  r.get("mat_code") or "",
            "container_no":   r.get("transport_ref") or "",
            "description":    mat,
            "quantity":       float(r.get("quantity")        or 0),
            "gross_kg":       float(r.get("gross_weight_kg") or 0),
            "net_kg":         float(r.get("net_weight_kg")   or 0),
            "packaging_type": pkg_names.get(pkg_id, "") if pkg_id else "",
            "mfg_date":       str(r["mfg_date"] or "") if r.get("mfg_date") else "",
            "exp_date":       str(r["exp_date"] or "") if r.get("exp_date") else "",
            "entry_item_id":  r.get("entry_item_id") or 0,
        })

    return result


# ─────────────────────────────────────────────────────────────────────────────
# TOTALS
# ─────────────────────────────────────────────────────────────────────────────

def _compute_totals(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    qty = gross = net = 0.0
    for r in rows:
        qty   += r["quantity"]
        gross += r["gross_kg"]
        net   += r["net_kg"]
    return {"quantity": qty, "gross_kg": gross, "net_kg": net}


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def build_ctx(transaction_id: int, lang: str = "en") -> Dict[str, Any]:
    header = _fetch_header(transaction_id, lang)
    rows   = _fetch_rows(transaction_id, lang)
    totals = _compute_totals(rows)
    wu     = DEFAULT_WEIGHT_UNIT

    ctx = {
        # parties & transaction info (flat — templates use these directly)
        "exporter":            header["exporter"],
        "importer":            header["importer"],
        "client":              header["client"],
        "transaction":         header["transaction"],
        "delivery_method":     header["delivery_method"],
        "country_of_origin":   header["country_of_origin"],
        "destination_country": header["destination_country"],
        "incoterms":           header["incoterms"],
        "port_of_loading":     header["port_of_loading"],
        "port_of_discharge":   header["port_of_discharge"],
        "notes":               header["notes"],

        # items
        "rows":   rows,
        "totals": totals,

        # tafqit (كتابة الأرقام بالحروف)
        "tafqit_qty":   spell_non_monetary(totals["quantity"], lang, "",  kind="qty"),
        "tafqit_gross": spell_non_monetary(totals["gross_kg"], lang, wu,  kind="weight"),
        "tafqit_net":   spell_non_monetary(totals["net_kg"],   lang, wu,  kind="weight"),

        "weight_unit": wu,
    }

    return blankify(ctx)


# backward compat alias
def build(transaction_id: int, lang: str = "en") -> Dict[str, Any]:
    return build_ctx(transaction_id, lang)