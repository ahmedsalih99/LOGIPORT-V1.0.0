# documents/registry.py
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from . import TEMPLATES_DIR

# خريطة الأكواد إلى مجلدات القوالب
# ملاحظة: CMR يستخدم قالب EN واحد بغض النظر عن اللغة (معيار دولي)
DOC_CODES: Dict[str, str] = {
    # ── Invoices — General ────────────────────────────────────────────────────
    "invoice.normal":               "invoices/normal",
    "invoice.commercial":           "invoices/commercial",
    "invoice.proforma":             "invoices/proforma",

    # ── Invoices — Syrian ─────────────────────────────────────────────────────
    "invoice.syrian":               "invoices/syrian/transit",   # fallback عام → transit
    "invoice.syrian.transit":       "invoices/syrian/transit",
    "invoice.syrian.intermediary":  "invoices/syrian/intermediary",
    "invoice.syrian.entry":         "invoices/syrian/entry",

    # ── Invoices — Foreign ────────────────────────────────────────────────────
    "invoice.foreign.commercial":   "invoices/commercial",       # legacy alias

    # ── Packing Lists ─────────────────────────────────────────────────────────
    "packing_list.export.simple":       "packing_list/export/simple",
    "packing_list.export.with_dates":   "packing_list/export/with_dates",
    "packing_list.export.with_line_id": "packing_list/export/with_line_id",

    # ── CMR — بوليصة الشحن البري الدولية (قالب EN فقط — معيار دولي) ─────────
    "cmr":                "cmr",            # النسخة الأساسية (بدون لون)
    "cmr.copy1.sender":   "cmr",            # نسخة المرسِل    — أحمر
    "cmr.copy2.consignee":"cmr",            # نسخة المستلِم   — أزرق
    "cmr.copy3.carrier":  "cmr",            # نسخة الناقل     — أخضر
    "cmr.copy4.archive":  "cmr",            # نسخة الأرشيف    — أسود

    # ── Form A — شهادة المنشأ (GSP) ───────────────────────────────────────────
    "form_a": "form_a",
    "form.a": "form_a",   # alias
}

LANG_SUFFIX = {"en": "en.html", "tr": "tr.html", "ar": "ar.html"}

# doc_codes التي تستخدم قالب EN واحداً بغض النظر عن اللغة المطلوبة
_ENGLISH_ONLY_DOCS = frozenset({
    "cmr",
    "cmr.copy1.sender",
    "cmr.copy2.consignee",
    "cmr.copy3.carrier",
    "cmr.copy4.archive",
})


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

    # ── CMR وأي مستند English-only: دائماً en.html ────────────────────────────
    if doc_code in _ENGLISH_ONLY_DOCS:
        # اختر الـ template حسب النسخة
        _CMR_COPY_FILES = {
            "cmr.copy1.sender":    "copy1_sender.html",
            "cmr.copy2.consignee": "copy2_consignee.html",
            "cmr.copy3.carrier":   "copy3_carrier.html",
            "cmr.copy4.archive":   "copy4_archive.html",
        }
        template_file = _CMR_COPY_FILES.get(doc_code, "en.html")
        path = TEMPLATES_DIR / rel_folder / template_file
        if path.exists():
            return TemplateSpec(doc_code, lang, path, None)
        # fallback للـ en.html لو الملف غير موجود
        path = TEMPLATES_DIR / rel_folder / "en.html"
        if path.exists():
            return TemplateSpec(doc_code, lang, path, None)
        raise FileNotFoundError(f"CMR template missing → {path}")

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

    # 3) سقوط لغوي → EN لو ملف اللغة ناقص
    en_fallback = TEMPLATES_DIR / rel_folder / LANG_SUFFIX["en"]
    if en_fallback.exists():
        extra = None
        if doc_code in ("invoice.proforma",):
            extra = {"title": _default_title_for_proforma("en")}
        return TemplateSpec(doc_code, lang, en_fallback, extra)

    raise FileNotFoundError(f"Template not found for {doc_code} [{lang}] → {path}")