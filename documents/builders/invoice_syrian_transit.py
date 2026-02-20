# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Tuple

try:
    # نعيد استخدام بلدر الإدخالات كأساس كما هو
    from documents.builders.invoice_syrian_entry import build_ctx as _entry_build_ctx
except Exception:
    _entry_build_ctx = None  # type: ignore


def _normalize_call(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    نقبل positional/keyword مثل استدعاءات النظام الحالية.
    أمثلة:
      build_ctx("invoice.syrian.transit", 123, "en")
      build_ctx(doc_code="invoice.syrian.transit", transaction_id=123, lang="en")
    """
    out = dict(kwargs)
    # doc_code
    if "doc_code" not in out and len(args) >= 1 and isinstance(args[0], str):
        out["doc_code"] = args[0]
    # transaction_id
    if "transaction_id" not in out:
        for a in args:
            if isinstance(a, int):
                out["transaction_id"] = a
                break
    # lang
    if "lang" not in out and len(args) >= 3 and isinstance(args[2], str):
        out["lang"] = args[2]
    if "lang" not in out and len(args) >= 2 and isinstance(args[1], str):
        out["lang"] = args[1]
    out.setdefault("lang", "en")
    if "transaction_id" not in out:
        raise TypeError("build_ctx missing required 'transaction_id'")
    return out


def build_ctx(*args, **kwargs) -> Dict[str, Any]:
    """
    Syrian Transit Invoice — نفس الإدخال تماماً لكن نغيّر القالب
    ونضيف كلمة TRANSIT تحت التاريخ.
    """
    if _entry_build_ctx is None:
        raise RuntimeError("invoice_syrian_entry.build_ctx is not importable")

    call = _normalize_call(args, kwargs)

    # ⚠️ بلدر الإدخال توقيعه positional: (doc_code, transaction_id, lang)
    base = _entry_build_ctx(
        call.get("doc_code", "invoice.syrian.transit"),
        int(call["transaction_id"]),
        call["lang"],
    )

    # استخدم قالب الترانزيت بدل قالب الإدخال
    lang = (call["lang"] or "en").lower()
    base["template_rel"] = f"documents/templates/invoices/syrian/transit/{'ar' if lang.startswith('ar') else ('tr' if lang.startswith('tr') else 'en')}.html"

    # علّم على أنه ترانزيت (لو حبيت تستخدمه لاحقاً)
    base.setdefault("doc", {})
    base["doc"]["type"] = "syrian_transit"

    # تظهر تحت التاريخ
    base["transit_label"] = "TRANSIT"

    return base
