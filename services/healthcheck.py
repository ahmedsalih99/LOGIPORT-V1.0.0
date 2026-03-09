"""
LOGIPORT – Health Check Service
================================
Checks availability of PDF rendering engines.
Primary: QtWebEngine (bundled with PySide6)
Fallback: WeasyPrint stack
"""
from dataclasses import dataclass, field


@dataclass
class HealthReport:
    qtwebengine:      bool = False
    weasyprint_stack: bool = False
    cairo:            bool = False
    pango:            bool = False
    gdk_pixbuf:       bool = False
    # kept for backward compat — always False
    playwright:       bool = False
    message:          str  = ""


def _try_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def _check_qtwebengine() -> bool:
    try:
        from PySide6.QtWebEngineCore import QWebEnginePage  # noqa: F401
        return True
    except Exception:
        return False


def _check_weasyprint_stack() -> bool:
    weasy = _try_import("weasyprint")
    cairo = _try_import("cairocffi") or _try_import("cairo")
    pango = _try_import("pangocffi") or _try_import("pango")
    gdk   = _try_import("gi.repository.GdkPixbuf")
    return weasy and cairo and pango and gdk


def check_pdf_runtime() -> HealthReport:
    qtwe  = _check_qtwebengine()
    weasy = _try_import("weasyprint")
    cairo = _try_import("cairocffi") or _try_import("cairo")
    pango = _try_import("pangocffi") or _try_import("pango")
    gdk   = _try_import("gi.repository.GdkPixbuf")
    stack = weasy and cairo and pango and gdk

    if qtwe:
        msg = "QtWebEngine available (primary PDF engine)."
    elif stack:
        msg = "QtWebEngine missing. Using WeasyPrint fallback."
    else:
        msg = "No PDF engine available. PySide6.QtWebEngineCore is required."

    return HealthReport(
        qtwebengine      = qtwe,
        weasyprint_stack = stack,
        cairo            = cairo,
        pango            = pango,
        gdk_pixbuf       = gdk,
        playwright       = False,
        message          = msg,
    )