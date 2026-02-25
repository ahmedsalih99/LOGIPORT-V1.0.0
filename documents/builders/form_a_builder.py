"""
documents/builders/form_a.py — LOGIPORT
=========================================
يبني سياق شهادة المنشأ Form A (GSP — Generalised System of Preferences)
المعروفة أيضاً بـ EUR.1 في السياق الأوروبي.

الحقول المعيارية:
  Box 1  : المُصدِّر (Exporter)
  Box 2  : رقم الشهادة (Certificate No.)
  Box 3  : المُستلِم (Consignee)
  Box 4  : بلد المنشأ / المعالجة
  Box 5  : بلد الوجهة
  Box 6  : معلومات النقل
  Box 7  : ملاحظات
  Box 8  : رقم البند الجمركي + وصف + وزن + قيمة
  Box 9  : الكمية الإجمالية
  Box 10 : الفواتير المرجعية
  Box 11 : الجهة المُصدِرة + التوقيع
  Box 12 : توقيع المُصدِّر
"""
from __future__ import annotations
from typing import Dict, Any, List
from decimal import Decimal
from sqlalchemy import text
from database.models import get_session_local


def _val(x) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _company_block(s, company_id, lang: str) -> Dict[str, str]:
    if not company_id:
        return {"name": "", "address": "", "city": "", "country": "", "tax_id": ""}
    r = s.execute(text("""
        SELECT name_ar, name_en, name_tr,
               address_ar, address_en, address_tr,
               city, country_id, phone, tax_id
        FROM companies WHERE id = :id
    """), {"id": company_id}).mappings().first()
    if not r:
        return {"name": "", "address": "", "city": "", "country": "", "tax_id": ""}

    name    = r.get(f"name_{lang}") or r.get("name_en") or r.get("name_ar") or ""
    address = r.get(f"address_{lang}") or r.get("address_en") or r.get("address_ar") or ""

    country = ""
    if r.get("country_id"):
        cr = s.execute(
            text("SELECT name_ar, name_en, name_tr FROM countries WHERE id=:id"),
            {"id": r["country_id"]}
        ).mappings().first()
        if cr:
            country = cr.get(f"name_{lang}") or cr.get("name_en") or cr.get("name_ar") or ""

    return {
        "name":    name,
        "address": address,
        "city":    _val(r.get("city")),
        "country": country,
        "tax_id":  _val(r.get("tax_id")),
    }


def build_ctx(doc_code: str, transaction_id: int, lang: str) -> Dict[str, Any]:
    """
    يبني سياق Form A من:
      - transactions (exporter, importer, origin/dest country, items)
      - transport_details (certificate_no, issuing_authority, shipment_date)
      - materials.code → يُستخدم كـ HS Code (كود جمركي)
    """
    lang = (lang or "en").lower()
    if lang not in ("ar", "en", "tr"):
        lang = "en"

    SessionLocal = get_session_local()
    with SessionLocal() as s:

        # ── رأس المعاملة ──────────────────────────────────────────────────────
        t = s.execute(text("""
            SELECT id,
                   COALESCE(transaction_no, CAST(id AS TEXT)) AS no,
                   transaction_date,
                   exporter_company_id, importer_company_id,
                   origin_country_id, dest_country_id,
                   currency_id, delivery_method_id,
                   transport_type, transport_ref,
                   notes
            FROM transactions WHERE id = :i
        """), {"i": int(transaction_id)}).mappings().first()
        if not t:
            raise ValueError(f"المعاملة #{transaction_id} غير موجودة.")

        # ── transport_details ─────────────────────────────────────────────────
        td = s.execute(text("""
            SELECT certificate_no, issuing_authority,
                   shipment_date, carrier_company_id,
                   truck_plate, loading_place, delivery_place
            FROM transport_details WHERE transaction_id = :i
        """), {"i": int(transaction_id)}).mappings().first()

        # ── الأطراف ───────────────────────────────────────────────────────────
        exporter  = _company_block(s, t["exporter_company_id"], lang)
        consignee = _company_block(s, t["importer_company_id"], lang)

        # ── الدول ─────────────────────────────────────────────────────────────
        def _country(cid):
            if not cid:
                return ""
            r = s.execute(
                text("SELECT name_ar, name_en, name_tr FROM countries WHERE id=:id"),
                {"id": cid}
            ).mappings().first()
            if not r:
                return ""
            return r.get(f"name_{lang}") or r.get("name_en") or r.get("name_ar") or ""

        origin_country = _country(t["origin_country_id"])
        dest_country   = _country(t["dest_country_id"])

        # ── العملة ────────────────────────────────────────────────────────────
        currency_code = ""
        if t["currency_id"]:
            cur = s.execute(
                text("SELECT code FROM currencies WHERE id=:id"),
                {"id": t["currency_id"]}
            ).mappings().first()
            if cur:
                currency_code = cur["code"] or ""

        # ── طريقة التسليم ─────────────────────────────────────────────────────
        delivery_method = ""
        if t["delivery_method_id"]:
            dm = s.execute(
                text("SELECT name_ar, name_en, name_tr FROM delivery_methods WHERE id=:id"),
                {"id": t["delivery_method_id"]}
            ).mappings().first()
            if dm:
                delivery_method = dm.get(f"name_{lang}") or dm.get("name_en") or dm.get("name_ar") or ""

        # ── بنود المعاملة ─────────────────────────────────────────────────────
        rows = s.execute(text(f"""
            SELECT ti.id,
                   m.code                AS hs_code,
                   m.name_{lang}         AS description,
                   ti.quantity           AS qty,
                   ti.gross_weight_kg    AS gross,
                   ti.net_weight_kg      AS net,
                   ti.unit_price         AS unit_price,
                   ti.line_total         AS amount,
                   pk.name_{lang}        AS packaging,
                   c_orig.name_{lang}    AS origin_country
            FROM transaction_items ti
            JOIN materials m                   ON m.id = ti.material_id
            LEFT JOIN packaging_types pk       ON pk.id = ti.packaging_type_id
            LEFT JOIN countries c_orig         ON c_orig.id = ti.origin_country_id
            WHERE ti.transaction_id = :tid
            ORDER BY ti.id
        """), {"tid": int(transaction_id)}).mappings().all()

        items: List[Dict[str, Any]] = []
        total_qty = total_gross = total_net = total_value = 0.0

        for idx, r in enumerate(rows, start=1):
            qty   = float(r["qty"]   or 0)
            gross = float(r["gross"] or 0)
            net   = float(r["net"]   or 0)
            amt   = float(r["amount"] or 0)
            total_qty   += qty
            total_gross += gross
            total_net   += net
            total_value += amt

            # بلد المنشأ لكل بند — يرجع لبلد المعاملة إذا لم يكن محدداً
            item_origin = _val(r["origin_country"]) or origin_country

            items.append({
                "n":           idx,
                "hs_code":     _val(r["hs_code"]),       # materials.code = HS Code
                "description": _val(r["description"]),
                "packaging":   _val(r["packaging"]),
                "qty":         qty,
                "gross":       gross,
                "net":         net,
                "amount":      amt,
                "unit_price":  float(r["unit_price"] or 0),
                "origin":      item_origin,
            })

        # ── بيانات الشهادة ────────────────────────────────────────────────────
        certificate_no    = _val(td["certificate_no"])    if td else ""
        issuing_authority = _val(td["issuing_authority"]) if td else ""
        shipment_date     = td["shipment_date"]            if td else None
        transport_info    = _val(t["transport_ref"])

        if td and td.get("loading_place") and td.get("delivery_place"):
            transport_info = f"{_val(td['loading_place'])} → {_val(td['delivery_place'])}"
        elif t["transport_type"]:
            transport_info = f"{_val(t['transport_type'])} — {_val(t['transport_ref'])}"

        return {
            # ── رقم الشهادة ────────────────────────────────────────────────
            "certificate_no":    certificate_no or _val(t["no"]),
            "reference_no":      _val(t["no"]),
            "date":              shipment_date or t["transaction_date"],
            "trx_date":          t["transaction_date"],

            # ── Box 1: المُصدِّر ──────────────────────────────────────────
            "exporter": exporter,

            # ── Box 3: المُستلِم ──────────────────────────────────────────
            "consignee": consignee,

            # ── Box 4: بلد المنشأ ─────────────────────────────────────────
            "origin_country":  origin_country,

            # ── Box 5: بلد الوجهة ─────────────────────────────────────────
            "dest_country":    dest_country,

            # ── Box 6: معلومات النقل ──────────────────────────────────────
            "transport_info":     transport_info,
            "delivery_method":    delivery_method,
            "transport_ref":      _val(t["transport_ref"]),

            # ── Box 8: البنود ─────────────────────────────────────────────
            "items": items,
            "totals": {
                "qty":   total_qty,
                "gross": total_gross,
                "net":   total_net,
                "value": total_value,
            },
            "currency_code": currency_code,

            # ── Box 10: الفواتير المرجعية ─────────────────────────────────
            "invoice_no": _val(t["no"]),

            # ── Box 11: الجهة المُصدِرة ────────────────────────────────────
            "issuing_authority": issuing_authority,

            # ── تحذيرات (للـ UI، لا تظهر في المستند) ─────────────────────
            "_warnings": _build_warnings(
                certificate_no, issuing_authority, origin_country, items
            ),
        }


def _build_warnings(certificate_no, issuing_authority, origin_country, items) -> list:
    w = []
    if not certificate_no:
        w.append("certificate_no_missing")
    if not issuing_authority:
        w.append("issuing_authority_missing")
    if not origin_country:
        w.append("origin_country_missing")
    if not items:
        w.append("no_items")
    return w
