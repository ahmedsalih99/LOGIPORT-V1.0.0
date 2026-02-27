from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import datetime as _dt
import os
import logging

# -----------------------------------------------------------------------------
# Logging
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
from .html_engine import render_html
from .persist_generated_doc import persist_document, allocate_group_doc_no
from .builder_router import get_builder
from .pdf_renderer import render_html_to_pdf, detect_engines

from documents import OUTPUT_DIR
from pathlib import Path as _Path

from database.models import get_session_local
from sqlalchemy import text


@dataclass
class RenderResult:
    doc_code: str
    lang: str
    doc_no: str
    out_html: Path
    out_pdf: Optional[Path]


def _get_output_root() -> Path:
    """
    يعيد مجلد الجذر لحفظ المستندات.
    إذا حدّد المستخدم مساراً في الإعدادات → يستخدمه.
    وإلا → يستخدم OUTPUT_DIR الافتراضي داخل التطبيق.
    """
    try:
        from core.settings_manager import SettingsManager
        custom = SettingsManager.get_instance().get_documents_output_path()
        if custom and _Path(custom).exists():
            return _Path(custom)
    except Exception:
        pass
    return OUTPUT_DIR


def _sanitize_tx_no(tx_no: str) -> str:
    """يحوّل رقم المعاملة لاسم ملف آمن (يستبدل / و \\ والمسافات بـ -)."""
    import re as _re
    return _re.sub(r"[/\\\s]+", "-", (tx_no or "").strip()) or "UNKNOWN"


def _output_paths(
    prefix: str,
    transaction_no: str,
    lang: str,
) -> tuple[Path, Path]:
    """
    بناء مسارَي HTML و PDF للمستند المُولَّد.

    هيكل المجلد (مجلد واحد بالشهر):
        {root}/{YYYY}/{MM}/
            {PREFIX}-{transaction_no}-{LANG}.pdf
            إذا الملف موجود → {PREFIX}-{transaction_no}-{LANG}-v2.pdf ...

    أمثلة:
        INV-COM-260006-AR.pdf
        PKL-260006-EN.pdf
        INV-SE-260006-AR-v2.pdf   ← عند إعادة التوليد
    """
    today = _dt.date.today()
    root = _get_output_root()
    folder = root / f"{today.year:04d}" / f"{today.month:02d}"
    folder.mkdir(parents=True, exist_ok=True)

    safe_tx = _sanitize_tx_no(transaction_no)
    base_stem = f"{prefix}-{safe_tx}-{lang.upper()}"   # INV-COM-260006-AR

    # ابحث عن أول اسم غير مستخدم
    html_path = folder / f"{base_stem}.html"
    pdf_path  = folder / f"{base_stem}.pdf"
    if not html_path.exists() and not pdf_path.exists():
        return html_path, pdf_path

    for v in range(2, 200):
        stem_v = f"{base_stem}-v{v}"
        hp = folder / f"{stem_v}.html"
        pp = folder / f"{stem_v}.pdf"
        if not hp.exists() and not pp.exists():
            return hp, pp

    # fallback (لا يجب أن يصل هنا)
    return html_path, pdf_path


def render_document(
    *,
    transaction_id: int,
    transaction_no: str,
    doc_code: str,
    lang: str,
    force_html_only: bool = False,
    explicit_doc_no: Optional[str] = None,
) -> RenderResult:
    """
    يولّد المستند (HTML/PDF) بالاعتماد على transaction_id فقط.
    """

    logger.info(
        "Render document started | tx_id=%s doc_code=%s lang=%s",
        transaction_id, doc_code, lang
    )

    # -------------------------------------------------------------------------
    # Runtime PDF diagnostics (non-blocking)
    try:
        from .healthcheck import check_pdf_runtime
        report = check_pdf_runtime()
        if not (report.weasyprint and report.cairo and report.pango and report.gdk_pixbuf):
            logger.warning(
                "WeasyPrint stack incomplete — will try browser engines | report=%s",
                report
            )
        else:
            logger.debug("WeasyPrint stack OK")
    except Exception as e:
        logger.debug("PDF runtime healthcheck skipped: %s", e)

    # -------------------------------------------------------------------------
    # Fetch real transaction_no from DB
    SessionLocal = get_session_local()
    s = SessionLocal()
    try:
        row = s.execute(
            text(
                "SELECT COALESCE(transaction_no, CAST(id AS TEXT)) "
                "FROM transactions WHERE id=:i"
            ),
            {"i": int(transaction_id)},
        ).fetchone()

        if not row or not row[0]:
            logger.error("Transaction not found | tx_id=%s", transaction_id)
            raise RuntimeError(f"Transaction id={transaction_id} not found")

        transaction_no = str(row[0])
        logger.debug("Resolved transaction_no=%s", transaction_no)
    finally:
        s.close()

    # -------------------------------------------------------------------------
    # Resolve builder
    try:
        builder = get_builder(doc_code)
        logger.debug("Builder resolved for doc_code=%s", doc_code)
    except Exception:
        logger.exception("Failed to resolve builder | doc_code=%s", doc_code)
        raise

    # -------------------------------------------------------------------------
    # Build context
    try:
        try:
            ctx = builder(doc_code, transaction_id, lang)
        except TypeError:
            ctx = builder(transaction_id, lang)

        if not isinstance(ctx, dict):
            raise TypeError("Builder must return dict context")

        logger.debug(
            "Context built | keys=%s",
            ", ".join(sorted(ctx.keys()))
        )
    except Exception:
        logger.exception(
            "Failed to build document context | tx_id=%s doc_code=%s",
            transaction_id, doc_code
        )
        raise

    # -------------------------------------------------------------------------
    # اختيار بادئة المستند حسب نوعه
    from services.numbering_service import NumberingService as _NS
    _doc_prefix = _NS.prefix_for_doc_code(doc_code)

    # doc_no = البادئة + رقم المعاملة (يُستخدم كمعرّف في doc_groups وعمود رقم المستند)
    if explicit_doc_no and explicit_doc_no.strip():
        doc_no = explicit_doc_no.strip()
        logger.info("Using explicit doc_no=%s", doc_no)
    else:
        doc_no = f"{_doc_prefix}-{transaction_no}"
        logger.info("Allocated doc_no=%s", doc_no)

    # Inject context
    ctx["transaction_no"] = transaction_no
    ctx["doc_no"] = doc_no
    ctx.setdefault("invoice_no", doc_no)

    # -------------------------------------------------------------------------
    # Render HTML
    try:
        html_str = render_html(doc_code, lang, ctx)
        logger.debug("HTML rendered successfully")
    except Exception:
        logger.exception(
            "HTML rendering failed | doc_code=%s lang=%s",
            doc_code, lang
        )
        raise

    # -------------------------------------------------------------------------
    # Output paths
    out_html, out_pdf = _output_paths(_doc_prefix, transaction_no, lang)
    out_html.parent.mkdir(parents=True, exist_ok=True)

    out_html.write_text(html_str, encoding="utf-8")
    logger.info("HTML written | path=%s", out_html)

    # -------------------------------------------------------------------------
    # PDF generation
    pdf_path: Optional[Path] = None

    if not force_html_only:
        try:
            base_url = str(out_html.parent)
            prefer_engine = "playwright"

            ok, info = render_html_to_pdf(
                html=html_str,
                out_path=str(out_pdf),
                base_url=base_url,
                prefer=prefer_engine,
            )

            if ok:
                pdf_path = out_pdf
                logger.info("PDF generated | engine=%s path=%s", prefer_engine, out_pdf)
            else:
                logger.warning(
                    "PDF generation failed — HTML only | details=%s",
                    info
                )
        except Exception:
            logger.exception("PDF rendering crashed — keeping HTML only")

    # -------------------------------------------------------------------------
    # Persist document
    try:
        persist_document(
            transaction_id=transaction_id,
            doc_code=doc_code,
            lang=lang,
            file_path=str(pdf_path or out_html),
            totals=ctx.get("totals"),
            data=ctx,
            document_no=doc_no,
        )
        logger.info(
            "Document persisted | tx_id=%s doc_no=%s type=%s lang=%s",
            transaction_id, doc_no, doc_code, lang
        )
    except Exception:
        logger.exception(
            "Failed to persist document | tx_id=%s doc_no=%s",
            transaction_id, doc_no
        )
        raise

    logger.info(
        "Render document finished successfully | tx_id=%s doc_no=%s",
        transaction_id, doc_no
    )

    return RenderResult(
        doc_code=doc_code,
        lang=lang,
        doc_no=doc_no,
        out_html=out_html,
        out_pdf=pdf_path,
    )