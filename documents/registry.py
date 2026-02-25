# documents/registry.py
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from . import TEMPLATES_DIR

# خريطة الأكواد إلى مجلدات القوالب (نسخة موسّعة مع Alias للخلفية)
DOC_CODES: Dict[str, str] = {
    # Invoices
    "invoice.normal":               "invoices/normal",
    "invoice.commercial":           "invoices/commercial",
    "invoice.proforma":             "invoices/proforma",
    "invoice.syrian.transit":       "invoices/syrian/transit",
    "invoice.syrian.intermediary":  "invoices/syrian/intermediary",
    "invoice.syrian.entry":         "invoices/syrian/entry",  # ← جديدنا

    # Packing List
    "packing_list.export.simple":       "packing_list/export/simple",
    "packing_list.export.with_dates":   "packing_list/export/with_dates",
    "packing_list.export.with_line_id": "packing_list/export/with_line_id",

    # CMR — بوليصة الشحن البري الدولية
    "cmr":                          "cmr",

    # Form A — شهادة المنشأ (GSP)
    "form_a":                       "form_a",
    "form.a":                       "form_a",

    # Legacy alias (للتوافق مع الموجود سابقًا)
    "invoice.foreign.commercial":   "invoices/commercial",
}

LANG_SUFFIX = {"en": "en.html", "tr": "tr.html", "ar": "ar.html"}

@dataclass(frozen=True)
class TemplateSpec:
    doc_code: str
    lang: str
    path: Path
    extra: dict | None = None  # معلومات إضافية اختيارية (مثل عنوان افتراضي)

def _default_title_for_proforma(lang: str) -> str:
    return "PROFORMA INVOICE" if lang == "en" else ("ÖN FATURA" if lang == "tr" else "فاتورة أولية")

def resolve_template(doc_code: str, lang: str) -> TemplateSpec:
    if lang not in LANG_SUFFIX:
        raise FileNotFoundError(f"Unsupported language: {lang}")

    rel_folder = DOC_CODES.get(doc_code)
    if not rel_folder:
        raise FileNotFoundError(f"Unknown doc_code: {doc_code}")

    lang_file = LANG_SUFFIX[lang]
    path = TEMPLATES_DIR / rel_folder / lang_file

    # 1) تطابق مباشر
    if path.exists():
        extra = None
        if doc_code in ("invoice.proforma",):
            extra = {"title": _default_title_for_proforma(lang)}
        return TemplateSpec(doc_code, lang, path, extra)

    # 2) سقوط خاص للـ Proforma → استخدم commercial إن لم توجد ملفاتها
    if doc_code in ("invoice.proforma",):
        fallback = TEMPLATES_DIR / DOC_CODES["invoice.commercial"] / lang_file
        if fallback.exists():
            return TemplateSpec(doc_code, lang, fallback, {"title": _default_title_for_proforma(lang)})

    # 3) سقوط لغوي اختياري → EN لو ملف اللغة ناقص
    en_fallback = TEMPLATES_DIR / rel_folder / LANG_SUFFIX["en"]
    if en_fallback.exists():
        extra = None
        if doc_code in ("invoice.proforma",):
            extra = {"title": _default_title_for_proforma("en")}
        return TemplateSpec(doc_code, lang, en_fallback, extra)

    raise FileNotFoundError(f"Template not found for {doc_code} [{lang}] → {path}")
