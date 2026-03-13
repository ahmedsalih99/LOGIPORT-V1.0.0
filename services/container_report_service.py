"""
container_report_service.py — LOGIPORT
========================================
يولّد تقارير PDF لتتبع الكونتينرات:
  - بطاقة كونتينر واحد  (card)
  - قائمة كونتينرات     (list / landscape)

الاستخدام:
    from services.container_report_service import ContainerReportService
    svc = ContainerReportService()

    # بطاقة كونتينر
    ok, path, err = svc.render_card(container, lang="ar")

    # قائمة كونتينرات
    ok, path, err = svc.render_list(containers, lang="ar", filters="حالة: جارٍ")
"""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_STATUS_COLOR = {
    "booked":     "#6366F1",
    "loaded":     "#0891B2",
    "in_transit": "#2563EB",
    "arrived":    "#7C3AED",
    "customs":    "#D97706",
    "delivered":  "#059669",
    "hold":       "#DC2626",
}

_TEMPLATES_DIR = Path(__file__).parent.parent / "documents" / "templates" / "container"


class ContainerReportService:

    def render_card(
        self,
        container,
        lang: str = "ar",
        out_path: Optional[str] = None,
    ) -> tuple[bool, str, str]:
        try:
            html = self._build_card_html(container, lang)
            return self._render(html, out_path, prefix=f"container_{_get(container,'container_no','card')}_")
        except Exception as e:
            logger.error("ContainerReportService.render_card: %s", e, exc_info=True)
            return False, "", str(e)

    def render_list(
        self,
        containers: list,
        lang: str = "ar",
        filters: str = "",
        out_path: Optional[str] = None,
    ) -> tuple[bool, str, str]:
        try:
            html = self._build_list_html(containers, lang, filters)
            return self._render(html, out_path, prefix="containers_list_")
        except Exception as e:
            logger.error("ContainerReportService.render_list: %s", e, exc_info=True)
            return False, "", str(e)

    # ── بناء HTML للبطاقة ─────────────────────────────────────────────────────

    def _build_card_html(self, container, lang: str) -> str:
        """يحاول Jinja2 أولاً، ويبني HTML مدمجاً كاحتياط."""
        template_path = _TEMPLATES_DIR / "card"
        tpl_file = template_path / f"{lang}.html"

        status = _get(container, "status") or "booked"
        client = _get(container, "client")
        tx     = _get(container, "transaction")

        client_name = _extract_name(client, lang)
        transaction_no = ""
        if tx:
            transaction_no = getattr(tx, "transaction_no", None) or str(_get(container, "transaction_id") or "")

        entries = getattr(container, "entries", None) or []
        entries_data = []
        for e in entries:
            e_client = getattr(e, "owner_client", None)
            entries_data.append({
                "id":          _get(e, "id"),
                "entry_no":    _get(e, "entry_no") or "",
                "entry_date":  str(_get(e, "entry_date") or ""),
                "client_name": _extract_name(e_client, lang),
                "items_count": len(getattr(e, "items", None) or []),
            })

        ctx = {
            "container":      _container_to_dict(container),
            "status_color":   _STATUS_COLOR.get(status, "#888"),
            "status_label":   self._status_label(status, lang),
            "client_name":    client_name,
            "transaction_no": transaction_no,
            "entries":        entries_data,
            "print_date":     date.today().strftime("%Y-%m-%d"),
            "company_name":   self._company_name(),
            "lang":           lang,
        }

        if tpl_file.exists():
            try:
                from jinja2 import Environment, FileSystemLoader, select_autoescape
                env = Environment(
                    loader=FileSystemLoader(str(template_path)),
                    autoescape=select_autoescape(["html"]),
                )
                return env.get_template(f"{lang}.html").render(**ctx)
            except Exception as exc:
                logger.warning("card template failed (%s), falling back to inline HTML", exc)

        return self._inline_card_html(ctx, lang)

    # ── بناء HTML للقائمة ─────────────────────────────────────────────────────

    def _build_list_html(self, containers: list, lang: str, filters: str) -> str:
        """
        يبني HTML القائمة مباشرة بدون Jinja2 لضمان التوافق.
        يُحاول استخدام الـ template الخارجي إن وُجد وكان سليماً.
        """
        rows = []
        status_counts: dict[str, int] = {}
        for c in containers:
            status = _get(c, "status") or "booked"
            status_counts[status] = status_counts.get(status, 0) + 1
            client = _get(c, "client")
            client_name = _extract_name(client, lang)
            entries = getattr(c, "entries", None) or []
            raw = _container_to_dict(c)
            eta_state = _calc_eta_state(_get(c, "eta"), status)
            row = {
                **raw,
                "client_name":   client_name,
                "entries_count": len(entries),
                "status_color":  _STATUS_COLOR.get(status, "#888"),
                "status_label":  self._status_label(status, lang),
                "eta_state":     eta_state,
                # nested للـ templates التي تستخدم {{ container.xxx }}
                "container":     {**raw, "client_name": client_name, "eta_state": eta_state},
            }
            rows.append(row)

        status_summary = [
            {
                "label": self._status_label(s, lang),
                "color": _STATUS_COLOR.get(s, "#888"),
                "count": cnt,
            }
            for s, cnt in status_counts.items()
        ]

        ctx = {
            "containers":     rows,
            "status_summary": status_summary,
            "filters":        filters,
            "print_date":     date.today().strftime("%Y-%m-%d"),
            "company_name":   self._company_name(),
            "lang":           lang,
        }

        # حاول الـ template الخارجي أولاً
        template_path = _TEMPLATES_DIR / "list"
        tpl_file = template_path / f"{lang}.html"
        if tpl_file.exists():
            try:
                from jinja2 import Environment, FileSystemLoader, select_autoescape
                env = Environment(
                    loader=FileSystemLoader(str(template_path)),
                    autoescape=select_autoescape(["html"]),
                )
                result = env.get_template(f"{lang}.html").render(**ctx)
                return result
            except Exception as exc:
                logger.warning(
                    "list template '%s' failed (%s) — falling back to inline HTML",
                    tpl_file, exc,
                )

        # ── Inline HTML كاحتياط كامل ──────────────────────────────────────
        return self._inline_list_html(rows, status_summary, filters, ctx["print_date"], ctx["company_name"], lang)

    # ── Inline HTML — القائمة ─────────────────────────────────────────────────

    def _inline_list_html(
        self,
        rows: list,
        status_summary: list,
        filters: str,
        print_date: str,
        company_name: str,
        lang: str,
    ) -> str:
        is_ar = lang == "ar"
        dir_  = "rtl" if is_ar else "ltr"
        title = {"ar": "قائمة الكونتينرات", "en": "Container List", "tr": "Konteyner Listesi"}.get(lang, "Container List")
        total_lbl = {"ar": "الإجمالي", "en": "Total", "tr": "Toplam"}.get(lang, "Total")
        no_data   = {"ar": "لا توجد بيانات", "en": "No data", "tr": "Veri yok"}.get(lang, "No data")
        filter_lbl= {"ar": "الفلتر", "en": "Filter", "tr": "Filtre"}.get(lang, "Filter")
        footer    = {"ar": "LOGIPORT — تقرير آلي", "en": "LOGIPORT — Auto Report", "tr": "LOGIPORT — Otomatik Rapor"}.get(lang, "LOGIPORT")

        headers = {
            "ar": ["رقم الكونتينر","رقم BL","الزبون","شركة الشحن","الباخرة","م.التحميل","م.التفريغ","ETD","ETA","ATA","إدخالات","الحالة"],
            "en": ["Container No","BL No","Client","Shipping Line","Vessel","POL","POD","ETD","ETA","ATA","Entries","Status"],
            "tr": ["Konteyner No","Konşimento No","Müşteri","Nakliye Şirketi","Gemi","Yükleme Limanı","Tahliye Limanı","ETD","ETA","ATA","Girişler","Durum"],
        }.get(lang, ["Container No","BL No","Client","Shipping Line","Vessel","POL","POD","ETD","ETA","ATA","Entries","Status"])

        # badges الحالات
        badges_html = ""
        for s in status_summary:
            badges_html += (
                f'<span class="badge" style="color:{s["color"]};border-color:{s["color"]}">'
                f'{s["label"]}: {s["count"]}</span>'
            )

        # رأس الجدول
        th_html = "".join(f"<th>{h}</th>" for h in headers)

        # صفوف الجدول
        td_rows = ""
        for r in rows:
            eta_cls = ""
            if r.get("eta_state") == "overdue":
                eta_cls = 'style="color:#dc2626;font-weight:700"'
            elif r.get("eta_state") == "today":
                eta_cls = 'style="color:#d97706;font-weight:700"'

            td_rows += f"""<tr>
<td style="font-family:monospace;font-weight:700;color:#1a56db">{r.get('container_no') or '—'}</td>
<td style="font-family:monospace">{r.get('bl_number') or '—'}</td>
<td>{r.get('client_name') or '—'}</td>
<td>{r.get('shipping_line') or '—'}</td>
<td>{r.get('vessel_name') or '—'}</td>
<td>{r.get('port_of_loading') or '—'}</td>
<td>{r.get('port_of_discharge') or '—'}</td>
<td>{r.get('etd') or '—'}</td>
<td {eta_cls}>{r.get('eta') or '—'}</td>
<td>{r.get('ata') or '—'}</td>
<td style="text-align:center">{r.get('entries_count', 0)}</td>
<td style="text-align:center">
  <span style="background:{r['status_color']};color:#fff;padding:2pt 7pt;border-radius:10pt;font-size:8pt;font-weight:600">
    {r['status_label']}
  </span>
</td>
</tr>"""

        if not td_rows:
            td_rows = f'<tr><td colspan="12" style="text-align:center;color:#888;padding:14pt">{no_data}</td></tr>'

        filter_section = f'<div class="filters">{filter_lbl}: {filters}</div>' if filters else ""
        company_section = f'<div class="company-name">{company_name}</div>' if company_name else ""
        summary_section = f'<div class="summary">{badges_html}</div>' if badges_html else ""

        return f"""<!doctype html>
<html lang="{lang}" dir="{dir_}">
<head>
<meta charset="utf-8"/>
<title>{title}</title>
<style>
@page {{size:A4 landscape;margin:12mm 14mm;}}
html{{color:#000;background:#fff;}}
body{{font:10pt/1.5 "Noto Naskh Arabic","Amiri","Segoe UI",Tahoma,Arial,sans-serif;}}
.page-header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10pt;border-bottom:2pt solid #1e3a5f;padding-bottom:8pt;}}
.page-title{{font-size:16pt;font-weight:700;color:#1e3a5f;margin:0;}}
.page-meta{{font-size:9pt;color:#555;}}
.company-name{{font-size:12pt;font-weight:700;color:#1e3a5f;}}
.summary{{display:flex;gap:8pt;margin-bottom:8pt;flex-wrap:wrap;}}
.badge{{display:inline-flex;align-items:center;gap:4pt;padding:3pt 9pt;border-radius:20pt;font-size:9pt;font-weight:600;border:1pt solid currentColor;}}
.filters{{font-size:9pt;color:#666;margin-bottom:6pt;}}
table{{width:100%;border-collapse:collapse;font-size:9pt;}}
thead th{{background:#1e3a5f;color:#fff;padding:5pt;text-align:right;font-weight:600;font-size:8.5pt;border-left:0.5pt solid rgba(255,255,255,0.2);}}
tbody tr:nth-child(even){{background:#f5f7fa;}}
tbody td{{padding:4pt 5pt;vertical-align:middle;border-bottom:0.5pt solid #ddd;border-left:0.5pt solid #eee;text-align:right;}}
tfoot td{{padding:5pt;font-weight:700;border-top:1.5pt solid #1e3a5f;background:#f0f4fa;text-align:right;}}
.page-footer{{margin-top:10pt;font-size:8pt;color:#888;display:flex;justify-content:space-between;border-top:0.5pt solid #ccc;padding-top:5pt;}}
</style>
</head>
<body>
<div class="page-header">
  <div>
    {company_section}
    <h1 class="page-title">{title}</h1>
    {filter_section}
  </div>
  <div class="page-meta">
    <div>{print_date}</div>
    <div>{total_lbl}: {len(rows)}</div>
  </div>
</div>
{summary_section}
<table>
<thead><tr>{th_html}</tr></thead>
<tbody>{td_rows}</tbody>
<tfoot><tr>
  <td colspan="10">{total_lbl}</td>
  <td style="text-align:center">{len(rows)}</td>
  <td></td>
</tr></tfoot>
</table>
<div class="page-footer"><span>{footer}</span><span>{print_date}</span></div>
</body>
</html>"""

    # ── Inline HTML — البطاقة ─────────────────────────────────────────────────

    def _inline_card_html(self, ctx: dict, lang: str) -> str:
        c = ctx["container"]
        dir_ = "rtl" if lang == "ar" else "ltr"
        title = {"ar": "بطاقة كونتينر", "en": "Container Card", "tr": "Konteyner Kartı"}.get(lang, "Container Card")
        return f"""<!doctype html>
<html lang="{lang}" dir="{dir_}">
<head><meta charset="utf-8"/><title>{title}</title>
<style>
@page{{size:A4;margin:18mm;}}
body{{font:12pt/1.6 "Noto Naskh Arabic","Segoe UI",Arial,sans-serif;}}
.title{{font-size:18pt;font-weight:700;color:#1e3a5f;margin-bottom:8pt;}}
.badge{{display:inline-block;padding:3pt 12pt;border-radius:20pt;color:#fff;font-weight:700;font-size:11pt;}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10pt;margin-top:12pt;}}
.box{{border:.5pt solid #ccc;padding:10pt;border-radius:4pt;}}
.kv{{display:grid;grid-template-columns:130px 1fr;gap:4pt 8pt;}}
.label{{font-weight:700;color:#555;font-size:10pt;}}
.val{{font-family:monospace;font-size:11pt;}}
</style>
</head>
<body>
<div class="title">{title}</div>
<span class="badge" style="background:{ctx['status_color']}">{ctx['status_label']}</span>
<div class="grid">
  <div class="box kv">
    <span class="label">Container No</span><span class="val">{c.get('container_no','')}</span>
    <span class="label">BL No</span><span class="val">{c.get('bl_number','') or '—'}</span>
    <span class="label">Booking No</span><span class="val">{c.get('booking_no','') or '—'}</span>
    <span class="label">Shipping Line</span><span class="val">{c.get('shipping_line','') or '—'}</span>
    <span class="label">Vessel</span><span class="val">{c.get('vessel_name','') or '—'}</span>
    <span class="label">Voyage</span><span class="val">{c.get('voyage_no','') or '—'}</span>
  </div>
  <div class="box kv">
    <span class="label">Client</span><span class="val">{ctx.get('client_name','') or '—'}</span>
    <span class="label">Transaction</span><span class="val">{ctx.get('transaction_no','') or '—'}</span>
    <span class="label">POL</span><span class="val">{c.get('port_of_loading','') or '—'}</span>
    <span class="label">POD</span><span class="val">{c.get('port_of_discharge','') or '—'}</span>
    <span class="label">ETD</span><span class="val">{c.get('etd','') or '—'}</span>
    <span class="label">ETA</span><span class="val">{c.get('eta','') or '—'}</span>
  </div>
</div>
<p style="font-size:8pt;color:#888;margin-top:20pt">{ctx['print_date']}</p>
</body>
</html>"""

    # ── ترجمة الحالة ─────────────────────────────────────────────────────────

    def _status_label(self, status: str, lang: str) -> str:
        _labels = {
            "booked":     {"ar": "محجوز",      "en": "Booked",      "tr": "Rezerve"},
            "loaded":     {"ar": "محمّل",       "en": "Loaded",      "tr": "Yüklendi"},
            "in_transit": {"ar": "في الطريق",   "en": "In Transit",  "tr": "Yolda"},
            "arrived":    {"ar": "وصل",         "en": "Arrived",     "tr": "Vardı"},
            "customs":    {"ar": "جمارك",       "en": "Customs",     "tr": "Gümrük"},
            "delivered":  {"ar": "تم التسليم",  "en": "Delivered",   "tr": "Teslim Edildi"},
            "hold":       {"ar": "محتجز",       "en": "On Hold",     "tr": "Beklemede"},
        }
        return _labels.get(status, {}).get(lang, status)

    # ── اسم الشركة ───────────────────────────────────────────────────────────

    def _company_name(self) -> str:
        try:
            from core.settings_manager import SettingsManager
            return SettingsManager.get_instance().get("company_name", "") or ""
        except Exception:
            return ""

    # ── render PDF ───────────────────────────────────────────────────────────

    def _render(
        self,
        html: str,
        out_path: Optional[str],
        prefix: str = "container_",
    ) -> tuple[bool, str, str]:
        if not out_path:
            tmp_dir = tempfile.gettempdir()
            out_path = os.path.join(
                tmp_dir,
                f"{prefix}{date.today().strftime('%Y%m%d')}.pdf",
            )

        from services.pdf_renderer import render_html_to_pdf
        ok, info = render_html_to_pdf(html, out_path)
        if ok:
            return True, out_path, ""
        return False, "", info.get("error", "PDF render failed")


# ── helpers ───────────────────────────────────────────────────────────────────

def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _extract_name(obj, lang: str) -> str:
    if not obj:
        return ""
    if lang == "ar":
        return getattr(obj, "name_ar", None) or getattr(obj, "name_en", None) or ""
    elif lang == "tr":
        return getattr(obj, "name_tr", None) or getattr(obj, "name_ar", None) or ""
    return getattr(obj, "name_en", None) or getattr(obj, "name_ar", None) or ""


def _calc_eta_state(eta, status: str) -> str:
    _ACTIVE = {"booked", "loaded", "in_transit", "arrived", "customs"}
    if not eta or status not in _ACTIVE:
        return ""
    from datetime import date as _d
    today = _d.today()
    try:
        delta = (eta - today).days
    except Exception:
        return ""
    if delta < 0:
        return "overdue"
    if delta == 0:
        return "today"
    if delta <= 3:
        return "soon"
    return ""


def _container_to_dict(c) -> dict:
    def _s(attr):
        val = _get(c, attr)
        return str(val) if val else ""

    return {
        "container_no":      _s("container_no"),
        "bl_number":         _s("bl_number"),
        "booking_no":        _s("booking_no"),
        "shipping_line":     _s("shipping_line"),
        "vessel_name":       _s("vessel_name"),
        "voyage_no":         _s("voyage_no"),
        "port_of_loading":   _s("port_of_loading"),
        "port_of_discharge": _s("port_of_discharge"),
        "final_destination": _s("final_destination"),
        "etd":               _s("etd"),
        "eta":               _s("eta"),
        "atd":               _s("atd"),
        "ata":               _s("ata"),
        "customs_date":      _s("customs_date"),
        "delivery_date":     _s("delivery_date"),
        "status":            _s("status"),
        "notes":             _s("notes"),
    }