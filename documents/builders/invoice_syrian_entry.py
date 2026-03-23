# documents/builders/invoice_syrian_entry.py
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
_join_with_and = join_with_and

# ------------------------- builder -------------------------

def build_ctx(doc_code: str, transaction_id: int, lang: str) -> Dict[str, Any]:
    """
    Syrian Entry Invoice — DB-first, per-item packaging & pricing unit, multi-language.
    """
    lang = (lang or "ar").lower()
    is_ar = lang.startswith("ar")
    is_tr = lang.startswith("tr")
    is_en = not (is_ar or is_tr)

    SessionLocal = get_session_local()
    with SessionLocal() as s:
        dest_col = _pick_dest_col(s)
        t = s.execute(text(f"""
            SELECT id, transaction_no, transaction_date,
                   client_id, exporter_company_id, importer_company_id,
                   currency_id, pricing_type_id, delivery_method_id,
                   origin_country_id, {dest_col} AS destination_country_id,
                   transport_type, transport_ref, notes
            FROM transactions WHERE id = :id
        """), {"id": int(transaction_id)}).mappings().first()
        if not t:
            raise ValueError(f"Transaction #{transaction_id} not found")

        # Delivery method
        delivery_method = ""
        if t["delivery_method_id"]:
            dm = s.execute(
                text("SELECT name_ar, name_en, name_tr FROM delivery_methods WHERE id=:id"),
                {"id": t["delivery_method_id"]}
            ).mappings().first()
            if dm:
                delivery_method = dm.get(f"name_{lang}") or dm.get("name_en") or dm.get("name_ar") or dm.get("name_tr") or ""

        # Currency (code + name + symbol)
        currency_code = currency_name = currency_symbol = ""
        if t["currency_id"]:
            currency_code, currency_name, currency_symbol = _currency_info(s, t["currency_id"], lang)
        else:
            cur_rows = s.execute(text("""
                SELECT DISTINCT c.id
                FROM transaction_items ti
                JOIN currencies c ON c.id = ti.currency_id
                WHERE ti.transaction_id = :tid AND ti.currency_id IS NOT NULL
            """), {"tid": int(transaction_id)}).mappings().all()
            if len(cur_rows) == 1:
                currency_code, currency_name, currency_symbol = _currency_info(s, cur_rows[0]["id"], lang)

        exporter = _company_obj(s, t["exporter_company_id"], lang)
        importer = _company_obj(s, t["importer_company_id"], lang)
        client   = _client_obj(s, t["client_id"], lang)

        # Bank info fallback
        if t["exporter_company_id"] and not (exporter.get("bank_info") or "").strip():
            bi = s.execute(text("SELECT bank_info FROM companies WHERE id=:id"),
                           {"id": t["exporter_company_id"]}).mappings().first()
            exporter["bank_info"] = (bi and bi.get("bank_info") or "") or ""
        if t["importer_company_id"] and not (importer.get("bank_info") or "").strip():
            bi2 = s.execute(text("SELECT bank_info FROM companies WHERE id=:id"),
                            {"id": t["importer_company_id"]}).mappings().first()
            importer["bank_info"] = (bi2 and bi2.get("bank_info") or "") or ""

        # Countries
        origin_name = _country_name(s, t["origin_country_id"], lang)
        dest_name   = _country_name(s, t["destination_country_id"], lang)

        # Items (packaging_types, pricing_types localized by {lang})
        rows = s.execute(text(f"""
            SELECT ti.id,
                   m.name_{lang}      AS material_name,
                   ti.quantity         AS qty,
                   ti.gross_weight_kg  AS gross,
                   ti.net_weight_kg    AS net,
                   ti.unit_price       AS unit_price,
                   ti.line_total       AS amount,
                   pk.name_{lang}      AS packaging,              -- per-item packaging (localized)
                   pt.code             AS pricing_type_code,
                   pt.name_{lang}      AS pricing_type_name,
                   pt.compute_by       AS pt_compute_by,
                   pt.price_unit       AS pt_price_unit,
                   pt.divisor          AS pt_divisor
            FROM transaction_items ti
            JOIN materials m             ON m.id = ti.material_id
            LEFT JOIN packaging_types pk ON pk.id = ti.packaging_type_id
            LEFT JOIN pricing_types  pt  ON pt.id = ti.pricing_type_id
            WHERE ti.transaction_id = :tid
            ORDER BY ti.id
        """), {"tid": int(transaction_id)}).mappings().all()

        items: List[Dict[str, Any]] = []
        total_qty = total_gross = total_net = total_value = 0.0

        price_units_for_items: List[str] = []
        pt_names: List[str] = []
        pack_names: List[str] = []

        def _label_from_code(code: str) -> str:
            c = (code or "").upper()
            if c in ("TON", "T", "MT", "TON_NET", "TON_GROSS"):
                return "TON"
            if c in ("KG", "KILO", "KG_NET", "KG_GROSS", "GROSS", "BRUT"):
                return "KG"
            return "UNIT"

        for idx, r in enumerate(rows, start=1):
            q  = float(r["qty"] or 0)
            gw = float(r["gross"] or 0)
            nw = float(r["net"] or 0)
            up = float(r["unit_price"] or 0)
            am = float(r["amount"] or 0)

            cb = (r.get("pt_compute_by") or "").upper()
            pu = (r.get("pt_price_unit") or "").upper()
            try:
                dv = float(r.get("pt_divisor") or 1.0)
            except Exception:
                dv = 1.0

            if not pu:
                pu = _label_from_code(r.get("pricing_type_code") or "")

            if (not am) and up:
                code = (r.get("pricing_type_code") or "").upper()
                if cb == "NET":
                    base = nw
                elif cb == "GROSS":
                    base = gw
                elif cb == "QTY":
                    base = q
                else:
                    if code in ("KG", "KILO", "KG_NET"):
                        base = nw
                    elif code in ("KG_GROSS", "GROSS", "BRUT"):
                        base = gw
                    elif code in ("TON", "T", "MT", "TON_NET"):
                        base = nw / 1000.0; dv = 1.0
                    elif code in ("TON_GROSS",):
                        base = gw / 1000.0; dv = 1.0
                    else:
                        base = q
                am = (base / (dv or 1.0)) * up

            total_qty   += q
            total_gross += gw
            total_net   += nw
            total_value += am

            price_units_for_items.append(pu)
            pt_names.append((r.get("pricing_type_name") or "").strip())
            pack_names.append((r.get("packaging") or "").strip())

            # per-item labels (localized)
            if is_ar:
                per_item_unit = {"TON": "طن", "KG": "كغ"}.get(pu, pu or "وحدة")
                pricing_label = f"{_coalesce(currency_code,'USD')}/{per_item_unit}"
            else:
                pricing_label = f"{_coalesce(currency_code,'USD')}/{pu or 'UNIT'}"

            items.append({
                "n": idx,
                "description_ar": r["material_name"],
                "description": r["material_name"],
                "unit": pu,
                "packaging_type": r["packaging"],   # localized packaging
                "unit_display": r["packaging"],
                "qty": q,
                "bags": q,
                "gross": gw, "gross_kg": gw,
                "net":  nw, "net_kg":  nw,
                "unit_price": up,
                "price": up,
                "amount": am,
                "total": am,
                "total_usd": am,
                "pricing_type": {
                    "code": r.get("pricing_type_code"),
                    "name": r.get("pricing_type_name"),
                },
                "pricing_type_label": pricing_label,
            })

        # Aggregations
        uniq_units = _dedup_preserve_order([(u or "").upper() for u in price_units_for_items if u is not None])
        uniq_packs = _dedup_preserve_order([p for p in pack_names if p])
        uniq_pt_names = _dedup_preserve_order([n for n in pt_names if n])

        unit_price_per = uniq_units[0] if len(uniq_units) == 1 else "UNIT"
        unit_price_label = " & ".join(uniq_units) if uniq_units else unit_price_per

        # الوزن يُعرض دائماً بالكيلوغرام بغض النظر عن نوع التسعير
        weight_unit_for_display = "KG";  conv = 1.0

        # table subheader (just a hint; per-row uses its own)
        qty_header_packaging = _join_with_and(uniq_packs, lang)

        for it in items:
            it["gross_display"] = (it["gross"] / conv) if conv != 1.0 else it["gross"]
            it["net_display"]   = (it["net"]   / conv) if conv != 1.0 else it["net"]

        totals_gross_display = (total_gross / conv) if conv != 1.0 else total_gross
        totals_net_display   = (total_net   / conv) if conv != 1.0 else total_net

        # localized table head labels
        def _label_ar(u: str) -> str:
            u = (u or "").upper()
            if u == "TON": return "طن"
            if u in ("KG", "KILOGRAM"): return "كغ"
            if u in ("UNIT", "PCS"): return "وحدة"
            return u or "وحدة"

        if is_ar:
            pricing_type_header = f"{_coalesce(currency_code, 'USD')}/{_label_ar(unit_price_per)}" if len(uniq_units)==1 else f"{_coalesce(currency_code,'USD')}/{_label_ar(unit_price_label)}"
            gross_unit_label = "كغ"
        else:
            pricing_type_header = f"{_coalesce(currency_code, 'USD')}/{(unit_price_per if len(uniq_units)==1 else unit_price_label)}"
            gross_unit_label = "KG"
        net_unit_label = gross_unit_label

        # ----------------- Tafqit (AR/EN/TR) -----------------
        # Quantity: number + ALL unique packaging names (localized, joined with 'and')
        pkg_phrase_ar = _join_with_and(uniq_packs, "ar")
        pkg_phrase_en = _join_with_and(uniq_packs, "en")
        pkg_phrase_tr = _join_with_and(uniq_packs, "tr")

        tafqit_qty_ar = (_num_words(total_qty, "ar") + (" " + pkg_phrase_ar if pkg_phrase_ar else "")).strip()
        tafqit_qty_en = (_num_words(total_qty, "en") + (" " + pkg_phrase_en if pkg_phrase_en else "")).strip()
        tafqit_qty_tr = (_num_words(total_qty, "tr") + (" " + pkg_phrase_tr if pkg_phrase_tr else "")).strip()

        # Weights: full unit word once
        full_weight_word_ar = _unit_word("KG", "ar", kind="weight")
        tafqit_gross_ar = (_num_words(totals_gross_display, "ar") + (" " + full_weight_word_ar)).strip()
        tafqit_net_ar   = (_num_words(totals_net_display,   "ar") + (" " + full_weight_word_ar)).strip()

        full_weight_en = "kilograms"
        full_weight_tr = "kilogram"
        tafqit_gross_en = (_num_words(totals_gross_display, "en") + (" " + full_weight_en)).strip()
        tafqit_net_en   = (_num_words(totals_net_display,   "en") + (" " + full_weight_en)).strip()
        tafqit_gross_tr = (_num_words(totals_gross_display, "tr") + (" " + full_weight_tr)).strip()
        tafqit_net_tr   = (_num_words(totals_net_display,   "tr") + (" " + full_weight_tr)).strip()

        tafqit_total_value_ar = (_tafqit_amount(total_value, currency_code, "ar") or "").strip()
        tafqit_total_value_en = (_tafqit_amount(total_value, currency_code, "en") or "").strip()
        tafqit_total_value_tr = (_tafqit_amount(total_value, currency_code, "tr") or "").strip()

        _lang_key = "ar" if is_ar else ("tr" if is_tr else "en")
        template_rel = f"documents/templates/invoices/syrian/entry/{_lang_key}.html"

        ctx: Dict[str, Any] = {
            "template_rel": template_rel,
            "title": "فاتورة" if is_ar else ("Fatura" if is_tr else "Invoice"),
            "invoice_no": _coalesce(t["transaction_no"], str(t["id"])),
            "date": t["transaction_date"],

            "exporter": exporter,
            "consignee": importer,
            "importer": importer,
            "client": client,

            "transport": {
                "type": t["transport_type"],
                "ref": t["transport_ref"],
                "delivery_method": delivery_method,
            },
            "shipment": {
                "transport_type": t["transport_type"],
                "transport_ref": t["transport_ref"],
                "delivery_method": delivery_method,
                "origin_country": origin_name,
                "destination_country": dest_name,
                "currency_code": currency_code,
            },

            "delivery_method": delivery_method,
            "origin_country": origin_name,
            "destination_country": dest_name,
            "country_of_origin": origin_name,
            "cur": currency_code,

            "items": items,

            "totals": {
                "qty": total_qty,
                "gross": total_gross,
                "net": total_net,
                "value": total_value,
                "total_value": total_value,
                "total": total_value,
                "subtotal": total_value,
                "total_qty": total_qty,
                "total_bags": total_qty,
                "total_gross": total_gross,
                "total_net": total_net,
                "gross_display": totals_gross_display,
                "net_display":   totals_net_display,
            },

            "unit_price_per": unit_price_per,
            "unit_price_label": unit_price_label,
            "pricing_type_header": pricing_type_header,
            "weight_unit_for_display": weight_unit_for_display,
            "gross_unit_label": gross_unit_label,
            "net_unit_label":   net_unit_label,
            "qty_header_packaging": qty_header_packaging,

            "currency": {"code": currency_code, "name": currency_name, "symbol": currency_symbol},
            "currency_symbol": currency_symbol,
            "pricing_type": (uniq_pt_names[0] if len(uniq_pt_names) == 1 else ""),
            "pricing_types_label": " & ".join(uniq_pt_names),

            # Tafqit (AR + EN + TR)
            "tafqit_qty_ar": tafqit_qty_ar,
            "tafqit_gross_ar": tafqit_gross_ar,
            "tafqit_net_ar": tafqit_net_ar,
            "tafqit_total_value_ar": tafqit_total_value_ar,

            "tafqit_qty_en": tafqit_qty_en,
            "tafqit_gross_en": tafqit_gross_en,
            "tafqit_net_en": tafqit_net_en,
            "tafqit_total_value_en": tafqit_total_value_en,

            "tafqit_qty_tr": tafqit_qty_tr,
            "tafqit_gross_tr": tafqit_gross_tr,
            "tafqit_net_tr": tafqit_net_tr,
            "tafqit_total_value_tr": tafqit_total_value_tr,

            "bank_info": exporter.get("bank_info") or "",
            "include_bank_from_company": True,
            "notes": t.get("notes") or "",
        }

        return _blankify(ctx)