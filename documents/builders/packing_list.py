"""
packing_list.py
================
Packing List builder for LOGIPORT

- يتوافق مع schema الحالي (exporter_company_id, importer_company_id, ...)
- يستخدم SessionLocal() بشكل صحيح (factory pattern)
- يجلب اسم المادة من جدول materials
- يجلب نوع التغليف من جدول packaging_types
- دعم كامل AR / EN / TR
"""

from __future__ import annotations
from contextlib import closing
from typing import Dict, List, Any, Optional
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
# Session helper
# ─────────────────────────────────────────────────────────────────────────────

def _open_session():
    """يُعيد session instance (وليس factory)."""
    SessionLocal = get_session_local()
    return closing(SessionLocal())


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_header(transaction_id: int, lang: str) -> Dict[str, Any]:
    SessionLocal = get_session_local()
    with closing(SessionLocal()) as s:
        dest_col = pick_dest_col(s)

        row = s.execute(text(f"""
            SELECT
                t.id,
                t.transaction_no,
                t.transaction_date   AS issue_date,
                t.exporter_company_id,
                t.importer_company_id,
                t.client_id,
                t.delivery_method_id,
                t.origin_country_id,
                t.{dest_col}         AS destination_country_id,
                t.transport_type,
                t.transport_ref,
                t.notes
            FROM transactions t
            WHERE t.id = :id
        """), {"id": transaction_id}).mappings().first()

        if not row:
            raise ValueError(f"Transaction #{transaction_id} not found")

        exporter  = company_obj(s, row["exporter_company_id"], lang)
        importer  = company_obj(s, row["importer_company_id"], lang)
        client    = client_obj(s,  row["client_id"],           lang)
        delivery  = delivery_method_name(s, row.get("delivery_method_id"), lang)

        origin_country = country_name(s, row.get("origin_country_id"),      lang)
        dest_country   = country_name(s, row.get("destination_country_id"), lang)

    return {
        "id":                 row["id"],
        "transaction_no":     row["transaction_no"] or "",
        "issue_date":         str(row["issue_date"] or ""),
        "exporter":           exporter,
        "importer":           importer,
        "client":             client,
        "delivery_method":    delivery,
        "country_of_origin":  origin_country,
        "destination_country": dest_country,
        "transport_type":     row.get("transport_type") or "",
        "transport":          row.get("transport_ref")  or "",
        "notes":              row.get("notes")          or "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# ITEMS
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_items(transaction_id: int, lang: str) -> List[Dict[str, Any]]:
    SessionLocal = get_session_local()
    with closing(SessionLocal()) as s:
        rows = s.execute(text("""
            SELECT
                ti.id,
                ti.quantity,
                ti.gross_weight_kg,
                ti.net_weight_kg,
                ti.packaging_type_id,
                ti.material_id,
                m.name_ar AS mat_ar,
                m.name_en AS mat_en,
                m.name_tr AS mat_tr
            FROM transaction_items ti
            LEFT JOIN materials m ON m.id = ti.material_id
            WHERE ti.transaction_id = :id
            ORDER BY ti.id
        """), {"id": transaction_id}).mappings().all()

        # جلب أسماء أنواع التغليف دفعة واحدة
        pkg_ids = {r["packaging_type_id"] for r in rows if r["packaging_type_id"]}
        pkg_names: Dict[int, str] = {}
        if pkg_ids:
            placeholders = ",".join(str(i) for i in pkg_ids)
            pkg_rows = s.execute(text(f"""
                SELECT id, name_ar, name_en, name_tr
                FROM packaging_types
                WHERE id IN ({placeholders})
            """)).mappings().all()
            for p in pkg_rows:
                name = (p.get(f"name_{lang}") or p.get("name_en")
                        or p.get("name_ar") or p.get("name_tr") or "")
                pkg_names[p["id"]] = name

    items: List[Dict[str, Any]] = []
    for i, r in enumerate(rows, 1):
        mat_name = (
            r.get(f"mat_{lang}") or r.get("mat_en")
            or r.get("mat_ar")   or r.get("mat_tr") or ""
        )
        pkg_id   = r.get("packaging_type_id")
        pkg_name = pkg_names.get(pkg_id, "") if pkg_id else ""

        items.append({
            "line":          i,
            "description":   mat_name,
            "quantity":      float(r.get("quantity")        or 0),
            "net_kg":        float(r.get("net_weight_kg")   or 0),
            "gross_kg":      float(r.get("gross_weight_kg") or 0),
            "package_type":  pkg_name,
            "package_count": 0,   # لا يوجد عمود package_count في الـ schema الحالي
        })

    return items


# ─────────────────────────────────────────────────────────────────────────────
# TOTALS
# ─────────────────────────────────────────────────────────────────────────────

def _compute_totals(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    qty = gross = net = total_packages = 0
    packages: Dict[str, int] = {}

    for r in items:
        qty   += r["quantity"]
        gross += r["gross_kg"]
        net   += r["net_kg"]
        pkg_type  = r.get("package_type")
        pkg_count = int(r.get("package_count") or 0)
        if pkg_type and pkg_count:
            packages[pkg_type] = packages.get(pkg_type, 0) + pkg_count
            total_packages     += pkg_count

    package_list = [f"{v} {k}" for k, v in packages.items()]

    return {
        "quantity":         qty,
        "gross_kg":         gross,
        "net_kg":           net,
        "packages_total":   total_packages,
        "packages_summary": join_with_and(package_list, "en") if package_list else "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def build_ctx(transaction_id: int, lang: str = "en") -> Dict[str, Any]:
    header = _fetch_header(transaction_id, lang)
    items  = _fetch_items(transaction_id, lang)
    totals = _compute_totals(items)

    weight_unit = DEFAULT_WEIGHT_UNIT

    qty_in_words   = spell_non_monetary(totals["quantity"], lang, "",           kind="qty")
    gross_in_words = spell_non_monetary(totals["gross_kg"], lang, weight_unit,  kind="weight")
    net_in_words   = spell_non_monetary(totals["net_kg"],   lang, weight_unit,  kind="weight")

    ctx = {
        "header":          header,
        "items":           items,
        "totals":          totals,
        "qty_in_words":    qty_in_words,
        "gross_in_words":  gross_in_words,
        "net_in_words":    net_in_words,
        "weight_unit":     weight_unit,
    }

    return blankify(ctx)


# backward compat alias
def build(transaction_id: int, lang: str = "en") -> Dict[str, Any]:
    return build_ctx(transaction_id, lang)