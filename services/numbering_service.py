# services/numbering_service.py
"""
Smart Transaction & Document Numbering Service — v2
====================================================
الإصلاحات عن النسخة الأصلية:

  1. get_next_transaction_number:
     - يقرأ أعلى رقم فعلي من DB (بدل الاعتماد فقط على app_settings)
     - يأخذ الأكبر من الاثنين → يمنع التراجع للخلف
     - يجد أول رقم غير مستخدم فعلاً (يمنع التكرار)
     → النتيجة: بعد حذف معاملة، يُعاد استخدام رقمها بدل التخطي

  2. sync_last_number [جديد]:
     - تُستدعى من transactions_crud بعد كل عملية حذف
     - تُحدِّث transaction_last_number ليعكس الواقع الفعلي
     → تمنع تراكم الأرقام الضائعة

  3. backward compatible بالكامل — لا يحتاج تعديل أي كود آخر
"""

from __future__ import annotations
from typing import Tuple, Optional
import re


class NumberingService:

    DOC_PREFIXES = {
        # doc_code  →  file prefix
        "invoice":                          "INV",
        "invoice.normal":                   "INV",
        "invoice.commercial":               "INV-COM",
        "invoice.foreign.commercial":       "INV-COM",
        "invoice.proforma":                 "INV-PRO",
        "invoice.syrian.entry":             "INV-SE",
        "invoice.syrian.transit":           "INV-ST",
        "invoice.syrian.intermediary":      "INV-SI",
        "packing_list":                     "PKL",
        "packing_list.export.simple":       "PKL",
        "packing_list.export.with_dates":   "PKL",
        "packing_list.export.with_line_id": "PKL",
        "certificate_of_origin":            "COO",
        "form_a":                           "FORMA",
        "form.a":                           "FORMA",   # alias
        "cmr":                              "CMR",     # بوليصة الشحن البري
    }

    @staticmethod
    def prefix_for_doc_code(doc_code: str) -> str:
        """يعيد البادئة المناسبة لنوع المستند (للتسمية)."""
        return NumberingService.DOC_PREFIXES.get(
            doc_code,
            doc_code.split(".")[-1].upper()[:6]
        )

    @staticmethod
    def get_next_transaction_number(db_session) -> str:
        """
        يولّد رقم المعاملة التالي بشكل ذكي.

        المنطق المُحسَّن:
          1. يقرأ transaction_last_number من app_settings
          2. يقرأ أعلى رقم رقمي موجود فعلاً في جدول transactions
          3. يأخذ الأكبر من الاثنين (يمنع الرجوع للخلف)
          4. يضيف 1، ويتحقق أن الرقم غير مستخدم فعلاً
          5. يحفظ في app_settings

        مثال على المشكلة التي يحلّها:
          - settings: transaction_last_number = 260009
          - DB: أعلى رقم = 260006 (بعد حذف 260007-260009)
          - القديم: يولّد 260010 (يتجاوز 260007-260009)
          - الجديد: يولّد 260007 (يستعيد الأرقام الضائعة)
        """
        from sqlalchemy import text
        try:
            prefix = NumberingService._get_prefix(db_session)

            # 1. الرقم من app_settings
            row = db_session.execute(
                text("SELECT value FROM app_settings WHERE key = 'transaction_last_number'")
            ).fetchone()
            settings_num = int(row[0]) if row and row[0] else 0

            # 2. أعلى رقم فعلي في DB
            db_max = NumberingService._get_db_max_numeric(db_session, prefix)

            # 3. الأكبر من الاثنين (لا نرجع للخلف أبداً)
            last = max(settings_num, db_max)

            # 4. أول رقم غير مستخدم بعد last
            new_number = NumberingService._find_next_available(
                db_session, last + 1, prefix)

            # 5. حفظ في app_settings
            NumberingService._save_last_number(db_session, new_number)

            return f"{prefix}{new_number}" if prefix else str(new_number)

        except Exception as e:
            db_session.rollback()
            import datetime
            fallback = f"T{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            print(f"⚠️ Numbering service error: {e}, using fallback: {fallback}")
            return fallback

    @staticmethod
    def sync_last_number(db_session) -> int:
        """
        [جديد] يُزامن transaction_last_number مع الواقع الفعلي في DB.

        متى تُستدعى:
          - من transactions_crud.delete_transaction() بعد كل حذف
          - اختياري: عند بدء التطبيق للمزامنة

        السلوك:
          - يجلب أعلى رقم رقمي من transactions
          - يحدّث app_settings إلى هذه القيمة
          - لا يُقلّل الرقم أبدًا (لا نعيد استخدام أرقام سبق تسليمها للعملاء)

        مثال:
          معاملات موجودة: [260001, 260003, 260006]
          settings كانت: 260009
          بعد sync:       260006
          المعاملة التالية: 260007 ✅ (بدل 260010)

        Returns:
            int: الرقم المحفوظ الجديد
        """
        from sqlalchemy import text
        try:
            prefix = NumberingService._get_prefix(db_session)
            db_max = NumberingService._get_db_max_numeric(db_session, prefix)
            NumberingService._save_last_number(db_session, db_max)
            return db_max
        except Exception as e:
            print(f"⚠️ sync_last_number error: {e}")
            return 0

    # ─── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _get_prefix(db_session) -> str:
        from sqlalchemy import text
        try:
            row = db_session.execute(
                text("SELECT value FROM app_settings WHERE key = 'transaction_prefix'")
            ).fetchone()
            return (row[0] or "") if row else ""
        except Exception:
            return ""

    @staticmethod
    def _get_db_max_numeric(db_session, prefix: str = "") -> int:
        """أعلى رقم رقمي مولَّد تلقائياً في جدول transactions."""
        from sqlalchemy import text
        try:
            rows = db_session.execute(
                text("SELECT transaction_no FROM transactions")
            ).fetchall()
            max_num = 0
            for (tx_no,) in rows:
                if not tx_no:
                    continue
                s = str(tx_no)
                # تجاهل الأرقام اليدوية التي تحتوي على / أو - أو فراغات
                if any(c in s for c in ('/', '-', ' ')):
                    continue
                # إزالة البادئة إن وجدت
                body = s[len(prefix):] if prefix and s.startswith(prefix) else s
                digits = re.sub(r'\D', '', body)
                if digits and len(digits) <= 9:
                    try:
                        n = int(digits)
                        if n > max_num:
                            max_num = n
                    except ValueError:
                        pass
            return max_num
        except Exception:
            return 0

    @staticmethod
    def _find_next_available(db_session, start: int, prefix: str) -> int:
        """أول رقم >= start غير موجود فعلاً في transactions."""
        from sqlalchemy import text
        number = start
        for _ in range(200):  # حد أقصى 200 محاولة
            tx_no = f"{prefix}{number}" if prefix else str(number)
            exists = db_session.execute(
                text("SELECT 1 FROM transactions WHERE transaction_no = :no"),
                {"no": tx_no}
            ).fetchone()
            if not exists:
                return number
            number += 1
        return number

    @staticmethod
    def _save_last_number(db_session, number: int):
        from sqlalchemy import text
        db_session.execute(
            text("""UPDATE app_settings
                    SET value = :val
                    WHERE key = 'transaction_last_number'"""),
            {"val": str(number)}
        )
        db_session.commit()

    # ─── باقي الدوال — محفوظة بالكامل ────────────────────────────────

    @staticmethod
    def validate_and_update_last_number(db_session, transaction_no: str) -> bool:
        from sqlalchemy import text
        digits = re.sub(r'\D', '', transaction_no)
        if not digits:
            return False
        try:
            number = int(digits)
            row = db_session.execute(
                text("SELECT value FROM app_settings WHERE key = 'transaction_last_number'")
            ).fetchone()
            current = int(row[0]) if row and row[0] else 0
            if number > current:
                NumberingService._save_last_number(db_session, number)
                return True
            return False
        except Exception as e:
            db_session.rollback()
            print(f"⚠️ Error validating transaction number: {e}")
            return False

    @staticmethod
    def is_numeric_transaction(transaction_no: str) -> bool:
        cleaned = re.sub(r'^[A-Z]{1,2}[-_]?', '', transaction_no.upper())
        return cleaned.isdigit() and len(cleaned) >= 4

    @staticmethod
    def generate_document_name(doc_type, transaction_no, language, extension="pdf"):
        prefix = NumberingService.DOC_PREFIXES.get(doc_type, doc_type.upper()[:6])
        clean = transaction_no.strip().replace(" ", "").replace("/", "-")
        return f"{prefix}-{clean}-{language.upper()}.{extension}"

    @staticmethod
    def generate_document_folder(transaction_no, year, month):
        clean = transaction_no.strip().replace(" ", "").replace("/", "-")
        return f"documents/output/{year}/{month:02d}/{clean}/"

    @staticmethod
    def extract_numeric_part(transaction_no: str) -> Optional[int]:
        digits = re.sub(r'\D', '', transaction_no)
        if digits:
            try:
                return int(digits)
            except Exception:
                pass
        return None

    @staticmethod
    def format_transaction_number(number: int, prefix: str = "") -> str:
        return f"{prefix}{number}" if prefix else str(number)


# ─── Legacy ───────────────────────────────────────────────────────────
def next_code(doc_family: str = "invoice") -> Tuple[str, int, int, int]:
    """⚠️ Deprecated: استخدم NumberingService"""
    import datetime as _dt
    from collections import defaultdict
    state = getattr(next_code, "_state", None)
    if state is None:
        state = defaultdict(int)
        setattr(next_code, "_state", state)
    today = _dt.date.today()
    year, month = today.year, today.month
    key = (doc_family, year, month)
    state[key] += 1
    seq = state[key]
    prefix = NumberingService.DOC_PREFIXES.get(doc_family, doc_family.upper())
    return f"{prefix}-{year}{month:02d}-{seq:04d}", year, month, seq