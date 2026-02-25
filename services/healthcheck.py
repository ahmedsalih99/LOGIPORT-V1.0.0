from __future__ import annotations
from dataclasses import dataclass


@dataclass
class HealthReport:
    playwright: bool
    weasyprint_stack: bool
    cairo: bool = False
    pango: bool = False
    gdk_pixbuf: bool = False
    message: str = ""


def _try_import(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def _check_weasyprint_stack() -> bool:
    weasy = _try_import("weasyprint")
    cairo = _try_import("cairocffi") or _try_import("cairo")
    pango = _try_import("pangocffi") or _try_import("pango")
    gdk   = _try_import("PIL.Image")

    return weasy and cairo and pango and gdk


def _check_playwright() -> bool:
    return _try_import("playwright")


def check_pdf_runtime() -> HealthReport:
    playwright_ok = _check_playwright()
    weasy_ok      = _try_import("weasyprint")
    cairo_ok      = _try_import("cairocffi") or _try_import("cairo")
    pango_ok      = _try_import("pangocffi") or _try_import("pango")
    gdk_ok        = _try_import("PIL.Image")
    stack_ok      = weasy_ok and cairo_ok and pango_ok and gdk_ok

    if playwright_ok:
        msg = "Playwright available (primary PDF engine)."
    elif stack_ok:
        msg = "Playwright missing. Using WeasyPrint fallback."
    else:
        msg = "No PDF engine available. Install Playwright or complete WeasyPrint stack."

    return HealthReport(
        playwright=playwright_ok,
        weasyprint_stack=stack_ok,
        cairo=cairo_ok,
        pango=pango_ok,
        gdk_pixbuf=gdk_ok,
        message=msg,
    )