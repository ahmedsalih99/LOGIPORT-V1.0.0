"""
documents/builders/cmr_builder.py — LOGIPORT
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
from documents.builders._shared import (
    blankify as _blankify,
    company_obj as _company_obj_full,
    country_name as _country_name,
    pick_dest_col as _pick_dest_col,
)


def _val(x) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _company_block(s, company_id, lang: str) -> dict:
    """wrapper → _shared.company_obj (unified)."""
    return _company_obj_full(s, company_id, lang) or {
        "name": "", "address": "", "city": "", "country": "", "phone": ""
    }

def build_ctx(doc_code: str, transaction_id: int, lang: str) -> Dict[str, Any]:
    """
    يبني سياق CMR من:
      - transactions (exporter, importer, origin, dest, items)
      - transport_details (carrier, truck_plate, driver, loading/delivery place, shipment_date)

    doc_code يمكن أن يحمل suffix للـ variant: e.g. "cmr__v2"
    أو يُمرَّر _opt_cmr_variant في الـ ctx لاحقاً من facade.
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
                   attached_documents, certificate_no, issuing_authority,
                   origin_country, dest_country, cmr_no,
                   cmr_second_label, cmr_no_2,
                   carrier_company_id_2, truck_plate_2, driver_name_2,
                   loading_place_2, delivery_place_2, shipment_date_2
            FROM transport_details WHERE transaction_id = :i
        """), {"i": int(transaction_id)}).mappings().first()

        # ── الأطراف ───────────────────────────────────────────────────────────
        sender    = _company_block(s, t["exporter_company_id"], lang)
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

        origin_country = (
            (td.get("origin_country") or "") if td else ""
        ) or _country(t["origin_country_id"])
        dest_country = (
            (td.get("dest_country") or "") if td else ""
        ) or _country(t["dest_country_id"])

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

        # ── البيانات المشتركة بين CMR الأول والثاني ───────────────────────────
        truck_plate    = _val(td["truck_plate"])    if td else ""
        driver_name    = _val(td["driver_name"])    if td else ""
        loading_place  = _val(td["loading_place"])  if td else ""
        delivery_place = _val(td["delivery_place"]) if td else ""
        shipment_date  = td["shipment_date"]         if td else None
        cmr_no_val     = _val(td["cmr_no"])          if td else ""
        carrier        = _company_block(s, td["carrier_company_id"] if td else None, lang)

        # ── CMR الثاني — يُطبَّق عند تمرير _opt_cmr_variant = "2" ─────────────
        # (facade يضيف _opt_cmr_variant للـ ctx بعد build_ctx،
        #  لكن نحفظ بيانات كلا الـ CMR هنا ونترك facade يختار)
        has_second = td and any([
            td.get("cmr_second_label"), td.get("cmr_no_2"),
            td.get("carrier_company_id_2"),
            td.get("truck_plate_2"), td.get("driver_name_2"),
            td.get("loading_place_2"), td.get("delivery_place_2"),
        ])

        carrier_2        = _company_block(s, td["carrier_company_id_2"] if td and has_second else None, lang)
        truck_plate_2    = _val(td["truck_plate_2"])    if td and has_second else ""
        driver_name_2    = _val(td["driver_name_2"])    if td and has_second else ""
        cmr_no_2_val     = _val(td["cmr_no_2"])         if td and has_second else ""
        cmr_second_label = _val(td["cmr_second_label"]) if td and has_second else ""
        loading_place_2  = _val(td["loading_place_2"])  if td and has_second else ""
        delivery_place_2 = _val(td["delivery_place_2"]) if td and has_second else ""
        shipment_date_2  = td["shipment_date_2"]         if td and has_second else None

        return {
            # ── رقم CMR الأول ─────────────────────────────────────────────────
            "cmr_no": cmr_no_val or f"CMR-{_val(t['no'])}",
            "date":          shipment_date,
            "trx_date":      t["transaction_date"],
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

            # ── Box 7/8: بيانات الناقل والشاحنة (CMR الأول) ──────────────────
            "carrier":     carrier,
            "truck_plate": truck_plate,
            "driver_name": driver_name,

            # ── بيانات CMR الثاني (للاستخدام من facade عند variant=2) ─────────
            "_cmr2": {
                "label":          cmr_second_label,
                "cmr_no":         cmr_no_2_val or f"CMR2-{_val(t['no'])}",
                "carrier":        carrier_2,
                "truck_plate":    truck_plate_2,
                "driver_name":    driver_name_2,
                "loading_place":  loading_place_2,
                "delivery_place": delivery_place_2,
                "shipment_date":  shipment_date_2,
            } if has_second else None,

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
                   attached_documents, certificate_no, issuing_authority,
                   origin_country, dest_country, cmr_no
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

        # الدول: من TransportDetails إن عبّأها المستخدم، وإلا من المعاملة
        origin_country = (
            (td.get("origin_country") or "") if td else ""
        ) or _country(t["origin_country_id"])
        dest_country = (
            (td.get("dest_country") or "") if td else ""
        ) or _country(t["dest_country_id"])

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

        # إذا لم يُحدَّد مكان التحميل/التسليم، يُترك فارغاً
        # (المستخدم يعبّئهم في تبويب الشحن)

        return {
            # ── رقم CMR: من transport_details إن وُجد، وإلا يُولَّد من رقم المعاملة ──
            "cmr_no": (
                _val(td["cmr_no"]) if td and td.get("cmr_no") else
                f"CMR-{_val(t['no'])}"
            ),
            # التاريخ من shipment_date التي يعبّئها المستخدم يدوياً
            "date":          shipment_date,
            "trx_date":      t["transaction_date"],
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