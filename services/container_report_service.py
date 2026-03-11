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
        """
        يولّد بطاقة كونتينر واحد PDF.
        Returns: (ok, path, error_message)
        """
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
        """
        يولّد قائمة كونتينرات PDF (landscape).
        Returns: (ok, path, error_message)
        """
        try:
            html = self._build_list_html(containers, lang, filters)
            return self._render(html, out_path, prefix="containers_list_")
        except Exception as e:
            logger.error("ContainerReportService.render_list: %s", e, exc_info=True)
            return False, "", str(e)

    # ── بناء HTML ─────────────────────────────────────────────────────────────

    def _build_card_html(self, container, lang: str) -> str:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        template_path = _TEMPLATES_DIR / "card"
        env = Environment(
            loader=FileSystemLoader(str(template_path)),
            autoescape=select_autoescape(["html"]),
        )
        tpl = env.get_template(f"{lang}.html")

        status = _get(container, "status") or "booked"
        client = _get(container, "client")
        tx     = _get(container, "transaction")

        client_name = ""
        if client:
            if lang == "ar":
                client_name = getattr(client, "name_ar", None) or getattr(client, "name_en", None) or ""
            elif lang == "tr":
                client_name = getattr(client, "name_tr", None) or getattr(client, "name_ar", None) or ""
            else:
                client_name = getattr(client, "name_en", None) or getattr(client, "name_ar", None) or ""

        transaction_no = ""
        if tx:
            transaction_no = getattr(tx, "transaction_no", None) or str(_get(container, "transaction_id") or "")

        entries = getattr(container, "entries", None) or []
        entries_data = []
        for e in entries:
            e_client = getattr(e, "owner_client", None)
            e_client_name = ""
            if e_client:
                if lang == "ar":
                    e_client_name = getattr(e_client, "name_ar", None) or ""
                elif lang == "tr":
                    e_client_name = getattr(e_client, "name_tr", None) or getattr(e_client, "name_ar", None) or ""
                else:
                    e_client_name = getattr(e_client, "name_en", None) or getattr(e_client, "name_ar", None) or ""
            entries_data.append({
                "id":          _get(e, "id"),
                "entry_no":    _get(e, "entry_no") or "",
                "entry_date":  str(_get(e, "entry_date") or ""),
                "client_name": e_client_name,
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
        return tpl.render(**ctx)

    def _build_list_html(self, containers: list, lang: str, filters: str) -> str:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        template_path = _TEMPLATES_DIR / "list"
        env = Environment(
            loader=FileSystemLoader(str(template_path)),
            autoescape=select_autoescape(["html"]),
        )
        tpl = env.get_template(f"{lang}.html")

        rows = []
        status_counts: dict[str, int] = {}
        for c in containers:
            status = _get(c, "status") or "booked"
            status_counts[status] = status_counts.get(status, 0) + 1
            client = _get(c, "client")
            client_name = ""
            if client:
                if lang == "ar":
                    client_name = getattr(client, "name_ar", None) or ""
                elif lang == "tr":
                    client_name = getattr(client, "name_tr", None) or getattr(client, "name_ar", None) or ""
                else:
                    client_name = getattr(client, "name_en", None) or getattr(client, "name_ar", None) or ""
            entries = getattr(c, "entries", None) or []
            rows.append({
                **_container_to_dict(c),
                "client_name":   client_name,
                "entries_count": len(entries),
                "status_color":  _STATUS_COLOR.get(status, "#888"),
                "status_label":  self._status_label(status, lang),
            })

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
        return tpl.render(**ctx)

    # ── ترجمة الحالة ─────────────────────────────────────────────────────────

    def _status_label(self, status: str, lang: str) -> str:
        _labels = {
            "booked":     {"ar": "محجوز",      "en": "Booked",     "tr": "Rezerve"},
            "loaded":     {"ar": "محمّل",       "en": "Loaded",     "tr": "Yüklendi"},
            "in_transit": {"ar": "في الطريق",   "en": "In Transit", "tr": "Yolda"},
            "arrived":    {"ar": "وصل",         "en": "Arrived",    "tr": "Vardı"},
            "customs":    {"ar": "جمارك",       "en": "Customs",    "tr": "Gümrük"},
            "delivered":  {"ar": "تم التسليم",  "en": "Delivered",  "tr": "Teslim Edildi"},
            "hold":       {"ar": "محتجز",       "en": "On Hold",    "tr": "Beklemede"},
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


def _container_to_dict(c) -> dict:
    """يحوّل ORM object → dict بيانات خام للـ template."""
    def _s(attr):
        val = _get(c, attr)
        return str(val) if val else ""

    return {
        "container_no":     _s("container_no"),
        "bl_number":        _s("bl_number"),
        "booking_no":       _s("booking_no"),
        "shipping_line":    _s("shipping_line"),
        "vessel_name":      _s("vessel_name"),
        "voyage_no":        _s("voyage_no"),
        "port_of_loading":  _s("port_of_loading"),
        "port_of_discharge":_s("port_of_discharge"),
        "final_destination":_s("final_destination"),
        "etd":              _s("etd"),
        "eta":              _s("eta"),
        "atd":              _s("atd"),
        "ata":              _s("ata"),
        "customs_date":     _s("customs_date"),
        "delivery_date":    _s("delivery_date"),
        "status":           _s("status"),
        "notes":            _s("notes"),
    }