"""
invoice_three_party.py — LOGIPORT
===================================
فاتورة ثلاثية الأطراف:
  EXPORTER  → exporter_company  (المُصدِّر / المشحون منه)
  SELLER    → broker_company    (البائع / الوسيط)
  IMPORTER  → importer_company  (المستورد / المشحون إليه)

يُستخدم عندما يكون البائع مختلفاً عن المُصدِّر.
مثال: شركة سورية تصدّر بضاعة يبيعها وسيط إماراتي لمستورد تركي.
"""
from __future__ import annotations
from typing import Dict, Any, List
from sqlalchemy import text
from database.models import get_session_local
from documents.builders._shared import (
    blankify, coalesce, dedup_preserve_order,
    country_name   as _country_name,
    company_obj    as _company_obj,
    client_obj     as _client_obj,
    tafqit_amount  as _tafqit_amount,
    spell_non_monetary as _spell_non_monetary,
    delivery_method_name,
)
_blankify = blankify
_coalesce = coalesce
_dedup    = dedup_preserve_order


def build_ctx(doc_code: str, transaction_id: int, lang: str) -> Dict[str, Any]:
    lang = (lang or "en").lower()
    SessionLocal = get_session_local()
    with SessionLocal() as s:
        t = s.execute(text("""
            SELECT id, transaction_no, transaction_date,
                   client_id, exporter_company_id, importer_company_id,
                   broker_company_id, currency_id, pricing_type_id,
                   delivery_method_id, origin_country_id, dest_country_id,
                   transport_type, transport_ref
            FROM transactions WHERE id = :id
        """), {"id": int(transaction_id)}).mappings().first()
        if not t:
            raise ValueError(f"Transaction #{transaction_id} not found")

        # ── الأطراف الثلاثة ────────────────────────────────────────────────
        exporter = _company_obj(s, t["exporter_company_id"], lang)   # EXPORTER
        seller   = _company_obj(s, t["broker_company_id"],   lang)   # SELLER
        importer = _company_obj(s, t["importer_company_id"], lang)   # IMPORTER
        client   = _client_obj(s, t["client_id"], lang)

        # bank_info للمُصدِّر والبائع
        for cid, obj in [
            (t["exporter_company_id"], exporter),
            (t["broker_company_id"],   seller),
            (t["importer_company_id"], importer),
        ]:
            if cid and not (obj.get("bank_info") or "").strip():
                bi = s.execute(
                    text("SELECT bank_info FROM companies WHERE id=:id"),
                    {"id": cid}
                ).mappings().first()
                obj["bank_info"] = (bi and bi.get("bank_info") or "") or ""

        # ── عملة ────────────────────────────────────────────────────────────
        currency_code = currency_name = ""
        if t["currency_id"]:
            cur = s.execute(
                text("SELECT code, name_ar, name_en, name_tr FROM currencies WHERE id=:id"),
                {"id": t["currency_id"]}
            ).mappings().first()
            if cur:
                currency_code = cur["code"]
                currency_name = (cur.get(f"name_{lang}") or cur.get("name_en")
                                 or cur.get("name_ar") or "")
        else:
            cur_rows = s.execute(text("""
                SELECT DISTINCT c.code, c.name_ar, c.name_en, c.name_tr
                FROM transaction_items ti
                JOIN currencies c ON c.id = ti.currency_id
                WHERE ti.transaction_id = :tid AND ti.currency_id IS NOT NULL
            """), {"tid": int(transaction_id)}).mappings().all()
            if len(cur_rows) == 1:
                currency_code = cur_rows[0]["code"]
                currency_name = (cur_rows[0].get(f"name_{lang}")
                                 or cur_rows[0].get("name_en")
                                 or cur_rows[0].get("name_ar") or "")

        # ── طريقة التسليم + دول ─────────────────────────────────────────────
        dm = ""
        if t["delivery_method_id"]:
            r = s.execute(
                text("SELECT name_ar, name_en, name_tr FROM delivery_methods WHERE id=:id"),
                {"id": t["delivery_method_id"]}
            ).mappings().first()
            if r:
                dm = r.get(f"name_{lang}") or r.get("name_en") or r.get("name_ar") or ""

        origin_name = _country_name(s, t["origin_country_id"], lang)
        dest_name   = _country_name(s, t["dest_country_id"],   lang)

        # ── بنود المعاملة ────────────────────────────────────────────────────
        rows = s.execute(text(f"""
            SELECT ti.id,
                   m.name_{lang}      AS material_name,
                   ti.quantity        AS qty,
                   ti.gross_weight_kg AS gross,
                   ti.net_weight_kg   AS net,
                   ti.unit_price      AS unit_price,
                   ti.line_total      AS amount,
                   pk.name_{lang}     AS packaging,
                   pt.code            AS pricing_type_code,
                   pt.name_{lang}     AS pricing_type_name,
                   pt.compute_by      AS pt_compute_by,
                   pt.price_unit      AS pt_price_unit,
                   pt.divisor         AS pt_divisor
            FROM transaction_items ti
            JOIN materials m             ON m.id = ti.material_id
            LEFT JOIN packaging_types pk ON pk.id = ti.packaging_type_id
            LEFT JOIN pricing_types  pt  ON pt.id = ti.pricing_type_id
            WHERE ti.transaction_id = :tid
            ORDER BY ti.id
        """), {"tid": int(transaction_id)}).mappings().all()

        items: List[Dict[str, Any]] = []
        total_qty = total_gross = total_net = total_value = 0.0
        price_units: List[str] = []
        pt_names:    List[str] = []
        pack_names:  List[str] = []

        def _label(code: str) -> str:
            c = (code or "").upper()
            if c in ("TON","T","MT","TON_NET","TON_GROSS"): return "TON"
            if c in ("KG","KILO","KG_NET","KG_GROSS","GROSS","BRUT"): return "KG"
            return "UNIT"

        for idx, r in enumerate(rows, start=1):
            q  = float(r["qty"]        or 0)
            gw = float(r["gross"]      or 0)
            nw = float(r["net"]        or 0)
            up = float(r["unit_price"] or 0)
            am = float(r["amount"]     or 0)

            cb = (r.get("pt_compute_by") or "").upper()
            pu = (r.get("pt_price_unit") or "").upper() or _label(r.get("pricing_type_code") or "")
            try:
                dv = float(r.get("pt_divisor") or 1.0)
            except Exception:
                dv = 1.0

            if not am and up:
                code = (r.get("pricing_type_code") or "").upper()
                base = nw if cb == "NET" else (
                       gw if cb == "GROSS" else (
                       q  if cb == "QTY" else (
                       nw if code in ("KG","KILO","KG_NET") else (
                       gw if code in ("KG_GROSS","GROSS","BRUT") else (
                       nw/1000 if code in ("TON","T","MT","TON_NET") else (
                       gw/1000 if code == "TON_GROSS" else q))))))
                if code in ("TON","T","MT","TON_NET","TON_GROSS"):
                    dv = 1.0
                am = (base / (dv or 1.0)) * up

            total_qty   += q
            total_gross += gw
            total_net   += nw
            total_value += am

            price_units.append(pu)
            pt_names.append((r.get("pricing_type_name") or "").strip())
            pack_names.append((r.get("packaging") or "").strip())

            items.append({
                "n": idx,
                "description": r["material_name"],
                "unit": r["packaging"] or pu,
                "pricing_unit": pu,
                "packaging": r["packaging"],
                "qty": q,
                "gross": gw, "gross_kg": gw,
                "net":   nw, "net_kg":   nw,
                "unit_price": up,
                "amount": am,
                "pricing_type": {
                    "code": r.get("pricing_type_code"),
                    "name": r.get("pricing_type_name"),
                },
            })

        uniq_units    = _dedup([(u or "").upper() for u in price_units if u])
        uniq_packs    = _dedup([p for p in pack_names if p])
        uniq_pt_names = _dedup([n for n in pt_names if n])

        unit_price_per   = uniq_units[0] if len(uniq_units) == 1 else "UNIT"
        unit_price_label = " & ".join(uniq_units) if uniq_units else unit_price_per
        qty_header_packaging = " & ".join(uniq_packs)

        for it in items:
            it["gross_display"] = it["gross"]
            it["net_display"]   = it["net"]

        # ── تفقيط ───────────────────────────────────────────────────────────
        amount_words = _tafqit_amount(total_value, currency_code, lang)
        qty_pack_unit = uniq_packs[0] if len(uniq_packs) == 1 else " & ".join(uniq_packs)
        qty_words   = _spell_non_monetary(total_qty,   lang, qty_pack_unit, kind="qty")
        gross_words = _spell_non_monetary(total_gross, lang, "KG", kind="weight")
        net_words   = _spell_non_monetary(total_net,   lang, "KG", kind="weight")

        ctx: Dict[str, Any] = {
            "invoice_no":  _coalesce(t["transaction_no"], str(t["id"])),
            "date":        t["transaction_date"],
            "issue_date":  t["transaction_date"],

            # ── الأطراف الثلاثة ──────────────────────────────────────────
            "exporter":    exporter,   # EXPORTER — المُصدِّر
            "seller":      seller,     # SELLER   — البائع / الوسيط
            "importer":    importer,   # IMPORTER — المستورد
            "consignee":   importer,   # alias
            "client":      client,

            # ── شحن + دول ────────────────────────────────────────────────
            "delivery_method":      dm,
            "origin_country":       origin_name,
            "destination_country":  dest_name,
            "country_of_origin":    origin_name,
            "cur":                  currency_code,

            "transport": {
                "type": t["transport_type"],
                "ref":  t["transport_ref"],
                "delivery_method": dm,
            },
            "shipment": {
                "transport_type":   t["transport_type"],
                "transport_ref":    t["transport_ref"],
                "delivery_method":  dm,
                "origin_country":   origin_name,
                "destination_country": dest_name,
                "currency_code":    currency_code,
            },

            # ── بنود ─────────────────────────────────────────────────────
            "items": items,
            "totals": {
                "qty":   total_qty,
                "gross": total_gross,   "gross_display": total_gross,
                "net":   total_net,     "net_display":   total_net,
                "value": total_value,   "total": total_value,
                "subtotal": total_value,
            },

            # ── تفقيط ────────────────────────────────────────────────────
            "amount_in_words":       amount_words,
            "totals_in_words":       amount_words,
            "value_in_words":        amount_words,
            "qty_in_words":          qty_words,
            "totals_qty_in_words":   qty_words,
            "gross_in_words":        gross_words,
            "totals_gross_in_words": gross_words,
            "net_in_words":          net_words,
            "totals_net_in_words":   net_words,

            # ── رؤوس ديناميكية ───────────────────────────────────────────
            "unit_price_per":          unit_price_per,
            "unit_price_label":        unit_price_label,
            "weight_unit_for_display": "KG",
            "qty_header_packaging":    qty_header_packaging,

            "currency": {"code": currency_code, "name": currency_name},
            "pricing_type": (uniq_pt_names[0] if len(uniq_pt_names) == 1 else ""),
            "pricing_types_label": " & ".join(uniq_pt_names),

            # بنك من المُصدِّر
            "bank_info": exporter.get("bank_info", ""),
            "include_bank_from_company": True,
        }

        return _blankify(ctx)
