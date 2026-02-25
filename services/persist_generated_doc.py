# services/persist_generated_doc.py (UPsert version)
from __future__ import annotations
from typing import Optional, Dict
import json
from datetime import date

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database.models import get_session_local

# ----------------------------------------------------------------------------
# Mapping template-code -> document_types.code in DB (no assumptions)
DOC_TYPE_MAP: dict[str, str] = {
    # Invoices — commercial/foreign
    "invoice.foreign.commercial":  "INV_EXT",
    "invoice.commercial":          "INV_EXT",

    # Invoices — normal
    "invoice.normal":              "INV_NORMAL",

    # Invoices — proforma
    "invoice.proforma":            "INV_PROFORMA",

    # Invoices — Syrian
    "invoice.syrian.intermediary": "INV_SYR_INTERM",
    "invoice.syrian.transit":      "INV_SYR_TRANS",
    "invoice.syrian.entry":        "invoice.syrian.entry",
    "invoice.syrian":              "INV_SY",

    # Packing Lists
    "packing_list.export.simple":       "PL_EXPORT_SIMPLE",
    "packing_list.export.with_dates":   "PL_EXPORT_WITH_DATES",
    "packing_list.export.with_line_id": "PL_EXPORT_WITH_LINE_ID",

    # CMR
    "cmr": "cmr",

    #form a
    "form_a": "form_a",
    "form.a": "form_a",
}



def _prefix_for(doc_code: str) -> str:
    """يعيد البادئة الصحيحة للمستند حسب نوعه."""
    try:
        from services.numbering_service import NumberingService
        return NumberingService.prefix_for_doc_code(doc_code)
    except Exception:
        return "INVPL" if doc_code.startswith(("invoice.", "packing_list.")) else "DOC"


def _resolve_document_type_code(doc_code: str) -> str:
    # مطابقة مباشرة أولاً
    code = DOC_TYPE_MAP.get(doc_code)
    if code:
        return code
    # محاولة إزالة suffix اللغة (مثل invoice.normal.ar → invoice.normal)
    parts = doc_code.rsplit(".", 1)
    if len(parts) == 2 and parts[1] in ("ar", "en", "tr"):
        code = DOC_TYPE_MAP.get(parts[0])
        if code:
            return code
    raise ValueError(
        (
            "لا يوجد mapping في DOC_TYPE_MAP للكود: {dc}.\n"
            "الرجاء إضافة سطر مناسب يشير إلى document_types.code الفعلي في القاعدة.\n"
            "المفاتيح المتاحة حالياً: {keys}"
        ).format(dc=doc_code, keys=", ".join(sorted(DOC_TYPE_MAP.keys())) or "<فارغ>")
    )


def _next_seq_db(s, year: int, month: int) -> int:
    row = s.execute(
        text("SELECT COALESCE(MAX(seq), 0) + 1 FROM doc_groups WHERE year=:y AND month=:m"),
        {"y": year, "m": month},
    ).first()
    return int(row[0]) if row and row[0] is not None else 1


def persist_document(
    transaction_id: int,
    doc_code: str,
    lang: str,
    file_path: str,
    totals: Optional[Dict] = None,
    data: Optional[Dict] = None,
    document_no: Optional[str] = None,
) -> Dict:
    """
    Persist (or upsert) a document row.
    doc_no = PREFIX-{transaction_no}  (مثال: INV-COM-260006)
    Uniqueness key: (transaction_id, document_type_id, language)
    → نفس النوع + نفس اللغة + نفس المعاملة = update الصف الموجود
    """
    SessionLocal = get_session_local()
    s = SessionLocal()
    try:
        # 1) نوع المستند
        dtype_code = _resolve_document_type_code(doc_code)
        row = s.execute(text("SELECT id FROM document_types WHERE code=:c"), {"c": dtype_code}).first()
        if not row:
            raise RuntimeError(f"document_types لا يحوي الكود '{dtype_code}' المطلوب لـ '{doc_code}'")
        document_type_id = int(row[0])

        # 2) رقم المعاملة الفعلي
        tx_row = s.execute(
            text("SELECT COALESCE(transaction_no, CAST(id AS TEXT)) FROM transactions WHERE id=:i"),
            {"i": int(transaction_id)}
        ).fetchone()
        transaction_no = str(tx_row[0]) if tx_row and tx_row[0] else str(transaction_id)

        # 3) doc_no = PREFIX-transaction_no
        if document_no and document_no.strip():
            doc_no = document_no.strip()
        else:
            prefix = _prefix_for(doc_code)
            import re as _re
            safe_tx = _re.sub(r"[\\/]", "-", transaction_no.strip())
            doc_no = f"{prefix}-{safe_tx}"   # مثال: INV-COM-260006

        # 4) upsert في doc_groups بناءً على (transaction_id, doc_no)
        today = date.today()
        year, month = today.year, today.month
        grp = s.execute(
            text("SELECT id, seq FROM doc_groups WHERE transaction_id=:t AND doc_no=:n ORDER BY id DESC LIMIT 1"),
            {"t": transaction_id, "n": doc_no}
        ).mappings().first()

        if grp:
            group_id = int(grp["id"])
            seq = int(grp["seq"] or 0)
        else:
            seq = _next_seq_db(s, year, month)
            inserted = False
            for attempt in range(8):
                try:
                    res = s.execute(
                        text("INSERT INTO doc_groups (transaction_id, doc_no, year, month, seq) VALUES (:t,:n,:y,:m,:s)"),
                        {"t": transaction_id, "n": doc_no, "y": year, "m": month, "s": seq}
                    )
                    s.commit()
                    group_id = int(res.lastrowid)
                    inserted = True
                    break
                except IntegrityError:
                    s.rollback()
                    seq += 1
                    continue
            if not inserted:
                raise RuntimeError("فشل إنشاء doc_groups بعد عدة محاولات.")

        # 5) UPSERT في documents بناءً على (group_id, document_type_id, language)
        totals_json = json.dumps(totals or {}, ensure_ascii=False)
        data_json   = json.dumps(data   or {}, ensure_ascii=False)

        s.execute(text("""
            INSERT INTO documents
                (group_id, document_type_id, language, status, file_path, totals_json, data_json)
            VALUES
                (:g, :dt, :lang, 'ready', :path, :totals, :data)
            ON CONFLICT(group_id, document_type_id, language) DO UPDATE SET
                status      = excluded.status,
                file_path   = excluded.file_path,
                totals_json = excluded.totals_json,
                data_json   = excluded.data_json
        """), {
            "g": group_id, "dt": document_type_id, "lang": lang,
            "path": file_path, "totals": totals_json, "data": data_json,
        })
        s.commit()

        return {
            "group_id":           int(group_id),
            "document_no":        doc_no,
            "document_type_code": dtype_code,
            "seq":                int(seq),
        }
    finally:
        s.close()


def allocate_group_doc_no(transaction_id: int, prefix: str = "INVPL") -> str:
    """
    يعيد doc_no = PREFIX-{transaction_no}.
    إذا موجود بالفعل → يعيده مباشرة (reuse).
    """
    import re as _re
    SessionLocal = get_session_local()
    s = SessionLocal()
    try:
        # جلب رقم المعاملة الفعلي
        tx_row = s.execute(
            text("SELECT COALESCE(transaction_no, CAST(id AS TEXT)) FROM transactions WHERE id=:i"),
            {"i": int(transaction_id)}
        ).fetchone()
        transaction_no = str(tx_row[0]) if tx_row and tx_row[0] else str(transaction_id)
        safe_tx = _re.sub(r"[\\/]", "-", transaction_no.strip())
        doc_no = f"{prefix}-{safe_tx}"

        # هل موجود مسبقاً؟
        row = s.execute(
            text("SELECT doc_no FROM doc_groups WHERE transaction_id=:t AND doc_no=:n ORDER BY id DESC LIMIT 1"),
            {"t": transaction_id, "n": doc_no}
        ).fetchone()
        if row and row[0]:
            return str(row[0])

        # أنشئ سجل جديد
        today = date.today()
        year, month = today.year, today.month
        seq = _next_seq_db(s, year, month)
        for attempt in range(8):
            try:
                s.execute(
                    text("INSERT INTO doc_groups (transaction_id, doc_no, year, month, seq) VALUES (:t,:n,:y,:m,:s)"),
                    {"t": transaction_id, "n": doc_no, "y": year, "m": month, "s": seq}
                )
                s.commit()
                return doc_no
            except IntegrityError:
                s.rollback()
                seq += 1
                continue
        raise RuntimeError("Failed to allocate doc_no after several attempts.")
    finally:
        s.close()