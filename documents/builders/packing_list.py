"""
packing_list.py
================

Packing List builder for LOGIPORT

Features
--------
• يعتمد على helpers من _shared
• حساب totals تلقائي
• توليد النصوص بالحروف (tafqit)
• دعم اللغات (AR / EN / TR)
• دمج أنواع التغليف تلقائياً
"""

from typing import Dict, List, Any
from sqlalchemy import text
from database.models import get_session_local

from documents.builders._shared import (
    blankify,
    coalesce,
    country_name,
    company_obj,
    client_obj,
    spell_non_monetary,
    pick_dest_col,
    delivery_method_name,
    join_with_and,
)

DEFAULT_WEIGHT_UNIT = "kg"


# =========================================================
# HEADER
# =========================================================

def _fetch_header(transaction_id: int, lang: str) -> Dict[str, Any]:

    s = get_session_local()
    dest_col = pick_dest_col(s)

    row = s.execute(text(f"""
        SELECT
            t.id,
            t.transaction_no,
            t.issue_date,

            t.exporter_id,
            t.importer_id,
            t.consignee_id,

            t.incoterm_id,
            t.delivery_method_id,

            t.country_of_origin_id,
            t.{dest_col} AS destination_country_id,

            t.port_of_loading,
            t.port_of_discharge,
            t.transport,
            t.notes

        FROM transactions t
        WHERE t.id = :id
    """), {"id": transaction_id}).mappings().first()

    if not row:
        raise ValueError("Transaction not found")

    exporter = company_obj(s, row["exporter_id"], lang)
    importer = client_obj(s, row["importer_id"], lang)
    consignee = client_obj(s, row["consignee_id"], lang)

    delivery = delivery_method_name(s, row.get("delivery_method_id"), lang)

    return {
        "id": row["id"],
        "transaction_no": row["transaction_no"],
        "issue_date": row["issue_date"],

        "exporter": exporter,
        "importer": importer,
        "consignee": consignee,

        "incoterms": row.get("incoterm_id") or "",
        "delivery_method": delivery,

        "country_of_origin": country_name(s, row.get("country_of_origin_id"), lang),
        "destination_country": country_name(s, row.get("destination_country_id"), lang),

        "port_of_loading": row.get("port_of_loading") or "",
        "port_of_discharge": row.get("port_of_discharge") or "",
        "transport": row.get("transport") or "",

        "notes": row.get("notes") or "",
    }


# =========================================================
# ITEMS
# =========================================================

def _fetch_items(transaction_id: int, lang: str) -> List[Dict[str, Any]]:

    s = get_session_local()

    rows = s.execute(text("""
        SELECT
            id,
            product_name,
            quantity,
            net_weight,
            gross_weight,
            package_type,
            package_count
        FROM transaction_items
        WHERE transaction_id = :id
        ORDER BY id
    """), {"id": transaction_id}).mappings().all()

    items: List[Dict[str, Any]] = []

    for i, r in enumerate(rows, 1):

        items.append({
            "line": i,
            "description": r.get("product_name") or "",
            "quantity": float(r.get("quantity") or 0),
            "net_kg": float(r.get("net_weight") or 0),
            "gross_kg": float(r.get("gross_weight") or 0),
            "package_type": r.get("package_type") or "",
            "package_count": int(r.get("package_count") or 0),
        })

    return items


# =========================================================
# TOTALS
# =========================================================

def _compute_totals(items: List[Dict[str, Any]]) -> Dict[str, Any]:

    qty = 0
    gross = 0
    net = 0

    packages = {}
    total_packages = 0

    for r in items:

        qty += r["quantity"]
        gross += r["gross_kg"]
        net += r["net_kg"]

        pkg_type = r.get("package_type")
        pkg_count = r.get("package_count")

        if pkg_type:
            packages[pkg_type] = packages.get(pkg_type, 0) + pkg_count
            total_packages += pkg_count

    package_list = [
        f"{v} {k}" for k, v in packages.items()
    ]

    return {
        "quantity": qty,
        "gross_kg": gross,
        "net_kg": net,
        "packages_total": total_packages,
        "packages_summary": join_with_and(package_list, "en") if package_list else "",
    }


# =========================================================
# BUILD CONTEXT
# =========================================================

def build_ctx(transaction_id: int, lang: str = "en") -> Dict[str, Any]:

    header = _fetch_header(transaction_id, lang)
    items = _fetch_items(transaction_id, lang)
    totals = _compute_totals(items)

    weight_unit = DEFAULT_WEIGHT_UNIT

    qty_in_words = spell_non_monetary(
        totals["quantity"],
        lang,
        "",
        kind="qty"
    )

    gross_in_words = spell_non_monetary(
        totals["gross_kg"],
        lang,
        weight_unit,
        kind="weight"
    )

    net_in_words = spell_non_monetary(
        totals["net_kg"],
        lang,
        weight_unit,
        kind="weight"
    )

    ctx = {
        "header": header,
        "items": items,
        "totals": totals,

        "qty_in_words": qty_in_words,
        "gross_in_words": gross_in_words,
        "net_in_words": net_in_words,

        "weight_unit": weight_unit,
    }

    return blankify(ctx)


# =========================================================
# EXPORT
# =========================================================

def build(transaction_id: int, lang: str = "en") -> Dict[str, Any]:
    return build_ctx(transaction_id, lang)