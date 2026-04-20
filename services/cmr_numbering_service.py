# services/cmr_numbering_service.py
"""
CMR Numbering Service — LOGIPORT
=================================
يولّد رقم CMR بالصيغة:  XX-NNNN
  XX   = أول حرفين من الاسم الإنجليزي للشركة الناقلة (مثال: SR, AL, TA)
  NNNN = رقم تسلسلي فريد لهذه الشركة (0001, 0002, ...)

قواعد:
  - كل شركة ناقلة لها عداد مستقل في جدول cmr_counters.
  - الرقم يُحجز فقط عند الحفظ الفعلي (peek لا يحجز شيئاً).
  - عند التعديل: إذا كان الحقل مملوءاً مسبقاً لا يُعاد توليده.
  - CMR الأول والثاني كل منهما عداد مستقل حسب الناقل الخاص به.
  - إذا ما كان في شركة ناقلة مختارة يُستخدم البادئة "CM".
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# البادئة الاحتياطية إذا لم تُختر شركة ناقلة
_FALLBACK_PREFIX = "CM"


def _extract_prefix(name_en: Optional[str]) -> str:
    """
    يستخرج أول حرفين من الاسم الإنجليزي.
    - يتجاهل المسافات والأحرف غير الأبجدية.
    - يحوّل للـ UPPERCASE.
    - إذا كان الاسم أقل من حرفين يُكمّل بـ 'X'.
    - Fallback: 'CM'.
    """
    if not name_en:
        return _FALLBACK_PREFIX
    letters = re.sub(r"[^A-Za-z]", "", name_en)
    if len(letters) < 1:
        return _FALLBACK_PREFIX
    prefix = letters[:2].upper()
    if len(prefix) == 1:
        prefix += "X"
    return prefix


def get_carrier_prefix(carrier_company_id: Optional[int]) -> str:
    """
    يجلب الاسم الإنجليزي للشركة الناقلة من DB ويستخرج البادئة.
    آمن: يعيد 'CM' في حالة أي خطأ.
    """
    if not carrier_company_id:
        return _FALLBACK_PREFIX
    try:
        from database.models import get_session_local
        from sqlalchemy import text
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            row = s.execute(
                text("SELECT name_en FROM companies WHERE id = :id"),
                {"id": int(carrier_company_id)},
            ).fetchone()
            name_en = row[0] if row else None
            return _extract_prefix(name_en)
    except Exception as e:
        logger.warning("get_carrier_prefix error: %s", e)
        return _FALLBACK_PREFIX


def peek_next_cmr_no(carrier_company_id: Optional[int]) -> str:
    """
    يعرض الرقم التالي المتوقع بدون حجزه — للعرض في الـ UI فقط.
    مثال: 'SR-0005'
    """
    prefix = get_carrier_prefix(carrier_company_id)
    try:
        from database.models import get_session_local
        from sqlalchemy import text
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            row = s.execute(
                text("SELECT last_number FROM cmr_counters WHERE carrier_prefix = :p"),
                {"p": prefix},
            ).fetchone()
            last = int(row[0]) if row else 0
            return f"{prefix}-{last + 1:04d}"
    except Exception as e:
        logger.warning("peek_next_cmr_no error: %s", e)
        return f"{prefix}-0001"


def allocate_cmr_no(carrier_company_id: Optional[int]) -> str:
    """
    يحجز ويعيد رقم CMR جديداً فريداً.
    - يزيد عداد الشركة بـ 1.
    - يتأكد من عدم التكرار في transport_details (cmr_no + cmr_no_2).
    - يُستدعى فقط عند الحفظ الفعلي.

    مثال: 'SR-0001'
    """
    prefix = get_carrier_prefix(carrier_company_id)
    try:
        from database.models import get_session_local
        from sqlalchemy import text
        SessionLocal = get_session_local()
        with SessionLocal() as s:
            # اجلب العداد الحالي أو ابدأ من 0
            row = s.execute(
                text("SELECT last_number FROM cmr_counters WHERE carrier_prefix = :p"),
                {"p": prefix},
            ).fetchone()
            last = int(row[0]) if row else 0
            next_num = last + 1

            # تحقق من عدم التكرار في transport_details
            for _ in range(500):
                candidate = f"{prefix}-{next_num:04d}"
                exists = s.execute(
                    text("""
                        SELECT 1 FROM transport_details
                        WHERE cmr_no = :c OR cmr_no_2 = :c
                        LIMIT 1
                    """),
                    {"c": candidate},
                ).fetchone()
                if not exists:
                    break
                next_num += 1

            # احفظ العداد
            s.execute(
                text("""
                    INSERT INTO cmr_counters (carrier_prefix, last_number)
                    VALUES (:p, :n)
                    ON CONFLICT(carrier_prefix) DO UPDATE
                        SET last_number = excluded.last_number,
                            updated_at  = datetime('now')
                """),
                {"p": prefix, "n": next_num},
            )
            s.commit()
            return f"{prefix}-{next_num:04d}"

    except Exception as e:
        logger.warning("allocate_cmr_no error: %s", e)
        import random
        return f"{prefix}-{random.randint(1000, 9999)}"