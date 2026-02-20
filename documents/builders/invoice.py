# documents/builders/invoice.py
from __future__ import annotations
from typing import Dict, Any, List
from decimal import Decimal

from sqlalchemy import text
from database.models import get_session_local

def _money(x) -> Decimal:
    return Decimal(str(x or "0")).quantize(Decimal("0.000"))

def _name(d: dict, lang: str) -> str:
    return d.get({ "ar":"name_ar", "en":"name_en", "tr":"name_tr" }[lang]) or ""

def _addr(d: dict, lang: str) -> str:
    # بعض الجداول قد لا تحتوي address_tr مثلًا، فنعتمد address عند اللزوم
    key = { "ar":"address_ar", "en":"address_en", "tr":"address_tr" }[lang]
    return d.get(key) or d.get("address") or ""

def _ensure(val, msg: str):
    if val in (None, "", 0):
        raise ValueError(msg)
    return val

def build_ctx(doc_code: str, transaction_id: int, lang: str) -> Dict[str, Any]:
    """
    يبني سياق الفاتورة (العادية/التجارية/البروفورما/السورية.*) بالاعتماد 100% على DB.
    لا افتراضات. أي نقص يرفع استثناء برسالة واضحة.
    """
    lang = (lang or "ar").lower()
    if lang not in ("ar","en","tr"):
        lang = "ar"

    SessionLocal = get_session_local()
    with SessionLocal() as s:
        # اكتشاف اسم عمود بلد الوجهة (يختلف بين إصدارات الـ schema)
        _tcols = {r["name"] for r in s.execute(text("PRAGMA table_info(transactions)")).mappings().all()}
        _dest_col = "destination_country_id" if "destination_country_id" in _tcols else "dest_country_id"

        # رأس المعاملة
        t = s.execute(text(f"""
            SELECT id,
                   COALESCE(transaction_no, CAST(id AS TEXT)) AS no,
                   transaction_date,
                   exporter_company_id, importer_company_id, client_id,
                   currency_id, delivery_method_id, transport_type, transport_ref,
                   origin_country_id, {_dest_col} AS destination_country_id,
                   notes
            FROM transactions WHERE id=:i
        """), {"i": int(transaction_id)}).mappings().first()
        if not t:
            raise ValueError("المعاملة غير موجودة.")

        # تحقق رأس المعاملة
        _ensure(t["currency_id"], f"المعاملة {t['no']} بلا عملة.")
        _ensure(t["delivery_method_id"], f"المعاملة {t['no']} بلا طريقة تسليم.")
        # transport_type/transport_ref اختياريان لكن يفضّل وجودهما
        # الدول: أصل/وجهة
        origin = s.execute(text("SELECT name_ar, name_en, name_tr FROM countries WHERE id=:id"),
                           {"id": t["origin_country_id"]}).mappings().first()
        dest = s.execute(text("SELECT name_ar, name_en, name_tr FROM countries WHERE id=:id"),
                         {"id": t["destination_country_id"]}).mappings().first()
        _ensure(origin, f"بلد المنشأ غير محدد في المعاملة {t['no']}.")
        _ensure(dest, f"بلد الوجهة غير محدد في المعاملة {t['no']}.")

        # العملة وطريقة التسليم
        cur = s.execute(text("SELECT code, name_ar, name_en, name_tr FROM currencies WHERE id=:id"),
                        {"id": t["currency_id"]}).mappings().first()
        _ensure(cur, "العملة غير موجودة.")
        dm  = s.execute(text("SELECT code, name_ar, name_en, name_tr FROM delivery_methods WHERE id=:id"),
                        {"id": t["delivery_method_id"]}).mappings().first()
        _ensure(dm, "طريقة التسليم غير موجودة.")

        currency_code = cur["code"]
        delivery_method = _name(dm, lang)

        # الأطراف
        exp = s.execute(text(f"SELECT id, name_{lang} AS name, address_{lang} AS address FROM companies WHERE id=:id"),
                        {"id": t["exporter_company_id"]}).mappings().first()
        _ensure(exp, "شركة المصدّر غير موجودة.")
        imp = s.execute(text(f"SELECT id, name_{lang} AS name, address_{lang} AS address FROM companies WHERE id=:id"),
                        {"id": t["importer_company_id"]}).mappings().first()
        cli = s.execute(text(f"SELECT id, name_{lang} AS name, COALESCE(address_{lang}, address) AS address FROM clients WHERE id=:id"),
                        {"id": t["client_id"]}).mappings().first()
        # بعض الفواتير قد تستخدم consignee = client
        consignee = cli or imp
        _ensure(consignee, "لا يوجد مستلم (client/importer).")

        # أسطر المعاملة
        rows = s.execute(text(f"""
            SELECT ti.id,
                   ti.quantity AS qty,
                   ti.net_weight_kg  AS net,
                   ti.gross_weight_kg AS gross,
                   ti.unit_label     AS unit_label,
                   m.name_{lang}     AS material,
                   pk.name_{lang}    AS packaging,
                   pt.code           AS pricing_code,
                   pt.name_{lang}    AS pricing_name,
                   ti.unit_price     AS unit_price
            FROM transaction_items ti
            JOIN materials m        ON m.id = ti.material_id
            LEFT JOIN packaging_types pk ON pk.id = ti.packaging_type_id
            LEFT JOIN pricing_types  pt ON pt.id = ti.pricing_type_id
            WHERE ti.transaction_id = :tid
            ORDER BY ti.id
        """), {"tid": int(transaction_id)}).mappings().all()
        if not rows:
            raise ValueError(f"لا توجد أسطر في المعاملة {t['no']}.")

        items: List[Dict[str, Any]] = []
        total_qty = Decimal("0")
        total_net = Decimal("0")
        total_gross = Decimal("0")
        total_value = Decimal("0")
        pricing_type_code = None
        pricing_type_name = None

        for r in rows:
            _ensure(r["packaging"], f"سطر {r['id']} بلا نوع تغليف (packaging_type).")
            _ensure(r["pricing_code"], f"سطر {r['id']} بلا نوع تسعير (pricing_type).")
            _ensure(r["unit_price"], f"سطر {r['id']} بلا سعر وحدة.")
            _ensure(r["unit_label"], f"سطر {r['id']} بلا وحدة قياس.")

            qty = Decimal(str(r["qty"] or "0"))
            net = Decimal(str(r["net"] or "0"))
            gross = Decimal(str(r["gross"] or "0"))
            price = Decimal(str(r["unit_price"] or "0"))
            amount = qty * price

            items.append({
                "no": r["id"],
                "description": r["material"],
                "packaging": r["packaging"],
                "qty": qty,
                "unit": r["unit_label"],
                "net_kg": net,
                "gross_kg": gross,
                "unit_price": _money(price),
                "amount": _money(amount),
            })

            total_qty   += qty
            total_net   += net
            total_gross += gross
            total_value += amount

            pricing_type_code = pricing_type_code or r["pricing_code"]
            pricing_type_name = pricing_type_name or r["pricing_name"]

        # تفقيط (اختياري إن كانت الخدمة مجهزة)
        amount_in_words = ""
        try:
            from services.tafqit_service import tafqit_amount as _tafqit_amount
            amount_in_words = _tafqit_amount(total_value, currency_code, lang)
        except Exception:
            # لا افتراضات نصية؛ نتركها فارغة إذا الخدمة غير متوفرة
            amount_in_words = ""

        ctx: Dict[str, Any] = {
            "title": None,  # العنوان من القالب
            "date": t["transaction_date"],
            "exporter": {"name": exp["name"], "addr": exp["address"]},
            "consignee": {"name": consignee["name"], "addr": consignee["address"]},
            "importer": {"name": imp["name"], "addr": imp["address"]} if imp else None,
            "shipment": {
                "delivery_method": delivery_method,
                "transport_type": t["transport_type"],
                "transport_ref": t["transport_ref"],
                "origin_country": _name(origin, lang),
                "destination": _name(dest, lang),
                "currency": currency_code,
            },
            "items": items,
            "totals": {"qty": total_qty, "gross": total_gross, "net": total_net, "value": _money(total_value)},
            "amount_in_words": amount_in_words,
            "pricing_type": {"code": pricing_type_code, "name": pricing_type_name},
            "currency": {"code": currency_code, "name": _name(cur, lang)},
            "notes": t.get("notes"),
        }
        return ctx