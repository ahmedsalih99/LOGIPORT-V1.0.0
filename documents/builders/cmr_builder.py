"""
documents/builders/cmr.py — LOGIPORT
======================================
يبني سياق مستند CMR (Convention on the Contract for the International
Carriage of Goods by Road) من بيانات المعاملة + transport_details.

الحقول المعيارية للـ CMR:
  Box 1  : المُرسِل (Sender / Consignor)
  Box 2  : المُستلِم (Consignee)
  Box 3  : مكان التسليم
  Box 4  : مكان وتاريخ التحميل
  Box 5  : الوثائق المرفقة
  Box 6  : ملاحظات خاصة
  Box 7  : رقم اللوحة
  Box 8  : الناقل (Carrier)
  Box 9  : الناقل اللاحق (اختياري)
  Box 13 : تعليمات المُرسِل
  Box 15 : الأجرة
  Box 16 : الوصل
  Box 17 : اتفاقيات خاصة
  Box 18 : المدفوع مسبقاً
  Box 23 : توقيع المُرسِل
  Box 24 : توقيع الناقل
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
    """يُعيد اسم + عنوان الشركة."""
    if not company_id:
        return {"name": "", "address": "", "city": "", "country": "", "phone": ""}
    r = s.execute(text("""
        SELECT name_ar, name_en, name_tr,
               address_ar, address_en, address_tr,
               city, country_id, phone, tax_id
        FROM companies WHERE id = :id
    """), {"id": company_id}).mappings().first()
    if not r:
        return {"name": "", "address": "", "city": "", "country": "", "phone": ""}

    name = r.get(f"name_{lang}") or r.get("name_en") or r.get("name_ar") or ""
    address = (
        r.get(f"address_{lang}") or r.get("address_en") or r.get("address_ar") or ""
    )
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
        "phone":   _val(r.get("phone")),
        "tax_id":  _val(r.get("tax_id")),
    }


def build_ctx(doc_code: str, transaction_id: int, lang: str) -> Dict[str, Any]:
    """
    يبني سياق CMR من:
      - transactions (exporter, importer, origin, dest, items)
      - transport_details (carrier, truck_plate, driver, loading/delivery place, shipment_date)
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
                   exporter_company_id, importer_company_id, client_id,
                   origin_country_id, dest_country_id,
                   transport_type, transport_ref,
                   notes
            FROM transactions WHERE id = :i
        """), {"i": int(transaction_id)}).mappings().first()
        if not t:
            raise ValueError(f"المعاملة #{transaction_id} غير موجودة.")

        # ── transport_details ─────────────────────────────────────────────────
        td = s.execute(text("""
            SELECT carrier_company_id, truck_plate, driver_name,
                   loading_place, delivery_place, shipment_date,
                   attached_documents,
                   certificate_no, issuing_authority
            FROM transport_details WHERE transaction_id = :i
        """), {"i": int(transaction_id)}).mappings().first()

        # ── الأطراف ───────────────────────────────────────────────────────────
        sender    = _company_block(s, t["exporter_company_id"], lang)
        consignee = _company_block(s, t["importer_company_id"], lang)
        carrier   = _company_block(s, td["carrier_company_id"] if td else None, lang)

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

        # ── بنود المعاملة ─────────────────────────────────────────────────────
        rows = s.execute(text(f"""
            SELECT ti.id,
                   m.code                AS material_code,
                   m.name_{lang}         AS material_name,
                   ti.quantity           AS qty,
                   ti.gross_weight_kg    AS gross,
                   ti.net_weight_kg      AS net,
                   pk.name_{lang}        AS packaging,
                   ti.notes              AS item_notes
            FROM transaction_items ti
            JOIN materials m              ON m.id = ti.material_id
            LEFT JOIN packaging_types pk  ON pk.id = ti.packaging_type_id
            WHERE ti.transaction_id = :tid
            ORDER BY ti.id
        """), {"tid": int(transaction_id)}).mappings().all()

        items: List[Dict[str, Any]] = []
        total_qty = total_gross = total_net = 0.0

        for idx, r in enumerate(rows, start=1):
            qty   = float(r["qty"]   or 0)
            gross = float(r["gross"] or 0)
            net   = float(r["net"]   or 0)
            total_qty   += qty
            total_gross += gross
            total_net   += net
            items.append({
                "n":           idx,
                "code":        _val(r["material_code"]),
                "description": _val(r["material_name"]),
                "packaging":   _val(r["packaging"]),
                "qty":         qty,
                "gross":       gross,
                "net":         net,
                "notes":       _val(r["item_notes"]),
            })

        # ── بيانات transport_details ──────────────────────────────────────────
        truck_plate    = _val(td["truck_plate"])    if td else ""
        driver_name    = _val(td["driver_name"])    if td else ""
        loading_place  = _val(td["loading_place"])  if td else ""
        delivery_place = _val(td["delivery_place"]) if td else ""
        shipment_date  = td["shipment_date"]         if td else None

        # إذا لم يُحدَّد مكان التحميل، استخدم بلد المنشأ
        if not loading_place:
            loading_place = origin_country
        # إذا لم يُحدَّد مكان التسليم، استخدم بلد الوجهة
        if not delivery_place:
            delivery_place = dest_country

        return {
            # ── معرّف المستند ─────────────────────────────────────────────────
            "cmr_no":       _val(t["no"]),
            "date":         shipment_date or t["transaction_date"],
            "trx_date":     t["transaction_date"],
            "shipment_date": shipment_date,

            # ── Box 1: المُرسِل ───────────────────────────────────────────────
            "sender": sender,

            # ── Box 2: المُستلِم ──────────────────────────────────────────────
            "consignee": consignee,

            # ── Box 3: مكان التسليم ───────────────────────────────────────────
            "delivery_place":  delivery_place,
            "dest_country":    dest_country,

            # ── Box 4: مكان وتاريخ التحميل ───────────────────────────────────
            "loading_place":   loading_place,
            "origin_country":  origin_country,

            # ── Box 5: الوثائق المرفقة ────────────────────────────────────────
            "attached_documents": _val(td["attached_documents"] if td else None) or _val(t["notes"]),
            "transport_ref":      _val(t["transport_ref"]),

            # ── Box 7/8: بيانات الناقل والشاحنة ──────────────────────────────
            "carrier":     carrier,
            "truck_plate": truck_plate,
            "driver_name": driver_name,

            # ── البنود ────────────────────────────────────────────────────────
            "items": items,
            "totals": {
                "qty":   total_qty,
                "gross": total_gross,
                "net":   total_net,
            },

            # ── مساعد: هل البيانات مكتملة؟ ───────────────────────────────────
            "_warnings": _build_warnings(
                carrier, truck_plate, loading_place, delivery_place, items
            ),
        }


def _build_warnings(carrier, truck_plate, loading_place, delivery_place, items) -> list:
    """يُعيد قائمة بالحقول الناقصة — للعرض في الـ UI لا في المستند."""
    w = []
    if not carrier.get("name"):
        w.append("carrier_missing")
    if not truck_plate:
        w.append("truck_plate_missing")
    if not loading_place:
        w.append("loading_place_missing")
    if not delivery_place:
        w.append("delivery_place_missing")
    if not items:
        w.append("no_items")
    return w
