# services/builder_router.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from importlib import import_module
from functools import lru_cache
from typing import Callable, Optional, Tuple

# قواعــد التوجيه: احرص أن تكون القواعد "الأكثر تحديدًا" قبل الأعم
_RULES = {
    # فاتورة سورية إدخال (الجديدة) — يجب أن تأتي قبل "invoice.syrian."
    "invoice.syrian.entry.": "documents.builders.invoice_syrian_entry",
    "invoice.syrian.entry":  "documents.builders.invoice_syrian_entry",

    # فواتير سورية - ترانزيت
    "invoice.syrian.intermediary.": "documents.builders.invoice_syrian_transit_intermediary",
    "invoice.syrian.intermediary": "documents.builders.invoice_syrian_transit_intermediary",
    "invoice.syrian.transit.": "documents.builders.invoice_syrian_transit",
    "invoice.syrian.transit": "documents.builders.invoice_syrian_transit",

    # فواتير التصدير الأجنبية فقط
    "invoice.foreign.": "documents.builders.invoice_foreign",

    # فواتير محلية/عامة (سورية/عادية/تجارية/بروفورما)
    "invoice.syrian.": "documents.builders.invoice",
    "invoice.normal.": "documents.builders.invoice",
    "invoice.normal":  "documents.builders.invoice",
    "invoice.commercial.": "documents.builders.invoice",
    "invoice.commercial": "documents.builders.invoice",
    "invoice.proforma.": "documents.builders.invoice_proforma",
    "invoice.proforma":  "documents.builders.invoice_proforma",

    # قوائم التعبئة
    "packing_list.": "documents.builders.packing_list",

    # CMR — بوليصة الشحن البري الدولية
    "cmr": "documents.builders.cmr_builder",

    # Form A — شهادة المنشأ (GSP)
    "form_a": "documents.builders.form_a_builder",
    "form.a": "documents.builders.form_a_builder",
}

def _best_rule(doc_code: str) -> Optional[Tuple[str, str]]:
    """
    يرجع (prefix, module_path) لأطول بادئة تطابق doc_code.
    مثال: 'invoice.syrian.entry.ar' سيطابق 'invoice.syrian.entry.' قبل 'invoice.syrian.'.
    """
    if not doc_code:
        return None
    # جرّب مطابقة الأطول أولاً
    candidates = sorted(_RULES.keys(), key=len, reverse=True)
    for prefix in candidates:
        if doc_code.startswith(prefix):
            return prefix, _RULES[prefix]
    return None

@lru_cache(maxsize=64)
def _import_build_ctx(mod_path: str) -> Callable[..., dict]:
    """
    يستورد الموديول ويعيد المؤشر إلى الدالة build_ctx.
    يرفع ValueError برسالة واضحة إن لم توجد الدالة.
    """
    mod = import_module(mod_path)
    build = getattr(mod, "build_ctx", None)
    if not callable(build):
        raise ValueError(f"Module '{mod_path}' does not define a callable 'build_ctx'")
    return build  # type: ignore[return-value]

def get_builder(doc_code: str) -> Callable[..., dict]:
    """
    يعيد دالة الـ builder المناسبة للـ doc_code.
    الاستخدام:
        build_ctx = get_builder("invoice.syrian.entry.ar")
        ctx = build_ctx(doc_code="invoice.syrian.entry", transaction_id=123, lang="ar")
    """
    hit = _best_rule(doc_code or "")
    if not hit:
        raise LookupError(f"No builder rule matched for doc_code='{doc_code}'")
    _prefix, mod_path = hit
    return _import_build_ctx(mod_path)

def resolve_builder_module(doc_code: str) -> str:
    """
    دالة مساعدة (للدِيبَج): ترجع مسار الموديول الذي سيُستخدم لهذا doc_code.
    """
    hit = _best_rule(doc_code or "")
    if not hit:
        raise LookupError(f"No builder rule matched for doc_code='{doc_code}'")
    return hit[1]
