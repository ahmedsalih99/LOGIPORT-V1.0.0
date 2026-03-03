# documents/builders/invoice_proforma.py
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

# ======================== builder ========================
# ابحث عن أول عمود موجود وقيمته غير NULL من بين مرشحين (ضمن جدول transactions)
def _first_existing_company_id(s, tx_id: int, candidates: list[str]) -> int | None:
    cols_info = s.execute(text("PRAGMA table_info(transactions)")).mappings().all()
    cols = {r["name"] for r in cols_info}
    present = [c for c in candidates if c in cols]
    if not present:
        return None
    # ابنِ SELECT ديناميكي لكل الأعمدة الموجودة
    cols_sql = ", ".join(present)
    row = s.execute(text(f"SELECT {cols_sql} FROM transactions WHERE id=:i"), {"i": int(tx_id)}).mappings().first()
    if not row:
        return None
    for c in present:
        v = row.get(c)
        if v not in (None, ""):
            try:
                return int(v)
            except Exception:
                pass
    return None



def build_ctx(doc_code: str, transaction_id: int, lang: str) -> Dict[str, Any]:
    """
    Proforma Invoice builder — مطابق لـ invoice_foreign مع أعلام/رايات خاصة بالبروفورما
    + دعم طرف ثالث Notify يظهر فقط عند توفره.
    """
    lang = (lang or "en").lower()
    SessionLocal = get_session_local()
    with SessionLocal() as s:
        # --- انتقاء عمود بلد الوجهة حسب مخطط DB ---
        dest_col = _pick_dest_col(s)

        # --- جلب المعاملة ---
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

        # --- Delivery method ---
        delivery_method = ""
        if t["delivery_method_id"]:
            dm = s.execute(
                text("SELECT name_ar, name_en, name_tr FROM delivery_methods WHERE id=:id"),
                {"id": t["delivery_method_id"]}
            ).mappings().first()
            if dm:
                delivery_method = dm.get(f"name_{lang}") or dm.get("name_en") or dm.get("name_ar") or dm.get("name_tr") or ""

        # --- Currency ---
        currency_code = currency_name = ""
        if t["currency_id"]:
            cur = s.execute(
                text("SELECT code, name_ar, name_en, name_tr FROM currencies WHERE id=:id"),
                {"id": t["currency_id"]}
            ).mappings().first()
            if cur:
                currency_code = cur["code"]
                currency_name = cur.get(f"name_{lang}") or cur.get("name_en") or cur.get("name_ar") or cur.get("name_tr") or ""
        else:
            cur_rows = s.execute(text("""
                SELECT DISTINCT c.code, c.name_ar, c.name_en, c.name_tr
                FROM transaction_items ti
                JOIN currencies c ON c.id = ti.currency_id
                WHERE ti.transaction_id = :tid AND ti.currency_id IS NOT NULL
            """), {"tid": int(transaction_id)}).mappings().all()
            if len(cur_rows) == 1:
                currency_code = cur_rows[0]["code"]
                currency_name = (
                    cur_rows[0].get(f"name_{lang}") or cur_rows[0].get("name_en")
                    or cur_rows[0].get("name_ar") or cur_rows[0].get("name_tr") or ""
                )

        # --- شركات الأطراف الأساسية ---
        exporter = _company_obj(s, t["exporter_company_id"], lang)
        importer = _company_obj(s, t["importer_company_id"], lang)
        client   = _client_obj(s, t["client_id"], lang)

        # --- Bank info تأكيد ---
        if t["exporter_company_id"] and not (exporter.get("bank_info") or "").strip():
            bi = s.execute(text("SELECT bank_info FROM companies WHERE id=:id"),
                           {"id": t["exporter_company_id"]}).mappings().first()
            exporter["bank_info"] = (bi and bi.get("bank_info") or "") or ""
        if t["importer_company_id"] and not (importer.get("bank_info") or "").strip():
            bi2 = s.execute(text("SELECT bank_info FROM companies WHERE id=:id"),
                            {"id": t["importer_company_id"]}).mappings().first()
            importer["bank_info"] = (bi2 and bi2.get("bank_info") or "") or ""

        # --- أسماء الدول (غير إلزامية للاستخدام أدناه) ---
        origin_name = _country_name(s, t["origin_country_id"], lang)
        dest_name   = _country_name(s, t["destination_country_id"], lang)

        # --- طرف ثالث: Notify/Broker/OrderBy... (يظهر فقط إن وُجد) ---
        # نفحص الأعمدة الموجودة فعليًا ونأخذ أول قيمة غير NULL حسب هذا الترتيب
        cols_info = s.execute(text("PRAGMA table_info(transactions)")).mappings().all()
        tx_cols = {r["name"] for r in cols_info}
        notify_candidates = [
            "notify_company_id",
            "broker_company_id",
            "order_by_company_id",
            "on_behalf_company_id",
            "on_behalf_of_company_id",
            "third_party_company_id",
        ]
        present = [c for c in notify_candidates if c in tx_cols]

        notify = {"name": "", "address": ""}
        if present:
            cols_sql = ", ".join(present)
            r = s.execute(text(f"SELECT {cols_sql} FROM transactions WHERE id=:i"),
                          {"i": int(t["id"])}).mappings().first()
            if r:
                notify_id = None
                for c in present:
                    v = r.get(c)
                    if v not in (None, ""):
                        try:
                            notify_id = int(v)
                            break
                        except Exception:
                            pass
                if notify_id:
                    notify = _company_obj(s, notify_id, lang)

        # --- Items ---
        rows = s.execute(text(f"""
            SELECT ti.id,
                   m.name_{lang}      AS material_name,
                   ti.quantity         AS qty,
                   ti.gross_weight_kg  AS gross,
                   ti.net_weight_kg    AS net,
                   ti.unit_price       AS unit_price,
                   ti.line_total       AS amount,
                   pk.name_{lang}      AS packaging,
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

            items.append({
                "n": idx,
                "description": r["material_name"],
                "unit": (r["packaging"] or pu),  # وحدة التغليف للعرض في العمود
                "pricing_unit": pu,              # وحدة التسعير (TON/KG/UNIT) للمرجعية
                "packaging": r["packaging"],
                "qty": q,
                "gross": gw, "gross_kg": gw,
                "net":  nw, "net_kg":  nw,
                "unit_price": up,
                "amount": am,
                "pricing_type": {
                    "code": r.get("pricing_type_code"),
                    "name": r.get("pricing_type_name"),
                },
            })

        # --- تجميعات ووحدات العرض ---
        uniq_units = _dedup_preserve_order([(u or "").upper() for u in price_units_for_items if u is not None])
        uniq_packs = _dedup_preserve_order([p for p in pack_names if p])
        uniq_pt_names = _dedup_preserve_order([n for n in pt_names if n])

        unit_price_per = uniq_units[0] if len(uniq_units) == 1 else "UNIT"
        unit_price_label = " & ".join(uniq_units) if uniq_units else unit_price_per

        # الوزن يُعرض دائماً بالكيلوغرام بغض النظر عن نوع التسعير
        weight_unit_for_display = "KG"
        conv = 1.0

        qty_header_packaging = " & ".join(uniq_packs)

        for it in items:
            it["gross_display"] = (it["gross"] / conv) if conv != 1.0 else it["gross"]
            it["net_display"]   = (it["net"]   / conv) if conv != 1.0 else it["net"]

        totals_gross_display = (total_gross / conv) if conv != 1.0 else total_gross
        totals_net_display   = (total_net   / conv) if conv != 1.0 else total_net

        # --- تفقيط/ألفاظ ---
        amount_words = _tafqit_amount(total_value, currency_code, lang)
        # الكمية كتابةً: تستخدم وحدة التغليف (كيس/bag) لا وحدة التسعير (TON/KG)
        qty_pack_unit = uniq_packs[0] if len(uniq_packs) == 1 else (" & ".join(uniq_packs) if uniq_packs else "")
        qty_words    = _spell_non_monetary(total_qty,             lang, qty_pack_unit, kind="qty")
        gross_words  = _spell_non_monetary(totals_gross_display,  lang, weight_unit_for_display, kind="weight")
        net_words    = _spell_non_monetary(totals_net_display,    lang, weight_unit_for_display, kind="weight")

        # --- عنوان المستند ---
        titles = {
            "ar": "بروفورما إنفويْس",
            "en": "Proforma Invoice",
            "tr": "Proforma Fatura",
        }

        # --- السياق النهائي ---
        ctx: Dict[str, Any] = {
            "invoice_no": _coalesce(t["transaction_no"], str(t["id"])),
            "date": t["transaction_date"],

            "exporter": exporter,
            "consignee": importer,
            "importer": importer,
            "client": client,
            "notify": notify,                    # <= يظهر فقط إذا notify.name غير فارغة
            "prepared_by": exporter.get("name"), # <= مساعد للفوتر

            "transport": {
                "type": t["transport_type"],
                "ref": t["transport_ref"],
                "delivery_method": delivery_method,
            },
            "shipment": {
                "transport_type": t["transport_type"],
                "transport_ref": t["transport_ref"],
                "delivery_method": delivery_method,
                "origin_country": _country_name(s, t["origin_country_id"], lang),
                "destination_country": _country_name(s, t["destination_country_id"], lang),
                "currency_code": currency_code,
            },

            "delivery_method": delivery_method,
            "origin_country": _country_name(s, t["origin_country_id"], lang),
            "destination_country": _country_name(s, t["destination_country_id"], lang),
            "country_of_origin": _country_name(s, t["origin_country_id"], lang),
            "cur": currency_code,

            "items": items,
            "totals": {
                "qty": total_qty,
                "gross": total_gross,
                "net": total_net,
                "value": total_value,
                "total": total_value,
                "subtotal": total_value,
                "gross_display": totals_gross_display,
                "net_display":   totals_net_display,
            },

            # ألفاظ بالأحرف
            "amount_in_words": amount_words,
            "totals_in_words": amount_words,
            "value_in_words":  amount_words,
            "qty_in_words":          qty_words,
            "totals_qty_in_words":   qty_words,
            "gross_in_words":        gross_words,
            "totals_gross_in_words": gross_words,
            "net_in_words":          net_words,
            "totals_net_in_words":   net_words,

            # رؤوس ديناميكية
            "unit_price_per": unit_price_per,
            "unit_price_label": unit_price_label,
            "weight_unit_for_display": weight_unit_for_display,
            "qty_header_packaging": qty_header_packaging,

            "currency": {"code": currency_code, "name": currency_name},
            "pricing_type": (uniq_pt_names[0] if len(uniq_pt_names) == 1 else ""),
            "pricing_types_label": " & ".join(uniq_pt_names),

            # ==== فروقات البروفورما ====
            "doc_kind": "proforma",
            "is_proforma": True,
            "doc_title": titles.get(lang, titles["en"]),
            "flags": {
                "hide_tax_fields": True,   # إخفاء عناصر ضريبية/ختم
                "show_bank_block": True,   # إظهار معلومات البنك
                "non_tax_notice": True,    # توضيح أنها ليست فاتورة ضريبية
            },

            # بنك
            "bank_info": exporter.get("bank_info") or "",
            "include_bank_from_company": True,

            # ملاحظات
            "notes": t.get("notes") or "",
        }

        return _blankify(ctx)
