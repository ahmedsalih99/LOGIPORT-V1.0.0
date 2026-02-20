# documents/builders/invoice_syrian_entry.py
from __future__ import annotations
from typing import Any, Dict, List
from sqlalchemy import text
from database.models import get_session_local

# ------------------------- helpers -------------------------

def _blankify(v):
    from collections.abc import Mapping, Sequence
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, Mapping):
        return {k: _blankify(val) for k, val in v.items()}
    if isinstance(v, Sequence) and not isinstance(v, (str, bytes, bytearray)):
        return [_blankify(x) for x in v]
    return v

def _coalesce(*vals):
    for v in vals:
        if v not in (None, ""):
            return v
    return ""

def _country_name(s, country_id, lang: str) -> str:
    if not country_id:
        return ""
    r = s.execute(
        text("SELECT name_ar, name_en, name_tr FROM countries WHERE id=:i"),
        {"i": country_id}
    ).mappings().first()
    if not r:
        return ""
    return r.get(f"name_{lang}") or r.get("name_en") or r.get("name_ar") or r.get("name_tr") or ""

def _company_obj(s, company_id, lang: str) -> Dict[str, Any]:
    if not company_id:
        return {"name": "", "address": ""}
    r = s.execute(text("""
        SELECT id,
               name_ar, name_en, name_tr,
               address_ar, address_en, address_tr,
               country_id, city, phone, email, website, tax_id, registration_number,
               bank_info
        FROM companies WHERE id=:id
    """), {"id": company_id}).mappings().first()
    if not r:
        return {"name": "", "address": ""}

    name = r.get(f"name_{lang}") or r.get("name_en") or r.get("name_ar") or r.get("name_tr") or ""
    address = (
        r.get(f"address_{lang}") or r.get("address_en") or r.get("address_ar") or r.get("address_tr") or ""
    )
    if not address:
        try:
            r2 = s.execute(text("SELECT address FROM companies WHERE id=:id"),
                           {"id": company_id}).mappings().first()
            if r2 and r2.get("address"):
                address = r2.get("address")
        except Exception:
            pass

    return {
        "name": name,
        "name_ar": name,
        "address": address,
        "address_ar": address,
        "city": r.get("city"),
        "country": _country_name(s, r.get("country_id"), lang),
        "phone": r.get("phone"),
        "email": r.get("email"),
        "website": r.get("website"),
        "tax_id": r.get("tax_id"),
        "registration_number": r.get("registration_number"),
        "bank_info": r.get("bank_info") or "",
        "vat_no": r.get("tax_id"),
        "cr_no": r.get("registration_number"),
    }

def _client_obj(s, client_id, lang: str) -> Dict[str, Any]:
    if not client_id:
        return {"name": "", "address": ""}
    r = s.execute(text("""
        SELECT id,
               name_ar, name_en, name_tr,
               COALESCE(address_ar, address) AS address_ar,
               COALESCE(address_en, address) AS address_en,
               COALESCE(address_tr, address) AS address_tr,
               country_id, city, phone, email, website, tax_id
        FROM clients WHERE id=:id
    """), {"id": client_id}).mappings().first()
    if not r:
        return {"name": "", "address": ""}

    name = r.get(f"name_{lang}") or r.get("name_en") or r.get("name_ar") or r.get("name_tr") or ""
    address = (
        r.get(f"address_{lang}") or r.get("address_en") or r.get("address_ar") or r.get("address_tr") or ""
    )
    return {
        "name": name,
        "name_ar": name,
        "address": address,
        "address_ar": address,
        "city": r.get("city"),
        "country": _country_name(s, r.get("country_id"), lang),
        "phone": r.get("phone"),
        "email": r.get("email"),
        "website": r.get("website"),
        "tax_id": r.get("tax_id"),
    }

def _tafqit_amount(total_value: float, currency_code: str, lang: str) -> str:
    try:
        from services.tafqit_service import tafqit
        return tafqit(total_value or 0.0, currency_code or "", (lang or "ar").lower())
    except Exception:
        try:
            from services.tafqit_service import TafqitService
            return TafqitService().amount_in_words(total_value or 0.0, currency_code or "", (lang or "ar").lower())
        except Exception:
            return ""

def _num_words(n: float, lang: str) -> str:
    n_int = int(round(float(n or 0)))
    try:
        if (lang or "ar").lower() == "ar":
            from services.tafqit_service import number_to_words_ar
            return number_to_words_ar(n_int)
        if (lang or "ar").lower() == "tr":
            from services.tafqit_service import number_to_words_tr
            return number_to_words_tr(n_int)
        from services.tafqit_service import number_to_words_en
        return number_to_words_en(n_int)
    except Exception:
        return str(n_int)

def _unit_word(unit_label: str | None, lang: str, *, kind: str = "qty") -> str:
    u = (unit_label or "").strip().upper()
    if (lang or "ar").lower() == "ar":
        if kind == "weight":
            return "كيلوغرام" if u in ("", "KG", "KILOGRAM") else ("طن" if u in ("T", "TON", "TONS") else unit_label or "كيلوغرام")
        return "وحدة" if not u else unit_label or "وحدة"
    if (lang or "ar").lower() == "tr":
        if kind == "weight":
            return "kilogram" if u in ("", "KG", "KILOGRAM") else ("ton" if u in ("T", "TON", "TONS") else unit_label or "kilogram")
        return "birim" if not u else unit_label or "birim"
    if kind == "weight":
        return "kilograms" if u in ("", "KG", "KILOGRAM") else ("tons" if u in ("T", "TON", "TONS") else (unit_label or "kilograms"))
    return "units" if not u else (unit_label or "units")

def _dedup_preserve_order(seq: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for v in seq:
        k = (v or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out

def _pick_dest_col(session) -> str:
    rows = session.execute(text("PRAGMA table_info(transactions)")).mappings().all()
    cols = {r["name"] for r in rows}
    return "destination_country_id" if "destination_country_id" in cols else "dest_country_id"

def _join_with_and(names: List[str], lang: str) -> str:
    """Join list with localized 'and' (no duplicates; preserves order)."""
    lst = _dedup_preserve_order([n for n in names if (n or "").strip()])
    if not lst:
        return ""
    if len(lst) == 1:
        return lst[0]
    sep = "، " if lang.startswith("ar") else ", "
    conj = " و " if lang.startswith("ar") else (" ve " if lang.startswith("tr") else " and ")
    return sep.join(lst[:-1]) + conj + lst[-1]

def _currency_info(s, currency_id, lang: str):
    """Return (code, localized name, symbol_or_code) from DB; fall back to code if symbol column missing."""
    if not currency_id:
        return "", "", ""
    cols = {r["name"] for r in s.execute(text("PRAGMA table_info(currencies)")).mappings().all()}
    has_symbol = "symbol" in cols
    if has_symbol:
        q = text("SELECT code, name_ar, name_en, name_tr, symbol FROM currencies WHERE id=:id")
    else:
        q = text("SELECT code, name_ar, name_en, name_tr FROM currencies WHERE id=:id")
    r = s.execute(q, {"id": currency_id}).mappings().first()
    if not r:
        return "", "", ""
    code = r["code"]
    name = r.get(f"name_{lang}") or r.get("name_en") or r.get("name_ar") or r.get("name_tr") or ""
    symbol = (r.get("symbol") if has_symbol else None) or code
    return code, name, symbol

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

        template_rel = f"documents/templates/invoices/syrian/entry/{{'ar' if is_ar else ('tr' if is_tr else 'en')}}.html"

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
