"""
container_report_service.py — LOGIPORT
========================================
يولّد تقارير PDF لتتبع الكونتينرات:
  - بطاقة كونتينر واحد  (card)
  - قائمة كونتينرات     (list / landscape)

الحقول الفعلية في الموديل:
  bl_number, shipping_line, cargo_type, quantity, origin_country,
  port_of_discharge, containers_count, docs_delivered, cargo_tracking,
  docs_received_date, bl_status, eta, status, notes,
  client_id→client, transaction_id→transaction, office_id→office
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
    "in_transit": "#2563EB",
    "arrived":    "#7C3AED",
    "customs":    "#D97706",
    "delivered":  "#059669",
    "hold":       "#DC2626",
}

_ACTIVE_STATUSES = {"booked", "in_transit", "arrived", "customs"}
_TEMPLATES_DIR   = Path(__file__).parent.parent / "documents" / "templates" / "container"


class ContainerReportService:

    # ── public API ────────────────────────────────────────────────────────────

    def render_card(self, container, lang: str = "ar",
                    out_path: Optional[str] = None) -> tuple[bool, str, str]:
        try:
            html = self._build_card_html(container, lang)
            return self._render(html, out_path,
                                prefix=f"container_{_get(container,'bl_number','card')}_")
        except Exception as e:
            logger.error("render_card: %s", e, exc_info=True)
            return False, "", str(e)

    def render_list(self, containers: list, lang: str = "ar",
                    filters: str = "",
                    out_path: Optional[str] = None) -> tuple[bool, str, str]:
        try:
            html = self._build_list_html(containers, lang, filters)
            return self._render(html, out_path, prefix="containers_list_")
        except Exception as e:
            logger.error("render_list: %s", e, exc_info=True)
            return False, "", str(e)

    # ── بناء context مشترك ────────────────────────────────────────────────────

    def _build_ctx(self, c, lang: str) -> dict:
        """يحوّل ORM/dict → dict جاهز للـ template، بناءً على الحقول الفعلية."""
        status       = _get(c, "status") or "booked"
        status_color = _STATUS_COLOR.get(status, "#888")
        status_label = self._status_label(status, lang)
        eta_state    = _calc_eta_state(_get(c, "eta"), status)

        # اسم العميل من pre-loaded أو relationship
        if hasattr(c, "_client_name_ar"):
            if lang == "ar":
                client_name = getattr(c, "_client_name_ar", "") or getattr(c, "_client_name_en", "")
            elif lang == "tr":
                client_name = getattr(c, "_client_name_tr", "") or getattr(c, "_client_name_ar", "")
            else:
                client_name = getattr(c, "_client_name_en", "") or getattr(c, "_client_name_ar", "")
        else:
            client = _get(c, "client")
            client_name = _extract_name(client, lang) if client else ""

        # رقم المعاملة
        transaction_no = ""
        tx = _get(c, "transaction")
        if tx:
            transaction_no = getattr(tx, "transaction_no", None) or str(_get(c, "transaction_id") or "")

        # تاريخ استلام الأوراق
        docs_date = _get(c, "docs_received_date")
        docs_date_str = str(docs_date) if docs_date else ""

        # أنواع بضاعة الشحنة (من shipment_containers)
        containers_list = []
        try:
            containers_rel = getattr(c, "containers", None) or []
            for sc in containers_rel:
                containers_list.append({
                    "container_no": getattr(sc, "container_no", "") or "",
                    "seal_no":      getattr(sc, "seal_no",      "") or "",
                    "recipient":    getattr(sc, "recipient",     "") or "",
                })
        except Exception:
            pass

        return {
            "id":                 _get(c, "id") or "",
            "bl_number":          _s(c, "bl_number"),
            "shipping_line":      _s(c, "shipping_line"),
            "cargo_type":         _s(c, "cargo_type"),
            "quantity":           _s(c, "quantity"),
            "origin_country":     _s(c, "origin_country"),
            "port_of_discharge":  _s(c, "port_of_discharge"),
            "containers_count":   str(_get(c, "containers_count") or ""),
            "docs_delivered":     bool(_get(c, "docs_delivered", False)),
            "cargo_tracking":     _s(c, "cargo_tracking"),
            "docs_received_date": docs_date_str,
            "bl_status":          _s(c, "bl_status"),
            "eta":                _s(c, "eta"),
            "notes":              _s(c, "notes"),
            "status":             status,
            "status_color":       status_color,
            "status_label":       status_label,
            "eta_state":          eta_state,
            "client_name":        client_name,
            "transaction_no":     transaction_no,
            "shipment_containers": containers_list,
        }

    # ── بناء HTML البطاقة ─────────────────────────────────────────────────────

    def _build_card_html(self, container, lang: str) -> str:
        ctx_item = self._build_ctx(container, lang)
        ctx = {
            "container":      ctx_item,
            "containers":     [ctx_item],
            "status_summary": [{"label": ctx_item["status_label"],
                                "color": ctx_item["status_color"], "count": 1}],
            "filters":        "",
            "print_date":     date.today().strftime("%Y-%m-%d"),
            "company_name":   self._company_name(),
            "lang":           lang,
        }
        tpl_dir  = _TEMPLATES_DIR / "card"
        tpl_file = tpl_dir / f"{lang}.html"
        if tpl_file.exists():
            try:
                from jinja2 import Environment, FileSystemLoader, select_autoescape
                env = Environment(loader=FileSystemLoader(str(tpl_dir)),
                                  autoescape=select_autoescape(["html"]))
                return env.get_template(f"{lang}.html").render(**ctx)
            except Exception as exc:
                logger.warning("card template failed: %s", exc)
        return self._inline_card_html(ctx, lang)

    # ── بناء HTML القائمة ─────────────────────────────────────────────────────

    def _build_list_html(self, containers: list, lang: str, filters: str) -> str:
        rows = []
        status_counts: dict[str, int] = {}
        for c in containers:
            ctx_item = self._build_ctx(c, lang)
            status = ctx_item["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
            rows.append(ctx_item)

        status_summary = [
            {"label": self._status_label(s, lang),
             "color": _STATUS_COLOR.get(s, "#888"),
             "count": cnt}
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
        tpl_dir  = _TEMPLATES_DIR / "list"
        tpl_file = tpl_dir / f"{lang}.html"
        if tpl_file.exists():
            try:
                from jinja2 import Environment, FileSystemLoader, select_autoescape
                env = Environment(loader=FileSystemLoader(str(tpl_dir)),
                                  autoescape=select_autoescape(["html"]))
                return env.get_template(f"{lang}.html").render(**ctx)
            except Exception as exc:
                logger.warning("list template failed: %s", exc)
        return self._inline_list_html(rows, status_summary, filters,
                                      ctx["print_date"], ctx["company_name"], lang)

    # ── Inline HTML — القائمة ─────────────────────────────────────────────────

    def _inline_list_html(self, rows, status_summary, filters,
                          print_date, company_name, lang) -> str:
        is_ar = lang == "ar"
        dir_  = "rtl" if is_ar else "ltr"
        L = {
            "title":      {"ar": "قائمة تتبع البوليصات",   "en": "BL Tracking List",    "tr": "Konşimento Takip Listesi"},
            "total":      {"ar": "الإجمالي",                "en": "Total",               "tr": "Toplam"},
            "no_data":    {"ar": "لا توجد بيانات",          "en": "No data",             "tr": "Veri yok"},
            "filter":     {"ar": "الفلتر",                  "en": "Filter",              "tr": "Filtre"},
            "footer":     {"ar": "LOGIPORT — تقرير آلي",    "en": "LOGIPORT — Auto Report", "tr": "LOGIPORT — Otomatik Rapor"},
            "yes":        {"ar": "نعم",                     "en": "Yes",                 "tr": "Evet"},
            "no":         {"ar": "لا",                      "en": "No",                  "tr": "Hayır"},
        }
        def t(k): return L[k].get(lang, L[k]["en"])

        headers = {
            "ar": ["رقم البوليصة","شركة الشحن","العميل","نوع البضاعة","العدد","الدولة المرسلة",
                   "ميناء الوصول","عدد الكونتينرات","الأوراق","تاريخ الأوراق","حالة البوليصة","ETA","الحالة"],
            "en": ["BL No","Shipping Line","Client","Cargo Type","Qty","Origin",
                   "POD","Containers","Docs","Docs Date","BL Status","ETA","Status"],
            "tr": ["Konşimento No","Nakliye Şirketi","Müşteri","Kargo Türü","Miktar","Köken",
                   "Liman","Konteyner","Belgeler","Belge Tarihi","Konşimento Durumu","ETA","Durum"],
        }.get(lang, [])

        badges_html = "".join(
            f'<span class="badge" style="color:{s["color"]};border-color:{s["color"]}">'
            f'{s["label"]}: {s["count"]}</span>'
            for s in status_summary
        )
        th_html  = "".join(f"<th>{h}</th>" for h in headers)
        td_rows  = ""
        for r in rows:
            eta_style = ""
            if r.get("eta_state") == "overdue":
                eta_style = 'style="color:#dc2626;font-weight:700"'
            elif r.get("eta_state") == "today":
                eta_style = 'style="color:#d97706;font-weight:700"'
            docs_val = t("yes") if r.get("docs_delivered") else "—"
            td_rows += f"""<tr>
<td style="font-family:monospace;color:#1a56db;font-weight:700">{r.get("bl_number") or "—"}</td>
<td>{r.get("shipping_line") or "—"}</td>
<td>{r.get("client_name") or "—"}</td>
<td>{r.get("cargo_type") or "—"}</td>
<td style="text-align:center">{r.get("quantity") or "—"}</td>
<td>{r.get("origin_country") or "—"}</td>
<td>{r.get("port_of_discharge") or "—"}</td>
<td style="text-align:center">{r.get("containers_count") or "—"}</td>
<td style="text-align:center">{docs_val}</td>
<td>{r.get("docs_received_date") or "—"}</td>
<td>{r.get("bl_status") or "—"}</td>
<td {eta_style}>{r.get("eta") or "—"}</td>
<td style="text-align:center">
  <span style="background:{r["status_color"]};color:#fff;padding:2pt 7pt;border-radius:10pt;font-size:8pt;font-weight:600">
    {r["status_label"]}
  </span>
</td>
</tr>"""
        if not td_rows:
            td_rows = f'<tr><td colspan="13" style="text-align:center;color:#888;padding:14pt">{t("no_data")}</td></tr>'

        company_sec = f'<div class="company-name">{company_name}</div>' if company_name else ""
        filter_sec  = f'<div class="filters">{t("filter")}: {filters}</div>' if filters else ""
        summary_sec = f'<div class="summary">{badges_html}</div>' if badges_html else ""
        col_count   = len(headers)

        return f"""<!doctype html>
<html lang="{lang}" dir="{dir_}">
<head><meta charset="utf-8"/><title>{t("title")}</title>
<style>
@page {{size:A4 landscape;margin:10mm 12mm;}}
html{{color:#000;background:#fff;}}
body{{font:9pt/1.4 "Noto Naskh Arabic","Amiri","Segoe UI",Tahoma,Arial,sans-serif;}}
.page-header{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8pt;border-bottom:2pt solid #1e3a5f;padding-bottom:6pt;}}
.page-title{{font-size:14pt;font-weight:700;color:#1e3a5f;margin:0;}}
.page-meta{{font-size:8pt;color:#555;}}
.company-name{{font-size:11pt;font-weight:700;color:#1e3a5f;}}
.summary{{display:flex;gap:6pt;margin-bottom:6pt;flex-wrap:wrap;}}
.badge{{display:inline-flex;align-items:center;gap:3pt;padding:2pt 8pt;border-radius:20pt;font-size:8pt;font-weight:600;border:1pt solid currentColor;}}
.filters{{font-size:8pt;color:#666;margin-bottom:5pt;}}
table{{width:100%;border-collapse:collapse;font-size:8pt;}}
thead th{{background:#1e3a5f;color:#fff;padding:4pt 4pt;text-align:right;font-weight:600;font-size:7.5pt;border-left:0.5pt solid rgba(255,255,255,0.2);}}
tbody tr:nth-child(even){{background:#f5f7fa;}}
tbody td{{padding:3pt 4pt;vertical-align:middle;border-bottom:0.5pt solid #ddd;border-left:0.5pt solid #eee;text-align:right;}}
tfoot td{{padding:4pt;font-weight:700;border-top:1.5pt solid #1e3a5f;background:#f0f4fa;}}
.page-footer{{margin-top:8pt;font-size:7pt;color:#888;display:flex;justify-content:space-between;border-top:0.5pt solid #ccc;padding-top:4pt;}}
</style></head>
<body>
<div class="page-header">
  <div>{company_sec}<h1 class="page-title">{t("title")}</h1>{filter_sec}</div>
  <div class="page-meta"><div>{print_date}</div><div>{t("total")}: {len(rows)}</div></div>
</div>
{summary_sec}
<table>
<thead><tr>{th_html}</tr></thead>
<tbody>{td_rows}</tbody>
<tfoot><tr><td colspan="{col_count - 1}">{t("total")}</td><td style="text-align:center">{len(rows)}</td></tr></tfoot>
</table>
<div class="page-footer"><span>{t("footer")}</span><span>{print_date}</span></div>
</body></html>"""

    # ── Inline HTML — البطاقة ─────────────────────────────────────────────────

    def _inline_card_html(self, ctx: dict, lang: str) -> str:
        c    = ctx["container"]
        dir_ = "rtl" if lang == "ar" else "ltr"
        L = {
            "title":  {"ar": "بطاقة تتبع بوليصة شحن", "en": "BL Tracking Card",    "tr": "Konşimento Takip Kartı"},
            "yes":    {"ar": "نعم ✅",                 "en": "Yes ✅",              "tr": "Evet ✅"},
            "no":     {"ar": "—",                      "en": "—",                   "tr": "—"},
            "footer": {"ar": "LOGIPORT — تقرير آلي",   "en": "LOGIPORT — Auto Report", "tr": "LOGIPORT — Otomatik Rapor"},
        }
        def t(k): return L[k].get(lang, L[k]["en"])

        fields = {
            "ar": [
                ("رقم البوليصة (BL)",   c.get("bl_number")),
                ("شركة الشحن",           c.get("shipping_line")),
                ("العميل / صاحب البضاعة",c.get("client_name")),
                ("رقم المعاملة",         c.get("transaction_no")),
                ("نوع البضاعة",          c.get("cargo_type")),
                ("العدد / الكمية",       c.get("quantity")),
                ("الدولة المرسلة",       c.get("origin_country")),
                ("ميناء الوصول",         c.get("port_of_discharge")),
                ("عدد الكونتينرات",      c.get("containers_count")),
                ("تسليم الأوراق",        t("yes") if c.get("docs_delivered") else t("no")),
                ("تاريخ استلام الأوراق", c.get("docs_received_date")),
                ("حالة البوليصة",        c.get("bl_status")),
                ("ETA",                  c.get("eta")),
                ("ملاحظات",              c.get("notes")),
            ],
            "en": [
                ("BL Number",            c.get("bl_number")),
                ("Shipping Line",        c.get("shipping_line")),
                ("Client",               c.get("client_name")),
                ("Transaction No",       c.get("transaction_no")),
                ("Cargo Type",           c.get("cargo_type")),
                ("Quantity",             c.get("quantity")),
                ("Origin Country",       c.get("origin_country")),
                ("Port of Discharge",    c.get("port_of_discharge")),
                ("Containers Count",     c.get("containers_count")),
                ("Docs Delivered",       t("yes") if c.get("docs_delivered") else t("no")),
                ("Docs Received Date",   c.get("docs_received_date")),
                ("BL Status",            c.get("bl_status")),
                ("ETA",                  c.get("eta")),
                ("Notes",                c.get("notes")),
            ],
            "tr": [
                ("Konşimento No",        c.get("bl_number")),
                ("Nakliye Şirketi",      c.get("shipping_line")),
                ("Müşteri",              c.get("client_name")),
                ("İşlem No",             c.get("transaction_no")),
                ("Kargo Türü",           c.get("cargo_type")),
                ("Miktar",               c.get("quantity")),
                ("Köken Ülke",           c.get("origin_country")),
                ("Tahliye Limanı",       c.get("port_of_discharge")),
                ("Konteyner Sayısı",     c.get("containers_count")),
                ("Belgeler Teslim",      t("yes") if c.get("docs_delivered") else t("no")),
                ("Belge Alım Tarihi",    c.get("docs_received_date")),
                ("Konşimento Durumu",    c.get("bl_status")),
                ("ETA",                  c.get("eta")),
                ("Notlar",               c.get("notes")),
            ],
        }.get(lang, [])

        rows_html = "".join(
            f'<tr><td class="label">{label}</td><td class="val">{val or "—"}</td></tr>'
            for label, val in fields
        )

        # جدول الكونتينرات (shipment_containers)
        sc_list = c.get("shipment_containers", [])
        sc_headers = {
            "ar": ["رقم الكونتينر", "رقم الختم", "المستلم"],
            "en": ["Container No",  "Seal No",    "Recipient"],
            "tr": ["Konteyner No",  "Mühür No",   "Alıcı"],
        }.get(lang, ["Container No", "Seal No", "Recipient"])
        sc_rows_html = ""
        for sc in sc_list:
            sc_rows_html += f"""<tr>
<td>{sc.get("container_no") or "—"}</td>
<td>{sc.get("seal_no") or "—"}</td>
<td>{sc.get("recipient") or "—"}</td>
</tr>"""
        sc_section = ""
        if sc_list:
            sc_th = "".join(f"<th>{h}</th>" for h in sc_headers)
            sc_section = f"""
<h3 style="color:#1e3a5f;font-size:11pt;margin-top:14pt;margin-bottom:6pt">
  {"الكونتينرات" if lang=="ar" else ("Containers" if lang=="en" else "Konteynерler")}
</h3>
<table><thead><tr>{sc_th}</tr></thead><tbody>{sc_rows_html}</tbody></table>"""

        # تتبع الكارجو
        cargo_tracking = c.get("cargo_tracking") or ""
        tracking_section = ""
        if cargo_tracking:
            tracking_label = {"ar": "تتبع الكارجو", "en": "Cargo Tracking", "tr": "Kargo Takibi"}.get(lang, "Cargo Tracking")
            tracking_section = f"""
<h3 style="color:#1e3a5f;font-size:11pt;margin-top:14pt;margin-bottom:6pt">{tracking_label}</h3>
<div style="white-space:pre-wrap;font-size:9pt;border:0.5pt solid #ddd;padding:8pt;border-radius:4pt;background:#f9fafb">
  {cargo_tracking}
</div>"""

        company_sec = f'<div style="font-size:12pt;font-weight:700;color:#1e3a5f;margin-bottom:4pt">{ctx["company_name"]}</div>' if ctx.get("company_name") else ""

        return f"""<!doctype html>
<html lang="{lang}" dir="{dir_}">
<head><meta charset="utf-8"/><title>{t("title")}</title>
<style>
@page {{size:A4;margin:15mm;}}
html{{color:#000;background:#fff;}}
body{{font:11pt/1.5 "Noto Naskh Arabic","Amiri","Segoe UI",Tahoma,Arial,sans-serif;}}
.header{{border-bottom:2pt solid #1e3a5f;padding-bottom:8pt;margin-bottom:12pt;display:flex;justify-content:space-between;align-items:flex-end;}}
.title{{font-size:16pt;font-weight:700;color:#1e3a5f;margin:0;}}
.badge{{display:inline-block;padding:3pt 12pt;border-radius:20pt;color:#fff;font-weight:700;font-size:11pt;}}
table{{width:100%;border-collapse:collapse;margin-top:8pt;}}
thead th{{background:#1e3a5f;color:#fff;padding:5pt;text-align:right;font-weight:600;border-left:0.5pt solid rgba(255,255,255,0.2);}}
tbody tr:nth-child(even){{background:#f5f7fa;}}
tbody td{{padding:5pt 8pt;border-bottom:0.5pt solid #ddd;vertical-align:middle;}}
.label{{font-weight:700;color:#374151;width:45%;}}
.val{{font-family:inherit;}}
.footer{{margin-top:14pt;font-size:8pt;color:#888;border-top:0.5pt solid #ccc;padding-top:5pt;display:flex;justify-content:space-between;}}
</style></head>
<body>
<div class="header">
  <div>
    {company_sec}
    <h1 class="title">{t("title")}</h1>
  </div>
  <div>
    <span class="badge" style="background:{c["status_color"]}">{c["status_label"]}</span>
    <div style="font-size:8pt;color:#888;margin-top:4pt">{ctx["print_date"]}</div>
  </div>
</div>
<table><tbody>{rows_html}</tbody></table>
{sc_section}
{tracking_section}
<div class="footer"><span>{t("footer")}</span><span>{ctx["print_date"]}</span></div>
</body></html>"""

    # ── helpers ───────────────────────────────────────────────────────────────

    def _status_label(self, status: str, lang: str) -> str:
        _labels = {
            "booked":     {"ar": "محجوز",      "en": "Booked",      "tr": "Rezerve"},
            "in_transit": {"ar": "في الطريق",  "en": "In Transit",  "tr": "Yolda"},
            "arrived":    {"ar": "وصل",         "en": "Arrived",     "tr": "Vardı"},
            "customs":    {"ar": "جمارك",       "en": "Customs",     "tr": "Gümrük"},
            "delivered":  {"ar": "تم التسليم", "en": "Delivered",   "tr": "Teslim Edildi"},
            "hold":       {"ar": "محتجز",       "en": "On Hold",     "tr": "Beklemede"},
        }
        return _labels.get(status, {}).get(lang, status)

    def _company_name(self) -> str:
        try:
            from core.settings_manager import SettingsManager
            return SettingsManager.get_instance().get("company_name", "") or ""
        except Exception:
            return ""

    def _render(self, html: str, out_path: Optional[str],
                prefix: str = "container_") -> tuple[bool, str, str]:
        if not out_path:
            tmp_dir  = tempfile.gettempdir()
            out_path = os.path.join(
                tmp_dir,
                f"{prefix}{date.today().strftime('%Y%m%d')}.pdf",
            )
        from services.pdf_renderer import render_html_to_pdf
        ok, info = render_html_to_pdf(html, out_path)
        if ok:
            return True, out_path, ""
        return False, "", info.get("error", "PDF render failed")


# ── module helpers ────────────────────────────────────────────────────────────

def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _s(obj, attr: str) -> str:
    val = _get(obj, attr)
    return str(val) if val else ""


def _extract_name(obj, lang: str) -> str:
    if not obj:
        return ""
    if lang == "ar":
        return getattr(obj, "name_ar", None) or getattr(obj, "name_en", None) or ""
    elif lang == "tr":
        return getattr(obj, "name_tr", None) or getattr(obj, "name_ar", None) or ""
    return getattr(obj, "name_en", None) or getattr(obj, "name_ar", None) or ""


def _calc_eta_state(eta, status: str) -> str:
    if not eta or status not in _ACTIVE_STATUSES:
        return ""
    from datetime import date as _d
    today = _d.today()
    try:
        delta = (eta - today).days
    except Exception:
        return ""
    if delta < 0:  return "overdue"
    if delta == 0: return "today"
    if delta <= 3: return "soon"
    return ""